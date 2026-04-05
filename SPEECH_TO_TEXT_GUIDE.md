# Speech-to-Text Integration Guide

## Overview

The speech-to-text feature enables your FastAPI backend to transcribe audio files to text with medical terminology support and webhook integration for async processing.

**Added: 9 new endpoints + webhook integration**
- Synchronous transcription
- Asynchronous batch processing  
- Webhook-based notifications
- Cache management

---

## Quick Start

### 1. Simple Transcription (Sync)

```bash
curl -X POST "http://localhost:8000/transcribe/quick" \
  -H "accept: application/json" \
  -F "file=@policy_discussion.mp3" \
  -F "context=med policy discussion"
```

**Response:**
```json
{
  "success": true,
  "file_name": "policy_discussion.mp3",
  "context": "med policy discussion",
  "transcription": {
    "full_text": "Coverage requires 72-hour notice for specialty drugs...",
    "medical_terms": ["specialty drugs", "prior authorization"],
    "policy_keywords": ["coverage", "requirement"],
    "confidence_assessment": "high"
  },
  "confidence": 87.5,
  "timestamp": "2026-04-05T10:30:00"
}
```

### 2. Async Transcription with Webhook

Register a webhook first:
```bash
curl -X POST "http://localhost:8000/api/speech-to-text/webhook/register" \
  -H "Content-Type: application/json" \
  -d '{
    "admin_id": "admin-123",
    "webhook_url": "https://your-domain.com/webhooks/transcription"
  }'
```

Upload audio for async processing:
```bash
curl -X POST "http://localhost:8000/api/speech-to-text/upload" \
  -H "accept: application/json" \
  -F "file=@policy_discussion.mp3" \
  -F "context=drug coverage policy" \
  -F "webhook_url=https://your-domain.com/webhooks/transcription"
```

**Webhook Callback (when complete):**
```json
{
  "event": "transcription.completed",
  "job_id": "a1b2c3d4-e5f6...",
  "file_name": "policy_discussion.mp3",
  "transcription": {
    "full_text": "...",
    "medical_terms": [...],
    "policy_keywords": [...]
  },
  "confidence": 87.5,
  "completed_at": "2026-04-05T10:32:00"
}
```

### 3. Batch Transcription

```bash
curl -X POST "http://localhost:8000/api/speech-to-text/batch" \
  -F "files=@file1.mp3" \
  -F "files=@file2.mp3" \
  -F "files=@file3.wav" \
  -F "webhook_url=https://your-domain.com/webhooks/batch-complete"
```

Check batch status:
```bash
curl "http://localhost:8000/api/speech-to-text/batch/batch-123"
```

---

## API Endpoints Reference

### Quick Transcription

**Endpoint:** `POST /transcribe/quick`

**Parameters:**
- `file` (multipart file, required): Audio file (MP3, WAV, M4A, WEBM, OGG, FLAC)
- `context` (string, optional): Context for transcription (e.g., "policy discussion", "drug coverage")

**Response:**
```json
{
  "success": boolean,
  "file_name": string,
  "context": string,
  "transcription": {
    "full_text": string,
    "medical_terms": string[],
    "policy_keywords": string[],
    "confidence_assessment": "high" | "medium" | "low",
    "unclear_sections": string[]
  },
  "confidence": number (0-100),
  "timestamp": ISO8601
}
```

### Demo Endpoint

**Endpoint:** `GET /transcription-demo`

Returns capabilities, example results, and all available endpoints.

### Upload & Transcribe (Async)

**Endpoint:** `POST /api/speech-to-text/upload`

**Parameters:**
- `file` (multipart file, required): Audio file
- `context` (string, optional): Context
- `webhook_url` (string, optional): URL for async notification

**Response (with webhook):**
```json
{
  "success": true,
  "message": "Audio file received. Processing asynchronously.",
  "job_id": "uuid",
  "status": "processing",
  "file_name": string,
  "webhook_url": string,
  "created_at": ISO8601,
  "check_status_url": "/speech-to-text/status/{job_id}"
}
```

### Check Job Status

**Endpoint:** `GET /api/speech-to-text/status/{job_id}`

