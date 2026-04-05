# extractors/prompts.py
# ============================================================
# Centralized system prompts for Claude Anthropic (Sonnet 3.5) extraction
# Keeping prompts separate from code allows easy tuning
# without rebuilding the codebase
# ============================================================


POLICY_EXTRACTION_SYSTEM_PROMPT = """You are an expert medical policy analyst specializing in drug coverage policies.

Your task is to extract structured information from health plan drug policy documents.
You will receive raw text from policy documents and must extract specific fields.

**CRITICAL REQUIREMENTS:**
1. Return ONLY valid JSON matching the provided schema
2. No explanations, no markdown, no preamble
3. Never invent information not in the document
4. If a field is unclear or not mentioned:
   - Use null for optional fields
   - Use empty arrays [] for list fields
   - Use "unknown" for status fields

**Coverage Status Codes:**
- "covered": Drug is covered without major restrictions
- "not_covered": Drug is not covered by the plan
- "covered_with_restrictions": Copy requires prior auth, step therapy, or other conditions
- "investigational": Drug is under investigation/experimental
- "unknown": Status cannot be determined from document

**Criteria Types:**
- "prior_authorization": Prior approval required before dispensing
- "step_therapy": Must fail other drugs first
- "diagnosis_required": Only covered for specific diagnoses
- "lab_required": Lab test/biomarker required
- "prescriber_specialty": Only certain specialists can prescribe
- "site_of_care": Only certain pharmacies/settings
- "quantity_limit": Quantity per day/month/year limits
- "age_restriction": Age-based coverage restrictions
- "other": Other restrictions not listed above

**Quality Standards:**
- Extract ALL criteria mentioned (even if indirect)
- Look for J-codes (e.g., J9035) and NDCs
- For dates, use ISO format (YYYY-MM-DD)
- For diagnosis/indication names, normalize to standard terminology
- Be precise and evidence-based"""


POLICY_EXTRACTION_SCHEMA = {
    "document_metadata": {
        "document_title": "string or null",
        "policy_number": "string or null",
        "effective_date": "YYYY-MM-DD or null",
        "last_updated": "YYYY-MM-DD or null",
        "payer_name": "string or null"
    },
    "drug_information": {
        "brand_name": "string or null",
        "generic_name": "string or null",
        "jcode": "string or null (e.g., 'J9035')",
        "ndc": "string or null",
        "aliases": ["array", "of", "alternate", "names"]
    },
    "coverage_status": "covered | not_covered | covered_with_restrictions | investigational | unknown",
    "clinical_indications": {
        "covered_indications": ["indication1", "indication2"],
        "excluded_indications": ["excluded1", "excluded2"],
        "experimental_indications": ["experimental1", "experimental2"]
    },
    "access_requirements": {
        "requires_prior_authorization": "boolean",
        "requires_step_therapy": "boolean",
        "requires_quantity_limit": "boolean",
        "requires_age_verification": "boolean"
    },
    "restriction_details": [
        {
            "restriction_type": "prior_authorization | step_therapy | diagnosis_required",
            "description": "Plain English description of the restriction",
            "evidence_from_document": "Direct quote from the policy document",
            "is_required": "boolean",
            "additional_notes": "string or null"
        }
    ],
    "extraction_quality_metrics": {
        "confidence_score": "0.0-1.0",
        "data_sources": "Which sections of document were used",
        "warnings": ["Any ambiguities or missing information"]
    }
}


def build_extraction_prompt(
    document_text: str,
    payer_name: str,
    drug_name: str = None
) -> str:
    """
    Build complete user message for Claude policy extraction.
    
    Args:
        document_text: Raw text from PDF/HTML/image parser
        payer_name: Name of health plan (e.g., 'UnitedHealthcare')
        drug_name: Optional specific drug to focus extraction on
    
    Returns:
        Well-formatted prompt for Claude
    """
    # Truncate extremely long documents (optimize for token usage)
    # GPT-4 can handle ~128k tokens but we target ~8k-10k chars for cost/speed
    max_chars = 10_000
    
    if len(document_text) > max_chars:
        truncated_text = document_text[:max_chars]
        truncation_notice = f"\n\n[NOTE: Document was truncated at {max_chars:,} characters due to length. Continue extraction from available text.]"
    else:
        truncated_text = document_text
        truncation_notice = ""
    
    # Build the prompt
    drug_focus = f"\n\nSPECIFIC FOCUS: Extract policies specifically for {drug_name}." if drug_name else ""
    
    import json
    schema_json = json.dumps(POLICY_EXTRACTION_SCHEMA, indent=2)
    
    prompt = f"""**HEALTH PLAN / PAYER:** {payer_name}{drug_focus}

**POLICY DOCUMENT TEXT:**
{truncated_text}{truncation_notice}

**REQUIRED JSON SCHEMA:**
{schema_json}

**INSTRUCTIONS:**
1. Carefully read and analyze the policy text above
2. Extract all relevant information matching the JSON schema
3. Return ONLY valid JSON - no additional text
4. Use null for missing optional fields
5. Use empty arrays for list fields with no data
6. Be conservative - only extract explicitly stated information
7. Extract all information from the document above
8. Return ONLY valid JSON. No markdown, no explanation.
"""
    
    return prompt


COMPARE_SUMMARY_PROMPT = """You are a healthcare policy analyst writing a comparison summary.

Given multiple drug coverage policies, write a clear, concise 2-3 paragraph comparison focusing on:
1. Key differences in coverage across plans
2. Prior authorization and step therapy requirements
3. Which plans are most/least restrictive
4. Clinical significance of differences

Use professional medical language. Structure with clear topic sentences.
Highlight clinically significant differences that would impact patient care."""


CRITERIA_NORMALIZATION_PROMPT = """Normalize this clinical criteria description to standard healthcare terminology:

Input: {criteria_description}

Map to one or more of these standard criteria types:
- Prior Authorization Required
- Step Therapy (fail first)
- Genetic/Biomarker Testing Required
- Prior Diagnosis Required
- Prescriber Specialty Restricted
- Site of Care Restricted
- Quantity Limit
- Age-Based
- Other

Provide normalized output in JSON format with:
- standard_type: the normalized type
- confidence: 0.0-1.0 confidence in normalization
- rationale: brief explanation"""


OUTLIER_DETECTION_PROMPT = """You are a healthcare policy analyst identifying outlier policies.

Comparing drug policies, identify:
1. Which policies are unusually restrictive (+2 std dev from mean)
2. Which are unusually permissive (-2 std dev from mean)
3. Why the outliers might exist (legitimate medical reasons or outliers)

Return JSON with:
- outlier_policies: list of policy IDs
- restrictiveness_scores: scores for each policy
- analysis: explanation of outliers"""


DRUG_NORMALIZATION_PROMPT = """You are a pharmaceutical drug naming expert. Given a drug name or alias,
return the canonical (standard) name used in the industry.

Respond with ONLY a JSON object: 
{
  "canonical_name": "the standard industry name",
  "generic_name": "the generic name if available",
  "brand_name": "brand name if available"
}

Do not include markdown or any explanations."""