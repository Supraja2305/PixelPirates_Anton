# utils/analytics.py
# ============================================================
# Analytics and monitoring for API and system performance
# Tracks requests, extractions, cache hits, errors, and more
# ============================================================

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading

from ..config import get_settings


logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """
    Track and analyze system metrics:
    - Request patterns
    - Extraction metrics
    - Cache performance
    - Error rates
    - API response times
    """
    
    def __init__(self, max_recent: int = 1000):
        """Initialize analytics engine."""
        self.config = get_settings()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.lock = threading.Lock()
        
        # Metrics
        self.total_requests = 0
        self.total_extractions = 0
        self.total_errors = 0
        
        # Recent events (for trending)
        self.recent_requests = deque(maxlen=max_recent)
        self.recent_extractions = deque(maxlen=max_recent)
        self.recent_errors = deque(maxlen=max_recent)
        
        # By endpoint
        self.endpoint_stats = defaultdict(lambda: {
            "count": 0,
            "total_time": 0.0,
            "errors": 0,
            "avg_time": 0.0,
        })
        
        # By file type
        self.file_type_stats = defaultdict(lambda: {
            "count": 0,
            "avg_chars": 0,
            "errors": 0,
            "avg_confidence": 0.0,
        })
        
        # Temporal metrics
        self.daily_stats = defaultdict(lambda: {
            "requests": 0,
            "extractions": 0,
            "errors": 0,
            "users": set(),
        })

    def record_request(
        self,
        endpoint: str,
        method: str,
        duration_ms: float,
        status_code: int = 200,
        user_id: Optional[str] = None
    ) -> None:
        """Record API request metric."""
        with self.lock:
            self.total_requests += 1
            
            # Record event
            event = {
                "timestamp": datetime.utcnow(),
                "endpoint": endpoint,
                "method": method,
                "duration_ms": duration_ms,
                "status_code": status_code,
                "user_id": user_id,
            }
            self.recent_requests.append(event)
            
            # Update endpoint stats
            stats = self.endpoint_stats[endpoint]
            stats["count"] += 1
            stats["total_time"] += duration_ms
            stats["avg_time"] = stats["total_time"] / stats["count"]
            
            if status_code >= 400:
                stats["errors"] += 1
                self.total_errors += 1
            
            # Daily stats
            today = datetime.utcnow().date().isoformat()
            self.daily_stats[today]["requests"] += 1
            if user_id:
                self.daily_stats[today]["users"].add(user_id)

    def record_extraction(
        self,
        file_type: str,
        char_count: int,
        confidence: float,
        duration_ms: float,
        error: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> None:
        """Record document extraction metric."""
        with self.lock:
            self.total_extractions += 1
            
            # Record event
            event = {
                "timestamp": datetime.utcnow(),
                "file_type": file_type,
                "char_count": char_count,
                "confidence": confidence,
                "duration_ms": duration_ms,
                "error": error,
                "user_id": user_id,
            }
            self.recent_extractions.append(event)
            
            # Update file type stats
            stats = self.file_type_stats[file_type]
            stats["count"] += 1
            stats["avg_chars"] = (
                (stats["avg_chars"] * (stats["count"] - 1) + char_count) / stats["count"]
            )
            stats["avg_confidence"] = (
                (stats["avg_confidence"] * (stats["count"] - 1) + confidence) / stats["count"]
            )
            
            if error:
                stats["errors"] += 1
                self.total_errors += 1
            
            # Daily stats
            today = datetime.utcnow().date().isoformat()
            self.daily_stats[today]["extractions"] += 1
            if user_id:
                self.daily_stats[today]["users"].add(user_id)

    def record_error(
        self,
        error_type: str,
        message: str,
        endpoint: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> None:
        """Record error occurrence."""
        with self.lock:
            self.total_errors += 1
            
            event = {
                "timestamp": datetime.utcnow(),
                "error_type": error_type,
                "message": message,
                "endpoint": endpoint,
                "user_id": user_id,
            }
            self.recent_errors.append(event)
            
            # Daily stats
            today = datetime.utcnow().date().isoformat()
            self.daily_stats[today]["errors"] += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive analytics summary."""
        with self.lock:
            return {
                "total_requests": self.total_requests,
                "total_extractions": self.total_extractions,
                "total_errors": self.total_errors,
                "error_rate": self.total_errors / max(self.total_requests, 1),
                "endpoints": dict(self.endpoint_stats),
                "file_types": dict(self.file_type_stats),
                "recent_request_count": len(self.recent_requests),
                "recent_extraction_count": len(self.recent_extractions),
                "recent_error_count": len(self.recent_errors),
            }

    def get_endpoint_stats(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """Get endpoint-specific statistics."""
        with self.lock:
            if endpoint:
                return dict(self.endpoint_stats.get(endpoint, {}))
            else:
                return {
                    k: dict(v) for k, v in self.endpoint_stats.items()
                }

    def get_recent_requests(self, limit: int = 100) -> list:
        """Get recent requests."""
        with self.lock:
            return list(self.recent_requests)[-limit:]

    def get_recent_errors(self, limit: int = 50) -> list:
        """Get recent errors."""
        with self.lock:
            return list(self.recent_errors)[-limit:]

    def get_daily_stats(self, days: int = 7) -> Dict[str, Dict[str, Any]]:
        """Get daily statistics for last N days."""
        with self.lock:
            cutoff = datetime.utcnow().date() - timedelta(days=days)
            return {
                date_str: {
                    "requests": stats["requests"],
                    "extractions": stats["extractions"],
                    "errors": stats["errors"],
                    "unique_users": len(stats["users"]),
                }
                for date_str, stats in self.daily_stats.items()
                if date_str >= cutoff.isoformat()
            }

    def get_health_metrics(self) -> Dict[str, Any]:
        """Get system health metrics."""
        with self.lock:
            total = self.total_requests or 1
            recent_100 = list(self.recent_requests)[-100:]
            recent_errors_100 = list(self.recent_errors)[-100:]
            
            # Calculate error rates
            recent_error_rate = len(recent_errors_100) / len(recent_100) if recent_100 else 0
            
            # Calculate average response time
            recent_avg_time = (
                sum(r.get("duration_ms", 0) for r in recent_100) / len(recent_100)
                if recent_100 else 0
            )
            
            # Determine health status
            health_score = 100
            
            if recent_error_rate > 0.1:  # >10% errors
                health_score -= 30
            elif recent_error_rate > 0.05:  # >5% errors
                health_score -= 15
            
            if recent_avg_time > 5000:  # >5s avg response
                health_score -= 20
            elif recent_avg_time > 2000:  # >2s avg response
                health_score -= 10
            
            health_status = "healthy" if health_score >= 80 else "degraded" if health_score >= 50 else "unhealthy"
            
            return {
                "health_status": health_status,
                "health_score": max(0, health_score),
                "error_rate": self.total_errors / total,
                "recent_error_rate": recent_error_rate,
                "avg_response_time_ms": recent_avg_time,
                "uptime_requests": self.total_requests,
                "top_error_types": self._get_top_errors(5),
            }

    def _get_top_errors(self, limit: int = 5) -> Dict[str, int]:
        """Get most common error types."""
        error_counts = defaultdict(int)
        for error in self.recent_errors:
            error_type = error.get("error_type", "unknown")
            error_counts[error_type] += 1
        
        return dict(sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:limit])

    def reset(self) -> None:
        """Reset all metrics."""
        with self.lock:
            self.total_requests = 0
            self.total_extractions = 0
            self.total_errors = 0
            self.recent_requests.clear()
            self.recent_extractions.clear()
            self.recent_errors.clear()
            self.endpoint_stats.clear()
            self.file_type_stats.clear()
            self.daily_stats.clear()
            self.logger.info("Analytics metrics reset")


# Global analytics instance
_analytics = None


def get_analytics() -> AnalyticsEngine:
    """Get or create global analytics instance."""
    global _analytics
    if _analytics is None:
        _analytics = AnalyticsEngine()
    return _analytics