**Response (processing):**
```json
{
  "job_id": "uuid",
  "status": "processing",
  "file_name": string,
  "created_at": ISO8601
}
```

**Response (completed):**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "file_name": string,
  "transcription": {...},
  "confidence": number,
  "created_at": ISO8601,
  "completed_at": ISO8601
}
```

### Batch Transcription

**Endpoint:** `POST /api/speech-to-text/batch`

**Parameters:**
- `files` (multipart files, required): Multiple audio files
- `context` (string, optional): Context for all files
- `webhook_url` (string, optional): URL for notification

**Response:**
```json
{
  "success": true,
  "batch_id": "uuid",
  "file_count": number,
  "job_ids": string[],
  "status": "processing",
  "created_at": ISO8601
}
```

### Check Batch Status

**Endpoint:** `GET /api/speech-to-text/batch/{batch_id}`

**Response:**
```json
{
  "batch_id": "uuid",
  "total_jobs": number,
  "completed": number,
  "failed": number,
  "processing": number,
  "jobs": [
    {
      "job_id": "uuid",
      "file_name": string,
      "status": "processing" | "completed" | "error"
    }
  ]
}
```

### Register Webhook

**Endpoint:** `POST /api/speech-to-text/webhook/register`

**Parameters:**
- `admin_id` (string): Admin ID
- `webhook_url` (string): Target URL for callbacks

**Response:**
```json
{
  "success": true,
  "webhook_id": "uuid",
  "webhook_url": string,
  "event_types": ["transcription.completed", "transcription.error"],
  "created_at": ISO8601
}
```

### Cache Statistics

**Endpoint:** `GET /api/speech-to-text/cache-stats`

**Response:**
```json
{
  "cached_files": number,
  "cache_size_bytes": number,
  "supported_formats": string[],
  "max_file_size_mb": number
}
```

### Clear Cache

**Endpoint:** `DELETE /api/speech-to-text/cache`

**Response:**
```json
{
  "success": true,
  "message": "Cleared X cached transcriptions"
}
```

---

## Supported Audio Formats

| Format | Extension | MIME Type |
|--------|-----------|-----------|
| MP3 | `.mp3` | `audio/mpeg` |
| WAV | `.wav` | `audio/wav` |
| M4A | `.m4a` | `audio/mp4` |
| WebM | `.webm` | `audio/webm` |
| Ogg Vorbis | `.ogg` | `audio/ogg` |
| FLAC | `.flac` | `audio/flac` |

**Max File Size:** 25 MB

---

## Features

### Medical Terminology Recognition
Automatically identifies and extracts:
- Drug names (brand and generic)
- Medical conditions
- Treatment types
- Prior authorization requirements

### Confidence Scoring
Returns 0-100 confidence score based on:
- Audio clarity
- Claude's assessment
- Number of unclear sections

### Caching
- Automatic caching of transcriptions by file hash
- Skip cache with `force_retranscribe` parameter
- Reduces costs and improves performance

### Webhook Integration
- Register multiple webhooks per admin
- Event types: `transcription.completed`, `transcription.error`
- Automatic retry logic
- Real-time notifications

### Batch Processing
- Process multiple files simultaneously
- Track individual job status
- Get batch completion summary

---

## Usage Examples

### Python Example

```python
import requests

# Quick sync transcription
with open("policy_discussion.mp3", "rb") as f:
    files = {"file": f}
    data = {"context": "medical policy discussion"}
    response = requests.post(
        "http://localhost:8000/transcribe/quick",
        files=files,
        data=data
    )
    result = response.json()
    print(f"Transcription: {result['transcription']['full_text']}")
    print(f"Confidence: {result['confidence']}%")
```

### JavaScript/TypeScript Example

```typescript
// Async transcription with webhook
const formData = new FormData();
formData.append("file", audioFile);
formData.append("context", "drug coverage policy");
formData.append("webhook_url", "https://your-domain.com/webhooks");

const response = await fetch(
  "http://localhost:8000/api/speech-to-text/upload",
  {
    method: "POST",
    body: formData
  }
);

