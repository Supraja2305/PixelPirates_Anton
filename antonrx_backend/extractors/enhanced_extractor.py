"""
Enhanced Document Extractor with Claude
Extracts policy data from documents with confidence scoring and versioning
"""

import logging
import json
import hashlib
from typing import Dict, Optional, Tuple
from datetime import datetime
from anthropic import Anthropic

logger = logging.getLogger(__name__)


class EnhancedExtractor:
    """
    Enhanced Claude-based document extractor with:
    - Confidence scoring
    - Checksum-based duplicate detection
    - Versioning support
    - Structured extraction with validation
    """

    def __init__(self):
        """Initialize extractor with Claude client."""
        self.client = Anthropic()
        self.model = "claude-3-5-sonnet-20241022"
        self.extraction_cache: Dict[str, Dict] = {}

    def extract_policy_from_document(
        self, document_text: str, document_id: str, force_reextract: bool = False
    ) -> Tuple[Dict, float, str]:
        """
        Extract policy information from document text using Claude.
        
        Args:
            document_text: Full text of the document
            document_id: ID of the document (for caching)
            force_reextract: Skip cache and force re-extraction
            
        Returns:
            Tuple of (extracted_data dict, confidence_score 0-100, checksum)
        """
        # Generate checksum for duplicate detection
        checksum = self._compute_checksum(document_text)

        # Check cache if not forcing re-extraction
        if not force_reextract and checksum in self.extraction_cache:
            logger.info(f"Using cached extraction for document {document_id}")
            cached = self.extraction_cache[checksum]
            return cached["data"], cached["confidence"], checksum

        logger.info(f"Starting policy extraction for document {document_id}")

        # Create extraction prompt
        prompt = self._create_extraction_prompt(document_text)

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text

            # Parse response and extract confidence
            extracted_data, confidence = self._parse_extraction_response(response_text)

            # Flag for human review if confidence too low
            if confidence < 70:
                extracted_data["requires_human_review"] = True
                logger.warning(
                    f"Low confidence extraction ({confidence:.1f}) for document {document_id} - flagging for review"
                )
            else:
                extracted_data["requires_human_review"] = False

            # Cache result
            self.extraction_cache[checksum] = {
                "data": extracted_data,
                "confidence": confidence,
                "document_id": document_id,
                "extracted_at": datetime.now().isoformat(),
            }

            logger.info(
                f"Policy extraction complete: {document_id} (confidence: {confidence:.1f}%)"
            )

            return extracted_data, confidence, checksum

        except Exception as e:
            logger.error(f"Error extracting policy from document {document_id}: {str(e)}")
            return {}, 0.0, checksum

    def reextract_with_updated_prompt(
        self, document_text: str, document_id: str, updated_prompt_template: str = None
    ) -> Tuple[Dict, float]:
        """
        Re-extract document with updated prompt (for testing/tuning).
        
        Args:
            document_text: Document text
            document_id: Document ID
            updated_prompt_template: Optional custom prompt template
            
        Returns:
            Tuple of (extracted_data, confidence)
        """
        logger.info(f"Re-extracting document {document_id} with updated prompt")

        if updated_prompt_template:
            prompt = updated_prompt_template.format(document_text=document_text)
        else:
            prompt = self._create_extraction_prompt(document_text)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text
            extracted_data, confidence = self._parse_extraction_response(response_text)

            logger.info(f"Re-extraction complete: {document_id} (confidence: {confidence:.1f}%)")

            return extracted_data, confidence

        except Exception as e:
            logger.error(f"Error re-extracting document {document_id}: {str(e)}")
            return {}, 0.0

    def manual_override(
        self, extracted_data: Dict, field_name: str, new_value, reason: str
    ) -> Dict:
        """
        Manually correct an extracted field.
        
        Args:
            extracted_data: Original extracted data
            field_name: Field to override
            new_value: New value for the field
            reason: Reason for override (for audit log)
            
        Returns:
            Updated extracted data with override metadata
        """
        if "overrides" not in extracted_data:
            extracted_data["overrides"] = []

        override_record = {
            "field": field_name,
            "old_value": extracted_data.get(field_name),
            "new_value": new_value,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }

        extracted_data["overrides"].append(override_record)
        extracted_data[field_name] = new_value

        logger.info(f"Manual override applied: {field_name} = {new_value} (reason: {reason})")

        return extracted_data

    def _create_extraction_prompt(self, document_text: str) -> str:
        """Create the extraction prompt for Claude."""
        prompt = f"""You are an expert medical insurance policy analyst.
Extract the following information from the policy document below and respond ONLY with valid JSON, no other text.

Required JSON fields:
{{
  "payer_name": "name of insurance company",
  "policy_name": "name of the policy",
  "effective_date": "YYYY-MM-DD format",
  "coverage_rules": {{
    "drug_name": {{
      "copay": number_or_null,
      "prior_auth": boolean,
      "step_therapy": boolean,
      "quantity_limit": number_or_null,
      "restrictions": "text description"
    }}
  }},
  "precertification_required": boolean,
  "appeals_process": "text description",
  "extraction_confidence_notes": "your assessment of how confident you are in this extraction (0-100)"
}}

Document to analyze:
{document_text}

Respond with ONLY the JSON object, no markdown, no extra text."""

        return prompt

    def _parse_extraction_response(self, response_text: str) -> Tuple[Dict, float]:
        """
        Parse Claude's response and extract confidence score.
        
        Returns:
            Tuple of (extracted_data dict, confidence_score 0-100)
        """
        try:
            # Clean response (remove markdown if present)
            response_text = response_text.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            response_text = response_text.strip()

            # Parse JSON
            data = json.loads(response_text)

            # Extract confidence from notes
            confidence_notes = data.get("extraction_confidence_notes", "75")
            try:
                # Try to extract number from confidence notes
                import re

                numbers = re.findall(r"\d+", str(confidence_notes))
                confidence = float(numbers[0]) if numbers else 75.0
                confidence = min(100, max(0, confidence))  # Clamp to 0-100
            except (ValueError, IndexError):
                confidence = 75.0

            # Remove confidence notes from final data (it's metadata)
            data.pop("extraction_confidence_notes", None)

            logger.debug(f"Parsed extraction: confidence={confidence:.1f}%")

            return data, confidence

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse extraction response as JSON: {str(e)}")
            return {}, 0.0

    def _compute_checksum(self, text: str) -> str:
        """Compute SHA256 checksum of document text for duplicate detection."""
        return hashlib.sha256(text.encode()).hexdigest()

    def get_cache_stats(self) -> Dict:
        """Get extraction cache statistics."""
        return {
            "cached_extractions": len(self.extraction_cache),
            "cache_size_mb": len(json.dumps(self.extraction_cache)) / (1024 * 1024),
        }


# Singleton instance
enhanced_extractor = EnhancedExtractor()
