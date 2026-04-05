"""
Admin and Enhanced API Routes
Exposes all admin controls, enhanced search, analytics, and webhook management
Mount this as: app.include_router(admin_routes.router, prefix="/api/admin")
"""

from fastapi import APIRouter, HTTPException, Query, Body, Header
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])


# ============================================================================
# POLICY MANAGEMENT - Soft Delete, Restore, Archive
# ============================================================================


@router.delete("/policies/{policy_id}")
async def soft_delete_policy(
    policy_id: str,
    reason: str = Query(..., description="Reason for deactivation"),
    admin_user_id: str = Header(..., alias="X-Admin-User-Id"),
    admin_email: str = Header(..., alias="X-Admin-Email"),
) -> Dict:
    """
    Soft delete a policy (mark as inactive, preserves history).
    
    Query params:
    - reason: Required reason for deletion
    
    Headers:
    - X-Admin-User-Id: Admin's user ID
    - X-Admin-Email: Admin's email
    
    Returns: Updated policy with is_active=False
    """
    from antonrx_backend.admin.admin_service import admin_service

    try:
        policy = admin_service.soft_delete_policy(
            policy_id=policy_id,
            reason=reason,
            admin_user_id=admin_user_id,
            admin_email=admin_email,
        )
        return {"success": True, "data": policy}
    except Exception as e:
        logger.error(f"Error soft deleting policy: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/policies/{policy_id}/restore")
async def restore_policy(
    policy_id: str,
    admin_user_id: str = Header(..., alias="X-Admin-User-Id"),
    admin_email: str = Header(..., alias="X-Admin-Email"),
) -> Dict:
    """Restore a soft-deleted policy."""
    from antonrx_backend.admin.admin_service import admin_service

    try:
        policy = admin_service.restore_policy(
            policy_id=policy_id,
            admin_user_id=admin_user_id,
            admin_email=admin_email,
        )
        return {"success": True, "data": policy}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/payers/{payer_id}/bulk-archive")
