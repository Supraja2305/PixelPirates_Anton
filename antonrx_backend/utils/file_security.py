"""
File Upload Security Module
Handles validation, sanitization, and secure storage of uploaded files
"""

import os
import re
import shutil
import logging
from pathlib import Path
from typing import Tuple, Optional
from ..config import get_settings
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)
settings = get_settings()


class FileSecurityValidator:
    """Comprehensive file upload security validation."""
    
    # Magic bytes (file signatures) for file type validation
    FILE_SIGNATURES = {
        'pdf': b'%PDF',
        'png': b'\x89PNG\r\n\x1a\n',
        'jpg': b'\xFF\xD8\xFF',
        'jpeg': b'\xFF\xD8\xFF',
        'html': b'<!DOCTYPE',
        'htm': b'<!DOCTYPE'
    }
    
    # Dangerous patterns in filenames
    DANGEROUS_FILENAME_PATTERNS = [
        r'\.\.[\\/]',  # Directory traversal (../ or ..\)
        r'^[\\/]',      # Absolute paths (/ or \ at start)
        r'[<>:"|?*]',   # Invalid Windows characters
        r'[\x00-\x1f]', # Control characters
        r'\.(exe|sh|bat|cmd|scr|vbs|jar)',  # Executable extensions
    ]
    
    @staticmethod
    def validate_file_type(filename: str, file_bytes: bytes) -> Tuple[bool, str]:
        """
        Validate file type by extension and magic bytes.
        
        Args:
            filename: Name of the file
            file_bytes: File content as bytes
        
        Returns:
            Tuple of (is_valid: bool, message: str)
        """
        # Get file extension
        file_ext = Path(filename).suffix.lower().lstrip('.')
        
        if not file_ext:
            return False, "File must have an extension"
        
        # Check against allowed types
        if file_ext not in settings.allowed_types_list:
            return False, f"File type '.{file_ext}' is not allowed. Allowed: {', '.join(settings.allowed_types_list)}"
        
        # Validate magic bytes (file signature)
        if file_ext in FileSecurityValidator.FILE_SIGNATURES:
            expected_sig = FileSecurityValidator.FILE_SIGNATURES[file_ext]
            if not file_bytes.startswith(expected_sig):
                logger.warning(f"File magic bytes don't match extension: {filename}")
                # For HTML/HTM, be more lenient (might have BOM or whitespace)
                if file_ext not in ['html', 'htm']:
                    return False, f"File content doesn't match .{file_ext} format"
        
        return True, "File type is valid"
    
    @staticmethod
    def validate_file_size(file_size_bytes: int) -> Tuple[bool, str]:
        """
        Validate file size against limits.
        
        Args:
            file_size_bytes: File size in bytes
        
        Returns:
            Tuple of (is_valid: bool, message: str)
        """
        max_bytes = settings.max_upload_size_bytes
        
        if file_size_bytes <= 0:
            return False, "File size must be greater than 0"
        
        if file_size_bytes > max_bytes:
            max_mb = settings.max_upload_size_mb
            file_mb = file_size_bytes / (1024 * 1024)
            return False, f"File size ({file_mb:.1f} MB) exceeds maximum of {max_mb} MB"
        
        return True, "File size is valid"
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent directory traversal and injection attacks.
        
        Removes:
        - Directory traversal attempts
        - Special characters
        - Control characters
        - Dangerous patterns
        
        Args:
            filename: Original filename
        
        Returns:
            Sanitized filename
        """
        if not filename:
            raise ValueError("Filename cannot be empty")
        
        # Remove path components (keep only filename)
        filename = Path(filename).name
        
        # Remove dangerous patterns
        for pattern in FileSecurityValidator.DANGEROUS_FILENAME_PATTERNS:
            filename = re.sub(pattern, '', filename, flags=re.IGNORECASE)
        
        # Replace spaces and special chars with underscore
        filename = re.sub(r'[^\w\-.]', '_', filename)
        
        # Limit filename length
        max_length = 255
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            filename = name[:max_length - len(ext)] + ext
        
        # Ensure filename is not empty after sanitization
        if not filename or filename.startswith('.'):
            filename = f"file_{hash(filename) % 10000}"
        
        logger.debug(f"Filename sanitized: {filename}")
        return filename
    
    @staticmethod
    def scan_content_for_malware(file_bytes: bytes) -> Tuple[bool, str]:
        """
        Basic malware scanning (signature-based).
        In production, integrate with ClamAV or similar service.
        
        Args:
            file_bytes: File content to scan
        
        Returns:
            Tuple of (is_safe: bool, message: str)
        """
        if not settings.enable_virus_scan:
            return True, "Virus scan disabled"
        
        # Basic signatures for obvious threats
        dangerous_signatures = [
            b'VirusSignature',  # Placeholder
            b'MalwareName',      # Placeholder
            b'PotentiallyUnwanted',  # Placeholder
        ]
        
        for sig in dangerous_signatures:
            if sig in file_bytes:
                logger.warning(f"Potential malware signature detected: {sig}")
                return False, "File contains potentially malicious content"
        
        return True, "File passed malware scan"


class FileStorageManager:
    """Handles secure file storage and retrieval."""
    
    @staticmethod
    def ensure_upload_directory_exists() -> Path:
        """
        Ensure upload directory exists and has proper permissions.
        
        Returns:
            Path to upload directory
        """
        upload_dir = Path(settings.file_upload_directory)
        
        try:
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            # Set restrictive permissions on Linux/Mac (rwx------)
            if os.name != 'nt':  # Not Windows
                os.chmod(upload_dir, 0o700)
            
            logger.info(f"Upload directory ready: {upload_dir}")
            return upload_dir
        except Exception as e:
            logger.error(f"Error creating upload directory: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to prepare upload directory"
            )
    
    @staticmethod
    def save_file_securely(
        file_bytes: bytes,
        sanitized_filename: str,
        user_id: str
    ) -> Tuple[bool, str]:
        """
        Save file in a secure manner with user isolation.
        
        Args:
            file_bytes: File content
            sanitized_filename: Already sanitized filename
            user_id: User making the upload (for isolation)
        
        Returns:
            Tuple of (success: bool, filepath: str or error_message)
        """
        try:
            # Create user-specific directory for file isolation
            upload_dir = FileStorageManager.ensure_upload_directory_exists()
            user_dir = upload_dir / user_id
            user_dir.mkdir(parents=True, exist_ok=True)
            
            # Set restrictive permissions
            if os.name != 'nt':
                os.chmod(user_dir, 0o700)
            
            # Create final filepath
            filepath = user_dir / sanitized_filename
            
            # Prevent overwriting existing files (use timestamp if needed)
            if filepath.exists():
                name, ext = os.path.splitext(sanitized_filename)
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                sanitized_filename = f"{name}_{timestamp}{ext}"
                filepath = user_dir / sanitized_filename
            
            # Write file with restricted permissions
            with open(filepath, 'wb') as f:
                f.write(file_bytes)
            
            # Set restrictive file permissions (rw-------)
            if os.name != 'nt':
                os.chmod(filepath, 0o600)
            
            logger.info(f"File saved securely: {filepath}")
            return True, str(filepath)
            
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            return False, f"Failed to save file: {str(e)}"
    
    @staticmethod
    def delete_file_securely(filepath: str) -> Tuple[bool, str]:
        """
        Securely delete a file (with overwriting in future versions).
        
        Args:
            filepath: Path to file to delete
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            path = Path(filepath)
            
            # Verify file exists and is in upload directory
            if not path.exists():
                return False, "File not found"
            
            upload_dir = Path(settings.file_upload_directory)
            if not str(path).startswith(str(upload_dir.resolve())):
                return False, "File is outside upload directory"
            
            # Delete file
            path.unlink()
            logger.info(f"File deleted securely: {filepath}")
            return True, "File deleted successfully"
            
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return False, f"Failed to delete file: {str(e)}"


