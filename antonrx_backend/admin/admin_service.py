"""
Admin control service
Handles policy soft deletes, overrides, audit logging, and bulk operations
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class AdminService:
    """
    Complete admin control system for:
    - Soft delete/restore policies (is_active boolean)
    - Bulk archive payers
    - Manual field overrides
    - Audit logging
    - Re-extraction triggers
    """

    def __init__(self):
        """Initialize admin service."""
        self.audit_logs: List[Dict] = []
        self.policy_versions: Dict[str, List[Dict]] = {}
        self.audit_log_store: Dict[str, Dict] = {}

    def soft_delete_policy(
        self, policy_id: str, reason: str, admin_user_id: str, admin_email: str
    ) -> Dict:
        """
        Soft delete a policy (mark as inactive, not permanent deletion).
        
        Args:
            policy_id: ID of policy to deactivate
            reason: Reason for deactivation
            admin_user_id: ID of admin performing action
            admin_email: Email of admin
            
        Returns:
            Updated policy with is_active=False
        """
        logger.info(f"Soft deleting policy {policy_id}: {reason}")

        updated_policy = {
            "id": policy_id,
            "is_active": False,
            "deactivated_at": datetime.utcnow().isoformat(),
            "deactivation_reason": reason,
        }

        # Log the action
        self._log_audit_action(
            action="POLICY_SOFT_DELETED",
            admin_user_id=admin_user_id,
            admin_email=admin_email,
            entity_type="policy",
            entity_id=policy_id,
            changes={"is_active": {"old": True, "new": False}},
            reason=reason,
        )

        return updated_policy

    def restore_policy(
        self, policy_id: str, admin_user_id: str, admin_email: str
    ) -> Dict:
        """
        Restore a soft-deleted policy.
        
        Args:
            policy_id: ID of policy to restore
            admin_user_id: ID of admin
            admin_email: Email of admin
            
        Returns:
            Restored policy with is_active=True
        """
        logger.info(f"Restoring policy {policy_id}")

        updated_policy = {
            "id": policy_id,
            "is_active": True,
            "deactivated_at": None,
            "deactivation_reason": None,
        }

        self._log_audit_action(
            action="POLICY_RESTORED",
            admin_user_id=admin_user_id,
            admin_email=admin_email,
            entity_type="policy",
            entity_id=policy_id,
            changes={"is_active": {"old": False, "new": True}},
        )

        return updated_policy

    def bulk_archive_payer(
        self, payer_id: str, payer_name: str, admin_user_id: str, admin_email: str
    ) -> Dict:
        """
        Bulk archive all policies for a payer (soft delete in one shot).
        
        Args:
            payer_id: ID of payer
            payer_name: Name of payer
            admin_user_id: ID of admin
            admin_email: Email of admin
            
        Returns:
            Result with count of archived policies
        """
        logger.info(f"Bulk archiving all policies for payer {payer_id} ({payer_name})")

        # In real implementation, this would query DB for all policies with this payer_id
        archived_count = 0  # Placeholder

        self._log_audit_action(
            action="PAYER_BULK_ARCHIVED",
            admin_user_id=admin_user_id,
            admin_email=admin_email,
            entity_type="payer",
            entity_id=payer_id,
            changes={"policies_archived": archived_count},
            metadata={"payer_name": payer_name},
        )

        return {
            "payer_id": payer_id,
            "payer_name": payer_name,
            "policies_archived": archived_count,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def bulk_archive_payers(
        self, payer_ids: List[str], admin_user_id: str, admin_email: str
    ) -> Dict:
        """
        Archive multiple payers at once.
        
        Args:
            payer_ids: List of payer IDs to archive
            admin_user_id: Admin ID
            admin_email: Admin email
            
        Returns:
            Summary of bulk operation
        """
        logger.info(f"Bulk archiving {len(payer_ids)} payers")

        results = []
        total_policies_archived = 0

        for payer_id in payer_ids:
            result = self.bulk_archive_payer(payer_id, f"Payer_{payer_id}", admin_user_id, admin_email)
            results.append(result)
            total_policies_archived += result.get("policies_archived", 0)

        return {
            "payers_archived": len(payer_ids),
            "total_policies_archived": total_policies_archived,
            "details": results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def override_policy_field(
        self,
        policy_id: str,
        field_name: str,
        old_value,
        new_value,
        reason: str,
        admin_user_id: str,
        admin_email: str,
    ) -> Dict:
        """
        Manually correct an extracted policy field.
        
        Args:
            policy_id: Policy ID
            field_name: Field to override (e.g., "prior_auth", "copay")
            old_value: Previous value
            new_value: New corrected value
            reason: Why the correction was needed
            admin_user_id: Admin ID
            admin_email: Admin email
            
        Returns:
            Override record with audit trail
        """
        logger.info(
            f"Override policy {policy_id} field {field_name}: {old_value} -> {new_value}"
        )

        override_record = {
            "id": str(uuid.uuid4()),
            "policy_id": policy_id,
            "field_name": field_name,
            "old_value": old_value,
            "new_value": new_value,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self._log_audit_action(
            action="POLICY_FIELD_OVERRIDDEN",
            admin_user_id=admin_user_id,
            admin_email=admin_email,
            entity_type="policy",
            entity_id=policy_id,
            changes={field_name: {"old": old_value, "new": new_value}},
            reason=reason,
            metadata={"override_id": override_record["id"]},
        )

        return override_record

    def get_audit_logs(
        self,
        admin_user_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        action: Optional[str] = None,
        days_back: int = 30,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Retrieve audit logs with filtering.
        
        Args:
            admin_user_id: Filter by specific admin
            entity_type: Filter by entity type
            action: Filter by action type
            days_back: How many days to look back
            limit: Max records to return
            
        Returns:
            List of audit log entries
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        results = []
        for log_id, log in self.audit_log_store.items():
            # Apply filters
            if admin_user_id and log.get("admin_user_id") != admin_user_id:
                continue
            if entity_type and log.get("entity_type") != entity_type:
                continue
            if action and log.get("action") != action:
                continue

            # Check date
            log_date = datetime.fromisoformat(log.get("created_at", ""))
            if log_date < cutoff_date:
                continue

            results.append(log)

        # Sort by date descending, limit results
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return results[:limit]

    def start_re_extraction(
        self,
        policy_id: str,
        document_text: str,
        updated_prompt: Optional[str] = None,
        admin_user_id: str = None,
        admin_email: str = None,
    ) -> Dict:
        """
        Trigger re-extraction of a policy with updated prompt.
        
        Args:
            policy_id: Policy to re-extract
            document_text: Original document text
            updated_prompt: Optional updated extraction prompt
            admin_user_id: Admin triggering re-extraction
            admin_email: Admin email
            
        Returns:
            Re-extraction job info
        """
        job_id = str(uuid.uuid4())
        logger.info(f"Starting re-extraction job {job_id} for policy {policy_id}")

        job = {
            "job_id": job_id,
            "policy_id": policy_id,
            "status": "pending",
            "started_at": datetime.utcnow().isoformat(),
            "extraction_method": "admin_reextraction",
        }

        self._log_audit_action(
            action="POLICY_RE_EXTRACTED",
            admin_user_id=admin_user_id or "system",
            admin_email=admin_email or "system@internal",
            entity_type="policy",
            entity_id=policy_id,
            metadata={"job_id": job_id, "has_custom_prompt": updated_prompt is not None},
        )

        return job

    def get_ingestion_queue_status(
        self, status_filter: Optional[str] = None, limit: int = 50
    ) -> Dict:
        """
        Dashboard showing recent ingestion status.
        
        Args:
            status_filter: Filter by status (pending, extracting, success, failed)
            limit: Max records to return
            
        Returns:
            Queue status summary with recent jobs
        """
        logger.info(f"Retrieving ingestion queue status (filter: {status_filter})")

        # In real implementation, query IngestionJob table
        status_summary = {
            "total_pending": 0,
            "total_extracting": 0,
            "total_success": 0,
            "total_failed": 0,
            "recent_jobs": [],
        }

        return status_summary

    def flag_outlier_policy(
        self,
        policy_id: str,
        metric_name: str,
        metric_value: float,
        average_value: float,
        std_dev: float,
    ) -> Dict:
        """
        Flag a policy as statistical outlier (2+ std devs from mean).
        
        Args:
            policy_id: Policy ID
            metric_name: What metric (e.g., "restrictiveness_score")
            metric_value: Actual value
            average_value: Mean value
            std_dev: Standard deviation
            
        Returns:
            Flag record
        """
        z_score = (metric_value - average_value) / std_dev if std_dev > 0 else 0
        severity = "critical" if abs(z_score) > 2.5 else "warning"

        logger.warning(
            f"Flagging policy {policy_id}: {metric_name} z-score={z_score:.2f}, severity={severity}"
        )

        flag = {
            "id": str(uuid.uuid4()),
            "policy_id": policy_id,
            "flag_type": "outlier",
            "severity": severity,
            "metric": metric_name,
            "metric_value": metric_value,
            "average_value": average_value,
            "std_deviation": std_dev,
            "z_score": z_score,
            "description": f"Policy {metric_name} is {abs(z_score):.1f} std deviations from average",
            "created_at": datetime.utcnow().isoformat(),
        }

        return flag

    def get_audit_summary(self, days: int = 30) -> Dict:
        """Get summary of audit activities."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        action_counts = {}
        admin_activity = {}

        for log in self.audit_log_store.values():
            log_date = datetime.fromisoformat(log.get("created_at", ""))
            if log_date < cutoff:
                continue

            # Count actions
            action = log.get("action", "unknown")
            action_counts[action] = action_counts.get(action, 0) + 1

            # Count by admin
            admin_email = log.get("admin_email", "unknown")
            admin_activity[admin_email] = admin_activity.get(admin_email, 0) + 1

        return {
            "period_days": days,
            "total_actions": sum(action_counts.values()),
            "action_breakdown": action_counts,
            "admin_activity": admin_activity,
        }

    def _log_audit_action(
        self,
        action: str,
        admin_user_id: str,
        admin_email: str,
        entity_type: str,
        entity_id: str,
        changes: Dict,
        reason: Optional[str] = None,
        metadata: Optional[Dict] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Internal method to log admin actions."""
        log_entry = {
            "id": str(uuid.uuid4()),
            "action": action,
            "admin_user_id": admin_user_id,
            "admin_email": admin_email,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "changes": changes,
            "reason": reason,
            "metadata": metadata or {},
            "ip_address": ip_address,
            "created_at": datetime.utcnow().isoformat(),
        }

        self.audit_log_store[log_entry["id"]] = log_entry
        logger.debug(f"Audit logged: {action} by {admin_email} on {entity_type} {entity_id}")


# Singleton instance
admin_service = AdminService()