async def bulk_archive_payer(
    payer_id: str,
    admin_user_id: str = Header(..., alias="X-Admin-User-Id"),
    admin_email: str = Header(..., alias="X-Admin-Email"),
) -> Dict:
    """Bulk archive all policies for a payer."""
    from antonrx_backend.admin.admin_service import admin_service

    try:
        result = admin_service.bulk_archive_payer(
            payer_id=payer_id,
            payer_name=f"Payer_{payer_id}",
            admin_user_id=admin_user_id,
            admin_email=admin_email,
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/payers/bulk-archive/multiple")
async def bulk_archive_multiple_payers(
    payer_ids: List[str] = Body(...),
    admin_user_id: str = Header(..., alias="X-Admin-User-Id"),
    admin_email: str = Header(..., alias="X-Admin-Email"),
) -> Dict:
    """Bulk archive multiple payers at once."""
    from antonrx_backend.admin.admin_service import admin_service

    try:
        result = admin_service.bulk_archive_payers(
            payer_ids=payer_ids,
            admin_user_id=admin_user_id,
            admin_email=admin_email,
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# POLICY FIELD OVERRIDES - Manual Corrections
# ============================================================================


@router.put("/policies/{policy_id}/override-field")
async def override_policy_field(
    policy_id: str,
    field_name: str = Query(...),
    new_value: Any = Body(...),
    reason: str = Body(...),
    admin_user_id: str = Header(..., alias="X-Admin-User-Id"),
    admin_email: str = Header(..., alias="X-Admin-Email"),
) -> Dict:
    """
    Manually correct an extracted policy field.
    
    Query params:
    - field_name: Field to correct (e.g., "prior_auth", "copay")
    
    Body:
    - new_value: New value for the field
    - reason: Why the correction was needed
    """
    from antonrx_backend.admin.admin_service import admin_service

    try:
        override = admin_service.override_policy_field(
            policy_id=policy_id,
            field_name=field_name,
            old_value=None,  # In production, fetch from DB
            new_value=new_value,
            reason=reason,
            admin_user_id=admin_user_id,
            admin_email=admin_email,
        )
        return {"success": True, "data": override}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# RE-EXTRACTION - Trigger new extraction with updated prompt
# ============================================================================


@router.post("/policies/{policy_id}/re-extract")
async def re_extract_policy(
    policy_id: str,
    updated_prompt: Optional[str] = Body(None),
    admin_user_id: str = Header(..., alias="X-Admin-User-Id"),
    admin_email: str = Header(..., alias="X-Admin-Email"),
) -> Dict:
    """
    Trigger re-extraction of a policy.
    
    Body:
    - updated_prompt: Optional custom extraction prompt template
    
    Returns: Re-extraction job info
    """
    from antonrx_backend.admin.admin_service import admin_service

    try:
        job = admin_service.start_re_extraction(
            policy_id=policy_id,
            document_text="",  # Fetch from DB in production
            updated_prompt=updated_prompt,
            admin_user_id=admin_user_id,
            admin_email=admin_email,
        )
        return {"success": True, "data": job}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# INGESTION QUEUE - Dashboard showing recent ingestions
# ============================================================================


@router.get("/queue")
async def get_ingestion_queue(
    status: Optional[str] = Query(None, description="Filter by status (pending/extracting/success/failed)"),
    limit: int = Query(50, ge=1, le=500),
) -> Dict:
    """
    Get ingestion queue status dashboard.
    
    Shows recent document ingestions, their status, and any errors.
    
    Query params:
    - status: Optional status filter
    - limit: Max records (default 50, max 500)
    """
    from antonrx_backend.admin.admin_service import admin_service

    try:
        queue_status = admin_service.get_ingestion_queue_status(
            status_filter=status,
            limit=limit,
        )
        return {"success": True, "data": queue_status}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# AUDIT LOGS - Complete audit trail
# ============================================================================


@router.get("/audit-logs")
async def get_audit_logs(
    admin_user_id: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    days_back: int = Query(30, ge=1, le=365),
    limit: int = Query(100, ge=1, le=1000),
) -> Dict:
    """
    Retrieve audit logs with filtering.
    
    Query params:
    - admin_user_id: Filter by specific admin
    - entity_type: Filter by entity type (policy, payer, extraction)
    - action: Filter by action (POLICY_DELETED, FIELD_OVERRIDDEN, etc.)
    - days_back: Look back this many days (default 30)
    - limit: Max records (default 100)
    """
    from antonrx_backend.admin.admin_service import admin_service

    try:
        logs = admin_service.get_audit_logs(
            admin_user_id=admin_user_id,
            entity_type=entity_type,
            action=action,
            days_back=days_back,
            limit=limit,
        )
        return {"success": True, "data": logs, "count": len(logs)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/audit-summary")
async def get_audit_summary(
    days: int = Query(30, ge=1, le=365),
) -> Dict:
    """Get summary of audit activities."""
    from antonrx_backend.admin.admin_service import admin_service

    try:
        summary = admin_service.get_audit_summary(days=days)
        return {"success": True, "data": summary}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# ANALYTICS & REPORTING
# ============================================================================


@router.get("/analytics/outliers")
async def detect_outliers(
    drug_name: str = Query(...),
    metric: str = Query("restrictiveness_score"),
) -> Dict:
    """
    Find policies that are statistical outliers (2+ std dev from mean).
    
    Query params:
    - drug_name: Required drug to analyze
    - metric: Metric to check (default: restrictiveness_score)
    """
    from antonrx_backend.analytics.analytics_service import analytics_service

    try:
        outliers = analytics_service.detect_outlier_policies(
            drug_name=drug_name,
            metric_name=metric,
        )
        return {
            "success": True,
            "drug": drug_name,
            "metric": metric,
            "outliers": outliers,
            "count": len(outliers),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/analytics/gaps")
async def get_coverage_gaps(
    drug: str = Query(...),
) -> Dict:
    """
    Find which payers don't cover a specific drug (coverage gaps).
    
    Query params:
    - drug: Required drug name
    """
    from antonrx_backend.analytics.analytics_service import analytics_service

    try:
        gaps = analytics_service.find_coverage_gaps(
            drug_name=drug,
            known_payers=None,  # In production, fetch all known payers
        )
        return {
            "success": True,
            "drug": drug,
            "gaps": gaps,
            "gap_count": len(gaps),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reports/quarterly")
async def get_quarterly_report(
    year: int = Query(...),
    quarter: int = Query(..., ge=1, le=4),
) -> Dict:
    """
    Get comprehensive quarterly change report.
    
    Query params:
    - year: Year (e.g., 2024)
    - quarter: Quarter 1-4
    
    Returns: Detailed report with changes, statistics, and trends
    """
    from antonrx_backend.analytics.analytics_service import analytics_service

    try:
        report = analytics_service.generate_quarterly_report(year=year, quarter=quarter)
        return {"success": True, "data": report}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/analytics/statistics")
async def get_policy_statistics() -> Dict:
    """Get overall statistics about policies in database."""
    from antonrx_backend.analytics.analytics_service import analytics_service

    try:
        stats = analytics_service.get_policy_statistics()
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/analytics/payer-rankings")
async def get_payer_restrictiveness_ranking(
    limit: int = Query(10, ge=1, le=100),
) -> Dict:
    """
    Rank payers by policy restrictiveness (most to least restrictive).
    
    Query params:
    - limit: Top N payers to return (default 10, max 100)
    """
    from antonrx_backend.analytics.analytics_service import analytics_service

    try:
        ranking = analytics_service.get_payer_restrictiveness_ranking(limit=limit)
        return {"success": True, "data": ranking}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# ENHANCED SEARCH with Filters
# ============================================================================


@router.get("/search/policies")
async def search_policies(
    q: Optional[str] = Query(None, description="Free-text search"),
    payer: Optional[str] = Query(None),
    drug: Optional[str] = Query(None),
    requires_prior_auth: Optional[bool] = Query(None),
    max_restrictiveness: Optional[float] = Query(None),
    min_confidence: Optional[float] = Query(None),
    max_copay: Optional[float] = Query(None),
    limit: int = Query(50, ge=1, le=500),
) -> Dict:
    """
    Search policies with multiple filter criteria.
    
    Query params:
    - q: Free-text search (matches drug/payer name)
    - payer: Filter by payer ID or name
    - drug: Filter by drug name
    - requires_prior_auth: Filter by prior auth requirement (true/false)
    - max_restrictiveness: Max restrictiveness score 0-100
    - min_confidence: Minimum extraction confidence 0-100
    - max_copay: Maximum copay amount
    - limit: Results limit (default 50)
    """
    from antonrx_backend.search.enhanced_search_service import enhanced_search_service

    try:
        results = enhanced_search_service.search_policies(
            query=q,
            payer=payer,
            drug=drug,
            requires_prior_auth=requires_prior_auth,
            max_restrictiveness_score=max_restrictiveness,
            min_confidence=min_confidence,
            max_copay=max_copay,
            limit=limit,
        )
        return {"success": True, "data": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/drug/{drug_name}/easiest")
async def find_easiest_approval_path(drug_name: str) -> Dict:
    """
    Find the payer with easiest approval for a drug (lowest restrictiveness).
    
    Returns: Single payer with lowest restrictiveness score and fewest criteria
    """
    from antonrx_backend.search.enhanced_search_service import enhanced_search_service

    try:
        result = enhanced_search_service.find_easiest_approval_path(drug_name)
        if not result:
            raise HTTPException(status_code=404, detail=f"No policies found for {drug_name}")
        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# NATURAL LANGUAGE Q&A CHAT
# ============================================================================


@router.post("/chat")
async def chat_with_policies(
    session_id: str = Query(...),
    message: str = Body(...),
) -> Dict:
    """
    Natural language Q&A with conversation history.
    
    Maintains conversation context for follow-up questions.
    
    Query params:
    - session_id: Conversation session ID (use same for follow-ups)
    
    Body:
    - message: User's question
    """
    from antonrx_backend.search.enhanced_search_service import enhanced_search_service

    try:
        response = enhanced_search_service.chat_with_policies(
            session_id=session_id,
            user_message=message,
        )
        return {"success": True, "data": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/chat/history")
async def get_chat_history(
    session_id: str = Query(...),
    limit: int = Query(20, ge=1, le=100),
) -> Dict:
    """Get conversation history for a chat session."""
    from antonrx_backend.search.enhanced_search_service import enhanced_search_service

    try:
        history = enhanced_search_service.get_conversation_history(
            session_id=session_id,
            limit=limit,
        )
        return {"success": True, "data": history, "count": len(history)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# WEBHOOKS - Register and Manage
# ============================================================================


@router.post("/webhooks/register")
async def register_webhook(
    webhook_url: str = Body(...),
    event_types: List[str] = Body(...),
    admin_user_id: str = Header(..., alias="X-Admin-User-Id"),
) -> Dict:
    """
    Register a webhook endpoint for notifications.
    
    Body:
    - webhook_url: URL to POST events to
    - event_types: List of event types to subscribe to
              Options: ["policy_change", "new_coverage", "outlier_detected", "price_update"]
    
    Headers:
    - X-Admin-User-Id: Admin's user ID
    """
    from antonrx_backend.webhooks.webhook_service import webhook_service

    try:
        webhook = webhook_service.register_webhook(
            admin_id=admin_user_id,
            webhook_url=webhook_url,
            event_types=event_types,
        )
        return {"success": True, "data": webhook}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/webhooks/{webhook_id}")
async def unregister_webhook(webhook_id: str) -> Dict:
    """Unregister a webhook."""
    from antonrx_backend.webhooks.webhook_service import webhook_service

    try:
        webhook = webhook_service.unregister_webhook(webhook_id)
        return {"success": True, "data": webhook}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/webhooks")
async def list_webhooks(
    admin_user_id: str = Header(..., alias="X-Admin-User-Id"),
) -> Dict:
    """List all webhooks for an admin."""
    from antonrx_backend.webhooks.webhook_service import webhook_service

    try:
        webhooks = webhook_service.get_webhooks(admin_id=admin_user_id)
        return {"success": True, "data": webhooks, "count": len(webhooks)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/webhooks/{webhook_id}/deliveries")
async def get_webhook_delivery_history(
    webhook_id: str,
    limit: int = Query(50, ge=1, le=500),
) -> Dict:
    """Get delivery attempt history for a webhook."""
    from antonrx_backend.webhooks.webhook_service import webhook_service

    try:
        history = webhook_service.get_delivery_history(webhook_id, limit)
        return {"success": True, "data": history, "count": len(history)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhooks/retry-failed")
async def retry_failed_webhook_deliveries() -> Dict:
    """Retry delivery for all failed webhooks."""
    from antonrx_backend.webhooks.webhook_service import webhook_service

    try:
        result = webhook_service.retry_failed_deliveries()
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# DUPLICATE DETECTION
# ============================================================================


@router.post("/documents/check-duplicate")
async def check_document_duplicate(
    document_checksum: str = Body(...),
) -> Dict:
    """
    Check if a document has already been extracted (by checksum).
    
    Avoids re-extracting the same document and saves Claude API costs.
    
    Body:
    - document_checksum: SHA256 checksum of document text
    """
    from antonrx_backend.analytics.analytics_service import analytics_service

    try:
        result = analytics_service.detect_duplicate_extractions(document_checksum)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
