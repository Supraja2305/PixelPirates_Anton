# storage/firestore_client.py
# ============================================================
# All Firestore database operations in one place.
# We abstract Firestore here so the rest of the code doesn't
# directly touch the DB — makes testing much easier.
#
# Collections used:
#   - policies          ← One doc per policy
#   - policy_versions   ← Historical versions of each policy
#   - users             ← User accounts
#   - embeddings        ← Vector embeddings for semantic search
#   - alerts            ← Alert subscriptions
# ============================================================

import os
from datetime import datetime
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from ..config import get_settings
from ..utils.error_handler import DatabaseError

settings = get_settings()

# ── Initialize Firebase once ──────────────────────────────────
# Firebase Admin SDK only needs to be initialized ONCE.
# We guard with _apps check so it doesn't double-initialize.
if not firebase_admin._apps:
    cred = credentials.Certificate(settings.firebase_credentials_path)
    firebase_admin.initialize_app(cred, {
        "projectId": settings.firebase_project_id
    })

# Get Firestore client
_db = firestore.client()


# ── Policy CRUD ───────────────────────────────────────────────

def save_policy(policy_dict: dict) -> str:
    """
    Save or update a policy document in Firestore.

    Steps:
    1. Use policy_id as the document ID.
    2. Set merge=True so we update existing docs (not overwrite).
    3. Return the policy_id.

    Args:
        policy_dict: Dict representation of the Policy model.

    Returns:
        The policy_id string.
    """
    policy_id = policy_dict.get("policy_id")
    if not policy_id:
        raise DatabaseError("Policy must have a policy_id before saving")

    try:
        doc_ref = _db.collection("policies").document(policy_id)
        doc_ref.set(policy_dict, merge=True)
        return policy_id
    except Exception as e:
        raise DatabaseError(f"Failed to save policy {policy_id}: {str(e)}")


def get_policy_by_id(policy_id: str) -> Optional[dict]:
    """
    Retrieve a single policy by its ID.

    Returns None if the policy doesn't exist.
    """
    try:
        doc = _db.collection("policies").document(policy_id).get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        raise DatabaseError(f"Failed to get policy {policy_id}: {str(e)}")


def get_policies_by_drug(drug_name: str) -> list[dict]:
    """
    Get all policies for a specific drug (across all payers).

    Steps:
    1. Query the 'policies' collection.
    2. Filter where drug.canonical_name == drug_name.
    3. Return list of policy dicts.

    Note: Firestore nested field queries use dot notation.
    """
    try:
        query = (
            _db.collection("policies")
            .where(filter=FieldFilter("drug.canonical_name", "==", drug_name))
        )
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        raise DatabaseError(f"Failed to query drug {drug_name}: {str(e)}")


def get_policies_by_payer(payer_id: str) -> list[dict]:
    """
    Get all policies for a specific payer.
    """
    try:
        query = (
            _db.collection("policies")
            .where(filter=FieldFilter("payer_id", "==", payer_id))
        )
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        raise DatabaseError(f"Failed to query payer {payer_id}: {str(e)}")


def get_all_policies(limit: int = 100) -> list[dict]:
    """
    Get all policies (with a safety limit).
    """
    try:
        docs = _db.collection("policies").limit(limit).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        raise DatabaseError(f"Failed to fetch all policies: {str(e)}")


def delete_policy(policy_id: str) -> bool:
    """Delete a policy. Returns True if deleted."""
    try:
        _db.collection("policies").document(policy_id).delete()
        return True
    except Exception as e:
        raise DatabaseError(f"Failed to delete policy {policy_id}: {str(e)}")


# ── Version History ───────────────────────────────────────────

def save_policy_version(policy_dict: dict, version_id: str) -> str:
    """
    Save a historical version of a policy.
    This is called every time a policy is ingested/updated.

    The version document is stored under:
      policy_versions/{version_id}

    And is linked to the parent policy via policy_id.
    """
    try:
        version_doc = {
            **policy_dict,
            "version_id": version_id,
            "archived_at": datetime.utcnow().isoformat(),
        }
        _db.collection("policy_versions").document(version_id).set(version_doc)
        return version_id
    except Exception as e:
        raise DatabaseError(f"Failed to save version {version_id}: {str(e)}")


def get_policy_versions(policy_id: str) -> list[dict]:
    """
    Get all historical versions for a policy, sorted newest first.
    """
    try:
        query = (
            _db.collection("policy_versions")
            .where(filter=FieldFilter("policy_id", "==", policy_id))
            .order_by("archived_at", direction=firestore.Query.DESCENDING)
        )
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        raise DatabaseError(f"Failed to get versions for {policy_id}: {str(e)}")


# ── User CRUD ─────────────────────────────────────────────────

def save_user(user_dict: dict) -> str:
    """Save a new user to Firestore."""
    user_id = user_dict.get("user_id")
    try:
        _db.collection("users").document(user_id).set(user_dict)
        return user_id
    except Exception as e:
        raise DatabaseError(f"Failed to save user: {str(e)}")


def get_user_by_email(email: str) -> Optional[dict]:
    """Look up a user by email address."""
    try:
        query = (
            _db.collection("users")
            .where(filter=FieldFilter("email", "==", email))
            .limit(1)
        )
        docs = list(query.stream())
        return docs[0].to_dict() if docs else None
    except Exception as e:
        raise DatabaseError(f"Failed to get user by email: {str(e)}")


def get_user_by_id(user_id: str) -> Optional[dict]:
    """Look up a user by their ID."""
    try:
        doc = _db.collection("users").document(user_id).get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        raise DatabaseError(f"Failed to get user {user_id}: {str(e)}")


# ── Embeddings ────────────────────────────────────────────────

def save_embedding(policy_id: str, embedding: list[float], text: str) -> None:
    """
    Save a vector embedding for a policy.
    We store the embedding as a list of floats alongside the
    policy text and ID so we can retrieve it for similarity search.
    """
    try:
        _db.collection("embeddings").document(policy_id).set({
            "policy_id": policy_id,
            "embedding": embedding,
            "text": text[:1000],  # Store first 1000 chars for context
            "created_at": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        raise DatabaseError(f"Failed to save embedding for {policy_id}: {str(e)}")


def get_all_embeddings() -> list[dict]:
    """
    Retrieve all stored embeddings for similarity comparison.
    """
    try:
        docs = _db.collection("embeddings").stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        raise DatabaseError(f"Failed to fetch embeddings: {str(e)}")


# ── Alert Subscriptions ───────────────────────────────────────

def save_alert_subscription(user_id: str, drug_name: str) -> None:
    """Subscribe a user to alerts for a drug."""
    try:
        _db.collection("alerts").document(f"{user_id}_{drug_name}").set({
            "user_id": user_id,
            "drug_name": drug_name,
            "created_at": datetime.utcnow().isoformat(),
            "active": True,
        })
    except Exception as e:
        raise DatabaseError(f"Failed to save alert subscription: {str(e)}")


def get_subscribers_for_drug(drug_name: str) -> list[str]:
    """Get all user_ids subscribed to alerts for a drug."""
    try:
        query = (
            _db.collection("alerts")
            .where(filter=FieldFilter("drug_name", "==", drug_name))
            .where(filter=FieldFilter("active", "==", True))
        )
        docs = query.stream()
        return [doc.to_dict().get("user_id") for doc in docs]
    except Exception as e:
        raise DatabaseError(f"Failed to get subscribers for {drug_name}: {str(e)}")