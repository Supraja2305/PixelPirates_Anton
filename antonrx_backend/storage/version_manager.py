# storage/version_manager.py
# ============================================================
# Manage policy versions.
# Every time a policy is ingested:
#   1. We check if a previous version exists.
#   2. If the content changed (different checksum), we archive
#      the old version and save the new one.
#   3. We return a flag indicating if the policy is new or updated.
# ============================================================

import uuid
from datetime import datetime
from typing import Optional

from .firestore_client import (
    get_policy_by_id,
    save_policy,
    save_policy_version,
    get_policy_versions,
)


def generate_policy_id(payer_id: str, drug_canonical_name: str) -> str:
    """
    Generate a stable policy ID from payer + drug.
    Same payer + drug always gives the same ID.
    This is the "primary key" for our policies.

    Format: "{payer_id}_{drug_slug}"
    Example: "uhc_adalimumab"
    """
    drug_slug = drug_canonical_name.lower().replace(" ", "_").replace("-", "_")
    return f"{payer_id}_{drug_slug}"


def generate_version_id(policy_id: str) -> str:
    """
    Generate a unique version ID using timestamp + UUID.
    Format: "{policy_id}_v{timestamp}_{short_uuid}"
    Example: "uhc_adalimumab_v20260403_a1b2c3"
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    short_id = str(uuid.uuid4())[:6]
    return f"{policy_id}_v{timestamp}_{short_id}"


def save_policy_with_versioning(policy_dict: dict) -> dict:
    """
    Save a policy and handle versioning automatically.

    Steps:
    1. Check if a policy with this ID already exists in Firestore.
    2. If it exists:
       a. Compare checksums. If same content → skip (no change).
       b. If different → archive the old version, save the new one.
       c. Set is_update=True in the result.
    3. If it doesn't exist → save as new.
    4. Return a result dict with status information.

    Args:
        policy_dict: Complete policy dict ready to save.

    Returns:
        {
            "policy_id": str,
            "version_id": str,
            "is_new": bool,
            "is_update": bool,
            "is_unchanged": bool,
        }
    """
    policy_id = policy_dict["policy_id"]
    new_checksum = policy_dict.get("checksum")

    # Step 1: Check for existing policy
    existing = get_policy_by_id(policy_id)

    if existing is None:
        # ── Brand new policy ─────────────────────────────────
        version_id = generate_version_id(policy_id)
        policy_dict["version_id"] = version_id

        save_policy(policy_dict)
        save_policy_version(policy_dict, version_id)

        return {
            "policy_id": policy_id,
            "version_id": version_id,
            "is_new": True,
            "is_update": False,
            "is_unchanged": False,
        }

    # ── Policy already exists ─────────────────────────────────
    existing_checksum = existing.get("checksum")

    if new_checksum and existing_checksum and new_checksum == existing_checksum:
        # Content hasn't changed — skip to avoid unnecessary writes
        return {
            "policy_id": policy_id,
            "version_id": existing.get("version_id"),
            "is_new": False,
            "is_update": False,
            "is_unchanged": True,
        }

    # Content has changed — archive old version, save new
    old_version_id = existing.get("version_id", generate_version_id(policy_id))
    save_policy_version(existing, old_version_id)

    # Save new version
    new_version_id = generate_version_id(policy_id)
    policy_dict["version_id"] = new_version_id
    save_policy(policy_dict)
    save_policy_version(policy_dict, new_version_id)

    return {
        "policy_id": policy_id,
        "version_id": new_version_id,
        "is_new": False,
        "is_update": True,
        "is_unchanged": False,
        "previous_version_id": old_version_id,
    }


def get_version_history(policy_id: str) -> list[dict]:
    """
    Get all historical versions for a policy, sorted newest first.

    Returns a list of version dicts. Each includes a version_id,
    archived_at timestamp, and the full policy data at that point in time.
    """
    return get_policy_versions(policy_id)