"""
PDF Parser Module
Extracts text from PDF files with fallback support
"""

import io
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Try to import optional PDF processing libraries
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import fitz
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def extract_text_from_pdf(file_bytes: bytes) -> Dict:
    """
    Extract text from PDF bytes with fallback options.
    
    Returns:
        Dict with success status, text, and metadata
    """
    try:
        if PDFPLUMBER_AVAILABLE:
            pdf_stream = io.BytesIO(file_bytes)
            with pdfplumber.open(pdf_stream) as pdf:
                pages_text = []
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    pages_text.append(text)
                
                full_text = "\n\n".join(pages_text)
                return {
                    "success": True,
                    "text": full_text,
                    "pages": len(pdf.pages),
                    "extraction_method": "pdfplumber",
                    "confidence": 0.9,
                }
        
        elif FITZ_AVAILABLE:
            pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
            pages_text = []
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                text = page.get_text()
                pages_text.append(text)
            pdf_doc.close()
            
            full_text = "\n\n".join(pages_text)
            return {
                "success": True,
                "text": full_text,
                "pages": len(pdf_doc),
                "extraction_method": "fitz",
                "confidence": 0.85,
            }
        else:
            # No PDF library available
            return {
                "success": False,
                "text": "",
                "error": "No PDF processing library available. Please install pdfplumber or PyMuPDF.",
                "extraction_method": "none",
            }
    
    except Exception as e:
        logger.error(f"PDF extraction error: {str(e)}")
        return {
            "success": False,
            "text": "",
            "error": str(e),
            "extraction_method": "error",
        }


class PDFParser:
    """Class-based PDF parser for compatibility with DocumentOrchestrator."""
    
    @staticmethod
    def extract(file_bytes: bytes) -> Dict:
        """Extract text from PDF using the function."""
        return extract_text_from_pdf(file_bytes)
    
    @staticmethod
    def extractFrom(filepath: str) -> Dict:
        """Extract text from PDF file path."""
        with open(filepath, 'rb') as f:
            return extract_text_from_pdf(f.read())


# For backward compatibility
__all__ = ['extract_text_from_pdf', 'PDFParser']
