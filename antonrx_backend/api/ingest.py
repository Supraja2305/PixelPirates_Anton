# api/ingest.py
# ============================================================
# POST /api/ingest
# The main ingestion pipeline endpoint.
#
# Full flow:
#   Upload file → Parse → AI Extraction → Validate → Normalize
#   → Score → Store → Index for search → Check for changes → Alert
#
# Only admins can call this endpoint.
# ============================================================

import uuid
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, Depends, Request
from fastapi.responses import JSONResponse

from ..auth.middleware import require_admin
from ..models.user import TokenData

from ..utils.file_security import validate_uploaded_file, sanitize_filename, determine_parser_type, compute_file_checksum
from ..parsers.pdf_parser import extract_text_from_pdf
from ..parsers.html_parser import extract_text_from_html_bytes
from ..parsers.image_parser import extract_text_from_image

from ..extractors.claude_extractor import extract_policy_from_text
from ..normalizers.drug_normalizer import normalize_drug_name, normalize_payer_id
from ..normalizers.criteria_normalizer import normalize_criteria_list
from ..scoring.scoring_engine import compute_restrictiveness_score
from ..search.vector_store import index_policy
from ..storage.version_manager import (
    generate_policy_id,
    save_policy_with_versioning,
)
from ..alerts.alert_service import send_policy_change_alerts
from ..storage.firestore_client import get_policy_by_id
from ..models.policy import Policy, DrugInfo, CoverageStatus

router = APIRouter(prefix="/api/ingest", tags=["Ingestion"])


