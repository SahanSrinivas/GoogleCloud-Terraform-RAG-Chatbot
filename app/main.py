"""FastAPI application for GCP RAG Chatbot."""

import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import get_settings
from app.document_processor import get_document_processor
from app.rag_chain import get_rag_chain, clear_session

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: Initialize document processor and index PDF
    print("Starting up GCP Knowledge Assistant...")
    processor = get_document_processor()

    pdf_path = settings.pdf_path
    if os.path.exists(pdf_path):
        count = processor.process_and_store_pdf(pdf_path)
        print(f"Document processor ready with {count} chunks indexed")
    else:
        print(f"Warning: PDF not found at {pdf_path}")

    yield

    # Shutdown
    print("Shutting down GCP Knowledge Assistant...")


app = FastAPI(
    title=settings.app_title,
    description="A RAG-based chatbot for Google Cloud Platform documentation",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class ChatRequest(BaseModel):
    """Chat request model."""

    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response model."""

    answer: str
    session_id: str
    sources_count: int


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    documents_indexed: int


# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    processor = get_document_processor()
    return HealthResponse(
        status="healthy",
        documents_indexed=processor.get_document_count(),
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint for asking questions about GCP.

    Send a message and get a response based on the GCP documentation.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())

    try:
        rag_chain = get_rag_chain(session_id)
        result = rag_chain.query(request.message)

        return ChatResponse(
            answer=result["answer"],
            session_id=session_id,
            sources_count=result["context_used"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


@app.post("/clear-history")
async def clear_history(session_id: Optional[str] = None):
    """Clear conversation history for a session."""
    sid = session_id or "default"
    clear_session(sid)
    return {"status": "success", "message": f"History cleared for session {sid}"}


@app.get("/stats")
async def get_stats():
    """Get statistics about the indexed documents."""
    processor = get_document_processor()
    return {
        "documents_indexed": processor.get_document_count(),
        "collection_name": settings.collection_name,
    }


# Serve the frontend
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the chat interface."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GCP & Terraform Assistant</title>

    <!-- Favicon -->
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Cdefs%3E%3ClinearGradient id='grad' x1='0%25' y1='0%25' x2='100%25' y2='100%25'%3E%3Cstop offset='0%25' style='stop-color:%23FF8C42'/%3E%3Cstop offset='100%25' style='stop-color:%23FF6B35'/%3E%3C/linearGradient%3E%3C/defs%3E%3Ccircle cx='50' cy='50' r='45' fill='url(%23grad)'/%3E%3Cpath d='M30 45 Q50 25 70 45 Q50 65 30 45' fill='white' opacity='0.9'/%3E%3Ccircle cx='50' cy='58' r='8' fill='white' opacity='0.9'/%3E%3C/svg%3E">

    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>

    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        orange: {
                            50: '#FFF7ED',
                            100: '#FFEDD5',
                            200: '#FED7AA',
                            300: '#FDBA74',
                            400: '#FB923C',
                            500: '#F97316',
                            600: '#EA580C',
                            700: '#C2410C',
                        },
                        warm: {
                            50: '#FFFBF5',
                            100: '#FFF5EB',
                            200: '#FFECD9',
                        }
                    },
                    fontFamily: {
                        sans: ['NeutraAlt', 'Outfit', 'system-ui', 'sans-serif'],
                    },
                }
            }
        }
    </script>

    <style>
        * {
            font-family: 'NeutraAlt', 'Outfit', system-ui, sans-serif;
        }

        body {
            background: linear-gradient(135deg, #FFF7ED 0%, #FFEDD5 50%, #FEF3C7 100%);
            min-height: 100vh;
        }

        .chat-container {
            height: calc(100vh - 280px);
            min-height: 400px;
        }

        .glass-card {
            background: rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.3);
            box-shadow: 0 8px 32px rgba(249, 115, 22, 0.1),
                        0 2px 8px rgba(0, 0, 0, 0.05);
        }

        .message-content pre {
            background: #282c34;
            border-radius: 12px;
            padding: 16px;
            overflow-x: auto;
            margin: 12px 0;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .message-content pre code {
            font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
            font-size: 0.875rem;
            color: #abb2bf;
            background: transparent;
        }

        .message-content code {
            font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
            font-size: 0.875rem;
            background: rgba(249, 115, 22, 0.1);
            color: #c7254e;
            padding: 2px 6px;
            border-radius: 4px;
        }

        /* Syntax highlighting colors */
        .message-content pre .hljs-keyword,
        .message-content pre .hljs-selector-tag { color: #c678dd; }
        .message-content pre .hljs-string,
        .message-content pre .hljs-attr { color: #98c379; }
        .message-content pre .hljs-number { color: #d19a66; }
        .message-content pre .hljs-comment { color: #5c6370; font-style: italic; }
        .message-content pre .hljs-function { color: #61afef; }
        .message-content pre .hljs-title { color: #61afef; }
        .message-content pre .hljs-params { color: #abb2bf; }
        .message-content pre .hljs-built_in { color: #e5c07b; }
        .message-content pre .hljs-literal { color: #56b6c2; }
        .message-content pre .hljs-type { color: #e5c07b; }
        .message-content pre .hljs-variable { color: #e06c75; }
        .message-content pre .hljs-name { color: #e06c75; }
        .message-content pre .hljs-selector-class { color: #e5c07b; }
        .message-content pre .hljs-selector-id { color: #61afef; }
        .message-content pre .hljs-attribute { color: #d19a66; }

        .message-content p {
            margin-bottom: 0.75rem;
            line-height: 1.7;
        }

        .message-content ul, .message-content ol {
            margin-left: 1.5rem;
            margin-top: 0.5rem;
            margin-bottom: 0.75rem;
        }

        .message-content li {
            margin-bottom: 0.375rem;
            line-height: 1.6;
        }

        .message-content h1, .message-content h2, .message-content h3 {
            font-weight: 600;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
            color: #1e293b;
        }

        .ai-message {
            background: linear-gradient(135deg, #ffffff 0%, #FFF7ED 100%);
            border: 1px solid rgba(249, 115, 22, 0.15);
        }

        .user-message {
            background: linear-gradient(135deg, #F97316 0%, #EA580C 100%);
        }

        .typing-indicator span {
            animation: bounce 1.4s infinite ease-in-out;
        }
        .typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
        .typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .message-fade-in {
            animation: fadeIn 0.3s ease-out;
        }

        .send-btn {
            background: linear-gradient(135deg, #F97316 0%, #EA580C 100%);
            transition: all 0.3s ease;
        }

        .send-btn:hover:not(:disabled) {
            background: linear-gradient(135deg, #EA580C 0%, #C2410C 100%);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(249, 115, 22, 0.4);
        }

        .send-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

        .example-btn {
            background: rgba(255, 255, 255, 0.7);
            border: 1px solid rgba(249, 115, 22, 0.2);
            transition: all 0.2s ease;
        }

        .example-btn:hover {
            background: rgba(249, 115, 22, 0.1);
            border-color: rgba(249, 115, 22, 0.4);
            transform: translateY(-2px);
        }

        .input-field {
            background: rgba(255, 255, 255, 0.9);
            border: 2px solid rgba(249, 115, 22, 0.2);
            transition: all 0.3s ease;
        }

        .input-field:focus {
            border-color: #F97316;
            box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.1);
            outline: none;
        }

        .avatar-ai {
            background: linear-gradient(135deg, #F97316 0%, #EA580C 100%);
            box-shadow: 0 2px 8px rgba(249, 115, 22, 0.3);
        }

        .avatar-user {
            background: linear-gradient(135deg, #64748b 0%, #475569 100%);
        }

        .header-gradient {
            background: linear-gradient(90deg, #F97316 0%, #EA580C 50%, #F97316 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            background-size: 200% auto;
        }

        /* Custom scrollbar */
        .chat-container::-webkit-scrollbar {
            width: 6px;
        }

        .chat-container::-webkit-scrollbar-track {
            background: rgba(249, 115, 22, 0.05);
            border-radius: 3px;
        }

        .chat-container::-webkit-scrollbar-thumb {
            background: rgba(249, 115, 22, 0.3);
            border-radius: 3px;
        }

        .chat-container::-webkit-scrollbar-thumb:hover {
            background: rgba(249, 115, 22, 0.5);
        }

        .logo-icon {
            filter: drop-shadow(0 2px 4px rgba(249, 115, 22, 0.3));
        }
    </style>
</head>
<body class="text-gray-800">
    <div class="container mx-auto px-4 py-8 max-w-4xl">
        <!-- Header -->
        <div class="text-center mb-8">
            <div class="flex items-center justify-center gap-3 mb-3">
                <svg class="w-12 h-12 logo-icon" viewBox="0 0 100 100">
                    <defs>
                        <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" style="stop-color:#F97316"/>
                            <stop offset="100%" style="stop-color:#EA580C"/>
                        </linearGradient>
                    </defs>
                    <circle cx="50" cy="50" r="45" fill="url(#logoGrad)"/>
                    <path d="M30 45 Q50 25 70 45 Q50 65 30 45" fill="white" opacity="0.95"/>
                    <circle cx="50" cy="58" r="8" fill="white" opacity="0.95"/>
                </svg>
                <h1 class="text-4xl font-bold header-gradient">GCP &amp; Terraform Assistant</h1>
            </div>
            <p class="text-gray-500 text-lg">Ask me anything about GCP & Terraform</p>
        </div>

        <!-- Chat Container -->
        <div class="glass-card rounded-2xl overflow-hidden">
            <!-- Chat Header -->
            <div class="bg-gradient-to-r from-orange-500 to-orange-400 px-6 py-4">
                <div class="flex items-center gap-3">
                    <div class="w-3 h-3 bg-white rounded-full animate-pulse"></div>
                    <span class="text-white font-medium">AI Assistant Online</span>
                </div>
            </div>

            <!-- Messages Area -->
            <div id="chat-messages" class="chat-container overflow-y-auto p-6 space-y-5 bg-gradient-to-b from-warm-50 to-white">
                <!-- Welcome Message -->
                <div class="flex items-start gap-4 message-fade-in">
                    <div class="w-10 h-10 rounded-xl avatar-ai flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
                        AI
                    </div>
                    <div class="flex-1 ai-message rounded-2xl rounded-tl-md p-5 shadow-sm">
                        <p class="text-gray-700 font-medium mb-3">
                            Hello! I'm <span class="font-bold text-orange-600">Gippy</span>, your GCP & Terraform Assistant. I can help you with:
                        </p>
                        <ul class="text-gray-600 space-y-2">
                            <li class="flex items-center gap-2">
                                <span class="w-2 h-2 bg-orange-400 rounded-full"></span>
                                Google Cloud Platform services & architecture
                            </li>
                            <li class="flex items-center gap-2">
                                <span class="w-2 h-2 bg-orange-400 rounded-full"></span>
                                Terraform infrastructure as code
                            </li>
                            <li class="flex items-center gap-2">
                                <span class="w-2 h-2 bg-orange-400 rounded-full"></span>
                                Cloud deployment & best practices
                            </li>
                            <li class="flex items-center gap-2">
                                <span class="w-2 h-2 bg-orange-400 rounded-full"></span>
                                DevOps & automation strategies
                            </li>
                        </ul>
                        <p class="mt-4 text-gray-700">What would you like to know?</p>
                    </div>
                </div>
            </div>

            <!-- Input Area -->
            <div class="border-t border-orange-100 p-5 bg-white">
                <form id="chat-form" class="flex gap-3">
                    <input
                        type="text"
                        id="message-input"
                        placeholder="Ask about GCP, Terraform, Cloud Run, deployments..."
                        class="flex-1 input-field rounded-xl px-5 py-4 text-gray-700"
                        autocomplete="off"
                    >
                    <button
                        type="submit"
                        id="send-button"
                        class="send-btn text-white px-8 py-4 rounded-xl font-semibold flex items-center gap-2"
                    >
                        <span>Send</span>
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/>
                        </svg>
                    </button>
                </form>
                <div class="mt-3 flex justify-between items-center">
                    <span id="status" class="text-sm text-gray-400"></span>
                    <button
                        id="clear-btn"
                        class="text-sm text-orange-500 hover:text-orange-600 font-medium transition-colors flex items-center gap-1"
                    >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                        </svg>
                        Clear conversation
                    </button>
                </div>
            </div>
        </div>

        <!-- Example Questions -->
        <div class="mt-8">
            <p class="text-gray-500 text-sm mb-3 font-medium">Quick questions to get started:</p>
            <div class="flex flex-wrap gap-3">
                <button class="example-btn text-gray-600 px-4 py-2 rounded-full text-sm font-medium">
                    What is Cloud Run?
                </button>
                <button class="example-btn text-gray-600 px-4 py-2 rounded-full text-sm font-medium">
                    How to deploy using Terraform?
                </button>
                <button class="example-btn text-gray-600 px-4 py-2 rounded-full text-sm font-medium">
                    Explain Compute Engine
                </button>
                <button class="example-btn text-gray-600 px-4 py-2 rounded-full text-sm font-medium">
                    GCP best practices
                </button>
            </div>
        </div>

        <!-- Footer -->
        <div class="mt-8 text-center">
            <a href="https://github.com/SahanSrinivas" target="_blank" rel="noopener noreferrer"
               class="inline-flex items-center gap-2 text-gray-500 hover:text-orange-500 transition-colors text-sm font-medium">
                <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path fill-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clip-rule="evenodd"/>
                </svg>
                <span>SahanSrinivas</span>
            </a>
        </div>
    </div>

    <script>
        // Session management
        let sessionId = localStorage.getItem('gcp-chat-session') || null;

        // DOM elements
        const chatMessages = document.getElementById('chat-messages');
        const chatForm = document.getElementById('chat-form');
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-button');
        const statusEl = document.getElementById('status');
        const clearBtn = document.getElementById('clear-btn');
        const exampleBtns = document.querySelectorAll('.example-btn');

        // Configure marked for markdown rendering
        marked.setOptions({
            highlight: function(code, lang) {
                if (lang && hljs.getLanguage(lang)) {
                    return hljs.highlight(code, { language: lang }).value;
                }
                return hljs.highlightAuto(code).value;
            },
            breaks: true
        });

        // Add message to chat
        function addMessage(content, isUser = false, isTyping = false) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'flex items-start gap-4 message-fade-in';

            if (isUser) {
                messageDiv.innerHTML = `
                    <div class="flex-1"></div>
                    <div class="max-w-[80%] user-message rounded-2xl rounded-tr-md p-5 shadow-sm">
                        <p class="text-white">${escapeHtml(content)}</p>
                    </div>
                    <div class="w-10 h-10 rounded-xl avatar-user flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
                        You
                    </div>
                `;
            } else if (isTyping) {
                messageDiv.innerHTML = `
                    <div class="w-10 h-10 rounded-xl avatar-ai flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
                        AI
                    </div>
                    <div class="ai-message rounded-2xl rounded-tl-md p-5 shadow-sm">
                        <div class="typing-indicator flex gap-1">
                            <span class="w-2.5 h-2.5 bg-orange-400 rounded-full"></span>
                            <span class="w-2.5 h-2.5 bg-orange-400 rounded-full"></span>
                            <span class="w-2.5 h-2.5 bg-orange-400 rounded-full"></span>
                        </div>
                    </div>
                `;
                messageDiv.id = 'typing-indicator';
            } else {
                messageDiv.innerHTML = `
                    <div class="w-10 h-10 rounded-xl avatar-ai flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
                        AI
                    </div>
                    <div class="flex-1 ai-message rounded-2xl rounded-tl-md p-5 shadow-sm message-content text-gray-700">
                        ${marked.parse(content)}
                    </div>
                `;
            }

            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;

            // Apply syntax highlighting
            if (!isUser && !isTyping) {
                messageDiv.querySelectorAll('pre code').forEach((block) => {
                    hljs.highlightElement(block);
                });
            }

            return messageDiv;
        }

        // Remove typing indicator
        function removeTypingIndicator() {
            const typing = document.getElementById('typing-indicator');
            if (typing) typing.remove();
        }

        // Escape HTML
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Send message
        async function sendMessage(message) {
            if (!message.trim()) return;

            // Add user message
            addMessage(message, true);
            messageInput.value = '';
            sendButton.disabled = true;
            statusEl.textContent = 'Thinking...';

            // Show typing indicator
            addMessage('', false, true);

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        message: message,
                        session_id: sessionId
                    }),
                });

                removeTypingIndicator();

                if (!response.ok) {
                    throw new Error('Failed to get response');
                }

                const data = await response.json();

                // Save session ID
                sessionId = data.session_id;
                localStorage.setItem('gcp-chat-session', sessionId);

                // Add AI response
                addMessage(data.answer);
                statusEl.textContent = `Referenced ${data.sources_count} document sections`;

            } catch (error) {
                removeTypingIndicator();
                addMessage('Sorry, I encountered an error. Please try again.');
                statusEl.textContent = 'Error occurred';
                console.error('Error:', error);
            } finally {
                sendButton.disabled = false;
                messageInput.focus();
            }
        }

        // Clear conversation
        async function clearConversation() {
            if (sessionId) {
                await fetch(`/clear-history?session_id=${sessionId}`, { method: 'POST' });
            }

            // Clear UI
            chatMessages.innerHTML = '';

            // Add welcome message back
            addMessage(`Hello! I'm Gippy, your GCP & Terraform Assistant. How can I help you today?`);

            // Generate new session
            sessionId = null;
            localStorage.removeItem('gcp-chat-session');
            statusEl.textContent = 'Conversation cleared';
        }

        // Event listeners
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            sendMessage(messageInput.value);
        });

        clearBtn.addEventListener('click', clearConversation);

        exampleBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                sendMessage(btn.textContent.trim());
            });
        });

        // Focus input on load
        messageInput.focus();
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
