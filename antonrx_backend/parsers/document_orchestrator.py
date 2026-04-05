# parsers/document_orchestrator.py
# ============================================================
# Unified document parser that routes to appropriate parser
# Supports PDF, HTML, images, Word documents
# ============================================================

import logging
from typing import Dict, Any, Optional
from pathlib import Path

from ..config import get_settings
from ..utils.file_security import FileSecurityValidator
from ..utils.error_handler import log_error, PipelineError

from .pdf_parser import PDFParser
from .html_parser import HTMLParser
from .image_parser import ImageParser
from .word_parser import WordParser


logger = logging.getLogger(__name__)


class DocumentOrchestrator:
    """
    Unified interface for parsing multiple document types.
    Routes to appropriate parser based on file extension and content.
    """
    
    # File type to parser mapping
    PARSER_MAP = {
        '.pdf': 'pdf',
        '.html': 'html',
        '.htm': 'html',
        '.png': 'image',
        '.jpg': 'image',
        '.jpeg': 'image',
        '.gif': 'image',
        '.docx': 'word',
        '.doc': 'word',
        '.odt': 'word',
    }
    
    def __init__(self):
        """Initialize all parsers."""
        self.config = get_settings()
        self.pdf_parser = PDFParser()
        self.html_parser = HTMLParser()
        self.image_parser = ImageParser()
        self.word_parser = WordParser()
        self.file_validator = FileSecurityValidator()
        self.logger = logging.getLogger(self.__class__.__name__)

    def parse_document(
        self,
        file_bytes: bytes,
        filename: str,
        file_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parse document automatically detecting type.
        
        Args:
            file_bytes: Raw file content
            filename: Original filename
            file_type: Optional explicit type ('pdf', 'html', 'word', 'image')
        
        Returns:
            Standardized extraction result with:
                - text: Extracted text content
                - tables: Table data if present
                - metadata: Document metadata
                - confidence: Extraction confidence (0.0-1.0)
                - method: Parser used
                - char_count: Total characters
                - errors: Any parsing errors
        
        Raises:
            PipelineError: If parsing fails or format unsupported
        """
        try:
            # Validate file
            is_valid, fmt, error = self.file_validator.validate_file_type(
                filename, file_bytes, expected_type=file_type
            )
            if not is_valid:
                raise PipelineError(f"File validation failed: {error}")
            
            # Determine parser to use
            if file_type:
                parser_type = file_type.lower()
            else:
                # Auto-detect from extension
                ext = Path(filename).suffix.lower()
                parser_type = self.PARSER_MAP.get(ext)
            
            if not parser_type:
                raise PipelineError(
                    f"Unsupported file type for {filename}. Supported: "
                    f"{', '.join(self.PARSER_MAP.keys())}"
                )
            
            # Route to appropriate parser
            if parser_type == 'pdf':
                result = self.pdf_parser.extract_text_from_pdf(file_bytes, filename)
            elif parser_type == 'html':
                result = self.html_parser.extract_text_from_html(file_bytes, filename)
            elif parser_type == 'image':
                result = self.image_parser.extract_text_from_image(file_bytes, filename)
            elif parser_type == 'word':
                result = self.word_parser.extract_text_from_word(file_bytes, filename)
            else:
                raise PipelineError(f"Unknown parser type: {parser_type}")
            
            # Standardize output
            standardized = self._standardize_result(result, parser_type, filename)
            
            self.logger.info(
                f"Successfully parsed {filename} ({parser_type}): "
                f"{standardized['char_count']} chars"
            )
            return standardized
            
        except PipelineError:
            raise
        except Exception as e:
            error_msg = f"Document parsing failed for {filename}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            log_error(error_msg, context={"filename": filename})
            raise PipelineError(error_msg)

    def _standardize_result(self, result: Dict, parser_type: str, filename: str) -> Dict[str, Any]:
        """Standardize parser output to common format."""
        return {
            "text": result.get("text", ""),
            "tables": result.get("tables", []),
            "pages": result.get("pages", 1),
            "metadata": result.get("metadata", {}),
            "confidence": result.get("confidence", 0.8),
            "method": result.get("method", parser_type),
            "char_count": result.get("char_count", 0),
            "checksum": result.get("checksum"),
            "errors": result.get("errors", []),
            "filename": filename,
            "parser_type": parser_type,
        }

    def get_supported_formats(self) -> Dict[str, str]:
        """Return map of supported file formats."""
        return {
            ".pdf": "PDF documents",
            ".html": "Web pages / HTML",
            ".htm": "Web pages / HTML",
            ".png": "PNG images with OCR",
            ".jpg": "JPEG images with OCR",
            ".jpeg": "JPEG images with OCR",
            ".docx": "Word documents (modern)",
            ".doc": "Word documents (legacy)",
            ".odt": "OpenDocument text",
        }
