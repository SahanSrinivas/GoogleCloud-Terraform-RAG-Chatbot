#!/bin/bash

# GCP Cloud Run Deployment Script
# ================================
# Make sure you have:
# 1. Google Cloud SDK installed (gcloud)
# 2. Docker installed
# 3. Authenticated with GCP: gcloud auth login
# 4. Set your project: gcloud config set project YOUR_PROJECT_ID

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="gcp-knowledge-assistant"
REPO_NAME="cloud-run-images"

# Artifact Registry image path
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${SERVICE_NAME}"

echo "=========================================="
echo "GCP Cloud Run Deployment"
echo "=========================================="
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo "Repository: ${REPO_NAME}"
echo "Image: ${IMAGE_NAME}"
echo "=========================================="

# Check if ANTHROPIC_API_KEY is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "Error: ANTHROPIC_API_KEY environment variable is not set"
    echo "Please set it: export ANTHROPIC_API_KEY=your_api_key"
    exit 1
fi

# Enable required APIs
echo "Enabling required GCP APIs..."
gcloud services enable artifactregistry.googleapis.com --project="${PROJECT_ID}"
gcloud services enable run.googleapis.com --project="${PROJECT_ID}"

# Create Artifact Registry repository (if it doesn't exist)
echo "Creating Artifact Registry repository..."
gcloud artifacts repositories create "${REPO_NAME}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="Docker images for Cloud Run" \
    --project="${PROJECT_ID}" 2>/dev/null || echo "Repository already exists, continuing..."

# Configure Docker to use Artifact Registry
echo "Configuring Docker authentication for Artifact Registry..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# Build the Docker image
echo "Building Docker image..."
docker build -t "${IMAGE_NAME}:latest" .

# Push to Artifact Registry
echo "Pushing image to Artifact Registry..."
docker push "${IMAGE_NAME}:latest"

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image "${IMAGE_NAME}:latest" \
    --platform managed \
    --region "${REGION}" \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --set-env-vars "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}" \
    --project "${PROJECT_ID}"

# Get the service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --platform managed \
    --region "${REGION}" \
    --project "${PROJECT_ID}" \
    --format 'value(status.url)')

echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo "Service URL: ${SERVICE_URL}"
echo "=========================================="
