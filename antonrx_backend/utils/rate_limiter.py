"""
Rate Limiting Module
Prevents API abuse with token bucket and sliding window algorithms
"""

import logging
import time
from typing import Dict, Tuple, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
from threading import Lock
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimiter:
    """Implements rate limiting with multiple strategies."""
    
    def __init__(self):
        """Initialize rate limiter with configurable limits."""
        self.general_limit = settings.rate_limit_per_minute
        self.extraction_limit = settings.rate_limit_extraction_per_day
        
        # Token bucket for general rate limiting (per minute)
        self.token_buckets: Dict[str, float] = defaultdict(lambda: float(self.general_limit))
        self.bucket_refill_rate = self.general_limit / 60  # Tokens per second
        self.bucket_timestamps: Dict[str, float] = {}
        
        #Sliding window for extraction limit (per day)
        self.extraction_windows: Dict[str, deque] = defaultdict(deque)
        
        # Thread safety
        self.lock = Lock()
    
    def is_allowed_general(self, identifier: str) -> Tuple[bool, Dict[str, any]]:
        """
        Check if request is allowed under general rate limit (per minute).
        Uses token bucket algorithm.
        
        Args:
            identifier: User ID, API key, or IP address
        
        Returns:
            Tuple of (allowed: bool, details: Dict with rate limit info)
        """
        with self.lock:
            current_time = time.time()
            
            # Initialize if needed
            if identifier not in self.bucket_timestamps:
                self.bucket_timestamps[identifier] = current_time
                self.token_buckets[identifier] = float(self.general_limit)
            
            # Refill tokens since last check
            time_passed = current_time - self.bucket_timestamps[identifier]
            tokens_to_add = time_passed * self.bucket_refill_rate
            self.token_buckets[identifier] = min(
                float(self.general_limit),
                self.token_buckets[identifier] + tokens_to_add
            )
            self.bucket_timestamps[identifier] = current_time
            
            # Check if request is allowed
            if self.token_buckets[identifier] >= 1.0:
                self.token_buckets[identifier] -= 1.0
                
                details = {
                    "allowed": True,
                    "tokens_remaining": int(self.token_buckets[identifier]),
                    "limit": self.general_limit,
                    "window_seconds": 60
                }
                
                logger.debug(f"Rate limit check passed for {identifier}: {details['tokens_remaining']} tokens left")
                return True, details
            else:
                # Calculate when next token will be available
                seconds_to_wait = (1.0 - self.token_buckets[identifier]) / self.bucket_refill_rate
                
                details = {
                    "allowed": False,
                    "tokens_remaining": int(self.token_buckets[identifier]),
                    "limit": self.general_limit,
                    "retry_after_seconds": int(seconds_to_wait) + 1,
                    "window_seconds": 60
                }
                
                logger.warning(f"Rate limit exceeded for {identifier}: {details}")
                return False, details
    
    def is_allowed_extraction(self, identifier: str) -> Tuple[bool, Dict[str, any]]:
        """
        Check if extraction request is allowed (daily limit).
        Uses sliding window algorithm.
        
        Args:
            identifier: User ID
        
        Returns:
            Tuple of (allowed: bool, details: Dict with rate limit info)
        """
        with self.lock:
            current_time = time.time()
            one_day_ago = current_time - (24 * 60 * 60)
            
            # Get or create window for this user
            window = self.extraction_windows[identifier]
            
            # Remove old entries outside the 24-hour window
            while window and window[0] < one_day_ago:
                window.popleft()
            
            # Check if limit exceeded
            if len(window) >= self.extraction_limit:
                # Find when the oldest request was made
                oldest_request_time = window[0]
                seconds_until_clear = (oldest_request_time + (24 * 60 * 60)) - current_time
                
                details = {
                    "allowed": False,
                    "requests_today": len(window),
                    "limit": self.extraction_limit,
                    "retry_after_seconds": max(1, int(seconds_until_clear) + 1),
                    "window_hours": 24
                }
                
                logger.warning(f"Extraction rate limit exceeded for {identifier}: {details}")
                return False, details
            else:
                # Add current request to window
                window.append(current_time)
                
                details = {
                    "allowed": True,
                    "requests_today": len(window),
                    "limit": self.extraction_limit,
                    "requests_remaining": self.extraction_limit - len(window),
                    "window_hours": 24
                }
                
                logger.debug(f"Extraction rate limit check passed: {details['requests_remaining']} requests left")
                return True, details
    
    def get_remaining_quota(self, identifier: str) -> Dict[str, any]:
        """
        Get current quota information for a user/identifier.
        
        Args:
            identifier: User ID
        
        Returns:
            Dictionary with current limits and usage
        """
        with self.lock:
            current_time = time.time()
            
            # General limit
            if identifier in self.bucket_timestamps:
                time_passed = current_time - self.bucket_timestamps[identifier]
                tokens = min(
                    float(self.general_limit),
                    self.token_buckets[identifier] + (time_passed * self.bucket_refill_rate)
                )
            else:
                tokens = float(self.general_limit)
            
            # Extraction limit
            one_day_ago = current_time - (24 * 60 * 60)
            window = self.extraction_windows.get(identifier, deque())
            requests_today = sum(1 for t in window if t >= one_day_ago)
            
            return {
                "general": {
                    "requests_per_minute": int(tokens),
                    "limit": self.general_limit,
                    "window_seconds": 60
                },
                "extraction": {
                    "requests_today": requests_today,
                    "limit": self.extraction_limit,
                    "remaining": max(0, self.extraction_limit - requests_today),
                    "window_hours": 24
                }
            }
    
    def reset_user(self, identifier: str) -> None:
        """
        Reset rate limits for a specific user (admin function).
        
        Args:
            identifier: User ID to reset
        """
        with self.lock:
            if identifier in self.token_buckets:
                del self.token_buckets[identifier]
            if identifier in self.bucket_timestamps:
                del self.bucket_timestamps[identifier]
            if identifier in self.extraction_windows:
                del self.extraction_windows[identifier]
            
            logger.info(f"Rate limits reset for {identifier}")
    
    def get_stats(self) -> Dict[str, any]:
        """
        Get statistics about rate limiter usage.
        
        Returns:
            Dictionary with usage stats
        """
        with self.lock:
            return {
                "tracked_identifiers": len(self.token_buckets),
                "general_limit": self.general_limit,
                "extraction_limit": self.extraction_limit,
                "timestamp": datetime.utcnow().isoformat()
            }


