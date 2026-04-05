# api/payer.py  ── GET /api/payer/{payer_id}
# ============================================================
from fastapi import APIRouter, Depends
from ..auth.middleware import get_current_user
from ..models.user import TokenData
from ..storage.firestore_client import get_policies_by_payer
from ..normalizers.drug_normalizer import normalize_payer_id

router = APIRouter(prefix="/api/payer", tags=["Payer"])


@router.get("/{payer_name}", summary="Get all drug policies for a payer")
async def get_payer_policies(
    payer_name: str,
    user: TokenData = Depends(get_current_user),
):
    """
    Return all drug policies for a specific health plan.

    Example: GET /api/payer/UnitedHealthcare
    Example: GET /api/payer/uhc   ← normalized ID also works
    """
    payer_id = normalize_payer_id(payer_name)
    policies = get_policies_by_payer(payer_id)

    if not policies:
        return {
            "payer_id": payer_id,
            "payer_name": payer_name,
            "policies_found": 0,
            "policies": [],
        }

    return {
        "payer_id": payer_id,
        "payer_name": payer_name,
        "policies_found": len(policies),
        "policies": policies,
    }