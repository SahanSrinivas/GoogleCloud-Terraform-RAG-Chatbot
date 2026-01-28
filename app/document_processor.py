"""PDF Document Processor and Vector Store Manager - Memory Optimized."""

import os
import gc
from typing import List, Optional, Generator
from pypdf import PdfReader
import chromadb
from sentence_transformers import SentenceTransformer
from app.config import get_settings

settings = get_settings()

# Batch size for processing to avoid memory issues
BATCH_SIZE = 50


class DocumentProcessor:
    """Handles PDF processing, chunking, and vector storage."""

    def __init__(self):
        print("[1/4] Loading embedding model...")
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

        # Use PersistentClient for persistent storage (new ChromaDB API)
        persist_dir = settings.chroma_persist_directory
        os.makedirs(persist_dir, exist_ok=True)

        print("[2/4] Initializing ChromaDB...")
        self.chroma_client = chromadb.PersistentClient(path=persist_dir)
        self.collection = None
        self._initialize_collection()

    def _initialize_collection(self):
        """Initialize or get the ChromaDB collection."""
        self.collection = self.chroma_client.get_or_create_collection(
            name=settings.collection_name,
            metadata={"description": "GCP Documentation"},
        )
        print(f"[3/4] Collection ready: {settings.collection_name}")

    def extract_pages_generator(self, pdf_path: str) -> Generator[tuple, None, None]:
        """Extract text from PDF page by page (memory efficient)."""
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        print(f"      PDF has {total_pages} pages")

        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text and page_text.strip():
                yield page_num + 1, page_text.strip()

            # Progress indicator every 50 pages
            if (page_num + 1) % 50 == 0:
                print(f"      Extracted {page_num + 1}/{total_pages} pages...")
                gc.collect()  # Free memory

    def chunk_text_simple(self, text: str, page_num: int, chunk_size: int = 800) -> List[dict]:
        """Simple chunking by splitting on sentences/paragraphs."""
        chunks = []

        # Split by paragraphs first
        paragraphs = text.split('\n\n')

        current_chunk = ""
        chunk_id = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If adding this paragraph exceeds chunk size, save current chunk
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                chunks.append({
                    "id": f"page{page_num}_chunk{chunk_id}",
                    "text": current_chunk.strip(),
                    "page": page_num,
                })
                chunk_id += 1
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        # Don't forget the last chunk
        if current_chunk.strip():
            chunks.append({
                "id": f"page{page_num}_chunk{chunk_id}",
                "text": current_chunk.strip(),
                "page": page_num,
            })

        return chunks

    def process_and_store_pdf(self, pdf_path: str) -> int:
        """Process a PDF and store chunks in vector database - memory optimized."""
        # Check if already processed
        if self.collection.count() > 0:
            print("Documents already indexed. Skipping processing.")
            return self.collection.count()

        print(f"[4/4] Processing PDF: {pdf_path}")

        all_chunks = []
        total_indexed = 0

        # Process page by page to save memory
        print("      Extracting and chunking pages...")
        for page_num, page_text in self.extract_pages_generator(pdf_path):
            page_chunks = self.chunk_text_simple(page_text, page_num)
            all_chunks.extend(page_chunks)

            # Process in batches to avoid memory issues
            if len(all_chunks) >= BATCH_SIZE:
                indexed = self._store_batch(all_chunks)
                total_indexed += indexed
                print(f"      Indexed batch: {total_indexed} chunks so far...")
                all_chunks = []
                gc.collect()  # Free memory

        # Store remaining chunks
        if all_chunks:
            indexed = self._store_batch(all_chunks)
            total_indexed += indexed

        print(f"      Total indexed: {total_indexed} chunks")
        gc.collect()
        return total_indexed

    def _store_batch(self, chunks: List[dict]) -> int:
        """Store a batch of chunks in the vector database."""
        if not chunks:
            return 0

        texts = [chunk["text"] for chunk in chunks]
        ids = [chunk["id"] for chunk in chunks]
        metadatas = [{"page": chunk["page"]} for chunk in chunks]

        # Generate embeddings
        embeddings = self.embedding_model.encode(texts, show_progress_bar=False)

        # Add to collection
        self.collection.add(
            ids=ids,
            embeddings=embeddings.tolist(),
            documents=texts,
            metadatas=metadatas,
        )

        return len(chunks)

    def search(self, query: str, n_results: int = None) -> List[dict]:
        """Search for relevant chunks based on query."""
        n_results = n_results or settings.max_context_chunks

        # Generate query embedding
        query_embedding = self.embedding_model.encode([query])[0]

        # Search in collection
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results,
            include=["documents", "distances", "metadatas"],
        )

        # Format results
        formatted_results = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                formatted_results.append(
                    {
                        "text": doc,
                        "distance": results["distances"][0][i]
                        if results["distances"]
                        else None,
                        "metadata": results["metadatas"][0][i]
                        if results["metadatas"]
                        else None,
                    }
                )

        return formatted_results

    def get_document_count(self) -> int:
        """Get the number of indexed documents."""
        return self.collection.count()


# Singleton instance
_processor: Optional[DocumentProcessor] = None


def get_document_processor() -> DocumentProcessor:
    """Get or create the document processor singleton."""
    global _processor
    if _processor is None:
        _processor = DocumentProcessor()
    return _processor
