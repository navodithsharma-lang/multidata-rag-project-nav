# Cross-Platform Docker Build Guide

This guide explains how to build Lambda Docker images on any platform (Windows, Mac Intel, Mac ARM).

---

## Quick Reference

| Your Machine | Lambda Target | Build Command |
|--------------|---------------|---------------|
| **Mac ARM (M1/M2/M3)** | ARM64 | `docker build -f Dockerfile.lambda.with-tesseract -t image:arm64 .` |
| **Mac ARM (M1/M2/M3)** | x86_64 | `docker build --platform linux/amd64 -f Dockerfile.lambda.with-tesseract -t image:amd64 .` |
| **Mac Intel** | ARM64 | `docker build --platform linux/arm64 -f Dockerfile.lambda.with-tesseract -t image:arm64 .` |
| **Mac Intel** | x86_64 | `docker build -f Dockerfile.lambda.with-tesseract -t image:amd64 .` |
| **Windows** | ARM64 | `docker build --platform linux/arm64 -f Dockerfile.lambda.with-tesseract -t image:arm64 .` |
| **Windows** | x86_64 | `docker build --platform linux/amd64 -f Dockerfile.lambda.with-tesseract -t image:amd64 .` |

---

## 🔧 Setup Requirements

### All Platforms:
1. **Docker Desktop** installed and running
2. Enable **BuildKit** (enabled by default in recent versions)

### Windows Additional Setup:
```powershell
# Enable WSL 2 backend
wsl --install

# Ensure Docker Desktop uses WSL 2
# Settings → General → Use the WSL 2 based engine ✓
```

### Mac:
```bash
# Docker Desktop should work out of the box
# Make sure it's updated to latest version
```

---

## 🚀 Building for AWS Lambda

### Option 1: Build for ARM64 (Recommended)

**Why ARM64?**
- ✅ 20% cheaper Lambda costs
- ✅ Better performance
- ✅ Smaller image size

**Build command (works on ALL platforms):**
```bash
# Without Tesseract (1.2 GB)
docker build --platform linux/arm64 \
    -f Dockerfile.lambda \
    -t rag-text-to-sql-lambda:arm64 .

# With Tesseract (3.64 GB)
docker build --platform linux/arm64 \
    -f Dockerfile.lambda.with-tesseract \
    -t rag-text-to-sql-lambda:arm64 .
```

**Deploy to Lambda:**
```bash
# Configure Lambda for ARM64
aws lambda update-function-configuration \
    --function-name your-function-name \
    --architectures arm64

# Push image
docker tag rag-text-to-sql-lambda:arm64 $ECR_URI:latest
docker push $ECR_URI:latest

# Update function
aws lambda update-function-code \
    --function-name your-function-name \
    --image-uri $ECR_URI:latest
```

---

### Option 2: Build for x86_64

**Build command (works on ALL platforms):**
```bash
# Without Tesseract (1.2 GB)
docker build --platform linux/amd64 \
    -f Dockerfile.lambda \
    -t rag-text-to-sql-lambda:amd64 .

# With Tesseract (10.1 GB - includes CUDA)
docker build --platform linux/amd64 \
    -f Dockerfile.lambda.with-tesseract \
    -t rag-text-to-sql-lambda:amd64 .
```

**Deploy to Lambda:**
```bash
# Lambda defaults to x86_64, no architecture change needed

# Push image
docker tag rag-text-to-sql-lambda:amd64 $ECR_URI:latest
docker push $ECR_URI:latest

# Update function
aws lambda update-function-code \
    --function-name your-function-name \
    --image-uri $ECR_URI:latest
```

---

## ⏱️ Build Time Expectations

| Platform | Target Architecture | Build Time | Notes |
|----------|-------------------|------------|-------|
| **Mac ARM** | ARM64 (native) | ~2-3 min | ✅ Fast (native build) |
| **Mac ARM** | x86_64 (emulated) | ~8-12 min | ⚠️ Slower (QEMU emulation) |
| **Mac Intel** | x86_64 (native) | ~2-3 min | ✅ Fast (native build) |
| **Mac Intel** | ARM64 (emulated) | ~8-12 min | ⚠️ Slower (QEMU emulation) |
| **Windows** | x86_64 (native) | ~3-5 min | ✅ Fast (native build) |
| **Windows** | ARM64 (emulated) | ~10-15 min | ⚠️ Slower (QEMU emulation) |

**Note:** Cross-platform builds use QEMU emulation and are 3-5x slower than native builds.

---

## 🐳 Docker Desktop Settings

### Enable BuildKit (if not already enabled):

**Windows/Mac:**
```json
{
  "experimental": true,
  "features": {
    "buildkit": true
  }
}
```

Or set via environment variable:
```bash
# Linux/Mac
export DOCKER_BUILDKIT=1

# Windows PowerShell
$env:DOCKER_BUILDKIT=1

# Windows CMD
set DOCKER_BUILDKIT=1
```

---

## 🔄 Multi-Platform Builds (Advanced)

Build for both ARM64 and x86_64 at once using buildx:

