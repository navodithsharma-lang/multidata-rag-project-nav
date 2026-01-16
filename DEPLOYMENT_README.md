# Lambda Deployment Guide - Quick Start

## 🎯 Recommended: Use ARM64 Architecture

**Why ARM64?**
- ✅ **20% cheaper** Lambda costs
- ✅ **Better performance**
- ✅ **Smaller image** (3.64 GB vs 10.1 GB)
- ✅ **Faster deployments**

---

## 🚀 Quick Deployment (5 steps)

### Step 1: Set Environment Variables

```bash
# Set your ECR repository URI
export ECR_URI=123456789012.dkr.ecr.us-east-1.amazonaws.com/rag-text-to-sql

# Set Lambda function name
export LAMBDA_FUNCTION_NAME=rag-text-to-sql

# Set architecture (arm64 recommended)
export LAMBDA_ARCHITECTURE=arm64
```

### Step 2: Build Docker Image

**For ARM64 (recommended):**
```bash
docker build --platform linux/arm64 \
    -f Dockerfile.lambda.with-tesseract \
    -t rag-text-to-sql-lambda:arm64 .
```

**For x86_64:**
```bash
docker build --platform linux/amd64 \
    -f Dockerfile.lambda.with-tesseract \
    -t rag-text-to-sql-lambda:amd64 .
```

**Note:** Cross-platform builds (e.g., building ARM64 on Windows) work but are slower (8-15 minutes).

### Step 3: Deploy Using Script

```bash
./deploy-lambda.sh
```

**Or manually:**

```bash
# Authenticate with ECR
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin $ECR_URI

# Tag and push
docker tag rag-text-to-sql-lambda:arm64 $ECR_URI:latest
docker push $ECR_URI:latest

# Update Lambda code AND architecture (must be done together)
# Note: --architectures can only be set with update-function-code, not update-function-configuration
aws lambda update-function-code \
    --function-name $LAMBDA_FUNCTION_NAME \
    --image-uri $ECR_URI:latest \
    --architectures arm64
```

### Step 4: Test Deployment

```bash
# Test health endpoint
curl -X POST "https://your-function-url/2015-03-31/functions/function/invocations" \
    -d '{"rawPath": "/health", "requestContext": {"http": {"method": "GET"}}}'
```

### Step 5: Verify

Check Lambda console for:
- ✅ Function updated successfully
- ✅ Architecture shows "arm64"
- ✅ Last deployment succeeded

---

## 🔧 For Windows Students

### Prerequisites
1. Install Docker Desktop for Windows
2. Enable WSL 2 backend
3. Install AWS CLI

### Build Command (Windows PowerShell/CMD)
```powershell
# Set environment variables
$env:ECR_URI="your-ecr-uri"
$env:LAMBDA_ARCHITECTURE="arm64"

# Build for ARM64 (works on Windows!)
docker build --platform linux/arm64 -f Dockerfile.lambda.with-tesseract -t rag-text-to-sql-lambda:arm64 .
```

**Build time on Windows:** ~10-15 minutes for ARM64 (uses emulation)

See `CROSS_PLATFORM_BUILD.md` for detailed instructions.

---

## 📊 Image Size Comparison

| Dockerfile | Architecture | Size | Use Case |
|------------|-------------|------|----------|
| **Dockerfile.lambda** | ARM64 | 1.2 GB | No OCR, most use cases ✅ |
| **Dockerfile.lambda** | x86_64 | 1.2 GB | No OCR, legacy systems |
| **Dockerfile.lambda.with-tesseract** | ARM64 | 3.64 GB | With OCR, recommended ✅ |
| **Dockerfile.lambda.with-tesseract** | x86_64 | 10.1 GB | With OCR + CUDA (overkill) |

**Recommendation:** Use `Dockerfile.lambda.with-tesseract` on **ARM64** for production.

---

## 🐛 Troubleshooting

