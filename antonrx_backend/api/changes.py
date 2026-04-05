# api/changes.py  ── GET /api/changes/{policy_id}
# ============================================================
from fastapi import APIRouter, Depends, HTTPException
from ..auth.middleware import get_current_user
from ..models.user import TokenData
from ..storage.version_manager import get_version_history
from ..scoring.diff_engine import compute_policy_diff

router = APIRouter(prefix="/api/changes", tags=["Changes"])


@router.get("/{policy_id}", summary="View version history and changes for a policy")
async def get_policy_changes(
    policy_id: str,
    user: TokenData = Depends(get_current_user),
):
    """
    Show the full version history for a policy, with diffs
    between each consecutive version.

    Example: GET /api/changes/uhc_adalimumab

    Returns:
    - List of all versions (newest first)
    - Diff between each consecutive version pair
    """
    versions = get_version_history(policy_id)

    if not versions:
        raise HTTPException(
            status_code=404,
            detail=f"No version history found for policy '{policy_id}'"
        )

    # Compute diffs between consecutive versions
    diffs = []
    for i in range(len(versions) - 1):
        newer = versions[i]
        older = versions[i + 1]
        diff = compute_policy_diff(older, newer)
        diffs.append({
            "from_version": older.get("version_id"),
            "to_version": newer.get("version_id"),
            "diff": diff,
        })

    return {
        "policy_id": policy_id,
        "version_count": len(versions),
        "versions": [
            {
                "version_id": v.get("version_id"),
                "archived_at": v.get("archived_at"),
                "effective_date": v.get("effective_date"),
                "coverage_status": v.get("coverage_status"),
                "restrictiveness_score": v.get("restrictiveness_score"),
            }
            for v in versions
        ],
        "diffs": diffs,
    }


# ─────────────────────────────────────────────────────────────
# api/alerts_route.py  ── POST /api/alerts
# ─────────────────────────────────────────────────────────────
from fastapi import APIRouter as _AR, Depends as _Dep, Body as _Body
from ..auth.middleware import get_current_user as _gcu
from ..models.user import TokenData as _TD
from ..storage.firestore_client import save_alert_subscription, get_user_by_id

alerts_router = _AR(prefix="/api/alerts", tags=["Alerts"])


@alerts_router.post("", summary="Subscribe to alerts for a drug")
async def subscribe_to_alerts(
    drug_name: str = _Body(..., embed=True),
    user: _TD = _Dep(_gcu),
):
    """
    Subscribe the current user to policy change alerts
    for a specific drug.

    When a policy for that drug is updated, the user will
    receive an alert.

    Body: { "drug_name": "adalimumab" }
    """
    from ..normalizers.drug_normalizer import normalize_drug_name
    canonical = normalize_drug_name(drug_name)

    save_alert_subscription(user.user_id, canonical)

    return {
        "success": True,
        "message": f"Subscribed to alerts for '{canonical}'",
        "user_id": user.user_id,
        "drug": canonical,
    }


@alerts_router.delete("", summary="Unsubscribe from alerts for a drug")
async def unsubscribe_from_alerts(
    drug_name: str = _Body(..., embed=True),
    user: _TD = _Dep(_gcu),
):
    """Unsubscribe from policy change alerts for a drug."""
    from ..normalizers.drug_normalizer import normalize_drug_name
    from ..storage.firestore_client import _db
    canonical = normalize_drug_name(drug_name)

    doc_id = f"{user.user_id}_{canonical}"
    _db.collection("alerts").document(doc_id).update({"active": False})

    return {
        "success": True,
        "message": f"Unsubscribed from alerts for '{canonical}'",
    }