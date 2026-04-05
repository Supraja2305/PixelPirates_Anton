# normalizers/criteria_normalizer.py
# ============================================================
# Normalize clinical criteria text so we can compare
# apples-to-apples across payers.
#
# The same requirement might be written as:
#   UHC:    "Patient must have tried and failed methotrexate"
#   Cigna:  "Inadequate response or intolerance to MTX"
#   Aetna:  "Failure of conventional DMARD therapy (e.g., MTX)"
#
# We normalize these to: "Step therapy: prior DMARD failure required"
# ============================================================

import re
from ..models.policy import ClinicalCriteria, CriteriaType


# ── Mapping tables ────────────────────────────────────────────

# Keywords → CriteriaType classification
_CRITERIA_TYPE_KEYWORDS: dict[CriteriaType, list[str]] = {
    CriteriaType.PRIOR_AUTH: [
        "prior authorization", "prior auth", "pa required",
        "preauthorization", "pre-authorization", "pre authorization",
        "requires approval", "must be approved"
    ],
    CriteriaType.STEP_THERAPY: [
        "step therapy", "step edit", "tried and failed",
        "inadequate response", "failure of", "must have tried",
        "prior treatment", "first-line", "second-line",
        "preferred agent", "dmard", "biosimilar first"
    ],
    CriteriaType.DIAGNOSIS_REQUIRED: [
        "diagnosis of", "confirmed diagnosis", "diagnosed with",
        "indicated for", "icd-10", "icd10", "condition",
        "indication", "disease", "disorder"
    ],
    CriteriaType.LAB_REQUIRED: [
        "lab", "laboratory", "blood test", "test result",
        "hba1c", "creatinine", "cbc", "serum", "level",
        "biomarker", "genetic test", "expression"
    ],
    CriteriaType.PRESCRIBER_SPECIALTY: [
        "prescriber", "specialist", "oncologist", "rheumatologist",
        "dermatologist", "neurologist", "gastroenterologist",
        "prescribed by", "ordered by", "specialty"
    ],
    CriteriaType.SITE_OF_CARE: [
        "site of care", "place of service", "infusion center",
        "outpatient", "physician office", "home infusion",
        "hospital outpatient", "ambulatory", "administered at"
    ],
    CriteriaType.QUANTITY_LIMIT: [
        "quantity limit", "dose limit", "frequency limit",
        "maximum dose", "units per", "per month", "per year",
        "not to exceed", "limit of"
    ],
    CriteriaType.AGE_RESTRICTION: [
        "age", "years old", "adult", "pediatric", "child",
        "18 years", "≥18", "≤18", "years of age"
    ],
}

# Normalized text patterns for common step therapy requirements
_STEP_THERAPY_NORMALIZATIONS = [
    (r"tried?\s+and\s+fail(ed)?", "failure of prior therapy"),
    (r"inadequate\s+response\s+to", "failure of"),
    (r"intolerance\s+to", "intolerance to"),
    (r"methotrexate|mtx", "methotrexate (MTX)"),
    (r"conventional\s+dmard", "conventional DMARD"),
    (r"first.?line\s+therapy", "first-line therapy"),
    (r"two\s+or\s+more|2\s+or\s+more", "≥2"),
]


def classify_criteria_type(text: str) -> CriteriaType:
    """
    Determine the type of a clinical criterion from its text.

    Steps:
    1. Lowercase the text.
    2. Check each keyword list for a match.
    3. Return the matching CriteriaType.
    4. Default to CriteriaType.OTHER if no match.

    Args:
        text: Raw criterion text from the policy.

    Returns:
        A CriteriaType enum value.

    Examples:
        classify_criteria_type("Patient must have tried methotrexate")
        → CriteriaType.STEP_THERAPY

        classify_criteria_type("Prior authorization required")
        → CriteriaType.PRIOR_AUTH
    """
    text_lower = text.lower()

    for criteria_type, keywords in _CRITERIA_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return criteria_type

    return CriteriaType.OTHER


def normalize_criteria_text(raw_text: str) -> str:
    """
    Standardize the wording of a clinical criterion.

    Steps:
    1. Clean whitespace.
    2. Apply normalization regex replacements.
    3. Title-case where appropriate.
    4. Return standardized text.

    This helps us identify when two payers have the "same" requirement
    even if they wrote it differently.
    """
    if not raw_text:
        return ""

    # Clean whitespace
    text = " ".join(raw_text.split())

    # Apply step therapy normalizations
    for pattern, replacement in _STEP_THERAPY_NORMALIZATIONS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Standardize yes/no
    text = re.sub(r'\byes\b', 'Yes', text, flags=re.IGNORECASE)
    text = re.sub(r'\brequired\b', 'required', text, flags=re.IGNORECASE)

    return text.strip()


def normalize_criteria_list(criteria_data: list[dict]) -> list[ClinicalCriteria]:
    """
    Normalize a list of raw criteria dicts (from Claude extraction)
    into proper ClinicalCriteria model objects.

    Steps:
    1. For each raw criterion dict:
       a. Classify its type (if not already classified).
       b. Normalize its text.
       c. Create a ClinicalCriteria object.
    2. Return the list.

    Args:
        criteria_data: List of raw dicts from Claude extraction.
        Example: [{"raw_text": "...", "criteria_type": "...", ...}, ...]

    Returns:
        List of ClinicalCriteria model objects.
    """
    normalized = []

    for raw in criteria_data:
        raw_text = raw.get("raw_text", "")

        # Classify type — use Claude's suggestion if valid, else re-classify
        try:
            criteria_type = CriteriaType(raw.get("criteria_type", "other"))
        except ValueError:
            criteria_type = classify_criteria_type(raw_text)

        # Normalize the text
        normalized_text = normalize_criteria_text(raw_text)

        criterion = ClinicalCriteria(
            criteria_type=criteria_type,
            raw_text=raw_text,
            normalized_text=normalized_text,
            required=raw.get("required", True),
            notes=raw.get("notes"),
        )
        normalized.append(criterion)

    return normalized