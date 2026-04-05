"""
Policy Comparison API Endpoint
Exposes comparison functionality for policies and coverage rules
"""

from typing import List
from pydantic import BaseModel, Field
from ..models.responses import PolicyComparisonResponse, DifferenceDetail
from ..scoring.diff_engine import diff_engine
import logging

logger = logging.getLogger(__name__)


class CompareRequest(BaseModel):
    """Request to compare policies."""
    policy_1_id: str = Field(..., description="First policy ID")
    policy_2_id: str = Field(..., description="Second policy ID")
    include_details: bool = Field(default=True, description="Include detailed differences")


class ComparePayerRequest(BaseModel):
    """Request to compare payers."""
    payer_1_id: str
    payer_2_id: str


class CompareDrugRequest(BaseModel):
    """Request to compare drug coverage across policies."""
    drug_name: str
    policy_ids: List[str] = Field(min_items=2, max_items=5)


class ComparisonService:
    """
    Service for comparing policies, payers, and drug coverage.
    Provides side-by-side analysis and impact assessment.
    """

    def __init__(self):
        """Initialize comparison service."""
        self.diff_engine = diff_engine

    def compare_policies(self, policy_1: dict, policy_2: dict) -> PolicyComparisonResponse:
        """
        Compare two policies in detail.
        
        Args:
            policy_1: First policy dict
            policy_2: Second policy dict
            
        Returns:
            PolicyComparisonResponse with differences and similarity
        """
        differences_list, similarity_score = self.diff_engine.compare_policies(policy_1, policy_2)

        # Convert to response format
        differences = [
            DifferenceDetail(
                field=d.field,
                old_value=d.old_value,
                new_value=d.new_value,
                change_type=d.change_type,
                severity=d.severity,
            )
            for d in differences_list
        ]

        high_priority = len([d for d in differences if d.severity == "high"])

        response = PolicyComparisonResponse(
            policy_1_id=policy_1.get("id", "unknown"),
            policy_2_id=policy_2.get("id", "unknown"),
            differences=differences,
            similarity_score=similarity_score,
            total_differences=len(differences),
            high_priority_differences=high_priority,
        )

        logger.info(
            f"Policy comparison: {policy_1.get('id')} vs {policy_2.get('id')} - "
            f"Similarity: {similarity_score:.2%}, Differences: {len(differences)}"
        )

        return response

    def compare_coverage_details(self, policy_id_1: str, policy_id_2: str, policies_data: dict) -> dict:
        """
        Deep comparison of coverage rules between two policies.
        
        Args:
            policy_id_1: First policy ID
            policy_id_2: Second policy ID
            policies_data: Dict of all policies
            
        Returns:
            Detailed comparison with drug-by-drug analysis
        """
        policy_1 = policies_data.get(policy_id_1, {})
        policy_2 = policies_data.get(policy_id_2, {})

        coverage_1 = policy_1.get("coverage_rules", {})
        coverage_2 = policy_2.get("coverage_rules", {})

        # Get all drugs
        all_drugs = set(coverage_1.keys()) | set(coverage_2.keys())

        comparison = {
            "total_drugs_compared": len(all_drugs),
            "coverage_differences": [],
            "only_in_policy_1": [],
            "only_in_policy_2": [],
        }

        for drug in sorted(all_drugs):
            cov_1 = coverage_1.get(drug)
            cov_2 = coverage_2.get(drug)

            if drug not in coverage_1:
                comparison["only_in_policy_2"].append({"drug": drug, "coverage": cov_2})
            elif drug not in coverage_2:
                comparison["only_in_policy_1"].append({"drug": drug, "coverage": cov_1})
            elif cov_1 != cov_2:
                comparison["coverage_differences"].append({
                    "drug": drug,
                    "policy_1_coverage": cov_1,
                    "policy_2_coverage": cov_2,
                })

        logger.info(f"Coverage comparison complete for policies {policy_id_1} and {policy_id_2}")

        return comparison

    def compare_drug_across_policies(self, drug_name: str, policies_list: List[dict]) -> dict:
        """
        Compare how a specific drug is covered across multiple policies.
        
        Args:
            drug_name: Name of the drug
            policies_list: List of policy dicts
            
        Returns:
            Comparison of drug coverage across policies
        """
        results = []

        for policy in policies_list:
            coverage = policy.get("coverage_rules", {}).get(drug_name)

            results.append({
                "policy_id": policy.get("id"),
                "policy_name": policy.get("name"),
                "payer_id": policy.get("payer_id"),
                "drug_covered": coverage is not None,
                "coverage_details": coverage,
            })

        # Calculate coverage percentage
        covered_count = len([r for r in results if r["drug_covered"]])
        coverage_percent = (covered_count / len(policies_list)) * 100 if policies_list else 0

        logger.info(f"Drug '{drug_name}' coverage comparison: {coverage_percent:.1f}% of policies cover it")

        return {
            "drug_name": drug_name,
            "policies_analyzed": len(results),
            "coverage_percent": coverage_percent,
            "policy_comparisons": results,
        }


# Singleton instance
comparison_service = ComparisonService()