# Global rate limiter instance
_rate_limiter = RateLimiter()


def check_rate_limit(identifier: str, limit_type: str = "general") -> Tuple[bool, Dict]:
    """
    Check if request should be allowed.
    
    Args:
        identifier: User ID, API key, or IP
        limit_type: "general" or "extraction"
    
    Returns:
        Tuple of (allowed, details)
    """
    if limit_type == "extraction":
        return _rate_limiter.is_allowed_extraction(identifier)
    else:
        return _rate_limiter.is_allowed_general(identifier)


def get_quota(identifier: str) -> Dict:
    """Get remaining quota for identifier."""
    return _rate_limiter.get_remaining_quota(identifier)


def reset_limits(identifier: str) -> None:
    """Reset limits for identifier (admin)."""
    _rate_limiter.reset_user(identifier)


# FastAPI middleware helper
class RateLimitMiddleware:
    """
    ASGI middleware for rate limiting.
    Add to app with: app.add_middleware(RateLimitMiddleware)
    """
    
    @staticmethod
    def check_limit(user_id: str, endpoint: str) -> Tuple[bool, Optional[Dict]]:
        """
        Check if request should be allowed.
        Different limits for different endpoints.
        
        Args:
            user_id: User making request
            endpoint: API endpoint
        
        Returns:
            Tuple of (allowed: bool, rate_limit_info: Optional[Dict])
        """
        # Extraction endpoints have stricter limits
        if "extraction" in endpoint or "ingest" in endpoint:
            return check_rate_limit(user_id, "extraction")
        else:
            return check_rate_limit(user_id, "general")
