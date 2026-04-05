"""
Response Models for Anton RX API
Defines all standardized API response structures
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ════════════════════════════════════════════════════════════════
# Base Response Models
# ════════════════════════════════════════════════════════════════

class SuccessResponse(BaseModel):
    """Standard success response wrapper."""
    success: bool = True
    message: str
    data: Optional[Any] = None
    timestamp: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response wrapper."""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    success: bool = True
    data: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


# ════════════════════════════════════════════════════════════════
# Policy Comparison Responses
# ════════════════════════════════════════════════════════════════

class DifferenceDetail(BaseModel):
    """Details of a single difference between policies."""
    field: str
    old_value: Any
    new_value: Any
    change_type: str  # "added", "removed", "modified"
    severity: str = "medium"  # "low", "medium", "high"


class PolicyComparisonResponse(BaseModel):
    """Response for policy comparison."""
    policy_1_id: str
    policy_2_id: str
    differences: List[DifferenceDetail]
    similarity_score: float = Field(..., ge=0, le=1)
    total_differences: int
    high_priority_differences: int


# ════════════════════════════════════════════════════════════════
# Scoring Responses
# ════════════════════════════════════════════════════════════════

class ScoringResult(BaseModel):
    """Result of policy scoring."""
    policy_id: str
    score: float = Field(..., ge=0, le=100)
    rank: int
    category: str  # "excellent", "good", "fair", "poor"
    breakdown: Dict[str, float]  # Scores per criterion


class SearchResult(BaseModel):
    """Single search result."""
    policy_id: str
    policy_name: str
    payer_id: str
    payer_name: str
    relevance_score: float = Field(..., ge=0, le=1)
    match_reasons: List[str]
    coverage_details: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    """Response for search query."""
    query: str
    results: List[SearchResult]
    total_results: int
    execution_time_ms: float


# ════════════════════════════════════════════════════════════════
# Alert Responses
# ════════════════════════════════════════════════════════════════

class AlertDetail(BaseModel):
    """Details of a single alert."""
    alert_id: str
    alert_type: str  # "policy_change", "new_coverage", "price_update", etc.
    severity: str = "info"  # "info", "warning", "critical"
    title: str
    description: str
    related_policy_ids: List[str] = []
    created_at: str
    resolved: bool = False


class AlertResponse(BaseModel):
    """Response containing alert information."""
    alerts: List[AlertDetail]
    total_alerts: int
    unresolved_count: int


# ════════════════════════════════════════════════════════════════
# Embedding Responses
# ════════════════════════════════════════════════════════════════

class EmbeddingResponse(BaseModel):
    """Response containing embedding data."""
    item_id: str
    item_type: str  # "policy", "drug", "coverage"
    embedding: List[float]
    embedding_model: str
    created_at: str


# ════════════════════════════════════════════════════════════════
# Extraction Responses
# ════════════════════════════════════════════════════════════════

class ExtractionResult(BaseModel):
    """Result of AI-powered extraction from document."""
    document_id: str
    extraction_type: str  # "policy_rules", "coverage_details", "requirements"
    extracted_data: Dict[str, Any]
    confidence_score: float = Field(..., ge=0, le=1)
    model_used: str
    extraction_time_ms: float


# ════════════════════════════════════════════════════════════════
# Sync/Ingestion Responses
# ════════════════════════════════════════════════════════════════

class IngestResponse(BaseModel):
    """Response from data ingestion."""
    items_processed: int
    items_created: int
    items_updated: int
    items_failed: int
    errors: List[str] = []
    execution_time_ms: float


# ════════════════════════════════════════════════════════════════
# Health Check Response
# ════════════════════════════════════════════════════════════════

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    timestamp: str
    version: str
    services: Dict[str, str] = Field(default_factory=dict)
