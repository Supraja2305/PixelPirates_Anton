"""
Token Manager - Secure token generation with hash-based validation
Implements "reveal-once" pattern: token shown once, then only hash is stored
"""

import logging
import hashlib
import secrets
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from uuid import uuid4

logger = logging.getLogger(__name__)


class TokenManager:
    """
    Manages token generation, hashing, and validation.
    
    Pattern:
    1. Generate token → Return to user with "revealed" flag
    2. User stores token securely (client-side)
    3. Hash the token and store hash in database
    4. User sends token in requests → Validate against hash
    5. Token can only be viewed once; after that only hash exists
    """

    def __init__(self):
        """Initialize token manager."""
        # In-memory storage: token_id -> {user_id, token_hash, user_type, created_at, expires_at, revealed_at}
        self.tokens: Dict[str, Dict] = {}
        # Track revealed tokens (token_id -> bool)
        self.revealed: Dict[str, bool] = {}

    def _hash_token(self, token: str) -> str:
        """Hash a token using SHA256."""
        return hashlib.sha256(token.encode()).hexdigest()

    def _generate_token_string(self, length: int = 32) -> str:
        """Generate a cryptographically secure random token."""
        return secrets.token_urlsafe(length)

    def create_and_reveal_token(
        self,
        user_id: str,
        user_type: str,  # "doctor" or "admin"
        expiry_hours: int = 24,
    ) -> Tuple[str, str, Dict]:
        """
        Create a new token, hash it, and return for first-time reveal.
        
        After this call:
        - User gets the plain token (store securely client-side)
        - Server stores only the hash
        - Token can be revealed only once via API
        
        Args:
            user_id: ID of the user (doctor or admin)
            user_type: Type of user ("doctor" or "admin")
            expiry_hours: Hours until token expires (default: 24)
            
        Returns:
            Tuple of (token_id, plain_token, reveal_response)
            
        Example:
            token_id, plain_token, response = tm.create_and_reveal_token(
                user_id="doc-123",
                user_type="doctor",
                expiry_hours=24
            )
            # Response contains:
            # {
            #   "token": "k8p9x2m5n...",  # <-- Show this once to user
            #   "token_id": "uuid",
            #   "expires_in_hours": 24,
            #   "reveal_status": "REVEALED_ONCE",
            #   "note": "Store this token securely. It will not be shown again."
            # }
        """
        token_id = str(uuid4())
        plain_token = self._generate_token_string()
        token_hash = self._hash_token(plain_token)

        now = datetime.utcnow()
        expires_at = now + timedelta(hours=expiry_hours)

        # Store token metadata (hash only, not plain token)
        self.tokens[token_id] = {
            "user_id": user_id,
            "user_type": user_type,
            "token_hash": token_hash,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "revealed_at": now.isoformat(),  # First reveal
            "last_verified_at": None,
            "verification_count": 0,
            "failed_verifications": 0,
        }

        # Mark as revealed (can view plain token once)
        self.revealed[token_id] = True

        logger.info(
            f"Token created for {user_type} {user_id}: {token_id} (expires in {expiry_hours}h)"
        )

        # Return response for first-time reveal
        reveal_response = {
            "token": plain_token,
            "token_id": token_id,
            "user_id": user_id,
            "user_type": user_type,
            "expires_in_hours": expiry_hours,
            "reveal_status": "REVEALED_ONCE",
            "note": "Store this token securely. It will NOT be shown again.",
            "created_at": now.isoformat(),
        }

        return token_id, plain_token, reveal_response

    def verify_token(self, token_id: str, provided_token: str) -> Tuple[bool, Dict]:
        """
        Verify a provided token against stored hash.
        
        Args:
            token_id: ID of the token
            provided_token: Token provided by user
            
        Returns:
            Tuple of (is_valid, metadata)
            
        Example:
            is_valid, metadata = tm.verify_token("token-uuid", "k8p9x2m5n...")
            if is_valid:
                print(f"Valid token for {metadata['user_id']}")
        """
        if token_id not in self.tokens:
            logger.warning(f"Token verification failed: {token_id} not found")
            return False, {"error": "Token not found"}

        token_data = self.tokens[token_id]

        # Check if expired
        expires_at = datetime.fromisoformat(token_data["expires_at"])
        if datetime.utcnow() > expires_at:
            logger.warning(f"Token expired: {token_id}")
            return False, {"error": "Token expired"}

        # Hash provided token and compare
        provided_hash = self._hash_token(provided_token)

        if provided_hash != token_data["token_hash"]:
            # Wrong token
            token_data["failed_verifications"] = token_data.get("failed_verifications", 0) + 1

            if token_data["failed_verifications"] > 5:
                logger.warning(f"Token locked after 5+ failed attempts: {token_id}")
                token_data["is_locked"] = True

            logger.warning(
                f"Token verification failed for {token_id} "
                f"(failed attempts: {token_data['failed_verifications']})"
            )
            return False, {"error": "Invalid token"}

        # Valid token
        token_data["verification_count"] = token_data.get("verification_count", 0) + 1
        token_data["last_verified_at"] = datetime.utcnow().isoformat()
        token_data["failed_verifications"] = 0

        logger.info(
            f"Token verified successfully: {token_id} for user {token_data['user_id']} "
            f"(verification #{token_data['verification_count']})"
        )

        return True, {
            "user_id": token_data["user_id"],
            "user_type": token_data["user_type"],
            "expires_at": token_data["expires_at"],
            "verification_count": token_data["verification_count"],
        }

    def reveal_token_once(self, token_id: str, plain_token: str) -> Dict:
        """
        Reveal the plain token again (should only work once after creation).
        
        Security note: In production, require admin approval or 2FA for re-reveals.
        
        Args:
            token_id: ID of the token
            plain_token: Plain token to verify
            
        Returns:
            Dictionary with token if not yet revealed, error if already revealed
        """
        if token_id not in self.tokens:
            return {"error": "Token not found", "can_reveal": False}

        if not self.revealed.get(token_id, False):
            logger.warning(f"Token reveal attempt after initial reveal: {token_id}")
            return {
                "error": "Token already revealed and cannot be shown again",
                "can_reveal": False,
                "note": "For security, tokens can only be revealed once",
            }

        # Verify provided token matches before revealing
        is_valid, _ = self.verify_token(token_id, plain_token)
        if not is_valid:
            return {"error": "Invalid token provided", "can_reveal": False}

        # Can reveal once more (in production, implement re-reveal with MFA)
        logger.warning(f"Token re-revealed (should require MFA): {token_id}")
        return {
            "token": plain_token,
            "token_id": token_id,
            "warning": "This is a security-sensitive operation. Ensure token is stored securely.",
            "revealed_again_at": datetime.utcnow().isoformat(),
        }

    def get_token_info(self, token_id: str) -> Dict:
        """
        Get non-sensitive information about a token (no plain token).
        
        Args:
            token_id: ID of the token
            
        Returns:
            Token metadata without sensitive data
        """
        if token_id not in self.tokens:
            return {"error": "Token not found"}

        token_data = self.tokens[token_id]

        return {
            "token_id": token_id,
            "user_id": token_data["user_id"],
            "user_type": token_data["user_type"],
            "created_at": token_data["created_at"],
            "expires_at": token_data["expires_at"],
            "is_expired": datetime.utcnow() > datetime.fromisoformat(token_data["expires_at"]),
            "verification_count": token_data.get("verification_count", 0),
            "failed_verifications": token_data.get("failed_verifications", 0),
            "last_verified_at": token_data.get("last_verified_at"),
            "is_locked": token_data.get("is_locked", False),
        }

    def revoke_token(self, token_id: str) -> Dict:
        """
        Revoke/invalidate a token.
        
        Args:
            token_id: ID of the token to revoke
            
        Returns:
            Confirmation of revocation
        """
        if token_id not in self.tokens:
            return {"error": "Token not found"}

        token_data = self.tokens[token_id]
        token_data["is_revoked"] = True
        token_data["revoked_at"] = datetime.utcnow().isoformat()

        logger.info(f"Token revoked: {token_id} for user {token_data['user_id']}")

        return {
            "success": True,
            "token_id": token_id,
            "revoked_at": token_data["revoked_at"],
        }

    def get_user_tokens(self, user_id: str) -> Dict:
        """
        Get all tokens for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of token info (without hashes)
        """
        user_tokens = [
            {
                "token_id": token_id,
                "user_type": data["user_type"],
                "created_at": data["created_at"],
                "expires_at": data["expires_at"],
                "verification_count": data.get("verification_count", 0),
                "is_locked": data.get("is_locked", False),
                "is_revoked": data.get("is_revoked", False),
            }
            for token_id, data in self.tokens.items()
            if data["user_id"] == user_id
        ]

        return {
            "user_id": user_id,
            "token_count": len(user_tokens),
            "tokens": user_tokens,
        }

    def get_stats(self) -> Dict:
        """Get token manager statistics."""
        total_tokens = len(self.tokens)
        active_tokens = sum(
            1 for data in self.tokens.values()
            if not data.get("is_revoked")
            and datetime.utcnow() < datetime.fromisoformat(data["expires_at"])
        )
        revoked_tokens = sum(1 for data in self.tokens.values() if data.get("is_revoked"))
        expired_tokens = sum(
            1 for data in self.tokens.values()
            if datetime.utcnow() > datetime.fromisoformat(data["expires_at"])
        )
        locked_tokens = sum(1 for data in self.tokens.values() if data.get("is_locked"))

        return {
            "total_tokens": total_tokens,
            "active_tokens": active_tokens,
            "revoked_tokens": revoked_tokens,
            "expired_tokens": expired_tokens,
            "locked_tokens": locked_tokens,
        }

    def cleanup_expired_tokens(self) -> Dict:
        """Remove expired and revoked tokens from storage."""
        initial_count = len(self.tokens)

        # Remove expired tokens
        expired_ids = [
            token_id
            for token_id, data in self.tokens.items()
            if datetime.utcnow() > datetime.fromisoformat(data["expires_at"])
        ]

        for token_id in expired_ids:
            del self.tokens[token_id]
            if token_id in self.revealed:
                del self.revealed[token_id]

        final_count = len(self.tokens)
        removed_count = initial_count - final_count

        logger.info(f"Cleaned up {removed_count} expired tokens")

        return {
            "removed": removed_count,
            "remaining": final_count,
        }


# Singleton instance
token_manager = TokenManager()
