"""
Speech-to-Text Webhook Routes
Handles audio uploads and speech-to-text transcription with webhook integration
"""

import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import Optional
from datetime import datetime
import uuid
from pathlib import Path

from antonrx_backend.extractors.speech_to_text_service import speech_to_text_service
from antonrx_backend.webhooks.webhook_service import webhook_service

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory storage for transcription jobs
transcription_jobs = {}


@router.post("/speech-to-text/upload", tags=["Speech-to-Text"])
async def upload_and_transcribe_audio(
    file: UploadFile = File(...),
    context: Optional[str] = None,
    webhook_url: Optional[str] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Upload audio file and transcribe to text.
    
    Supports: MP3, WAV, M4A, WEBM, OGG, FLAC
    Max size: 25 MB
    
    - If webhook_url provided: async processing with callback
    - Otherwise: synchronous response
    
    Args:
        file: Audio file to transcribe
        context: Optional context for the audio (e.g., "policy discussion", "drug coverage")
        webhook_url: Optional webhook endpoint to POST results to
        
    Returns:
        Job details with transcription_id for async tracking
    """
    job_id = str(uuid.uuid4())
    
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        file_ext = Path(file.filename).suffix.lstrip(".").lower()
        if file_ext not in speech_to_text_service.supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format: {file_ext}. Supported: {', '.join(speech_to_text_service.supported_formats)}"
            )
        
        # Read file
        audio_data = await file.read()
        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        if len(audio_data) > speech_to_text_service.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {len(audio_data)} bytes (max: {speech_to_text_service.max_file_size})"
            )
        
        # Store job metadata
        job_metadata = {
            "job_id": job_id,
            "file_name": file.filename,
            "file_size": len(audio_data),
            "context": context,
            "status": "processing",
            "created_at": datetime.utcnow().isoformat(),
            "webhook_url": webhook_url,
            "result": None,
        }
        transcription_jobs[job_id] = job_metadata
        
        # Process asynchronously if webhook URL provided
        if webhook_url:
            background_tasks.add_task(
                _process_transcription_async,
                job_id=job_id,
                audio_data=audio_data,
                file_name=file.filename,
                context=context,
                webhook_url=webhook_url,
            )
            
            return {
                "success": True,
                "message": "Audio file received. Processing asynchronously.",
                "job_id": job_id,
                "status": "processing",
                "file_name": file.filename,
                "webhook_url": webhook_url,
                "created_at": job_metadata["created_at"],
                "check_status_url": f"/speech-to-text/status/{job_id}",
            }
        
        # Process synchronously
        transcription, confidence, file_hash = await speech_to_text_service.transcribe_audio(
            audio_data=audio_data,
            file_name=file.filename,
            context=context,
        )
        
        job_metadata["status"] = "completed"
        job_metadata["result"] = transcription
        job_metadata["confidence"] = confidence
        job_metadata["file_hash"] = file_hash
        job_metadata["completed_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Transcription job {job_id} completed synchronously")
        
        return {
            "success": True,
            "job_id": job_id,
            "status": "completed",
            "file_name": file.filename,
            "transcription": transcription,
            "confidence": confidence,
            "created_at": job_metadata["created_at"],
            "completed_at": job_metadata["completed_at"],
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing audio file: {str(e)}")
        if job_id in transcription_jobs:
            transcription_jobs[job_id]["status"] = "error"
            transcription_jobs[job_id]["error"] = str(e)
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")


@router.get("/speech-to-text/status/{job_id}", tags=["Speech-to-Text"])
async def get_transcription_status(job_id: str):
    """
    Get status of a transcription job.
    
    Args:
        job_id: ID of the transcription job
        
    Returns:
        Job status with result if completed
    """
    if job_id not in transcription_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = transcription_jobs[job_id]
    
    response = {
        "job_id": job_id,
        "status": job["status"],
        "file_name": job["file_name"],
        "created_at": job["created_at"],
    }
    
    if job["status"] == "completed":
        response.update({
            "transcription": job["result"],
            "confidence": job.get("confidence", 0),
            "completed_at": job.get("completed_at"),
        })
    elif job["status"] == "error":
        response["error"] = job.get("error")
    
    return response


@router.post("/speech-to-text/batch", tags=["Speech-to-Text"])
async def batch_transcribe_audio(
    files: list[UploadFile] = File(...),
    context: Optional[str] = None,
    webhook_url: Optional[str] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Batch transcribe multiple audio files.
    
    Args:
        files: List of audio files to transcribe
        context: Optional context for all files
        webhook_url: Optional webhook for completion notification
        
    Returns:
        Batch job details with individual job IDs
    """
    batch_id = str(uuid.uuid4())
    job_ids = []
    
    try:
        for file in files:
            job_id = str(uuid.uuid4())
            job_ids.append(job_id)
            
            audio_data = await file.read()
            job_metadata = {
                "job_id": job_id,
                "file_name": file.filename,
                "file_size": len(audio_data),
                "context": context,
                "status": "processing",
                "batch_id": batch_id,
                "created_at": datetime.utcnow().isoformat(),
                "result": None,
            }
            transcription_jobs[job_id] = job_metadata
            
            if webhook_url:
                background_tasks.add_task(
                    _process_transcription_async,
                    job_id=job_id,
                    audio_data=audio_data,
                    file_name=file.filename,
                    context=context,
                    webhook_url=webhook_url,
                )
        
        return {
            "success": True,
            "batch_id": batch_id,
            "file_count": len(files),
            "job_ids": job_ids,
            "status": "processing",
            "created_at": datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        logger.error(f"Error in batch transcription: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/speech-to-text/batch/{batch_id}", tags=["Speech-to-Text"])
async def get_batch_status(batch_id: str):
    """
    Get status of all jobs in a batch.
    
    Args:
        batch_id: ID of the batch
        
    Returns:
        Status of all jobs in the batch
    """
    batch_jobs = [
        job for job in transcription_jobs.values()
        if job.get("batch_id") == batch_id
    ]
    
    if not batch_jobs:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
    
    completed = sum(1 for job in batch_jobs if job["status"] == "completed")
    failed = sum(1 for job in batch_jobs if job["status"] == "error")
    
    return {
        "batch_id": batch_id,
        "total_jobs": len(batch_jobs),
        "completed": completed,
        "failed": failed,
        "processing": len(batch_jobs) - completed - failed,
        "jobs": [
            {
                "job_id": job["job_id"],
                "file_name": job["file_name"],
                "status": job["status"],
            }
            for job in batch_jobs
        ],
    }


@router.post("/speech-to-text/webhook/register", tags=["Speech-to-Text"])
async def register_stt_webhook(
    admin_id: str,
    webhook_url: str,
):
    """
    Register a webhook for speech-to-text events.
    
    Args:
        admin_id: Admin registering the webhook
        webhook_url: URL to receive transcription results
        
    Returns:
        Webhook registration details
    """
    try:
        webhook = webhook_service.register_webhook(
            admin_id=admin_id,
            webhook_url=webhook_url,
            event_types=["transcription.completed", "transcription.error"],
        )
        
        return {
            "success": True,
            "webhook_id": webhook["id"],
            "webhook_url": webhook_url,
            "event_types": webhook["event_types"],
            "created_at": webhook["created_at"],
        }
    
    except Exception as e:
        logger.error(f"Error registering webhook: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/speech-to-text/cache-stats", tags=["Speech-to-Text"])
async def get_cache_statistics():
    """
    Get speech-to-text cache statistics.
    
    Returns:
        Cache stats including file count and size
    """
    return speech_to_text_service.get_cache_stats()


@router.delete("/speech-to-text/cache", tags=["Speech-to-Text"])
async def clear_transcription_cache():
    """
    Clear all cached transcriptions.
    
    Returns:
        Number of items cleared
    """
    result = speech_to_text_service.clear_cache()
    return {
        "success": True,
        "message": f"Cleared {result['cleared']} cached transcriptions",
    }


# ════════════════════════════════════════════════════════════════
# Background Task Handler
# ════════════════════════════════════════════════════════════════

async def _process_transcription_async(
    job_id: str,
    audio_data: bytes,
    file_name: str,
    context: Optional[str],
    webhook_url: str,
):
    """
    Process transcription asynchronously and POST result to webhook.
    
    Args:
        job_id: Job ID for tracking
        audio_data: Audio file bytes
        file_name: Name of the audio file
        context: Context for transcription
        webhook_url: Webhook endpoint to POST results to
    """
    try:
        logger.info(f"Starting async transcription for job {job_id}")
        
        # Perform transcription
        transcription, confidence, file_hash = await speech_to_text_service.transcribe_audio(
            audio_data=audio_data,
            file_name=file_name,
            context=context,
        )
        
        # Update job status
        job = transcription_jobs[job_id]
        job["status"] = "completed"
        job["result"] = transcription
        job["confidence"] = confidence
        job["file_hash"] = file_hash
        job["completed_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Transcription job {job_id} completed, posting to webhook")
        
        # Send webhook notification
        webhook_payload = {
            "event": "transcription.completed",
            "job_id": job_id,
            "file_name": file_name,
            "transcription": transcription,
            "confidence": confidence,
            "completed_at": job["completed_at"],
        }
        
        await webhook_service.deliver_webhook_event(webhook_url, webhook_payload)
    
    except Exception as e:
        logger.error(f"Error in async transcription job {job_id}: {str(e)}")
        
        # Update job with error
        if job_id in transcription_jobs:
            job = transcription_jobs[job_id]
            job["status"] = "error"
            job["error"] = str(e)
            job["error_at"] = datetime.utcnow().isoformat()
        
        # Send error webhook notification
        try:
            webhook_payload = {
                "event": "transcription.error",
                "job_id": job_id,
                "file_name": file_name,
                "error": str(e),
                "error_at": datetime.utcnow().isoformat(),
            }
            await webhook_service.deliver_webhook_event(webhook_url, webhook_payload)
        except Exception as webhook_error:
            logger.error(f"Failed to send error webhook: {str(webhook_error)}")
