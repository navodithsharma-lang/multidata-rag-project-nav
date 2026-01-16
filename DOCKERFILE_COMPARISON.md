# Lambda Dockerfile Comparison

## Which Dockerfile Should I Use?

### Option 1: `Dockerfile.lambda` (Smaller, No OCR)
**Use this if:** You don't need OCR capabilities for scanned PDFs/images.

**Pros:**
- ✅ Smaller image size (~1.2GB)
- ✅ Faster build time (~3-4 minutes)
- ✅ Faster cold starts
- ✅ Lower storage costs

**Cons:**
- ❌ Cannot process scanned PDFs or images with text
- ❌ `unstructured` library will have limited document parsing

**Build command:**
```bash
docker build -f Dockerfile.lambda -t rag-text-to-sql-lambda:latest .
```

---

### Option 2: `Dockerfile.lambda.with-tesseract` (Full OCR Support)
**Use this if:** You need to extract text from scanned PDFs, images, or screenshots.

**Pros:**
- ✅ Full OCR capabilities with Tesseract 5.3.3
- ✅ Better document parsing for complex PDFs
- ✅ Supports image-based text extraction
- ✅ English language pack included (can add more)

**Cons:**
- ❌ Larger image size (~1.6-1.8GB)
- ❌ Longer build time (~8-10 minutes)
- ❌ Slightly slower cold starts
- ❌ Requires build dependencies

**Build command:**
```bash
docker build -f Dockerfile.lambda.with-tesseract -t rag-text-to-sql-lambda:latest .
```

---

## Image Size Comparison

| Component | Base Image | + Python Deps | + Tesseract & Build Tools | Total |
|-----------|-----------|---------------|---------------------------|-------|
| **Dockerfile.lambda** | 150 MB | ~1050 MB | - | **~1.2 GB** |
| **Dockerfile.lambda.with-tesseract** | 150 MB | ~1050 MB | ~2440 MB | **3.64 GB** |

**Note:** The with-tesseract image is larger than expected because it includes all build dependencies (gcc, make, autoconf, etc.). This can be optimized with a multi-stage build to ~1.8-2GB.

---

## Build Time Comparison

| Dockerfile | First Build | Cached Build |
|-----------|-------------|--------------|
| **Dockerfile.lambda** | ~3-4 min | ~1 min |
| **Dockerfile.lambda.with-tesseract** | ~8-10 min | ~1 min |

---

## Decision Tree

```
Do you need to process scanned PDFs or images?
│
├─ NO  → Use Dockerfile.lambda
│        (Smaller, faster, sufficient for most use cases)
│
└─ YES → Use Dockerfile.lambda.with-tesseract
         (Full OCR support, larger image)
```

---

## Testing OCR Capabilities

After deploying, test if OCR is working:

```python
# Add this to your Lambda function for testing
import subprocess

def test_ocr():
    try:
        result = subprocess.run(
            ['tesseract', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return {
            'tesseract_available': True,
            'version': result.stdout.split('\n')[0]
        }
    except Exception as e:
        return {
            'tesseract_available': False,
            'error': str(e)
        }
```

---

## Switching Between Dockerfiles

You can easily switch between versions:

```bash
# Deploy without OCR (smaller)
docker build -f Dockerfile.lambda -t $ECR_URI:no-ocr .
docker push $ECR_URI:no-ocr

# Deploy with OCR (full-featured)
docker build -f Dockerfile.lambda.with-tesseract -t $ECR_URI:with-ocr .
docker push $ECR_URI:with-ocr

# Update Lambda to use specific version
aws lambda update-function-code \
    --function-name your-function-name \
    --image-uri $ECR_URI:no-ocr  # or :with-ocr
```

---

## Recommendation

**Start with `Dockerfile.lambda`** (without tesseract) for the following reasons:

1. Most documents (PDFs, Word, Excel) don't require OCR
2. Smaller image = faster deployments and lower costs
3. You can always switch to the OCR version later if needed
4. Easier to debug and maintain

**Upgrade to `Dockerfile.lambda.with-tesseract`** only if you encounter:
- Scanned PDF documents
- Screenshots with text
- Image files that need text extraction
- Document parsing errors due to missing OCR

---

## Cost Implications

### Storage Costs (ECR):
- Dockerfile.lambda: ~$0.12/month (1.2GB × $0.10/GB)
- Dockerfile.lambda.with-tesseract: **~$0.36/month (3.64GB × $0.10/GB)**

### Compute Costs (Lambda):
- Cold start time: +100-200ms with tesseract
- Memory usage: +50-100MB with tesseract
- Initial download time: Longer first deployment
- Minimal impact on execution costs after deployment

### Transfer Costs:
- Initial push to ECR: 3.64GB upload
- Each deployment: 3.64GB download to Lambda
- Consider regional ECR for faster deployments

**Verdict:** The cost difference is ~$0.24/month for storage. The main consideration is deployment time due to image size, not cost.