def validate_and_sanitize_upload(
    file_bytes: bytes,
    filename: str,
    user_id: str
) -> Tuple[bool, str, Optional[str]]:
    """
    Complete validation and sanitization pipeline for file uploads.
    
    Steps:
    1. Validate filename format
    2. Validate file size
    3. Validate file type (extension + magic bytes)
    4. Scan for malware
    5. Sanitize filename
    6. Save securely
    
    Args:
        file_bytes: File content
        filename: Original filename
        user_id: User making the upload
    
    Returns:
        Tuple of (success: bool, message: str, stored_path: Optional[str])
    """
    try:
        # Step 1: Validate filename
        if not filename or len(filename) > 255:
            return False, "Invalid filename", None
        
        # Step 2: Validate file size
        size_valid, size_msg = FileSecurityValidator.validate_file_size(len(file_bytes))
        if not size_valid:
            return False, size_msg, None
        
        # Step 3: Validate file type
        type_valid, type_msg = FileSecurityValidator.validate_file_type(filename, file_bytes)
        if not type_valid:
            return False, type_msg, None
        
        # Step 4: Scan for malware
        scan_valid, scan_msg = FileSecurityValidator.scan_content_for_malware(file_bytes)
        if not scan_valid:
            return False, scan_msg, None
        
        # Step 5: Sanitize filename
        sanitized = FileSecurityValidator.sanitize_filename(filename)
        
        # Step 6: Save securely
        save_success, save_result = FileStorageManager.save_file_securely(
            file_bytes,
            sanitized,
            user_id
        )
        
        if not save_success:
            return False, save_result, None
        
        logger.info(f"File uploaded successfully by user {user_id}: {sanitized}")
        return True, "File uploaded successfully", save_result
        
    except Exception as e:
        logger.error(f"Error in upload validation pipeline: {str(e)}")
        return False, f"Upload validation failed: {str(e)}", None
