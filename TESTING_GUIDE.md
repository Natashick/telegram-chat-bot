# Testing Guide for Resource Optimization PR

This guide helps you test the new resource optimization, OCR throttling, and indexing features.

## Prerequisites

Before testing, ensure you have:
- Docker and docker-compose installed
- Ollama running (optional, but recommended for full testing)
- At least 4GB RAM available
- Two test PDFs:
  - One text-based PDF (e.g., digital document)
  - One scanned PDF (image-based)

## Quick Start

```bash
# 1. Build and start with docker-compose
docker-compose up --build

# 2. Monitor resource usage in another terminal
docker stats telegram-pdf-bot

# 3. Check logs for startup messages
docker-compose logs -f
```

## Test 1: Startup Health Checks

**Expected Behavior:**
- Bot should start successfully
- Ollama connection test should run
- Clear log messages about configuration

**Expected Log Output:**
```
[INFO] PDFParser initialized: min_text_length=80, default_dpi=180, ocr_concurrency=3
[INFO] LLM URL: http://host.docker.internal:11434/api/generate
[INFO] LLM Model: llama3.2:3b
[INFO] LLM Timeout: 60s
Testing Ollama connection...
✅ Ollama connection successful! Available models: 3
✅ Configured model 'llama3.2:3b' is available
```

**If Ollama Not Running:**
```
❌ Ollama connection failed: Cannot connect to host
   URL: http://host.docker.internal:11434
   Check that OLLAMA_URL environment variable is set correctly
⚠️ WARNING: Ollama connection failed. LLM queries may not work.
```

## Test 2: OCR Throttling

**Test Steps:**
1. Upload or select a scanned PDF
2. Use `/index` command
3. Monitor docker stats and logs

**Expected Behavior:**
- Maximum of 3 concurrent OCR processes (OCR_CONCURRENCY)
- Memory usage should stay within docker-compose limits (4GB)
- CPU usage should respect limits (2.0 cores)

**Expected Log Output:**
```
[INFO] Processing PDF: scanned_document.pdf (10 pages)
[INFO] Page 1: insufficient text (12 chars), triggering OCR
[INFO] OCR page 1: mode=6, dpi=180, duration=2.34s, text_length=892
[INFO] Page 2: insufficient text (8 chars), triggering OCR
[INFO] OCR page 2: mode=6, dpi=180, duration=1.89s, text_length=756
```

**Verify:**
```bash
# Check concurrent processes
docker exec telegram-pdf-bot ps aux | grep tesseract | wc -l
# Should be <= 3

# Check memory usage
docker stats --no-stream telegram-pdf-bot
# Should be < 4GB
```

## Test 3: Early Exit for Text-Based PDFs

**Test Steps:**
1. Upload or select a digital (text-based) PDF
2. Use `/index` command
3. Check logs

**Expected Behavior:**
- No OCR should be triggered
- Fast processing (seconds, not minutes)
- Text extraction via PyPDF2/pdfminer only

**Expected Log Output:**
```
[INFO] Processing PDF: digital_document.pdf (50 pages)
[INFO] Page 1: sufficient text without OCR (1234 chars)
[INFO] Page 2: sufficient text without OCR (2456 chars)
[INFO] Page 3: sufficient text without OCR (1890 chars)
[INFO] PDF processing complete: 98765 total characters
```

**Verify:**
- Indexing should complete in < 1 minute for 50-page digital PDF
- No "triggering OCR" messages in logs

## Test 4: OCR Fallback

**Test Steps:**
1. Use a low-quality scanned PDF
2. Use `/index` command
3. Check logs for fallback usage

**Expected Behavior:**
- First attempt with PSM=6, DPI=180
- If insufficient text, fallback to PSM=3, DPI=240
- Fallback logged clearly

**Expected Log Output:**
```
[INFO] Page 5: insufficient text (23 chars), triggering OCR
[INFO] OCR page 5: mode=6, dpi=180, duration=2.12s, text_length=45
[INFO] Page 5: OCR insufficient, trying fallback (psm=3, dpi=240)
[INFO] OCR page 5: mode=3, dpi=240, duration=3.89s, text_length=234
[INFO] Fallback OCR used for page 5
```

## Test 5: Indexing Command

**Test Steps:**
1. Start bot and select a document with `/start`
2. Try to search without indexing (should fail)
3. Use `/index` command
4. Wait for progress updates
5. Try searching again (should work)

**Expected Behavior:**
- Clear error message if document not indexed
- Progress updates during indexing
- Success message when complete
- Search works after indexing

**Telegram Conversation:**
```
You: What is chapter 5 about?
Bot: ⚠️ Document 'my-document.pdf' is not indexed yet.
     Use /index to index this document before searching.

You: /index
Bot: 🔄 Starting indexing of 'my-document.pdf'...
     This may take a few minutes depending on document size.

Bot: Extracted 150 paragraphs, adding to index...
Bot: Progress: 50% (75/150 paragraphs)
Bot: Progress: 100% (150/150 paragraphs)
Bot: ✅ Indexing complete!
     You can now ask questions about 'my-document.pdf'.

You: What is chapter 5 about?
Bot: [Answer based on document content]
```

## Test 6: Concurrent Indexing Control

