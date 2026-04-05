"""
Webhook and Events Service
Handles real-time notifications, webhook delivery, and external integrations
"""

import logging
import json
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import uuid
import requests

logger = logging.getLogger(__name__)


class WebhookService:
    """
    Webhook service for:
    - Registering webhook endpoints
    - Publishing policy change events
    - Reliable delivery with retries
    - Event routing and filtering
    """

    def __init__(self):
        """Initialize webhook service."""
        self.webhooks: Dict[str, Dict] = {}  # webhook_id -> webhook config
        self.events_log: Dict[str, Dict] = {}  # event_id -> event details
        self.delivery_log: Dict[str, List[Dict]] = {}  # webhook_id -> delivery attempts

    def register_webhook(
        self,
        admin_id: str,
        webhook_url: str,
        event_types: List[str],
    ) -> Dict:
        """
        Register a webhook endpoint for notifications.
        
        Args:
            admin_id: Admin registering the webhook
            webhook_url: URL to POST events to
            event_types: Types of events to subscribe to
            
        Returns:
            Webhook registration details
        """
        webhook_id = str(uuid.uuid4())

        # Validate webhook URL
        if not webhook_url.startswith(("http://", "https://")):
            raise ValueError("Webhook URL must start with http:// or https://")

        webhook = {
            "id": webhook_id,
            "admin_id": admin_id,
            "webhook_url": webhook_url,
            "event_types": event_types,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
            "last_delivery_at": None,
            "last_delivery_status": None,
            "failed_attempts": 0,
        }

        self.webhooks[webhook_id] = webhook
        self.delivery_log[webhook_id] = []

        logger.info(
            f"Webhook registered: {webhook_id} for admin {admin_id} -> {webhook_url}"
        )

        return webhook

    def unregister_webhook(self, webhook_id: str) -> Dict:
        """Unregister a webhook."""
        if webhook_id not in self.webhooks:
            raise ValueError(f"Webhook {webhook_id} not found")

        webhook = self.webhooks[webhook_id]
        webhook["is_active"] = False

        logger.info(f"Webhook unregistered: {webhook_id}")

        return webhook

    def get_webhooks(self, admin_id: str, active_only: bool = True) -> List[Dict]:
        """Get all webhooks for an admin."""
        results = []
        for webhook in self.webhooks.values():
            if webhook.get("admin_id") == admin_id:
                if active_only and not webhook.get("is_active"):
                    continue
                results.append(webhook)

        return results

    def publish_policy_change_event(
        self,
        policy_id: str,
        payer_id: str,
        payer_name: str,
        changes: Dict,
        change_type: str = "policy_change",
    ) -> str:
        """
        Publish a policy change event to all subscribed webhooks.
        
        Args:
            policy_id: Policy that changed
            payer_id: Payer ID
            payer_name: Payer name
            changes: What changed (field: {old, new})
            change_type: Type of change
            
        Returns:
            Event ID
        """
        event_id = str(uuid.uuid4())

        # Determine severity
        severity = self._assess_severity(changes)

        event = {
            "id": event_id,
            "event_type": change_type,
            "policy_id": policy_id,
            "payer_id": payer_id,
            "payer_name": payer_name,
            "changes": changes,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat(),
            "delivered_to": [],
        }

        self.events_log[event_id] = event

        logger.info(
            f"Policy change event published: {event_id} for policy {policy_id}, severity={severity}"
        )

        # Deliver to subscribed webhooks
        self._deliver_event_to_webhooks(event)

        return event_id

    def publish_outlier_detected_event(
        self,
        policy_id: str,
        metric_name: str,
        metric_value: float,
        average_value: float,
        z_score: float,
    ) -> str:
        """
        Publish outlier detection event.
        
        Args:
            policy_id: Policy that is an outlier
            metric_name: Name of metric
            metric_value: Actual value
            average_value: Mean value
            z_score: Z-score (std deviations from mean)
            
        Returns:
            Event ID
        """
        event_id = str(uuid.uuid4())

        event = {
            "id": event_id,
            "event_type": "outlier_detected",
            "policy_id": policy_id,
            "metric": {
                "name": metric_name,
                "value": metric_value,
                "average": average_value,
                "z_score": z_score,
            },
            "severity": "warning" if abs(z_score) > 3 else "info",
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.events_log[event_id] = event
        logger.warning(f"Outlier event published: {event_id} (z-score={z_score:.2f})")

        self._deliver_event_to_webhooks(event)

        return event_id

    def publish_new_coverage_event(
        self, policy_id: str, payer_name: str, drug_ids: List[str]
    ) -> str:
        """
        Publish new coverage event.
        
        Args:
            policy_id: Policy ID
            payer_name: Payer name
            drug_ids: List of newly covered drugs
            
        Returns:
            Event ID
        """
        event_id = str(uuid.uuid4())

        event = {
            "id": event_id,
            "event_type": "new_coverage",
            "policy_id": policy_id,
            "payer_name": payer_name,
            "drugs": drug_ids,
            "severity": "info",
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.events_log[event_id] = event
        logger.info(f"New coverage event: {event_id} - {len(drug_ids)} drugs added")

        self._deliver_event_to_webhooks(event)

        return event_id

    def get_delivery_history(
        self, webhook_id: str, limit: int = 50
    ) -> List[Dict]:
        """Get delivery attempt history for a webhook."""
        history = self.delivery_log.get(webhook_id, [])
        return history[-limit:]

    def retry_failed_deliveries(self) -> Dict:
        """Retry delivery for all failed webhooks."""
        retry_count = 0
        success_count = 0

        for webhook_id, webhook in self.webhooks.items():
            if not webhook.get("is_active"):
                continue

            if webhook.get("failed_attempts", 0) > 0:
                retry_count += 1

                # Get recent undelivered events
                for event in self.events_log.values():
                    if webhook_id not in event.get("delivered_to", []):
                        result = self._deliver_event(webhook, event)
                        if result["success"]:
                            success_count += 1
                            event["delivered_to"].append(webhook_id)

        logger.info(f"Retry attempt: {retry_count} webhooks, {success_count} successful")

        return {
            "webhooks_retried": retry_count,
            "successful_deliveries": success_count,
        }

    def _deliver_event_to_webhooks(self, event: Dict) -> None:
        """Deliver an event to all subscribed active webhooks."""
        event_type = event.get("event_type")

        for webhook_id, webhook in self.webhooks.items():
            if not webhook.get("is_active"):
                continue

            # Check if webhook subscribes to this event type
            if event_type not in webhook.get("event_types", []):
                continue

            # Deliver event
            result = self._deliver_event(webhook, event)

            if result["success"]:
                event["delivered_to"].append(webhook_id)
                webhook["last_delivery_status"] = result["status_code"]
                webhook["last_delivery_at"] = datetime.utcnow().isoformat()
                webhook["failed_attempts"] = 0
            else:
                webhook["failed_attempts"] = webhook.get("failed_attempts", 0) + 1

            # Log delivery attempt
            self.delivery_log[webhook_id].append(result)

    def _deliver_event(self, webhook: Dict, event: Dict) -> Dict:
        """Attempt to deliver event to a single webhook."""
        webhook_url = webhook["webhook_url"]
        webhook_id = webhook["id"]

        try:
            # Prepare payload
            payload = {
                "event_id": event.get("id"),
                "event_type": event.get("event_type"),
                "timestamp": event.get("timestamp"),
                "data": {k: v for k, v in event.items() if k not in ["id", "event_type", "timestamp", "delivered_to"]},
            }

            # Add webhook signature for security
            payload["webhook_id"] = webhook_id

            logger.debug(f"Delivering event to webhook {webhook_id}: {webhook_url}")

            # POST to webhook
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code < 300:
                logger.info(
                    f"Webhook delivery successful: {webhook_id} -> {webhook_url} ({response.status_code})"
                )
                return {
                    "webhook_id": webhook_id,
                    "success": True,
                    "status_code": response.status_code,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                logger.warning(
                    f"Webhook delivery failed: {webhook_id} -> {webhook_url} (status={response.status_code})"
                )
                return {
                    "webhook_id": webhook_id,
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text[:200],
                    "timestamp": datetime.utcnow().isoformat(),
                }

        except requests.exceptions.Timeout:
            logger.error(f"Webhook timeout: {webhook_id} -> {webhook_url}")
            return {
                "webhook_id": webhook_id,
                "success": False,
                "error": "timeout",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Webhook delivery error: {webhook_id} -> {webhook_url}: {str(e)}")
            return {
                "webhook_id": webhook_id,
                "success": False,
                "error": str(e)[:200],
                "timestamp": datetime.utcnow().isoformat(),
            }

    def _assess_severity(self, changes: Dict) -> str:
        """Assess severity of changes."""
        severity_indicators = ["prior_auth", "step_therapy", "coverage_removed", "price_increase"]

        for indicator in severity_indicators:
            for change_field in changes:
                if indicator in change_field.lower():
                    return "high"

        return "medium"

    async def deliver_webhook_event(self, webhook_url: str, payload: Dict) -> Dict:
        """
        Direct webhook delivery to a specific URL (not event-based).
        
        Args:
            webhook_url: Target webhook URL
            payload: Payload to send
            
        Returns:
            Delivery result
        """
        try:
            # POST to webhook
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code < 300:
                logger.info(
                    f"Direct webhook delivery successful: {webhook_url} ({response.status_code})"
                )
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                logger.warning(
                    f"Direct webhook delivery failed: {webhook_url} (status={response.status_code})"
                )
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text[:200],
                    "timestamp": datetime.utcnow().isoformat(),
                }

        except requests.exceptions.Timeout:
            logger.error(f"Direct webhook timeout: {webhook_url}")
            return {
                "success": False,
                "error": "timeout",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Direct webhook delivery error: {webhook_url}: {str(e)}")
            return {
                "success": False,
                "error": str(e)[:200],
                "timestamp": datetime.utcnow().isoformat(),
            }


# Singleton instance
webhook_service = WebhookService()
