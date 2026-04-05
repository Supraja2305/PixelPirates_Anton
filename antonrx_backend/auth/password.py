from passlib.context import CryptContext
import logging
import re

logger = logging.getLogger(__name__)

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)


def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password using bcrypt with 12 rounds.
    """

    if not plain_password or not isinstance(plain_password, str):
        logger.error("Invalid password input for hashing")
        raise ValueError("Password must be a non-empty string")

    # 🔴 FIX: bcrypt max length = 72 bytes
    byte_length = len(plain_password.encode("utf-8"))
    if byte_length > 72:
        logger.warning(f"Password too long: {byte_length} bytes (max 72 for bcrypt)")
        raise ValueError(f"Password is too long ({byte_length} bytes). Maximum allowed is 72 bytes for security reasons. Please use a shorter password.")

    try:
        hashed = pwd_context.hash(plain_password)
        logger.debug("Password hashed successfully")
        return hashed

    except Exception as e:
        logger.exception("Error during password hashing")  # logs full traceback
        raise ValueError(f"Failed to hash password: {str(e)}")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a stored bcrypt hash.
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.warning(f"Password verification error: {str(e)}")
        return False


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength according to security policy.
    """

    if not password:
        return False, "Password is required"

    # 🔴 Add this too (consistency with bcrypt limit)
    if len(password.encode("utf-8")) > 72:
        return False, "Password must not exceed 72 bytes"

    if len(password) < 12:
        return False, "Password must be at least 12 characters long"

    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"

    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
        return False, "Password must contain at least one special character"

    return True, "Password is strong"


def is_password_common(password: str) -> bool:
    """
    Check if password is in common password list.
    """

    common_passwords = {
        "password", "123456", "12345678", "qwerty", "abc123",
        "password123", "admin", "letmein", "welcome", "monkey",
        "password1", "admin123", "test", "test123", "1234567890"
    }

    return password.lower() in common_passwords