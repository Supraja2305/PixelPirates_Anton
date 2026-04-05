"""
Alert Service - Manages and dispatches policy change alerts
Monitors policies and notifies users of changes, new coverage, and critical updates
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Types of alerts."""
    POLICY_CHANGE = "policy_change"
    NEW_COVERAGE = "new_coverage"
    COVERAGE_REMOVED = "coverage_removed"
    PRICE_UPDATE = "price_update"
    REQUIREMENT_CHANGE = "requirement_change"
    POLICY_EXPIRING = "policy_expiring"
    NEW_POLICY = "new_policy"


class Alert:
    """Represents a single alert."""

    def __init__(
        self,
        alert_id: str,
        alert_type: AlertType,
        title: str,
        description: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        related_policy_ids: List[str] = None,
        related_drug_ids: List[str] = None,
        metadata: Dict = None,
    ):
        """Initialize alert."""
        self.alert_id = alert_id
        self.alert_type = alert_type
        self.title = title
        self.description = description
        self.severity = severity
        self.related_policy_ids = related_policy_ids or []
        self.related_drug_ids = related_drug_ids or []
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.resolved = False
        self.resolved_at = None

    def resolve(self):
        """Mark this alert as resolved."""
        self.resolved = True
        self.resolved_at = datetime.now()

    def to_dict(self) -> Dict:
        """Convert alert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "related_policy_ids": self.related_policy_ids,
            "related_drug_ids": self.related_drug_ids,
            "created_at": self.created_at.isoformat(),
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "metadata": self.metadata,
        }


class AlertService:
    """
    Service for creating, managing, and dispatching alerts.
    """

    def __init__(self):
        """Initialize alert service."""
        self.alerts: Dict[str, Alert] = {}
        self.user_subscriptions: Dict[str, List[AlertType]] = {}  # user_id -> alert_types
        self.alert_listeners = []

    def create_alert(
        self,
        alert_type: AlertType,
        title: str,
        description: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        related_policy_ids: List[str] = None,
        related_drug_ids: List[str] = None,
        metadata: Dict = None,
    ) -> Alert:
        """
        Create a new alert.
        
        Args:
            alert_type: Type of alert
            title: Alert title
            description: Description of the alert
            severity: Alert severity level
            related_policy_ids: Policy IDs related to this alert
            related_drug_ids: Drug IDs related to this alert
            metadata: Additional metadata
            
        Returns:
            Created Alert object
        """
        import uuid

        alert_id = str(uuid.uuid4())

        alert = Alert(
            alert_id=alert_id,
            alert_type=alert_type,
            title=title,
            description=description,
            severity=severity,
            related_policy_ids=related_policy_ids,
            related_drug_ids=related_drug_ids,
            metadata=metadata,
        )

        self.alerts[alert_id] = alert

        logger.info(
            f"Alert created: {alert_id} (type: {alert_type.value}, severity: {severity.value})"
        )

        # Notify listeners
        self._dispatch_alert(alert)

        return alert

    def alert_policy_change(self, policy_id: str, changes: List[Dict]) -> Alert:
        """
        Create alert for policy changes.
        
        Args:
            policy_id: ID of the policy that changed
            changes: List of changes (from diff engine)
            
        Returns:
            Created Alert
        """
        high_severity_changes = [
            c for c in changes if c.get("severity") == "high"
        ]

        severity = (
            AlertSeverity.CRITICAL
            if high_severity_changes
            else AlertSeverity.WARNING
        )

        title = f"Policy {policy_id} has been updated"
        description_parts = [
            f"{len(changes)} changes detected:",
        ]

        for change in changes[:5]:  # Show first 5 changes
            description_parts.append(
                f"- {change.get('field')}: {change.get('old_value')} → "
                f"{change.get('new_value')}"
            )

        if len(changes) > 5:
            description_parts.append(f"- ... and {len(changes) - 5} more")

        description = "\n".join(description_parts)

        return self.create_alert(
            alert_type=AlertType.POLICY_CHANGE,
            title=title,
            description=description,
            severity=severity,
            related_policy_ids=[policy_id],
            metadata={"change_count": len(changes), "high_severity": len(high_severity_changes)},
        )

    def alert_new_coverage(self, policy_id: str, drug_ids: List[str]) -> Alert:
        """
        Create alert for new drug coverage.
        
        Args:
            policy_id: ID of policy
            drug_ids: IDs of newly covered drugs
            
        Returns:
            Created Alert
        """
        title = f"Policy {policy_id}: New drug coverage added"
        description = f"{len(drug_ids)} drugs are now covered under this policy"

        return self.create_alert(
            alert_type=AlertType.NEW_COVERAGE,
            title=title,
            description=description,
            severity=AlertSeverity.INFO,
            related_policy_ids=[policy_id],
            related_drug_ids=drug_ids,
        )

    def alert_price_change(self, policy_id: str, old_price: float, new_price: float) -> Alert:
        """
        Create alert for pricing changes.
        
        Args:
            policy_id: ID of policy
            old_price: Previous price
            new_price: New price
            
        Returns:
            Created Alert
        """
        percent_change = ((new_price - old_price) / old_price * 100) if old_price else 0
        severity = (
            AlertSeverity.CRITICAL if percent_change > 20 else AlertSeverity.WARNING
        )

        title = f"Price update for policy {policy_id}"
        description = (
            f"Price changed from ${old_price:.2f} to ${new_price:.2f} "
            f"({percent_change:+.1f}%)"
        )

        return self.create_alert(
            alert_type=AlertType.PRICE_UPDATE,
            title=title,
            description=description,
            severity=severity,
            related_policy_ids=[policy_id],
            metadata={"old_price": old_price, "new_price": new_price, "percent_change": percent_change},
        )

    def resolve_alert(self, alert_id: str) -> bool:
        """
        Mark an alert as resolved.
        
        Args:
            alert_id: ID of alert to resolve
            
        Returns:
            True if successful
        """
        if alert_id in self.alerts:
            self.alerts[alert_id].resolve()
            logger.info(f"Alert {alert_id} resolved")
            return True

        logger.warning(f"Alert {alert_id} not found")
        return False

    def get_alerts(
        self,
        limit: int = 50,
        alert_type: Optional[AlertType] = None,
        severity: Optional[AlertSeverity] = None,
        unresolved_only: bool = False,
    ) -> List[Dict]:
        """
        Get alerts with optional filtering.
        
        Args:
            limit: Maximum number of alerts
            alert_type: Filter by alert type
            severity: Filter by severity
            unresolved_only: Only return unresolved alerts
            
        Returns:
            List of alerts as dicts
        """
        alerts = list(self.alerts.values())

        # Apply filters
        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        if unresolved_only:
            alerts = [a for a in alerts if not a.resolved]

        # Sort by created_at descending
        alerts.sort(key=lambda a: a.created_at, reverse=True)

        # Convert to dicts and limit
        return [a.to_dict() for a in alerts[:limit]]

    def get_policy_alerts(self, policy_id: str) -> List[Dict]:
        """Get all alerts related to a policy."""
        relevant_alerts = [
            a for a in self.alerts.values()
            if policy_id in a.related_policy_ids
        ]

        return [a.to_dict() for a in relevant_alerts]

    def subscribe_user(self, user_id: str, alert_types: List[AlertType]) -> None:
        """Subscribe user to alert types."""
        self.user_subscriptions[user_id] = alert_types
        logger.info(f"User {user_id} subscribed to alerts: {alert_types}")

    def get_unresolved_count(self) -> int:
        """Get count of unresolved alerts."""
        return len([a for a in self.alerts.values() if not a.resolved])

    def _dispatch_alert(self, alert: Alert) -> None:
        """Dispatch alert to listeners."""
        for listener in self.alert_listeners:
            try:
                listener(alert)
            except Exception as e:
                logger.error(f"Error notifying listener: {str(e)}")

    def add_listener(self, callback) -> None:
        """Add a listener to be notified of new alerts."""
        self.alert_listeners.append(callback)


# Singleton instance
alert_service = AlertService()
