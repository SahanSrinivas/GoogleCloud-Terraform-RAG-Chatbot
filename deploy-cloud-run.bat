@echo off
REM GCP Cloud Run Deployment Script for Windows
REM =============================================
REM Make sure you have:
REM 1. Google Cloud SDK installed (gcloud)
REM 2. Docker installed
REM 3. Authenticated with GCP: gcloud auth login
REM 4. Set your project: gcloud config set project YOUR_PROJECT_ID

setlocal enabledelayedexpansion

REM Configuration - Update these values
set PROJECT_ID=your-project-id
set REGION=us-central1
set SERVICE_NAME=gcp-knowledge-assistant
set REPO_NAME=cloud-run-images

REM Artifact Registry image path
set IMAGE_NAME=%REGION%-docker.pkg.dev/%PROJECT_ID%/%REPO_NAME%/%SERVICE_NAME%

echo ==========================================
echo GCP Cloud Run Deployment
echo ==========================================
echo Project: %PROJECT_ID%
echo Region: %REGION%
echo Service: %SERVICE_NAME%
echo Repository: %REPO_NAME%
echo Image: %IMAGE_NAME%
echo ==========================================

REM Check if ANTHROPIC_API_KEY is set
if "%ANTHROPIC_API_KEY%"=="" (
    echo Error: ANTHROPIC_API_KEY environment variable is not set
    echo Please set it: set ANTHROPIC_API_KEY=your_api_key
    exit /b 1
)

REM Enable required APIs
echo Enabling required GCP APIs...
call gcloud services enable artifactregistry.googleapis.com --project=%PROJECT_ID%
call gcloud services enable run.googleapis.com --project=%PROJECT_ID%

REM Create Artifact Registry repository (if it doesn't exist)
echo Creating Artifact Registry repository...
call gcloud artifacts repositories create %REPO_NAME% ^
    --repository-format=docker ^
    --location=%REGION% ^
    --description="Docker images for Cloud Run" ^
    --project=%PROJECT_ID% 2>nul || echo Repository already exists, continuing...

REM Configure Docker to use Artifact Registry
echo Configuring Docker authentication for Artifact Registry...
call gcloud auth configure-docker %REGION%-docker.pkg.dev --quiet

REM Build the Docker image
echo Building Docker image...
docker build -t %IMAGE_NAME%:latest .

REM Push to Artifact Registry
echo Pushing image to Artifact Registry...
docker push %IMAGE_NAME%:latest

REM Deploy to Cloud Run
echo Deploying to Cloud Run...
call gcloud run deploy %SERVICE_NAME% ^
    --image %IMAGE_NAME%:latest ^
    --platform managed ^
    --region %REGION% ^
    --allow-unauthenticated ^
    --memory 2Gi ^
    --cpu 2 ^
    --timeout 300 ^
    --set-env-vars "ANTHROPIC_API_KEY=%ANTHROPIC_API_KEY%" ^
    --project %PROJECT_ID%

REM Get the service URL
echo ==========================================
echo Deployment Complete!
echo ==========================================
call gcloud run services describe %SERVICE_NAME% --platform managed --region %REGION% --project %PROJECT_ID% --format "value(status.url)"
echo ==========================================

endlocal