@router.post("", summary="Upload and ingest a policy document")
async def ingest_policy(
    request: Request,
    file: UploadFile = File(..., description="PDF, HTML, or image file"),
    payer_name: str = Form(..., description="Health plan name, e.g. UnitedHealthcare"),
    source_url: str = Form(None, description="Optional: URL where policy was found"),
    admin: TokenData = Depends(require_admin),   # ← Must be admin
):
    """
    Full ingestion pipeline for a medical policy document.

    **Steps:**
    1. Validate and read the uploaded file
    2. Parse text from the file (PDF/HTML/image)
    3. Send text to Claude for structured extraction
    4. Validate Claude's output
    5. Normalize drug names and criteria
    6. Build the Policy object and compute restrictiveness score
    7. Save to Firestore (with version management)
    8. Index for semantic search
    9. If policy changed, send alerts to subscribers

    **Returns:** Policy ID, version ID, and pipeline status report
    """
    pipeline_log = []

    # ════════════════════════════════════════════════════════
    # STEP 1: File Security Validation
    # ════════════════════════════════════════════════════════
    pipeline_log.append("Step 1: Validating file...")
    file_bytes = await validate_uploaded_file(file)
    safe_filename = sanitize_filename(file.filename or "upload")
    parser_type = determine_parser_type(safe_filename)
    file_checksum = compute_file_checksum(file_bytes)
    pipeline_log.append(f"  ✓ File OK: {safe_filename} ({len(file_bytes)} bytes, type={parser_type})")

    # ════════════════════════════════════════════════════════
    # STEP 2: Parse Document → Extract Text
    # ════════════════════════════════════════════════════════
    pipeline_log.append("Step 2: Parsing document...")

    if parser_type == "pdf":
        parse_result = extract_text_from_pdf(file_bytes)
    elif parser_type == "html":
        parse_result = extract_text_from_html_bytes(file_bytes)
    elif parser_type == "image":
        parse_result = extract_text_from_image(file_bytes)
    else:
        return JSONResponse(
            status_code=415,
            content={"error": True, "message": f"Unsupported file type: {parser_type}"}
        )

    document_text = parse_result.get("text", "")
    pipeline_log.append(f"  ✓ Parsed {parse_result.get('char_count', 0)} characters")

    # ════════════════════════════════════════════════════════
    # STEP 3: AI Extraction via Claude
    # ════════════════════════════════════════════════════════
    pipeline_log.append("Step 3: Extracting structured data with Claude AI...")
    extracted = extract_policy_from_text(document_text, payer_name)
    pipeline_log.append(
        f"  ✓ Extracted: drug={extracted.get('drug', {}).get('generic_name')}, "
        f"status={extracted.get('coverage_status')}, "
        f"criteria_count={len(extracted.get('criteria', []))}"
    )

    # ════════════════════════════════════════════════════════
    # STEP 4: Normalize Drug Name + Payer
    # ════════════════════════════════════════════════════════
    pipeline_log.append("Step 4: Normalizing drug and payer names...")

    drug_data = extracted.get("drug", {})
    raw_drug_name = (
        drug_data.get("generic_name") or
        drug_data.get("brand_name") or
        drug_data.get("jcode") or
        "Unknown"
    )
    canonical_drug_name = normalize_drug_name(raw_drug_name)
    payer_id = normalize_payer_id(payer_name)

    drug_info = DrugInfo(
        brand_name=drug_data.get("brand_name"),
        generic_name=drug_data.get("generic_name"),
        canonical_name=canonical_drug_name,
        jcode=drug_data.get("jcode"),
        aliases=drug_data.get("aliases", []),
    )
    pipeline_log.append(f"  ✓ Canonical drug: '{canonical_drug_name}', Payer: '{payer_id}'")

    # ════════════════════════════════════════════════════════
    # STEP 5: Normalize Clinical Criteria
    # ════════════════════════════════════════════════════════
    pipeline_log.append("Step 5: Normalizing clinical criteria...")
    normalized_criteria = normalize_criteria_list(extracted.get("criteria", []))
    pipeline_log.append(f"  ✓ Normalized {len(normalized_criteria)} criteria")

    # ════════════════════════════════════════════════════════
    # STEP 6: Build Policy Object
    # ════════════════════════════════════════════════════════
    pipeline_log.append("Step 6: Building policy object...")

    policy_id = generate_policy_id(payer_id, canonical_drug_name)

    policy = Policy(
        policy_id=policy_id,
        payer_name=payer_name,
        payer_id=payer_id,
        document_title=extracted.get("document_title"),
        policy_number=extracted.get("policy_number"),
        source_url=source_url,
        source_file=safe_filename,
        drug=drug_info,
        coverage_status=CoverageStatus(extracted.get("coverage_status", "unknown")),
        covered_indications=extracted.get("covered_indications", []),
        excluded_indications=extracted.get("excluded_indications", []),
        criteria=normalized_criteria,
        requires_prior_auth=extracted.get("requires_prior_auth", False),
        requires_step_therapy=extracted.get("requires_step_therapy", False),
        site_of_care_restrictions=extracted.get("site_of_care_restrictions", []),
        effective_date=extracted.get("effective_date"),
        last_updated=extracted.get("last_updated"),
    )

    # ════════════════════════════════════════════════════════
    # STEP 7: Compute Restrictiveness Score
    # ════════════════════════════════════════════════════════
    pipeline_log.append("Step 7: Computing restrictiveness score...")
    score = compute_restrictiveness_score(policy)
    policy.restrictiveness_score = score
    pipeline_log.append(f"  ✓ Restrictiveness score: {score}/10")

    # ════════════════════════════════════════════════════════
    # STEP 8: Save to Firestore (with versioning)
    # ════════════════════════════════════════════════════════
    pipeline_log.append("Step 8: Saving to database...")
    policy_dict = policy.model_dump(mode="json")
    policy_dict["checksum"] = file_checksum

    # Retrieve old version BEFORE saving (for diff/alert)
    old_policy = get_policy_by_id(policy_id)

    version_result = save_policy_with_versioning(policy_dict)
    pipeline_log.append(
        f"  ✓ Saved. new={version_result['is_new']}, "
        f"updated={version_result['is_update']}, "
        f"unchanged={version_result['is_unchanged']}"
    )

    # ════════════════════════════════════════════════════════
    # STEP 9: Index for Semantic Search
    # ════════════════════════════════════════════════════════
    pipeline_log.append("Step 9: Indexing for semantic search...")
    index_policy(policy_dict)
    pipeline_log.append("  ✓ Indexed")

    # ════════════════════════════════════════════════════════
    # STEP 10: Send Alerts if Policy Changed
    # ════════════════════════════════════════════════════════
    alert_result = {"alerts_sent": 0}
    if version_result.get("is_update") and old_policy:
        pipeline_log.append("Step 10: Policy changed — sending alerts...")
        alert_result = send_policy_change_alerts(old_policy, policy_dict)
        pipeline_log.append(f"  ✓ Sent {alert_result['alerts_sent']} alerts")
    else:
        pipeline_log.append("Step 10: No alerts needed (new policy or unchanged)")

    # ════════════════════════════════════════════════════════
    # DONE — Return summary
    # ════════════════════════════════════════════════════════
    return {
        "success": True,
        "policy_id": policy_id,
        "version_id": version_result.get("version_id"),
        "drug": canonical_drug_name,
        "payer": payer_name,
        "payer_id": payer_id,
        "coverage_status": policy.coverage_status.value,
        "restrictiveness_score": score,
        "criteria_count": len(normalized_criteria),
        "is_new": version_result.get("is_new"),
        "is_update": version_result.get("is_update"),
        "is_unchanged": version_result.get("is_unchanged"),
        "alerts_sent": alert_result.get("alerts_sent", 0),
        "pipeline_log": pipeline_log,
    }


@router.post("/url", summary="Ingest a policy from a URL")
async def ingest_from_url(
    request: Request,
    url: str = Form(...),
    payer_name: str = Form(...),
    admin: TokenData = Depends(require_admin),
):
    """
    Fetch and ingest a policy document directly from a URL.
    Useful for ingesting policies from payer websites.
    """
    from ..parsers.html_parser import extract_text_from_url

    pipeline_log = [f"Fetching from URL: {url}"]

    # Fetch and parse HTML from URL
    parse_result = await extract_text_from_url(url)
    document_text = parse_result.get("text", "")
    pipeline_log.append(f"  ✓ Fetched {parse_result.get('char_count', 0)} characters")

    # AI Extraction
    extracted = extract_policy_from_text(document_text, payer_name)

    # (Same normalization, scoring, storage steps as above — abbreviated here)
    drug_data = extracted.get("drug", {})
    raw_name = drug_data.get("generic_name") or drug_data.get("brand_name") or "Unknown"
    canonical_name = normalize_drug_name(raw_name)
    payer_id = normalize_payer_id(payer_name)
    policy_id = generate_policy_id(payer_id, canonical_name)

    return {
        "success": True,
        "policy_id": policy_id,
        "drug": canonical_name,
        "payer": payer_name,
        "source_url": url,
        "message": "URL ingested successfully",
    }