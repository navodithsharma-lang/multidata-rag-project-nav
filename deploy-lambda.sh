#!/bin/bash
set -e

# AWS Lambda Deployment Script
# Works on Windows, Mac (Intel/ARM), and Linux

echo "🚀 AWS Lambda Deployment Script"
echo "================================"
echo ""

# Configuration
FUNCTION_NAME="${LAMBDA_FUNCTION_NAME:-rag-text-to-sql}"
AWS_REGION="${AWS_REGION:-us-east-1}"
ARCHITECTURE="${LAMBDA_ARCHITECTURE:-arm64}"  # arm64 or x86_64

# Check if ECR_URI is set
if [ -z "$ECR_URI" ]; then
    echo "❌ Error: ECR_URI environment variable not set"
    echo ""
    echo "Please set ECR_URI to your ECR repository URI:"
    echo "  export ECR_URI=123456789012.dkr.ecr.us-east-1.amazonaws.com/my-repo"
    echo ""
    exit 1
fi

# Determine platform based on architecture
if [ "$ARCHITECTURE" = "arm64" ]; then
    PLATFORM="linux/arm64"
    IMAGE_TAG="arm64"
elif [ "$ARCHITECTURE" = "x86_64" ]; then
    PLATFORM="linux/amd64"
    IMAGE_TAG="amd64"
else
    echo "❌ Error: Invalid architecture: $ARCHITECTURE"
    echo "   Valid options: arm64, x86_64"
    exit 1
fi

echo "Configuration:"
echo "  Function: $FUNCTION_NAME"
echo "  Region: $AWS_REGION"
echo "  Architecture: $ARCHITECTURE ($PLATFORM)"
echo "  ECR URI: $ECR_URI"
echo ""

# Ask for confirmation
read -p "Continue with deployment? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled"
    exit 1
fi

echo ""
echo "Step 1/5: Building Docker image for $ARCHITECTURE..."
docker build \
    --platform $PLATFORM \
    -f Dockerfile.lambda.with-tesseract \
    -t rag-text-to-sql-lambda:$IMAGE_TAG \
    .

echo ""
echo "Step 2/5: Authenticating with ECR..."
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $ECR_URI

echo ""
echo "Step 3/5: Tagging image..."
docker tag rag-text-to-sql-lambda:$IMAGE_TAG $ECR_URI:$IMAGE_TAG
docker tag rag-text-to-sql-lambda:$IMAGE_TAG $ECR_URI:latest

echo ""
echo "Step 4/5: Pushing image to ECR..."
docker push $ECR_URI:$IMAGE_TAG
docker push $ECR_URI:latest

echo ""
echo "Step 5/5: Updating Lambda function..."

# Update function code AND architecture in one command
# Note: --architectures can only be set when updating code, not configuration
echo "  Updating function code and architecture to $ARCHITECTURE..."
aws lambda update-function-code \
    --function-name $FUNCTION_NAME \
    --image-uri $ECR_URI:latest \
    --architectures $ARCHITECTURE \
    --region $AWS_REGION \
    --output json | jq -r '.FunctionArn, .LastUpdateStatus, .Architectures[0]'

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Function URL:"
aws lambda get-function-url-config \
    --function-name $FUNCTION_NAME \
    --region $AWS_REGION \
    --output json 2>/dev/null | jq -r '.FunctionUrl' || echo "  (No Function URL configured)"

echo ""
echo "To test the function:"
echo "  aws lambda invoke --function-name $FUNCTION_NAME --payload '{}' response.json"
echo ""
