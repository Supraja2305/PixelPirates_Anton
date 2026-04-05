# models/policy.py
# ============================================================
# Pydantic models (data shapes) for everything related to a
# medical benefit drug policy.
# ============================================================

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


# ── Enums ─────────────────────────────────────────────────────

class CoverageStatus(str, Enum):
    COVERED = "covered"
    NOT_COVERED = "not_covered"
    COVERED_WITH_RESTRICTIONS = "covered_with_restrictions"
    INVESTIGATIONAL = "investigational"
    UNKNOWN = "unknown"


class CriteriaType(str, Enum):
    PRIOR_AUTH = "prior_authorization"
    STEP_THERAPY = "step_therapy"
    DIAGNOSIS_REQUIRED = "diagnosis_required"
    LAB_REQUIRED = "lab_required"
    PRESCRIBER_SPECIALTY = "prescriber_specialty"
    SITE_OF_CARE = "site_of_care"
    QUANTITY_LIMIT = "quantity_limit"
    AGE_RESTRICTION = "age_restriction"
    OTHER = "other"


# ── Sub-models ────────────────────────────────────────────────

class ClinicalCriteria(BaseModel):
    """One individual coverage criterion from a policy."""
    criteria_type: CriteriaType
    raw_text: str = Field(..., description="Original text from the policy document")
    normalized_text: str = Field("", description="Standardized version of the criterion")
    required: bool = True
    notes: Optional[str] = None


class DrugInfo(BaseModel):
    """Drug identity info extracted from a policy."""
    brand_name: Optional[str] = None
    generic_name: Optional[str] = None
    canonical_name: str = Field(..., description="Normalized drug name after lookup")
    jcode: Optional[str] = Field(None, description="HCPCS J-code, e.g. J9035")
    aliases: list[str] = Field(default_factory=list)


class PolicyVersion(BaseModel):
    """Metadata about a specific version of a policy."""
    version_id: str
    policy_id: str
    effective_date: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source_file: Optional[str] = None
    checksum: Optional[str] = None   # SHA-256 of raw text — used for change detection


# ── Main Policy Model ─────────────────────────────────────────

class Policy(BaseModel):
    """
    The core data model. One Policy = one drug at one payer.
    This is what gets stored in Firestore after full extraction + normalization.
    """
    # Identity
    policy_id: str = Field(..., description="Unique ID: payer_drug_version")
    payer_name: str = Field(..., description="Health plan name, e.g. UnitedHealthcare")
    payer_id: str = Field(..., description="Normalized payer slug, e.g. uhc")
    document_title: Optional[str] = None
    policy_number: Optional[str] = None
    source_url: Optional[str] = None
    source_file: Optional[str] = None

    # Drug
    drug: DrugInfo

    # Coverage
    coverage_status: CoverageStatus = CoverageStatus.UNKNOWN
    covered_indications: list[str] = Field(
        default_factory=list,
        description="List of diagnoses/conditions for which drug is covered"
    )
    excluded_indications: list[str] = Field(default_factory=list)

    # Clinical criteria
    criteria: list[ClinicalCriteria] = Field(default_factory=list)
    requires_prior_auth: bool = False
    requires_step_therapy: bool = False

    # Site of care
    site_of_care_restrictions: list[str] = Field(default_factory=list)

    # Scoring (filled in by scoring engine)
    restrictiveness_score: Optional[float] = Field(
        None,
        ge=0.0, le=10.0,
        description="0 = least restrictive, 10 = most restrictive"
    )

    # Versioning
    effective_date: Optional[str] = None
    last_updated: Optional[str] = None
    version_id: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Embedding (stored separately but referenced here)
    embedding_id: Optional[str] = None


# ── Request / Input Models ────────────────────────────────────

class IngestRequest(BaseModel):
    """Metadata sent alongside a file upload."""
    payer_name: str
    payer_id: str
    source_url: Optional[str] = None


class CompareRequest(BaseModel):
    """Request to compare policies for a given drug across payers."""
    drug_name: str
    payer_ids: Optional[list[str]] = Field(
        default=None,
        description="If None, compare across all available payers"
    )


class SearchRequest(BaseModel):
    """Natural language search query."""
    query: str
    top_k: int = Field(default=5, ge=1, le=20)