# Team Setup Guide - For All Students

This guide ensures **everyone** on your team (Windows, Mac Intel, Mac ARM) can build and deploy the Lambda function successfully.

---

## 🎯 TL;DR - Quick Start

**Everyone should build for ARM64, regardless of their machine:**

```bash
# This works on ALL platforms (Windows, Mac, Linux)
docker build --platform linux/arm64 \
    -f Dockerfile.lambda.with-tesseract \
    -t rag-text-to-sql-lambda:arm64 .
```

**Why?** ARM64 Lambda is 20% cheaper and faster than x86_64.

---

## 📋 One-Time Setup (Each Team Member)

### 1. Install Required Software

#### Windows:
```powershell
# Install Docker Desktop for Windows
# Download from: https://www.docker.com/products/docker-desktop/

# Install AWS CLI
# Download from: https://aws.amazon.com/cli/

# Enable WSL 2
wsl --install
```

#### Mac:
```bash
# Install Docker Desktop for Mac
# Download from: https://www.docker.com/products/docker-desktop/

# Install AWS CLI
brew install awscli
```

#### Linux:
```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Install AWS CLI
pip install awscli
```

### 2. Configure AWS Credentials

```bash
# Configure AWS CLI (same for all platforms)
aws configure

# Enter:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region: us-east-1
# - Default output format: json
```

### 3. Set Environment Variables

**Windows (PowerShell):**
```powershell
# Add to your PowerShell profile or set each session
$env:ECR_URI="123456789012.dkr.ecr.us-east-1.amazonaws.com/rag-text-to-sql"
$env:LAMBDA_FUNCTION_NAME="rag-text-to-sql"
$env:LAMBDA_ARCHITECTURE="arm64"
```

**Mac/Linux (Bash):**
```bash
# Add to ~/.bashrc or ~/.zshrc
export ECR_URI="123456789012.dkr.ecr.us-east-1.amazonaws.com/rag-text-to-sql"
export LAMBDA_FUNCTION_NAME="rag-text-to-sql"
export LAMBDA_ARCHITECTURE="arm64"
```

---

## 🚀 Standard Deployment Workflow

### Step 1: Clone Repository
```bash
git clone <repository-url>
cd multidata-rag-project
```

### Step 2: Build Docker Image

**ALL platforms use this same command:**
```bash
docker build --platform linux/arm64 \
    -f Dockerfile.lambda.with-tesseract \
    -t rag-text-to-sql-lambda:arm64 .
```

**Expected build time:**
- Mac ARM (M1/M2/M3): ~2-3 minutes ⚡ (native)
- Mac Intel: ~10-12 minutes 🐌 (emulated)
- Windows: ~10-15 minutes 🐌 (emulated)

**Note:** First build downloads everything. Subsequent builds are much faster thanks to caching!

### Step 3: Deploy

**Option A - Automated (Recommended):**
```bash
./deploy-lambda.sh
```

**Option B - Manual:**
```bash
# 1. Login to ECR
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin $ECR_URI

# 2. Tag image
docker tag rag-text-to-sql-lambda:arm64 $ECR_URI:latest

# 3. Push to ECR
docker push $ECR_URI:latest

# 4. Update Lambda
aws lambda update-function-code \
    --function-name $LAMBDA_FUNCTION_NAME \
    --image-uri $ECR_URI:latest
```

---

## 🔍 Verify Your Build

### Check Image Architecture
```bash
docker inspect rag-text-to-sql-lambda:arm64 | grep Architecture
```

**Expected output:**
```json
"Architecture": "arm64"
```

### Check Image Size
```bash
docker images | grep rag-text-to-sql-lambda
```

**Expected output:**
```
rag-text-to-sql-lambda:arm64   <id>   3.64GB   <time>
```

### Test Tesseract
```bash
docker run --rm --entrypoint tesseract \
    rag-text-to-sql-lambda:arm64 --version
```

**Expected output:**
```
tesseract 5.3.3
 leptonica-1.84.1
 ...
```

---

## ⚠️ Common Issues & Solutions

### Issue 1: "Docker Desktop not running"

**Windows:**
1. Start Docker Desktop from Start Menu
2. Wait for Docker to fully start (whale icon in system tray)
3. Retry your command

**Mac:**
1. Start Docker Desktop from Applications
2. Wait for Docker to fully start (whale icon in menu bar)
3. Retry your command

---

### Issue 2: "cannot connect to Docker daemon"

**Solution:**
```bash
# Restart Docker Desktop
# Wait 30 seconds
# Try again
```

---

### Issue 3: Build is taking too long (>30 minutes)

**Cause:** First-time download of large dependencies

**Solution:**
- Be patient, this is normal for first build
- Subsequent builds will be much faster (2-5 minutes)
- Check your internet connection

---

