"""RAG Chain with Claude API for answering questions."""

from typing import List, Optional
import anthropic
from app.config import get_settings
from app.document_processor import get_document_processor

settings = get_settings()


class RAGChain:
    """Retrieval-Augmented Generation chain using Claude."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.document_processor = get_document_processor()
        self.conversation_history: List[dict] = []

    def _build_system_prompt(self) -> str:
        """Build the system prompt for Claude."""
        return """You are a knowledgeable Google Cloud Platform (GCP) assistant. Your role is to help users understand GCP services, concepts, and best practices based on the provided documentation.

Guidelines:
1. Answer questions accurately based on the context provided from the GCP documentation.
2. If asked about a specific service (like Cloud Run, Compute Engine, etc.), provide:
   - A clear explanation of what it is
   - Key features and capabilities
   - Basic deployment/usage steps when relevant
   - Best practices if applicable
3. Keep answers concise but comprehensive. For technical topics, include practical examples.
4. If the context doesn't contain enough information to answer the question, say so honestly.
5. Format responses using markdown for better readability (use headers, bullet points, code blocks when appropriate).
6. When explaining deployment steps, be specific and actionable.

Remember: You are helping users understand GCP concepts and services. Be helpful, accurate, and practical."""

    def _build_context_prompt(self, context_chunks: List[dict]) -> str:
        """Build the context section from retrieved chunks."""
        if not context_chunks:
            return "No relevant context found in the documentation."

        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            context_parts.append(f"[Context {i}]\n{chunk['text']}")

        return "\n\n".join(context_parts)

    def query(
        self,
        question: str,
        include_history: bool = True,
        max_context_chunks: int = None,
    ) -> dict:
        """
        Process a user question and generate a response.

        Args:
            question: The user's question
            include_history: Whether to include conversation history
            max_context_chunks: Maximum number of context chunks to retrieve

        Returns:
            dict with 'answer', 'sources', and 'context_used'
        """
        max_chunks = max_context_chunks or settings.max_context_chunks

        # Retrieve relevant context
        relevant_chunks = self.document_processor.search(question, n_results=max_chunks)

        # Build the context
        context = self._build_context_prompt(relevant_chunks)

        # Build messages
        messages = []

        # Add conversation history if enabled
        if include_history and self.conversation_history:
            messages.extend(self.conversation_history[-6:])  # Last 3 exchanges

        # Add current question with context
        user_message = f"""Based on the following context from GCP documentation, please answer my question.

CONTEXT:
{context}

QUESTION: {question}

Please provide a helpful and accurate answer based on the context above. If you need to explain how to deploy or use something, include practical steps."""

        messages.append({"role": "user", "content": user_message})

        # Call Claude API
        response = self.client.messages.create(
            model=settings.claude_model,
            max_tokens=2048,
            system=self._build_system_prompt(),
            messages=messages,
        )

        answer = response.content[0].text

        # Update conversation history
        self.conversation_history.append({"role": "user", "content": question})
        self.conversation_history.append({"role": "assistant", "content": answer})

        # Keep history manageable
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

        return {
            "answer": answer,
            "sources": [
                {"text": chunk["text"][:200] + "...", "relevance": chunk.get("distance")}
                for chunk in relevant_chunks
            ],
            "context_used": len(relevant_chunks),
        }

    def clear_history(self):
        """Clear the conversation history."""
        self.conversation_history = []

    def get_history(self) -> List[dict]:
        """Get the conversation history."""
        return self.conversation_history


# Session-based RAG chains
_rag_chains: dict = {}


def get_rag_chain(session_id: str = "default") -> RAGChain:
    """Get or create a RAG chain for a session."""
    if session_id not in _rag_chains:
        _rag_chains[session_id] = RAGChain()
    return _rag_chains[session_id]


def clear_session(session_id: str = "default"):
    """Clear a session's RAG chain."""
    if session_id in _rag_chains:
        del _rag_chains[session_id]
