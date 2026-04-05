"""
Schema Validator Module
Validates AI extraction outputs and ensures data integrity
"""

import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class SchemaValidator:
    """Comprehensive data schema validation for policy extractions."""
    
    # Required fields for policy extraction
    REQUIRED_EXTRACTION_FIELDS = {
        'payer': str,
        'coverage_status': str,
        'extracted_at': str
    }
    
    # Optional fields with type validation
    OPTIONAL_EXTRACTION_FIELDS = {
        'drugs': list,
        'criteria': list,
        'restrictions': list,
        'confidence': float,
        'errors': list
    }
    
    # Valid values for enums
    VALID_COVERAGE_STATUSES = {
        'covered',
        'not_covered',
        'covered_with_restrictions',
        'investigational',
        'unknown'
    }
    
    VALID_CRITERIA_TYPES = {
        'prior_authorization',
        'step_therapy',
        'diagnosis_required',
        'lab_required',
        'prescriber_specialty',
        'site_of_care',
        'quantity_limit',
        'age_restriction',
        'other'
    }
    
    @staticmethod
    def validate_extraction_output(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate full extraction output from Claude.
        
        Checks:
        1. All required fields present
        2. All field types correct
        3. Enum values valid
        4. No malicious or invalid data
        
        Args:
            data: Extracted data dictionary from Claude
        
        Returns:
            Tuple of (is_valid: bool, errors: List[str])
        """
        validation_errors = []
        
        if not isinstance(data, dict):
            return False, ["Data must be a dictionary"]
        
        # Check required fields
        for field, field_type in SchemaValidator.REQUIRED_EXTRACTION_FIELDS.items():
            if field not in data:
                validation_errors.append(f"Missing required field: {field}")
            elif not isinstance(data[field], field_type):
                validation_errors.append(f"Field '{field}' must be {field_type.__name__}, got {type(data[field]).__name__}")
        
        # Validate coverage_status enum
        if 'coverage_status' in data:
            if data['coverage_status'] not in SchemaValidator.VALID_COVERAGE_STATUSES:
                validation_errors.append(
                    f"Invalid coverage_status '{data['coverage_status']}'. "
                    f"Must be one of: {', '.join(SchemaValidator.VALID_COVERAGE_STATUSES)}"
                )
        
        # Validate optional fields
        for field, field_type in SchemaValidator.OPTIONAL_EXTRACTION_FIELDS.items():
            if field in data and not isinstance(data[field], field_type):
                validation_errors.append(
                    f"Field '{field}' must be {field_type.__name__}, got {type(data[field]).__name__}"
                )
        
        # Validate nested structures
        if 'drugs' in data and isinstance(data['drugs'], list):
            for idx, drug in enumerate(data['drugs']):
                drug_errors = SchemaValidator._validate_drug_object(drug, idx)
                validation_errors.extend(drug_errors)
        
        if 'criteria' in data and isinstance(data['criteria'], list):
            for idx, criterion in enumerate(data['criteria']):
                criteria_errors = SchemaValidator._validate_criterion_object(criterion, idx)
                validation_errors.extend(criteria_errors)
        
        # Validate date format
        if 'extracted_at' in data:
            if not SchemaValidator._is_valid_iso_datetime(data['extracted_at']):
                validation_errors.append(f"Invalid datetime format: {data['extracted_at']}. Use ISO format (YYYY-MM-DD or ISO 8601)")
        
        # Validate confidence score
        if 'confidence' in data:
            if not isinstance(data['confidence'], (int, float)) or not (0.0 <= data['confidence'] <= 1.0):
                validation_errors.append("Confidence must be a number between 0.0 and 1.0")
        
        is_valid = len(validation_errors) == 0
        
        if not is_valid:
            logger.warning(f"Schema validation failed: {len(validation_errors)} errors")
            for error in validation_errors:
                logger.warning(f"  - {error}")
        else:
            logger.info("Schema validation passed")
        
        return is_valid, validation_errors
    
    @staticmethod
    def _validate_drug_object(drug: Any, index: int) -> List[str]:
        """Validate individual drug object."""
        errors = []
        
        if not isinstance(drug, dict):
            errors.append(f"Drug[{index}] must be a dictionary")
            return errors
        
        # Check for required drug fields
        if 'generic_name' not in drug and 'brand_name' not in drug:
            errors.append(f"Drug[{index}] must have at least generic_name or brand_name")
        
        # Validate drug property types
        for field in ['generic_name', 'brand_name', 'jcode', 'ndc']:
            if field in drug and not isinstance(drug[field], (str, type(None))):
                errors.append(f"Drug[{index}].{field} must be string or null")
        
        if 'aliases' in drug and not isinstance(drug['aliases'], list):
            errors.append(f"Drug[{index}].aliases must be a list")
        
        # Validate aliases are strings
        if 'aliases' in drug and isinstance(drug['aliases'], list):
            for alias_idx, alias in enumerate(drug['aliases']):
                if not isinstance(alias, str):
                    errors.append(f"Drug[{index}].aliases[{alias_idx}] must be string")
        
        return errors
    
    @staticmethod
    def _validate_criterion_object(criterion: Any, index: int) -> List[str]:
        """Validate individual criteria object."""
        errors = []
        
        if not isinstance(criterion, dict):
            errors.append(f"Criterion[{index}] must be a dictionary")
            return errors
        
        # Check required fields
        if 'restriction_type' not in criterion:
            errors.append(f"Criterion[{index}] missing required field: restriction_type")
        elif criterion['restriction_type'] not in SchemaValidator.VALID_CRITERIA_TYPES:
            errors.append(
                f"Criterion[{index}].restriction_type '{criterion['restriction_type']}' is invalid. "
                f"Must be one of: {', '.join(SchemaValidator.VALID_CRITERIA_TYPES)}"
            )
        
        # Validate field types
        for field in ['description', 'evidence_from_document', 'additional_notes']:
            if field in criterion and not isinstance(criterion[field], (str, type(None))):
                errors.append(f"Criterion[{index}].{field} must be string or null")
        
        if 'is_required' in criterion and not isinstance(criterion['is_required'], bool):
            errors.append(f"Criterion[{index}].is_required must be boolean")
        
        return errors
    
    @staticmethod
    def _is_valid_iso_datetime(datetime_str: str) -> bool:
        """Check if string is valid ISO datetime."""
        if not isinstance(datetime_str, str):
            return False
        
        # Try parsing as ISO datetime
        try:
            datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return True
        except (ValueError, AttributeError):
            return False
    
    @staticmethod
    def sanitize_extraction_output(data: Dict[str, Any], strict: bool = False) -> Dict[str, Any]:
        """
        Sanitize extraction output by:
        1. Removing malicious fields
        2. Normalizing standard fields
        3. Setting safe defaults
        
        Args:
            data: Extracted data
            strict: If True, only allow known fields
        
        Returns:
            Sanitized data
        """
        sanitized = {}
        
        # Only copy known safe fields
        known_fields = set(SchemaValidator.REQUIRED_EXTRACTION_FIELDS.keys()) | set(SchemaValidator.OPTIONAL_EXTRACTION_FIELDS.keys())
        
        for field, value in data.items():
            if field in known_fields:
                sanitized[field] = value
            elif not strict:
                logger.warning(f"Unknown field '{field}' in extraction output")
        
        # Ensure required fields exist
        for field, field_type in SchemaValidator.REQUIRED_EXTRACTION_FIELDS.items():
            if field not in sanitized:
                # Set safe defaults
                if field_type == str:
                    sanitized[field] = "unknown"
        
        # Normalize coverage status
        if 'coverage_status' in sanitized:
            sanitized['coverage_status'] = sanitized['coverage_status'].lower()
            if sanitized['coverage_status'] not in SchemaValidator.VALID_COVERAGE_STATUSES:
                sanitized['coverage_status'] = 'unknown'
        
        # Ensure lists are lists
        for list_field in ['drugs', 'criteria', 'restrictions', 'errors']:
            if list_field in sanitized and not isinstance(sanitized[list_field], list):
                sanitized[list_field] = []
        
        logger.info(f"Extraction output sanitized: {list(sanitized.keys())}")
        
        return sanitized
    
    @staticmethod
    def validate_user_input(input_data: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Generic validation against a schema.
        
        Args:
            input_data: Data to validate
            schema: Validation schema
        
        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []
        
        # Simple validation
        for field, expected_type in schema.items():
            if field not in input_data:
                errors.append(f"Missing required field: {field}")
            elif not isinstance(input_data[field], expected_type):
                errors.append(f"Field '{field}' has wrong type")
        
        return len(errors) == 0, errors


# Convenience functions
def validate_extraction(data: Dict[str, Any]) -> bool:
    """Quick validation check - returns True only if fully valid."""
    is_valid, errors = SchemaValidator.validate_extraction_output(data)
    return is_valid


def sanitize_extraction(data: Dict[str, Any]) -> Dict[str, Any]:
    """Quick sanitization."""
    return SchemaValidator.sanitize_extraction_output(data)