### Issue 4: "No basic auth credentials" when pushing to ECR

**Solution:**
```bash
# Re-authenticate with ECR
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin $ECR_URI
```

---

### Issue 5: "Architecture mismatch" error in Lambda

**Cause:** Lambda is configured for x86_64 but image is ARM64

**Solution:**
```bash
# Update Lambda to ARM64
aws lambda update-function-configuration \
    --function-name $LAMBDA_FUNCTION_NAME \
    --architectures arm64

# Wait 30 seconds for config update
# Then push your image again
```

---

## 🎓 Platform-Specific Notes

### Mac ARM (M1/M2/M3) Users
- ✅ Native ARM64 builds are FAST (~2-3 min)
- ✅ No special flags needed (omit `--platform` for native)
- ✅ Best development experience

### Mac Intel Users
- ⚠️ ARM64 builds use emulation (~10-12 min)
- ✅ Use `--platform linux/arm64` flag
- ✅ Builds are slower but work perfectly

### Windows Users
- ⚠️ ARM64 builds use emulation (~10-15 min)
- ✅ Must use `--platform linux/arm64` flag
- ✅ Ensure WSL 2 is enabled in Docker Desktop
- ℹ️ Use PowerShell or CMD (both work)

### Linux Users
- ⚠️ ARM64 builds use emulation (if on x86_64)
- ✅ Use `--platform linux/arm64` flag
- ✅ May need `sudo` for Docker commands

---

## 🤝 Collaboration Best Practices

### 1. Always Build for ARM64
Everyone should build for `linux/arm64` regardless of their local machine:
```bash
docker build --platform linux/arm64 ...
```

### 2. Use Consistent Tags
Always tag images as `:arm64` or `:latest`:
```bash
docker tag rag-text-to-sql-lambda:arm64 $ECR_URI:arm64
docker tag rag-text-to-sql-lambda:arm64 $ECR_URI:latest
```

### 3. Document Your Deployments
```bash
# Add to commit message or deployment log
git log --oneline | head -1
aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME \
    | jq -r '.Configuration.LastModified'
```

### 4. Share ECR Access
Ensure all team members have ECR push/pull permissions:
```bash
# Admin runs this for each team member
aws ecr set-repository-policy --repository-name rag-text-to-sql \
    --policy-text file://ecr-policy.json
```

---

## 📊 Build Time Comparison

| Platform | Architecture | Native? | Build Time |
|----------|-------------|---------|------------|
| Mac ARM | ARM64 | ✅ Yes | 2-3 min |
| Mac Intel | ARM64 | ❌ No | 10-12 min |
| Windows x64 | ARM64 | ❌ No | 10-15 min |
| Linux x64 | ARM64 | ❌ No | 10-12 min |

**First build** includes downloading all dependencies (~1.5GB). **Subsequent builds** only rebuild changed layers (much faster!).

---

## 🔧 Advanced: CI/CD Setup (Optional)

Instead of building locally, set up GitHub Actions:

### Benefits:
- ✅ Consistent builds for everyone
- ✅ No waiting for local builds
- ✅ Automatic deployment on merge to main
- ✅ No platform-specific issues

### Setup:
See `CROSS_PLATFORM_BUILD.md` for GitHub Actions workflow.

---

## 📚 Additional Resources

| Document | Purpose |
|----------|---------|
| **DEPLOYMENT_README.md** | Quick deployment guide |
| **CROSS_PLATFORM_BUILD.md** | Detailed platform-specific instructions |
| **BUILD_SUMMARY.md** | Build verification and results |
| **DOCKERFILE_COMPARISON.md** | Compare different Dockerfile options |

---

## ✅ Team Checklist

### Before Starting Development:
- [ ] Docker Desktop installed
- [ ] AWS CLI configured
- [ ] Access to ECR repository
- [ ] Environment variables set
- [ ] Successfully built image locally
- [ ] Successfully pushed to ECR

### Before Each Deployment:
- [ ] Latest code from git
- [ ] Image builds successfully
- [ ] Tesseract test passes
- [ ] Pushed to ECR
- [ ] Lambda updated
- [ ] Health endpoint tested

---

## 🆘 Getting Help

### If build fails:
1. Check Docker is running: `docker ps`
2. Check disk space: `docker system df`
3. Clean up if needed: `docker system prune -a`
4. Try again

### If deployment fails:
1. Check AWS credentials: `aws sts get-caller-identity`
2. Check ECR authentication: Login again
3. Check Lambda permissions: IAM role configured?
4. Check logs: `aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME`

### Still stuck?
- Check platform-specific notes above
- See `CROSS_PLATFORM_BUILD.md` for detailed troubleshooting
- Ask team members who successfully deployed

---

**Remember:** Everyone builds for **ARM64** - it's cheaper, faster, and works great! 🚀
