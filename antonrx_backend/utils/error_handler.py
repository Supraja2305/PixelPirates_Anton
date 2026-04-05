"""
Error Handler Module
Centralized error handling, logging, and standardized error responses
"""

import logging
import traceback
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import HTTPException, status
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    """Error categories for organization and debugging."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    RESOURCE_NOT_FOUND = "resource_not_found"
    CONFLICT = "conflict"
    RATE_LIMIT = "rate_limit"
    EXTERNAL_API = "external_api"
    DATABASE = "database"
    FILE_OPERATION = "file_operation"
    EXTRACTION = "extraction"
    PARSING = "parsing"
    UNKNOWN = "unknown"


class AntonRXException(Exception):
    """Base exception for AntonRX backend."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        status_code: int = 500,
        details: Dict[str, Any] = None
    ):
        self.message = message
        self.category = category
        self.status_code = status_code
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat()
        
        super().__init__(self.message)


class AuthenticationError(AntonRXException):
    """Authentication error (missing/invalid credentials)."""
    
    def __init__(self, message: str = "Authentication failed", details: Dict = None):
        super().__init__(
            message,
            category=ErrorCategory.AUTHENTICATION,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class AuthorizationError(AntonRXException):
    """Authorization error (insufficient permissions)."""
    
    def __init__(self, message: str = "Insufficient permissions", details: Dict = None):
        super().__init__(
            message,
            category=ErrorCategory.AUTHORIZATION,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class ValidationError(AntonRXException):
    """Data validation error."""
    
    def __init__(self, message: str = "Validation failed", details: Dict = None):
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class ResourceNotFoundError(AntonRXException):
    """Resource not found error."""
    
    def __init__(self, resource_type: str = "Resource", resource_id: str = None):
        message = f"{resource_type} not found"
        if resource_id:
            message += f": {resource_id}"
        
        super().__init__(
            message,
            category=ErrorCategory.RESOURCE_NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource_type": resource_type, "resource_id": resource_id}
        )


class ConflictError(AntonRXException):
    """Resource conflict error (e.g., duplicate)."""
    
    def __init__(self, message: str = "Resource conflict", details: Dict = None):
        super().__init__(
            message,
            category=ErrorCategory.CONFLICT,
            status_code=status.HTTP_409_CONFLICT,
            details=details
        )


class RateLimitError(AntonRXException):
    """Rate limit exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        super().__init__(
            message,
            category=ErrorCategory.RATE_LIMIT,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"retry_after": retry_after}
        )


class ExternalAPIError(AntonRXException):
    """External API (Claude, Supabase) error."""
    
    def __init__(self, api_name: str, message: str, details: Dict = None):
        full_message = f"{api_name} API error: {message}"
        super().__init__(
            full_message,
            category=ErrorCategory.EXTERNAL_API,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details
        )


class DatabaseError(AntonRXException):
    """Database operation error."""
    
    def __init__(self, message: str = "Database error", details: Dict = None):
        super().__init__(
            message,
            category=ErrorCategory.DATABASE,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class FileOperationError(AntonRXException):
    """File operation error."""
    
    def __init__(self, message: str = "File operation failed", details: Dict = None):
        super().__init__(
            message,
            category=ErrorCategory.FILE_OPERATION,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class ExtractionError(AntonRXException):
    """Data extraction error."""
    
    def __init__(self, message: str = "Extraction failed", details: Dict = None):
        super().__init__(
            message,
            category=ErrorCategory.EXTRACTION,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class PipelineError(AntonRXException):
    """Error during processing pipeline."""
    
    def __init__(self, stage: str, message: str, details: Dict = None):
        full_message = f"Pipeline error at '{stage}': {message}"
        super().__init__(
            full_message,
            category=ErrorCategory.EXTRACTION,
            status_code=status.HTTP_400_BAD_REQUEST,
            details={**(details or {}), "stage": stage}
        )


class ErrorHandler:
    """Centralized error logging and standardization."""
    
    @staticmethod
    def format_error_response(exception: AntonRXException) -> Dict[str, Any]:
        """
        Format exception as standardized error response.
        
        Returns:
            Dictionary with error details for API response
        """
        response = {
            "error": {
                "message": exception.message,
                "category": exception.category.value,
                "timestamp": exception.timestamp,
                "status_code": exception.status_code
            }
        }
        
        if exception.details:
            response["error"]["details"] = exception.details
        
        return response
    
    @staticmethod
    def log_error(
        exception: Exception,
        endpoint: str = None,
        user_id: str = None,
        additional_context: Dict = None
    ) -> None:
        """
        Log error with context for debugging.
        
        Args:
            exception: Exception object
            endpoint: API endpoint where error occurred
            user_id: User ID if applicable
            additional_context: Any additional context data
        """
        log_entry = {
            "error_type": type(exception).__name__,
            "message": str(exception),
            "timestamp": datetime.utcnow().isoformat(),
            "endpoint": endpoint,
            "user_id": user_id
        }
        
        if additional_context:
            log_entry["context"] = additional_context
        
        # Log with appropriate level
        if isinstance(exception, AntonRXException):
            if exception.status_code >= 500:
                logger.error(f"Server error: {log_entry}", exc_info=True)
            elif exception.status_code >= 400:
                logger.warning(f"Client error: {log_entry}")
            else:
                logger.info(f"Info: {log_entry}")
        else:
            logger.error(f"Unexpected error: {log_entry}", exc_info=True)
    
    @staticmethod
    def handle_exception(
        exception: Exception,
        endpoint: str = None,
        user_id: str = None,
        allow_detail_exposure: bool = False
    ) -> HTTPException:
        """
        Convert exception to HTTPException for FastAPI.
        
        Args:
            exception: Exception to handle
            endpoint: API endpoint context
            user_id: User making the request
            allow_detail_exposure: Whether to expose details to client
        
        Returns:
            HTTPException for FastAPI to return
        """
        # Log the error
        ErrorHandler.log_error(exception, endpoint, user_id)
        
        # If it's already an AntonRXException, convert to HTTPException
        if isinstance(exception, AntonRXException):
            response = ErrorHandler.format_error_response(exception)
            
            detail = response if allow_detail_exposure else exception.message
            
            return HTTPException(
                status_code=exception.status_code,
                detail=detail
            )
        
        # For unknown exceptions, return 500
        logger.error(f"Unhandled exception: {exception}", exc_info=True)
        
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later."
        )
    
    @staticmethod
    def safe_execute(
        func,
        *args,
        default_return=None,
        error_category: ErrorCategory = ErrorCategory.UNKNOWN,
        **kwargs
    ):
        """
        Safety wrapper for function execution with error handling.
        
        Args:
            func: Function to execute
            *args: Function arguments
            default_return: Value to return on error
            error_category: Category for error logging
            **kwargs: Function keyword arguments
        
        Returns:
            Function result or default_return on error
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            return default_return


# Convenience functions for common error scenarios

def raise_auth_error(message: str = "Authentication required") -> None:
    """Raise authentication error."""
    raise AuthenticationError(message)


def raise_auth_error_if_missing(user: Optional[Any], message: str = "User not authenticated") -> None:
    """Raise auth error if user is None."""
    if user is None:
        raise AuthenticationError(message)


def raise_permission_error(message: str = "Permission denied") -> None:
    """Raise authorization error."""
    raise AuthorizationError(message)


def raise_not_found(resource_type: str, resource_id: str = None) -> None:
    """Raise resource not found error."""
    raise ResourceNotFoundError(resource_type, resource_id)


def raise_validation_error(message: str, details: Dict = None) -> None:
    """Raise validation error."""
    raise ValidationError(message, details)


def log_error(
    exception: Exception,
    endpoint: str = None,
    user_id: str = None,
    additional_context: Dict = None
) -> None:
    """
    Module-level convenience function for logging errors.
    
    Args:
        exception: Exception object
        endpoint: API endpoint where error occurred
        user_id: User ID if applicable
        additional_context: Any additional context data
    """
    ErrorHandler.log_error(exception, endpoint, user_id, additional_context)
