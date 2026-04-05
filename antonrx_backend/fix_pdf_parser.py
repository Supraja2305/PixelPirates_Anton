#!/usr/bin/env python
"""Quick script to fix the PDF parser import"""

with open('parsers/pdf_parser.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the direct import with try-except
old_import = """import logging
import fitz  # PyMuPDF
import pdfplumber"""

new_import = """import logging
import pdfplumber

# Try to import fitz (PyMuPDF) for advanced PDF handling
try:
    import fitz  # PyMuPDF — import name is 'fitz'
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False"""

if old_import in content:
    content = content.replace(old_import, new_import)
    with open('parsers/pdf_parser.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ File updated successfully")
else:
    print("❌ Could not find the replacement text")
