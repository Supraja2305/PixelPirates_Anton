"""
Extended database models for policy versioning, audit logging, and analytics
Includes soft delete support, change tracking, and admin controls
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import uuid


class PolicyVersion(BaseModel):
    """Stores complete history of policy changes."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    policy_id: str
    version_number: int
    extracted_data: Dict
    checksum: str
    confidence_score: float
    extracted_by_user: str
    extraction_method: str  # "claude_extraction", "manual_upload", "api_import"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_current: bool = True  # Latest version flag
    changes_summary: Optional[str] = None


class Policy(BaseModel):
    """Enhanced policy model with soft delete and versioning."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    payer_id: str
    payer_name: str
    policy_name: str
    effective_date: datetime
    
    # Soft delete support
    is_active: bool = True
    deactivated_at: Optional[datetime] = None
    deactivation_reason: Optional[str] = None
    
    # Content
    coverage_rules: Dict = Field(default_factory=dict)
    precertification_required: bool = False
    appeals_process: Optional[str] = None
    
    # Extraction tracking
    source_document_id: Optional[str] = None
    extraction_confidence: float = Field(..., ge=0, le=100)
    requires_human_review: bool = False
    reviewed_by: Optional[str] = None
    
    # Versioning
    current_version: int = 1
    version_id: str  # Points to current PolicyVersion
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = Field(default_factory=list)


class AuditLogAction(str, Enum):
    """Types of actions that get logged."""
    
    POLICY_CREATED = "policy_created"
    POLICY_UPDATED = "policy_updated"
    POLICY_DELETED = "policy_deleted"
    POLICY_SOFT_DELETED = "policy_soft_deleted"
    POLICY_ARCHIVED = "policy_archived"
    POLICY_RESTORED = "policy_restored"
    POLICY_FIELD_OVERRIDDEN = "policy_field_overridden"
    POLICY_RE_EXTRACTED = "policy_re_extracted"
    PAYER_ARCHIVED = "payer_archived"
    PAYER_BULK_ARCHIVED = "payer_bulk_archived"
    ADMIN_LOGIN = "admin_login"
    EXTRACTION_TRIGGERED = "extraction_triggered"


class AuditLog(BaseModel):
    """Complete audit trail of admin actions."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action: AuditLogAction
    admin_user_id: str
    admin_email: str
    entity_type: str  # "policy", "payer", "extraction", etc.
    entity_id: str
    changes: Dict = Field(default_factory=dict)  # What changed {field: {old, new}}
    metadata: Dict = Field(default_factory=dict)  # Additional context
    reason: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PolicyFlag(BaseModel):
    """Alerts admin about unusual policies."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    policy_id: str
    flag_type: str  # "outlier", "duplicate", "low_confidence", "missing_data"
    severity: str  # "info", "warning", "critical"
    metric: str  # What metric triggered the flag (e.g., "restrictiveness_score")
    metric_value: float
    average_value: Optional[float] = None  # For outlier detection
    std_deviation: Optional[float] = None
    description: str
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class IngestionJob(BaseModel):
    """Tracks document ingestion progress."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    file_name: str
    file_size_bytes: int
    checksum: str
    
    status: str  # "pending", "extracting", "success", "failed"
    extraction_method: str  # "claude_extraction", "manual_upload"
    
    created_policy_id: Optional[str] = None
    extraction_error: Optional[str] = None
    confidence_score: Optional[float] = None
    
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str  # Admin who uploaded


class CoverageGap(BaseModel):
    """Identifies drugs not covered by certain payers."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    drug_name: str
    drug_id: Optional[str] = None
    payer_id: str
    payer_name: str
    gap_type: str  # "not_ingested", "not_covered", "expired_policy"
    last_checked: datetime = Field(default_factory=datetime.utcnow)


class AnalyticsSnapshot(BaseModel):
    """Quarterly/monthly analytics for reporting."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    period: str  # "2024-Q1", "2024-03"
    period_start: datetime
    period_end: datetime
    
    total_policies_ingested: int = 0
    total_policy_changes: int = 0
    policies_archived: int = 0
    low_confidence_extractions: int = 0
    
    # Drug-specific
    drugs_tracked: int = 0
    drugs_with_coverage_gaps: int = 0
    
    # Flag statistics
    outlier_policies_flagged: int = 0
    
    # Top changes
    most_changed_drugs: List[Dict] = Field(default_factory=list)  # [{drug, count}]
    top_restrictive_payers: List[Dict] = Field(default_factory=list)  # [{payer, avg_restriciveness}]
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WebhookSubscription(BaseModel):
    """Webhook endpoints for policy change notifications."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    admin_id: str
    webhook_url: str
    event_types: List[str]  # ["policy_change", "new_coverage", "outlier_detected"]
    is_active: bool = True
    
    # Delivery tracking
    last_delivery_at: Optional[datetime] = None
    last_delivery_status: Optional[int] = None  # HTTP status code
    failed_attempts: int = 0
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PolicyChangeEvent(BaseModel):
    """Event payload for webhooks and internal event bus."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str  # "policy_change", "new_coverage", "outlier_detected"
    policy_id: str
    payer_id: str
    payer_name: str
    changes: Dict  # What changed
    severity: str  # "low", "medium", "high"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # For webhook retries
    delivered_to: List[str] = Field(default_factory=list)  # List of webhook IDs


class AdminSession(BaseModel):
    """Track admin access for security."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    admin_user_id: str
    admin_email: str
    ip_address: str
    user_agent: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    reason_ended: Optional[str] = None
