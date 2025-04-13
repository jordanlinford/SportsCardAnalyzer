#!/bin/bash

# Exit on error
set -e

echo "🚀 Starting deployment process..."

# Check if all required environment variables are set
required_vars=(
    "FIREBASE_API_KEY"
    "FIREBASE_AUTH_DOMAIN"
    "FIREBASE_PROJECT_ID"
    "FIREBASE_STORAGE_BUCKET"
    "STRIPE_SECRET_KEY"
    "STRIPE_PUBLISHABLE_KEY"
    "STRIPE_WEBHOOK_SECRET"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Error: $var is not set"
        exit 1
    fi
done

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Run tests
echo "🧪 Running tests..."
python -m pytest tests/

# Build the application
echo "🏗️ Building application..."
python setup.py build

# Deploy to Lightstream
echo "🚀 Deploying to Lightstream..."
lightstream deploy

echo "✅ Deployment completed successfully!" 