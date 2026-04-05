"""
OpenAI Extraction Service
Uses GPT-4 Turbo to extract structured policy data from documents
"""

import json
import logging
from typing import Optional, Dict, Any
from openai import OpenAI, APIError
from ..config import get_settings
from .prompts import (
    POLICY_EXTRACTION_SYSTEM_PROMPT,
    COMPARE_SUMMARY_PROMPT,
    build_extraction_prompt,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize OpenAI client (reused across requests)
openai_client = OpenAI(api_key=settings.openai_api_key)


class OpenAIExtractor:
    """AI-powered policy data extraction using GPT-4."""
    
    @staticmethod
    def extract_policy_from_text(
        document_text: str,
        payer_name: str,
        drug_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract structured policy data from document text using GPT-4.
        
        Process:
        1. Validate input text length
        2. Build extraction prompt with context
        3. Call OpenAI GPT-4 API with system prompt
        4. Parse JSON response
        5. Validate against schema
        6. Return structured data
        
        Args:
            document_text: Raw text from PDF/HTML/image parser
            payer_name: Name of health plan (e.g., "UnitedHealthcare")
            drug_name: Optional specific drug to extract policies for
        
        Returns:
            Dictionary with extracted policy data:
            {
                "payer": "UnitedHealthcare",
                "drugs": [...],
                "criteria": [...],
                "extracted_at": "2024-01-01T00:00:00Z"
            }
        
        Raises:
            ValueError: If text is too short or invalid
            APIError: If OpenAI API call fails
        """
        # Validate input
        if not document_text or len(document_text.strip()) < 100:
            raise ValueError("Document text is too short for meaningful extraction (min 100 chars)")
        
        logger.info(f"Extracting policy from {payer_name}, text length: {len(document_text)}")
        
        # Build prompt
        user_message = build_extraction_prompt(document_text, payer_name, drug_name)
        
        try:
            # Call OpenAI GPT-4 API
            response = openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": POLICY_EXTRACTION_SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent extraction
                max_tokens=4096,
                response_format={"type": "json_object"}  # Ensure JSON response
            )
            
            # Extract response text
            raw_response = response.choices[0].message.content.strip()
            logger.debug(f"OpenAI raw response: {len(raw_response)} characters")
            
            # Parse JSON
            extracted_data = OpenAIExtractor._parse_json_response(raw_response)
            
            # Validate structure
            extracted_data = OpenAIExtractor._validate_extraction_schema(extracted_data)
            
            logger.info(f"Policy extraction successful: {len(extracted_data.get('drugs', []))} drugs found")
            
            return extracted_data
        
        except APIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise ValueError(f"OpenAI API call failed: {str(e)}")
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            raise ValueError(f"OpenAI returned invalid JSON: {str(e)}")
        
        except Exception as e:
            logger.error(f"Unexpected extraction error: {str(e)}")
            raise ValueError(f"Extraction failed: {str(e)}")
    
    @staticmethod
    def generate_comparison_summary(policies_data: list[Dict]) -> str:
        """
        Generate natural language comparison of multiple policies.
        
        Args:
            policies_data: List of extracted policy dictionaries
        
        Returns:
            Natural language comparison text
        """
        if not policies_data:
            return "No policies provided for comparison."
        
        if len(policies_data) < 2:
            return f"Only one policy provided ({policies_data[0].get('payer', 'Unknown')}). Need at least 2 for comparison."
        
        try:
            # Format policies as clean JSON
            policies_json = json.dumps(policies_data, indent=2)
            
            prompt = f"""{COMPARE_SUMMARY_PROMPT}

Policies to compare:
{policies_json}

Generate a 2-3 paragraph comparison focusing on:
1. Coverage differences across plans
2. Prior authorization and step therapy requirements
3. Most restrictive and most lenient plans
4. Key takeaways for patients/clinicians"""
            
            response = openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a healthcare policy analyst. Write clear, structured comparisons of drug coverage policies."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.5,
                max_tokens=2000
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info(f"Comparison summary generated: {len(summary)} characters")
            return summary
        
        except Exception as e:
            logger.error(f"Error generating comparison: {str(e)}")
            return "Failed to generate comparison summary."
    
    @staticmethod
    def extract_clinical_criteria(policy_text: str) -> Dict[str, Any]:
        """
        Extract clinical criteria (step therapy, biomarkers, etc.)
        
        Args:
            policy_text: Policy document text
        
        Returns:
            Dictionary with extracted criteria
        """
        try:
            prompt = """Analyze this drug coverage policy and extract clinical criteria:
- Prior authorization required (yes/no)
- Step therapy requirements
- Biomarker/genetic testing requirements
- Age restrictions
- Other clinical restrictions

Policy text:
""" + policy_text[:2000]  # Limit to first 2000 chars
            
            response = openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Extract clinical criteria from drug coverage policy. Return as JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            criteria = OpenAIExtractor._parse_json_response(
                response.choices[0].message.content
            )
            return criteria
        
        except Exception as e:
            logger.error(f"Clinical criteria extraction error: {str(e)}")
            return {}
    
    @staticmethod
    def _parse_json_response(raw_response: str) -> Dict[str, Any]:
        """
        Safely parse JSON response from OpenAI.
        
        Args:
            raw_response: Raw response text from OpenAI
        
        Returns:
            Parsed JSON dictionary
        """
        try:
            # Try direct parsing first
            return json.loads(raw_response)
        except json.JSONDecodeError:
            # Try extracting JSON from markdown code blocks
            if "```json" in raw_response:
                json_str = raw_response.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in raw_response:
                json_str = raw_response.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            else:
                # Last resort: try to find JSON-like structure
                import re
                json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    raise json.JSONDecodeError("Could not find JSON in response", raw_response, 0)
    
    @staticmethod
    def _validate_extraction_schema(data: Dict) -> Dict:
        """
        Validate extracted data against expected schema.
        
        Ensures all required fields are present and correctly formatted.
        
        Args:
            data: Extracted data dictionary
        
        Returns:
            Validated data with defaults for missing fields
        """
        # Ensure required structure
        if not isinstance(data, dict):
            raise ValueError("Extracted data must be a dictionary")
        
        # Set defaults for missing fields
        validated = {
            "payer": data.get("payer", "Unknown"),
            "drugs": data.get("drugs", []),
            "criteria": data.get("criteria", []),
            "prior_auth_required": data.get("prior_auth_required", False),
            "step_therapy_required": data.get("step_therapy_required", False),
            "restrictions": data.get("restrictions", []),
            "extracted_at": data.get("extracted_at", ""),
            "confidence": data.get("confidence", 0.8)
        }
        
        # Validate drugs list
        if not isinstance(validated["drugs"], list):
            validated["drugs"] = []
        
        # Validate criteria list
        if not isinstance(validated["criteria"], list):
            validated["criteria"] = []
        
        logger.debug(f"Schema validation passed: {len(validated['drugs'])} drugs, {len(validated['criteria'])} criteria")
        
        return validated
    
    @staticmethod
    def test_connection() -> bool:
        """
        Test OpenAI API connection.
        
        Returns:
            True if connection successful
        """
        try:
            response = openai_client.models.list()
            logger.info("OpenAI connection test successful")
            return True
        except Exception as e:
            logger.error(f"OpenAI connection test failed: {str(e)}")
            return False


# Convenience functions for backward compatibility
def extract_policy_from_text(
    document_text: str,
    payer_name: str
) -> Dict[str, Any]:
    """Wrapper for backward compatibility."""
    return OpenAIExtractor.extract_policy_from_text(document_text, payer_name)


def generate_comparison_summary(policies_data: list[Dict]) -> str:
    """Wrapper for backward compatibility."""
    return OpenAIExtractor.generate_comparison_summary(policies_data)