### Setup (one-time):
```bash
# Create a new builder
docker buildx create --name multiplatform --use

# Verify
docker buildx inspect --bootstrap
```

### Build for both platforms:
```bash
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -f Dockerfile.lambda.with-tesseract \
    -t $ECR_URI:latest \
    --push \
    .
```

**Benefits:**
- Single command builds both architectures
- Automatically pushes to registry
- Lambda can pull the correct architecture automatically

---

## 🎓 For Students/Team Members

### Recommended Workflow:

1. **Choose your target architecture:**
   - **ARM64** - Cheaper, faster, recommended
   - **x86_64** - Standard, if you have specific requirements

2. **Build the image:**
   ```bash
   # For ARM64 (recommended)
   docker build --platform linux/arm64 \
       -f Dockerfile.lambda.with-tesseract \
       -t rag-text-to-sql-lambda:latest .
   ```

3. **Verify the build:**
   ```bash
   # Check image exists
   docker images | grep rag-text-to-sql-lambda

   # Test tesseract (optional)
   docker run --rm --entrypoint tesseract \
       rag-text-to-sql-lambda:latest --version
   ```

4. **Push to ECR:**
   ```bash
   # Authenticate
   aws ecr get-login-password --region us-east-1 | \
       docker login --username AWS --password-stdin $ECR_URI

   # Tag and push
   docker tag rag-text-to-sql-lambda:latest $ECR_URI:latest
   docker push $ECR_URI:latest
   ```

5. **Deploy to Lambda:**
   ```bash
   aws lambda update-function-code \
       --function-name your-function-name \
       --image-uri $ECR_URI:latest
   ```

---

## ⚠️ Common Issues

### Issue 1: "no match for platform" error
```bash
Error: no match for platform in manifest
```

**Solution:** The base image doesn't support your target platform. Verify:
```bash
docker manifest inspect public.ecr.aws/lambda/python:3.12
```

### Issue 2: Build is extremely slow
```bash
# Cross-platform builds use emulation and are slower
```

**Solutions:**
1. **Use native architecture** when possible
2. **Use CI/CD** (GitHub Actions, GitLab CI) to build on native runners
3. **Use buildx cache** to speed up subsequent builds

### Issue 3: Docker Desktop not starting on Windows
```bash
Error: Docker Desktop failed to start
```

**Solution:**
1. Enable WSL 2: `wsl --install`
2. Enable virtualization in BIOS
3. Restart Docker Desktop

---

## 🤖 CI/CD Builds (Recommended for Teams)

Instead of building locally, use GitHub Actions or GitLab CI:

### GitHub Actions Example:
```yaml
name: Build and Push Lambda Image

on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Login to ECR
        run: |
          aws ecr get-login-password --region us-east-1 | \
          docker login --username AWS --password-stdin $ECR_URI

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          file: ./Dockerfile.lambda.with-tesseract
          platforms: linux/arm64
          push: true
          tags: ${{ env.ECR_URI }}:latest

      - name: Update Lambda function
        run: |
          aws lambda update-function-code \
            --function-name your-function-name \
            --image-uri $ECR_URI:latest
```

**Benefits:**
- ✅ Consistent builds across team
- ✅ No local build time
- ✅ Automatic deployment
- ✅ No platform issues

---

## 📊 Architecture Decision

### Use ARM64 if:
- ✅ You want lower costs (20% cheaper)
- ✅ You want better performance
- ✅ You're starting fresh (no specific x86 dependencies)

### Use x86_64 if:
- ⚠️ You have legacy x86-only dependencies
- ⚠️ You need specific x86 tools not available on ARM
- ⚠️ You're migrating existing x86 Lambda functions

**Recommendation:** **ARM64** for new projects

---

## 🔍 Verify Your Build

### Check image architecture:
```bash
docker inspect rag-text-to-sql-lambda:latest | grep Architecture
```

Output:
```json
"Architecture": "arm64"  // or "amd64"
```

### Check image size:
```bash
docker images rag-text-to-sql-lambda:latest
```

### Test tesseract:
```bash
docker run --rm --entrypoint tesseract \
    rag-text-to-sql-lambda:latest --version
```

Expected output:
```
tesseract 5.3.3
 leptonica-1.84.1
 ...
```

---

## 📚 Additional Resources

- [AWS Lambda ARM64](https://aws.amazon.com/blogs/aws/aws-lambda-functions-powered-by-aws-graviton2-processor-run-your-functions-on-arm-and-get-up-to-34-better-price-performance/)
- [Docker Multi-Platform Builds](https://docs.docker.com/build/building/multi-platform/)
- [Docker Buildx](https://docs.docker.com/buildx/working-with-buildx/)

---

## 💡 Quick Tips

1. **First build is always slow** - subsequent builds use cache
2. **Use .dockerignore** - reduces build context size
3. **BuildKit caching** - saves time on repeated builds
4. **CI/CD is better** - consistent builds for teams
5. **ARM64 is the future** - better price/performance

---

**Questions?** Check the troubleshooting section or create an issue in the repository.