const { job_id, status_url } = await response.json();
console.log(`Job ID: ${job_id}`);
console.log(`Check progress: ${status_url}`);
```

### cURL - Batch Processing

```bash
# Upload multiple files
curl -X POST "http://localhost:8000/api/speech-to-text/batch" \
  -F "files=@meeting1.mp3" \
  -F "files=@meeting2.mp3" \
  -F "files=@meeting3.wav" \
  -F "context=quarterly policy review" \
  -F "webhook_url=https://your-domain.com/webhooks/batch"

# Check progress every 30 seconds
curl "http://localhost:8000/api/speech-to-text/batch/batch-id-here"
```

---

## Error Handling

### Common Errors

| Status | Error | Solution |
|--------|-------|----------|
| 400 | Unsupported format | Use MP3, WAV, M4A, WEBM, OGG, or FLAC |
| 413 | File too large | Reduce file size below 25 MB |
| 404 | Job not found | Check job_id is correct |
| 500 | Processing error | Check audio quality, retry |

### Retry Strategy

```python
import time

job_id = response.json()["job_id"]
max_retries = 30
retry_delay = 2  # seconds

for attempt in range(max_retries):
    status_response = requests.get(
        f"http://localhost:8000/api/speech-to-text/status/{job_id}"
    )
    status = status_response.json()["status"]
    
    if status == "completed":
        print("Done!", status_response.json()["transcription"])
        break
    elif status == "error":
        print("Error:", status_response.json()["error"])
        break
    else:
        time.sleep(retry_delay)
```

---

## Webhook Payload Structure

### Success Event

```json
{
  "event": "transcription.completed",
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "file_name": "policy_discussion.mp3",
  "transcription": {
    "full_text": "The policy requires 72-hour notice...",
    "medical_terms": ["specialty drugs", "prior authorization"],
    "policy_keywords": ["coverage", "requirement", "notification"],
    "confidence_assessment": "high",
    "unclear_sections": []
  },
  "confidence": 87.5,
  "completed_at": "2026-04-05T10:32:00.123456"
}
```

### Error Event

```json
{
  "event": "transcription.error",
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "file_name": "policy_discussion.mp3",
  "error": "Audio quality too poor to process",
  "error_at": "2026-04-05T10:32:15.654321"
}
```

---

## Performance Tips

1. **Use async/webhooks for batch operations** - Prevents timeout, gets results via callback
2. **Leverage caching** - Same file processed twice will use cache
3. **Batch similar files** - Process multiple files in one batch request
4. **Monitor cache** - Use `/api/speech-to-text/cache-stats` to track size
5. **Clear cache periodically** - Use `/api/speech-to-text/cache` to free memory

---

## Integration with Other Features

### With Policy Analysis
```
Audio → Transcribe → Extract medical terms → Score policies → Return ranking
```

### With Webhooks
```
Audio → Upload with webhook → Process async → Fire webhook → Update UI
```

### With Search
```
Transcribe → Extract text → Index in vector store → Enable semantic search
```

---

## Troubleshooting

### Webhook Not Triggering
- Verify webhook URL is accessible from server
- Check webhook URL in registration response
- Ensure firewall allows outbound HTTPS connections

### Poor Transcription Quality
- Try different audio format (MP3 usually best)
- Reduce background noise
- Check audio sample rate (44.1kHz+ recommended)
- Provide context for better accuracy

### Slow Processing
- Use cache-stats endpoint to check cache size
- Clear cache if needed
- Process smaller batches
- Check server resources

### File Size Errors
- Reduce audio file size below 25MB
- Compress audio (reduce bitrate)
- Split long recordings into chunks

---

## Next Steps

1. **Test Quick Endpoint** - Try `/transcription-demo` to see example output
2. **Register Webhook** - Set up webhook for async processing
3. **Upload Test Files** - Use `/api/speech-to-text/upload` with sample MP3s
4. **Monitor Status** - Use `/api/speech-to-text/status/{job_id}` to track progress
5. **Integrate Webhooks** - Implement receiving endpoint for notifications

---

## Summary

- **9 New Endpoints** for audio transcription
- **Webhook Integration** for async processing
- **Medical Terminology** support
- **Batch Processing** for efficiency
- **Confidence Scoring** for reliability
- **Caching** for performance
- **Full Error Handling** for robustness