**Test Steps:**
1. Try to index multiple documents simultaneously
2. Check that only INDEX_CONCURRENCY (default 1) runs at a time

**Expected Behavior:**
- Second index request waits until first completes
- Clear indication in logs

**Expected Log Output:**
```
[INFO] Starting background indexing for doc1.pdf
[INFO] Starting background indexing for doc2.pdf
[DEBUG] Processing embedding batch 1/3
# doc1.pdf completes
[INFO] Successfully indexed doc1.pdf with 150 paragraphs
# doc2.pdf starts processing
[DEBUG] Processing embedding batch 1/2
[INFO] Successfully indexed doc2.pdf with 89 paragraphs
```

## Test 7: Embedding Model

**Test Steps:**
1. Start bot
2. Check logs for embedding model information
3. Index a document
4. Verify batching in logs

**Expected Behavior:**
- Model should be "sentence-transformers/all-MiniLM-L6-v2"
- Batch size should be 64
- Memory usage should be reasonable

**Expected Log Output:**
```
[INFO] Ollama Embedding Model: sentence-transformers/all-MiniLM-L6-v2
[INFO] Ollama Embedding URL: http://host.docker.internal:11434
[INFO] Batch size: 64
[DEBUG] Processing embedding batch 1/3
[DEBUG] Processing embedding batch 2/3
[DEBUG] Processing embedding batch 3/3
```

## Test 8: Resource Limits

**Test Steps:**
1. Start bot with docker-compose
2. Index multiple large PDFs
3. Monitor resource usage

**Expected Behavior:**
- CPU usage stays below 2.0 cores
- Memory usage stays below 4GB
- Bot doesn't crash or freeze

**Monitoring:**
```bash
# Real-time monitoring
watch -n 1 docker stats telegram-pdf-bot

# Expected output:
CONTAINER            CPU %    MEM USAGE / LIMIT     MEM %
telegram-pdf-bot     45.2%    1.8GiB / 4GiB        45.0%
```

## Test 9: Connection Test Script

**Test Steps:**
```bash
# Run connection test
python test_llm_client.py
```

**Expected Output:**
```
====================================================================
LLM CLIENT CONNECTION TESTS
====================================================================

====================================================================
Testing Ollama Connection (Async)
====================================================================
Testing URL: http://host.docker.internal:11434
Expected Model: llama3.2:3b

[INFO] Testing Ollama connection...
[INFO] ✅ Ollama connection successful! Available models: 3
[INFO] ✅ Configured model 'llama3.2:3b' is available

✅ PASS: Connection successful

====================================================================
TEST SUMMARY
====================================================================
✅ PASS: Async Connection Test
✅ PASS: Sync Wrapper Test
✅ PASS: Invalid URL Handling

Tests passed: 3/3

🎉 All tests passed!
```

## Performance Benchmarks

### Digital PDF (Text-Based)
- **50 pages**: < 1 minute indexing
- **Memory**: < 500MB peak
- **OCR calls**: 0

### Scanned PDF (Image-Based)
- **50 pages**: 5-10 minutes indexing
- **Memory**: 1-2GB peak
- **OCR calls**: 50 (one per page)
- **Average OCR time**: 2-3 seconds per page

### Resource-Constrained System (2GB RAM)
- Set `OCR_CONCURRENCY=1`
- Set `INDEX_CONCURRENCY=1`
- Set `MIN_TEXT_LENGTH=100`
- Expect slower but stable operation

## Troubleshooting

### Issue: Bot crashes during indexing
**Solution:** Reduce OCR_CONCURRENCY to 1 or 2

### Issue: Memory exceeds 4GB
**Solution:** Reduce batch_size in vector_store.py

### Issue: Ollama connection fails
**Solution:** 
- Check OLLAMA_URL is correct
- For Docker, use `http://host.docker.internal:11434`
- Ensure Ollama is running on host

### Issue: OCR is too slow
**Solution:** Increase OCR_CONCURRENCY (if RAM allows)

### Issue: OCR quality is poor
**Solution:** Increase MIN_TEXT_LENGTH to force more OCR usage

## Environment Variables for Testing

```bash
# Conservative (low-RAM systems)
export OCR_CONCURRENCY=2
export INDEX_CONCURRENCY=1
export MIN_TEXT_LENGTH=100
export OLLAMA_TIMEOUT=30

# Aggressive (high-RAM systems)
export OCR_CONCURRENCY=5
export INDEX_CONCURRENCY=2
export MIN_TEXT_LENGTH=50
export OLLAMA_TIMEOUT=120
```

## Success Criteria

✅ All imports successful
✅ Bot starts without errors
✅ Ollama connection test runs
✅ OCR throttling limits concurrent processes
✅ Text-based PDFs skip OCR
✅ Scanned PDFs trigger OCR with conservative settings
✅ Fallback OCR works when needed
✅ /index command works with progress updates
✅ Unindexed documents show clear error
✅ Resource limits are respected
✅ Memory usage stays within 4GB
✅ No system freezes or crashes

## Next Steps

After successful testing:
1. Document any edge cases found
2. Adjust default values based on typical workload
3. Consider adding metrics/monitoring
4. Add integration tests for CI/CD
