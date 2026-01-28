# Gippy - GCP & Terraform Assistant

A RAG (Retrieval-Augmented Generation) chatbot that answers questions about Google Cloud Platform and Terraform using a PDF knowledge base. Built with FastAPI, ChromaDB, and Claude AI.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Claude](https://img.shields.io/badge/Claude-API-purple)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)
![Cloud Run](https://img.shields.io/badge/Cloud%20Run-Deployed-orange)

## Features

- **RAG-powered Q&A**: Uses vector similarity search to find relevant context from PDF documents
- **Claude AI Integration**: Generates intelligent responses using Anthropic's Claude API
- **Memory-Optimized**: Handles large PDFs with streaming and batch processing
- **Modern UI**: Glassmorphism design with light orange theme
- **Session Management**: Maintains conversation history per user session
- **Cloud-Ready**: Dockerized for easy deployment to Google Cloud Run

## Architecture

```
┌─────────────┐     ┌──────────────────────────────────────────────────┐
│             │     │              Google Cloud Run                     │
│   Browser   │────▶│  ┌─────────┐  ┌──────────────┐  ┌─────────────┐  │
│  (Chat UI)  │     │  │ FastAPI │──│  RAG Chain   │──│  Claude API │  │
│             │◀────│  └────┬────┘  └──────┬───────┘  └─────────────┘  │
└─────────────┘     │       │              │                            │
                    │       ▼              ▼                            │
                    │  ┌─────────┐  ┌──────────────┐                    │
                    │  │Document │  │   ChromaDB   │                    │
                    │  │Processor│  │(Vector Store)│                    │
                    │  └────┬────┘  └──────────────┘                    │
                    │       │                                           │
                    │       ▼                                           │
                    │  ┌─────────────────────┐                          │
                    │  │ Sentence Transformers│                          │
                    │  │  (all-MiniLM-L6-v2) │                          │
                    │  └─────────────────────┘                          │
                    └──────────────────────────────────────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI + Uvicorn |
| Vector Database | ChromaDB (PersistentClient) |
| Embeddings | Sentence Transformers (all-MiniLM-L6-v2) |
| LLM | Claude API (Anthropic) |
| PDF Processing | pypdf |
| Frontend | Embedded HTML + Tailwind CSS |
| Containerization | Docker |
| Deployment | Google Cloud Run |

## Project Structure

```
RAG-GCP-Sample-Demo/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app + Frontend
│   ├── config.py            # Settings & configuration
│   ├── document_processor.py # PDF processing & ChromaDB
│   └── rag_chain.py         # Claude API integration
├── Dockerfile
├── requirements.txt
├── deploy-cloud-run.bat     # Windows deployment script
├── deploy-cloud-run.sh      # Linux/Mac deployment script
├── architecture.drawio      # Architecture diagram
├── .env                     # Environment variables
└── Google Cloud Platform (GCP).pdf  # Knowledge base PDF
```

## Prerequisites

- Python 3.12+
- Docker Desktop
- Google Cloud SDK (gcloud CLI)
- Anthropic API Key
- GCP Project with billing enabled

## Local Development

### 1. Clone and Setup

```bash
cd RAG-GCP-Sample-Demo
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key
CLAUDE_MODEL=claude-sonnet-4-20250514
PORT=8080
```

### 3. Run Locally

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Visit `http://localhost:8080`

---

## Deploy to Google Cloud Run

### Step 1: Authenticate with Google Cloud

```bash
gcloud auth login
```

### Step 2: Set Your GCP Project

```bash
gcloud config set project YOUR_PROJECT_ID
```

### Step 3: Enable Required APIs

```bash
gcloud services enable artifactregistry.googleapis.com
gcloud services enable run.googleapis.com
```

### Step 4: Create Artifact Registry Repository (One-time)

```bash
gcloud artifacts repositories create cloud-run-images \
    --repository-format=docker \
    --location=us-central1 \
    --description="Docker images for Cloud Run"
```

### Step 5: Configure Docker Authentication

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
```

### Step 6: Build Docker Image

```bash
docker build -t us-central1-docker.pkg.dev/YOUR_PROJECT_ID/cloud-run-images/gcp-knowledge-assistant:latest .
```

### Step 7: Push to Artifact Registry

```bash
docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/cloud-run-images/gcp-knowledge-assistant:latest
```

### Step 8: Deploy to Cloud Run

```bash
gcloud run deploy gcp-knowledge-assistant \
    --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/cloud-run-images/gcp-knowledge-assistant:latest \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --min-instances 0 \
    --max-instances 3 \
    --port 8080 \
    --set-env-vars ANTHROPIC_API_KEY=YOUR_API_KEY
```

After deployment, you'll receive a URL like:
```
https://gcp-knowledge-assistant-xxxxx-uc.a.run.app
```

---

## Custom Domain Setup (mindflayer.cloud)

### Step 1: Verify Domain Ownership

```bash
gcloud domains verify mindflayer.cloud
```

This will open a browser to add a TXT record to your DNS. Add the verification record to your domain's DNS settings.

### Step 2: Set Default Region (Required)

```bash
gcloud config set run/region us-central1
```

### Step 3: Map Custom Domain to Cloud Run

> **Note:** Use `gcloud beta` for domain mapping commands.

```bash
gcloud beta run domain-mappings create \
    --service gcp-knowledge-assistant \
    --domain mindflayer.cloud \
    --region us-central1
```

Or for a subdomain (recommended):

```bash
gcloud beta run domain-mappings create \
    --service gcp-knowledge-assistant \
    --domain gippy.mindflayer.cloud \
    --region us-central1
```

### Step 4: Configure DNS Records

After running the domain mapping command, you'll get DNS records to add. Go to your domain registrar (where you bought mindflayer.cloud) and add:

**For apex domain (mindflayer.cloud):**

| Type | Name | Value |
|------|------|-------|
| A | @ | 216.239.32.21 |
| A | @ | 216.239.34.21 |
| A | @ | 216.239.36.21 |
| A | @ | 216.239.38.21 |
| AAAA | @ | 2001:4860:4802:32::15 |
| AAAA | @ | 2001:4860:4802:34::15 |
| AAAA | @ | 2001:4860:4802:36::15 |
| AAAA | @ | 2001:4860:4802:38::15 |

**For subdomain (gippy.mindflayer.cloud):**

| Type | Name | Value |
|------|------|-------|
| CNAME | gippy | ghs.googlehosted.com. |

### Step 5: Wait for SSL Certificate

Google Cloud automatically provisions an SSL certificate. Check status:

```bash
gcloud beta run domain-mappings describe \
    --domain gippy.mindflayer.cloud \
    --region us-central1
```

Wait until `certificateStatus` shows `ACTIVE` (can take 15-30 minutes).

### Step 6: Verify Domain is Working

```bash
curl -I https://mindflayer.cloud
# or
curl -I https://gippy.mindflayer.cloud
```

### Complete Custom Domain Commands Summary

```bash
# 1. Verify domain ownership
gcloud domains verify mindflayer.cloud

# 2. Set default region
gcloud config set run/region us-central1

# 3. Create domain mapping (use gcloud beta)
gcloud beta run domain-mappings create \
    --service gcp-knowledge-assistant \
    --domain gippy.mindflayer.cloud \
    --region us-central1

# 4. List domain mappings
gcloud beta run domain-mappings list --region us-central1

# 5. Check domain mapping status
gcloud beta run domain-mappings describe \
    --domain gippy.mindflayer.cloud \
    --region us-central1

# 6. Delete domain mapping (if needed)
gcloud beta run domain-mappings delete \
    --domain gippy.mindflayer.cloud \
    --region us-central1
```

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key | Yes |
| `CLAUDE_MODEL` | Claude model to use | No (default: claude-sonnet-4-20250514) |
| `PORT` | Server port | No (default: 8080) |

## Troubleshooting

### Docker not running
```
ERROR: error during connect: ... dockerDesktopLinuxEngine: The system cannot find the file specified
```
**Solution**: Start Docker Desktop and wait until it's fully running.

### Memory errors with large PDFs
The application uses memory-optimized processing with:
- Page-by-page PDF extraction
- Batch processing (50 chunks at a time)
- Garbage collection between batches

### Cloud Run cold starts
First request may be slow due to model loading. Consider:
- Setting `--min-instances 1` to keep one instance warm
- Note: This incurs additional costs

## License

MIT License

## Author

**Sahan Srinivas**
- GitHub: [@SahanSrinivas](https://github.com/SahanSrinivas)
