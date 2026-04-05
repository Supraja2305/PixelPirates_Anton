"""
HTML Parser Module
Extracts text and structured content from HTML files
"""

import logging
from typing import Dict, Any

logger =logging.getLogger(__name__)

# Try to import HTML processing libraries
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


def extract_text_from_html_bytes(html_bytes: bytes) -> Dict:
    """Extract text from HTML bytes."""
    try:
        if BS4_AVAILABLE:
            html_str = html_bytes.decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html_str, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text(separator='\n', strip=True)
            return {
                "success": True,
                "text": text,
                "extraction_method": "beautifulsoup4",
                "confidence": 0.9,
            }
        else:
            # Fallback: simple regex extraction
            html_str = html_bytes.decode('utf-8', errors='ignore')
            import re
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', html_str)
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            return {
                "success": True,
                "text": text,
                "extraction_method": "regex_fallback",
                "confidence": 0.6,
            }
    except Exception as e:
        logger.error(f"HTML extraction error: {str(e)}")
        return {
            "success": False,
            "text": "",
            "error": str(e),
        }


def extract_text_from_url(url: str) -> Dict:
    """Extract text from HTML URL."""
    try:
        import urllib.request
        with urllib.request.urlopen(url) as response:
            html_bytes = response.read()
        return extract_text_from_html_bytes(html_bytes)
    except Exception as e:
        logger.error(f"URL fetch error: {str(e)}")
        return {
            "success": False,
            "text": "",
            "error": str(e),
        }


class HTMLParser:
    """Class-based HTML parser for compatibility."""
    
    @staticmethod
    def extract(html_bytes: bytes) -> Dict:
        """Extract text from HTML bytes."""
        return extract_text_from_html_bytes(html_bytes)
    
    @staticmethod
    def extractFrom(filepath: str) -> Dict:
        """Extract text from HTML file."""
        with open(filepath, 'rb') as f:
            return extract_text_from_html_bytes(f.read())


__all__ = ['extract_text_from_html_bytes', 'extract_text_from_url', 'HTMLParser']
