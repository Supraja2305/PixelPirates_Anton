# api/drug.py  ── GET /api/drug/{name}
# ============================================================
from fastapi import APIRouter, Depends
from ..auth.middleware import get_current_user
from ..models.user import TokenData
from ..storage.firestore_client import get_policies_by_drug
from ..scoring.scoring_engine import rank_policies_by_restrictiveness
from ..normalizers.drug_normalizer import normalize_drug_name

router = APIRouter(prefix="/api/drug", tags=["Drug"])


@router.get("/{drug_name}", summary="Get all payer policies for a drug")
async def get_drug_coverage(
    drug_name: str,
    user: TokenData = Depends(get_current_user),
):
    """
    Return all payer policies for a given drug, ranked from
    least to most restrictive.

    Steps:
    1. Normalize the drug name (handles aliases).
    2. Query Firestore for all policies matching that drug.
    3. Rank by restrictiveness score.
    4. Return ranked list.

    Example: GET /api/drug/adalimumab
    Example: GET /api/drug/Humira   ← also works (normalized)
    """
    # Normalize input so "Humira" and "adalimumab" both work
    canonical = normalize_drug_name(drug_name)

    policies = get_policies_by_drug(canonical)

    if not policies:
        return {
            "drug": canonical,
            "policies_found": 0,
            "policies": [],
            "message": f"No policies found for '{canonical}'",
        }

    # Rank by restrictiveness
    ranked = rank_policies_by_restrictiveness(policies)

    return {
        "drug": canonical,
        "policies_found": len(ranked),
        "policies": ranked,
    }