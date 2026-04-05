# storage/supabase_client.py
# ============================================================
# Supabase database client with full CRUD operations
# Handles users, policies, versions, alerts, and embeddings
# ============================================================

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from ..config import get_settings
from ..utils.error_handler import log_error, DatabaseError


logger = logging.getLogger(__name__)


class SupabaseClient:
    """
    Client for Supabase database operations.
    Manages users, policies, versions, alerts, and embeddings.
    """
    
    def __init__(self):
        """Initialize Supabase client."""
        self.config = get_settings()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.initialized = False
        self._initialize()

    def _initialize(self):
        """Initialize Supabase connection."""
        try:
            from supabase import create_client
            
            if not self.config.supabase_url or not self.config.supabase_key:
                raise DatabaseError(
                    "Supabase URL and key not configured. "
                    "Set SUPABASE_URL and SUPABASE_KEY in .env"
                )
            
            self.client = create_client(
                self.config.supabase_url,
                self.config.supabase_key
            )
            self.initialized = True
            self.logger.info("Supabase client initialized successfully")
            
        except ImportError:
            raise DatabaseError("supabase library not installed. Install with: pip install supabase")
        except Exception as e:
            error_msg = f"Supabase initialization failed: {str(e)}"
            self.logger.error(error_msg)
            raise DatabaseError(error_msg)

    def test_connection(self) -> bool:
        """Test Supabase connection."""
        try:
            response = self.client.table("users").select("count", count="exact").execute()
            self.logger.info("Supabase connection test successful")
            return True
        except Exception as e:
            self.logger.error(f"Supabase connection test failed: {str(e)}")
            return False

    # USER OPERATIONS
    def create_user(self, email: str, password_hash: str, role: str = "user") -> Dict[str, Any]:
        """Create new user."""
        try:
            user_data = {
                "email": email,
                "password_hash": password_hash,
                "role": role,
                "created_at": datetime.utcnow().isoformat(),
                "is_active": True,
            }
            response = self.client.table("users").insert(user_data).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            error_msg = f"Failed to create user: {str(e)}"
            log_error(error_msg, context={"email": email})
            raise DatabaseError(error_msg)

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        try:
            response = self.client.table("users").select("*").eq("email", email).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            self.logger.warning(f"Get user failed for {email}: {str(e)}")
            return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            response = self.client.table("users").select("*").eq("id", user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            self.logger.warning(f"Get user failed for ID {user_id}: {str(e)}")
            return None

    # POLICY OPERATIONS
    def create_policy(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new policy in database."""
        try:
            policy_data["created_at"] = datetime.utcnow().isoformat()
            policy_data["updated_at"] = datetime.utcnow().isoformat()
            policy_data["version"] = 1
            
            response = self.client.table("policies").insert(policy_data).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            error_msg = f"Failed to create policy: {str(e)}"
            log_error(error_msg, context=policy_data)
            raise DatabaseError(error_msg)

    def get_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """Get policy by ID."""
        try:
            response = self.client.table("policies").select("*").eq("id", policy_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            self.logger.warning(f"Get policy failed: {str(e)}")
            return None

    def search_policies(
        self,
        drug_name: Optional[str] = None,
        payer_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search policies with filters."""
        try:
            query = self.client.table("policies").select("*")
            
            if drug_name:
                query = query.ilike("drug_name", f"%{drug_name}%")
            
            if payer_name:
                query = query.ilike("payer_name", f"%{payer_name}%")
            
            response = query.limit(limit).execute()
            return response.data or []
        except Exception as e:
            self.logger.warning(f"Policy search failed: {str(e)}")
            return []

    def update_policy(self, policy_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing policy."""
        try:
            updates["updated_at"] = datetime.utcnow().isoformat()
            response = self.client.table("policies").update(updates).eq("id", policy_id).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            error_msg = f"Failed to update policy: {str(e)}"
            log_error(error_msg)
            raise DatabaseError(error_msg)

    # VERSION OPERATIONS
    def create_version(self, policy_id: str, version_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create policy version for change tracking."""
        try:
            version_data["policy_id"] = policy_id
            version_data["created_at"] = datetime.utcnow().isoformat()
            
            response = self.client.table("policy_versions").insert(version_data).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            error_msg = f"Failed to create version: {str(e)}"
            log_error(error_msg)
            raise DatabaseError(error_msg)

    def get_policy_versions(self, policy_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get version history for policy."""
        try:
            response = (
                self.client.table("policy_versions")
                .select("*")
                .eq("policy_id", policy_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data or []
        except Exception as e:
            self.logger.warning(f"Get versions failed: {str(e)}")
            return []

    # ALERT OPERATIONS
    def create_alert_subscription(self, subscription_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create user alert subscription."""
        try:
            subscription_data["created_at"] = datetime.utcnow().isoformat()
            subscription_data["is_active"] = True
            
            response = self.client.table("alert_subscriptions").insert(subscription_data).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            error_msg = f"Failed to create alert subscription: {str(e)}"
            log_error(error_msg)
            raise DatabaseError(error_msg)

    def get_user_alerts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get alert subscriptions for user."""
        try:
            response = (
                self.client.table("alert_subscriptions")
                .select("*")
                .eq("user_id", user_id)
                .eq("is_active", True)
                .execute()
            )
            return response.data or []
        except Exception as e:
            self.logger.warning(f"Get alerts failed: {str(e)}")
            return []

    # EMBEDDING OPERATIONS
    def store_embedding(
        self,
        policy_id: str,
        embedding: List[float],
        embedding_type: str = "policy_text"
    ) -> Dict[str, Any]:
        """Store policy embedding for vector search."""
        try:
            data = {
                "policy_id": policy_id,
                "embedding": embedding,  # pgvector format
                "embedding_type": embedding_type,
                "created_at": datetime.utcnow().isoformat(),
            }
            response = self.client.table("embeddings").insert(data).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            self.logger.warning(f"Embedding storage failed: {str(e)}")
            return {}

    def search_similar_policies(
        self,
        embedding: List[float],
        limit: int = 5,
        similarity_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Vector similarity search in database.
        Requires pgvector extension in Supabase.
        """
        try:
            # For pgvector, use RPC call or raw SQL
            # This example uses a stored procedure approach
            response = self.client.rpc(
                "search_similar_policies",
                {
                    "query_embedding": embedding,
                    "similarity_threshold": similarity_threshold,
                    "limit": limit
                }
            ).execute()
            return response.data or []
        except Exception as e:
            self.logger.warning(f"Vector search failed: {str(e)}")
            # Fallback: return all policies
            return self.search_policies(limit=limit)

    # BATCH OPERATIONS
    def batch_create_policies(self, policies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create multiple policies efficiently."""
        try:
            now = datetime.utcnow().isoformat()
            for policy in policies:
                policy["created_at"] = now
                policy["updated_at"] = now
                policy["version"] = 1
            
            response = self.client.table("policies").insert(policies).execute()
            return response.data or []
        except Exception as e:
            error_msg = f"Batch create failed: {str(e)}"
            log_error(error_msg)
            raise DatabaseError(error_msg)

    def batch_update_policies(self, updates: Dict[str, List[Dict]]) -> bool:
        """Update multiple policies efficiently."""
        try:
            for policy_id, policy_updates in updates.items():
                self.update_policy(policy_id, policy_updates)
            return True
        except Exception as e:
            self.logger.error(f"Batch update failed: {str(e)}")
            return False

    # ANALYTICS
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            stats = {
                "total_policies": self._count_table("policies"),
                "total_users": self._count_table("users"),
                "total_versions": self._count_table("policy_versions"),
                "active_alerts": self._count_table("alert_subscriptions", eq={"is_active": True}),
            }
            return stats
        except Exception as e:
            self.logger.warning(f"Stats retrieval failed: {str(e)}")
            return {}

    def _count_table(self, table_name: str, eq: Optional[Dict] = None) -> int:
        """Count rows in table with optional filters."""
        try:
            query = self.client.table(table_name).select("count", count="exact")
            
            if eq:
                for key, value in eq.items():
                    query = query.eq(key, value)
            
            response = query.execute()
            return response.count or 0
        except Exception as e:
            self.logger.warning(f"Count failed for {table_name}: {str(e)}")
            return 0
