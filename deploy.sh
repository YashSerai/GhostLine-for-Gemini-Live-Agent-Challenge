#!/bin/bash
# deploy.sh
# Automated deployment script for Ghostline backend to Google Cloud Run
# 
# Usage:
#   ./deploy.sh [PROJECT_ID] [REGION]
#
# Examples:
#   ./deploy.sh
#   ./deploy.sh my-gcp-project us-central1

set -e

# Configuration
SERVICE_NAME="ghostline-backend"
DEFAULT_REGION="us-central1"

# Get project ID
PROJECT_ID=${1:-""}
if [ -z "$PROJECT_ID" ]; then
    echo "Fetching default Google Cloud Project..."
    PROJECT_ID=$(gcloud config get-value project)
    if [ -z "$PROJECT_ID" ]; then
        echo "Error: No project ID provided and no default GCP project configured."
        echo "Usage: ./deploy.sh [PROJECT_ID] [REGION]"
        exit 1
    fi
fi

# Get region
REGION=${2:-$DEFAULT_REGION}

echo "=========================================================="
echo " Deploying Ghostline Backend to Cloud Run"
echo "=========================================================="
echo " Project: $PROJECT_ID"
echo " Region:  $REGION"
echo " Service: $SERVICE_NAME"
echo "=========================================================="
echo ""

# Enable required APIs if not already enabled
echo "Ensuring required APIs are enabled..."
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    aiplatform.googleapis.com \
    firestore.googleapis.com \
    --project="$PROJECT_ID"

echo ""
echo "Building and deploying from source..."
cd server

# Deploy directly from source using Cloud Build
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --allow-unauthenticated \
    --port=8000 \
    --set-env-vars="APP_ENV=production,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION,VERTEX_AI_MODEL=gemini-live-2.5-flash-native-audio" \
    --min-instances=0 \
    --max-instances=10 \
    --memory=512Mi \
    --cpu=1

echo ""
echo "=========================================================="
echo " Deployment Complete!"
echo "=========================================================="
echo "Your backend is now running on Google Cloud Run."
echo "Make sure to update your VITE_SESSION_WS_URL in the client .env file"
echo "to point to the new wss://... URL provided above."