### Issue: "404 Not Found" when testing

**Cause:** Architecture mismatch (built for ARM64, Lambda configured for x86_64)

**Solution:**
```bash
# Update Lambda to ARM64
aws lambda update-function-configuration \
    --function-name $LAMBDA_FUNCTION_NAME \
    --architectures arm64
```

### Issue: Build is very slow

**Cause:** Cross-platform build (e.g., building ARM64 on x86_64 Windows)

**Solutions:**
1. Use native architecture (faster but costs more on Lambda)
2. Use CI/CD (GitHub Actions) for consistent builds
3. Be patient - first build caches layers for faster subsequent builds

### Issue: "No basic auth credentials"

**Cause:** Not authenticated with ECR

**Solution:**
```bash
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin $ECR_URI
```

---

## 📁 Important Files

| File | Purpose |
|------|---------|
| **CROSS_PLATFORM_BUILD.md** | Detailed cross-platform build guide |
| **BUILD_SUMMARY.md** | Build verification and test results |
| **DOCKERFILE_COMPARISON.md** | Comparison of Dockerfile options |
| **deploy-lambda.sh** | Automated deployment script |
| **Dockerfile.lambda** | Lightweight Lambda image (no OCR) |
| **Dockerfile.lambda.with-tesseract** | Full image with OCR support |

---

## 🎓 Team Workflow

### For Mac Users:
```bash
# Build natively for ARM64
docker build -f Dockerfile.lambda.with-tesseract -t rag-text-to-sql-lambda:arm64 .
```

### For Windows/Linux Users:
```bash
# Build for ARM64 (uses emulation, slower)
docker build --platform linux/arm64 -f Dockerfile.lambda.with-tesseract -t rag-text-to-sql-lambda:arm64 .
```

### Alternative: Use CI/CD
Set up GitHub Actions to build automatically on push - see `CROSS_PLATFORM_BUILD.md` for examples.

---

## 💰 Cost Comparison

### Lambda Costs (1M requests, 1GB memory, 1s avg duration)

| Architecture | Compute Cost | Total Cost | Savings |
|-------------|-------------|------------|---------|
| **ARM64** | $16.67 | ~$16.90/mo | 20% cheaper ✅ |
| **x86_64** | $20.84 | ~$21.00/mo | Baseline |

### Storage Costs (ECR)

| Image | Size | Cost/mo |
|-------|------|---------|
| ARM64 with OCR | 3.64 GB | $0.36 |
| x86_64 with OCR | 10.1 GB | $1.01 |

**Total Savings with ARM64:** ~$4.85/month (~23% cheaper)

---

## ✅ Deployment Checklist

- [ ] Docker Desktop installed and running
- [ ] AWS CLI configured with credentials
- [ ] ECR repository created
- [ ] Environment variables set (`ECR_URI`, `LAMBDA_FUNCTION_NAME`)
- [ ] Lambda function created (or ready to create)
- [ ] Built Docker image for ARM64
- [ ] Pushed image to ECR
- [ ] Updated Lambda configuration to ARM64
- [ ] Deployed image to Lambda
- [ ] Tested health endpoint

---

## 🔗 Next Steps

1. **Deploy to Lambda** - Use this guide
2. **Set up API Gateway** - Create REST API endpoint
3. **Configure environment variables** - Add API keys to Lambda
4. **Test endpoints** - Verify all functionality works
5. **Set up monitoring** - CloudWatch logs and metrics
6. **Configure CI/CD** - Automate future deployments

---

## 🆘 Need Help?

- **Cross-platform builds:** See `CROSS_PLATFORM_BUILD.md`
- **Architecture comparison:** See `DOCKERFILE_COMPARISON.md`
- **Build verification:** See `BUILD_SUMMARY.md`
- **Tesseract OCR:** See `LAMBDA_LAYERS.md`

---

**Remember:** Always use **ARM64** for new deployments unless you have specific x86-only requirements!
