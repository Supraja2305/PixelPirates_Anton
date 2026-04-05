"""
Diff Engine - Computes differences between policies, drugs, and coverage rules
Provides granular change detection and impact analysis
"""

from typing import Any, Dict, List, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DifferenceDelta:
    """Represents a single difference between two items."""
    field: str
    old_value: Any
    new_value: Any
    change_type: str  # "added", "removed", "modified"
    severity: str = "medium"  # "low", "medium", "high"
    impact_area: str = ""  # e.g., "coverage", "pricing", "requirements"


class DiffEngine:
    """
    Engine for computing structured differences between policies and other entities.
    Supports deep comparison of nested objects and provides impact analysis.
    """

    def __init__(self):
        """Initialize the diff engine."""
        self.severity_map = {
            "coverage": "high",
            "pricing": "high",
            "requirements": "medium",
            "description": "low",
            "metadata": "low",
        }

    def compare_policies(self, policy_1: Dict, policy_2: Dict) -> Tuple[List[DifferenceDelta], float]:
        """
        Compare two policies and return differences and similarity score.
        
        Args:
            policy_1: First policy dict
            policy_2: Second policy dict
            
        Returns:
            Tuple of (differences list, similarity_score 0-1)
        """
        differences = []

        # Compare direct fields
        for field in policy_1.keys() | policy_2.keys():
            val1 = policy_1.get(field)
            val2 = policy_2.get(field)

            if field == "id":
                continue

            if field not in policy_1:
                differences.append(
                    DifferenceDelta(
                        field=field,
                        old_value=None,
                        new_value=val2,
                        change_type="added",
                        severity=self._get_severity(field),
                        impact_area=self._categorize_field(field),
                    )
                )
            elif field not in policy_2:
                differences.append(
                    DifferenceDelta(
                        field=field,
                        old_value=val1,
                        new_value=None,
                        change_type="removed",
                        severity=self._get_severity(field),
                        impact_area=self._categorize_field(field),
                    )
                )
            elif isinstance(val1, dict) and isinstance(val2, dict):
                # Recursive comparison for nested dicts
                nested_diffs = self._compare_nested_dicts(field, val1, val2)
                differences.extend(nested_diffs)
            elif val1 != val2:
                differences.append(
                    DifferenceDelta(
                        field=field,
                        old_value=val1,
                        new_value=val2,
                        change_type="modified",
                        severity=self._get_severity(field),
                        impact_area=self._categorize_field(field),
                    )
                )

        # Calculate similarity score
        total_fields = len(policy_1.keys() | policy_2.keys())
        similarity_score = 1.0 - (len([d for d in differences if d.change_type == "modified"]) / max(total_fields, 1))

        logger.info(f"Policy comparison: {len(differences)} differences found, similarity: {similarity_score:.2f}")

        return differences, similarity_score

    def compare_coverage_rules(self, rules_1: Dict, rules_2: Dict) -> List[DifferenceDelta]:
        """
        Compare two coverage rule sets.
        
        Args:
            rules_1: First coverage rules dict
            rules_2: Second coverage rules dict
            
        Returns:
            List of differences
        """
        differences = []

        # Compare drug coverage
        for drug in set(rules_1.keys()) | set(rules_2.keys()):
            coverage_1 = rules_1.get(drug, {})
            coverage_2 = rules_2.get(drug, {})

            if drug not in rules_1:
                differences.append(
                    DifferenceDelta(
                        field=f"coverage.{drug}",
                        old_value=None,
                        new_value=coverage_2,
                        change_type="added",
                        severity="high",
                        impact_area="coverage",
                    )
                )
            elif drug not in rules_2:
                differences.append(
                    DifferenceDelta(
                        field=f"coverage.{drug}",
                        old_value=coverage_1,
                        new_value=None,
                        change_type="removed",
                        severity="high",
                        impact_area="coverage",
                    )
                )
            elif coverage_1 != coverage_2:
                differences.append(
                    DifferenceDelta(
                        field=f"coverage.{drug}",
                        old_value=coverage_1,
                        new_value=coverage_2,
                        change_type="modified",
                        severity="high",
                        impact_area="coverage",
                    )
                )

        return differences

    def _compare_nested_dicts(self, parent_field: str, dict_1: Dict, dict_2: Dict) -> List[DifferenceDelta]:
        """Compare nested dictionaries recursively."""
        differences = []

        for key in dict_1.keys() | dict_2.keys():
            val_1 = dict_1.get(key)
            val_2 = dict_2.get(key)
            field_path = f"{parent_field}.{key}"

            if key not in dict_1:
                differences.append(
                    DifferenceDelta(
                        field=field_path,
                        old_value=None,
                        new_value=val_2,
                        change_type="added",
                        severity=self._get_severity(field_path),
                        impact_area=self._categorize_field(field_path),
                    )
                )
            elif key not in dict_2:
                differences.append(
                    DifferenceDelta(
                        field=field_path,
                        old_value=val_1,
                        new_value=None,
                        change_type="removed",
                        severity=self._get_severity(field_path),
                        impact_area=self._categorize_field(field_path),
                    )
                )
            elif val_1 != val_2:
                differences.append(
                    DifferenceDelta(
                        field=field_path,
                        old_value=val_1,
                        new_value=val_2,
                        change_type="modified",
                        severity=self._get_severity(field_path),
                        impact_area=self._categorize_field(field_path),
                    )
                )

        return differences

    def _get_severity(self, field: str) -> str:
        """Determine severity level for a field change."""
        field_lower = field.lower()

        for keyword, severity in self.severity_map.items():
            if keyword in field_lower:
                return severity

        return "medium"

    def _categorize_field(self, field: str) -> str:
        """Categorize a field for impact analysis."""
        field_lower = field.lower()

        if "coverage" in field_lower or "drug" in field_lower:
            return "coverage"
        elif "price" in field_lower or "cost" in field_lower or "fee" in field_lower:
            return "pricing"
        elif "requirement" in field_lower or "precertif" in field_lower or "auth" in field_lower:
            return "requirements"
        elif "effective" in field_lower or "date" in field_lower:
            return "timing"
        else:
            return "other"


# Singleton instance
diff_engine = DiffEngine()
