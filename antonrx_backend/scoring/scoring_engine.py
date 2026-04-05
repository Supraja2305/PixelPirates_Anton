"""
Scoring Engine - Scores and ranks policies based on multiple criteria
Provides comprehensive policy evaluation and recommendation
"""

from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class ScoringEngine:
    """
    Comprehensive scoring engine for evaluating policies based on:
    - Coverage breadth (drug classes covered)
    - Pricing competitiveness
    - Requirements complexity
    - Updates recency (how recently updated)
    - Match relevance to search criteria
    """

    def __init__(self):
        """Initialize scoring engine with default weights."""
        self.weights = {
            "coverage": 0.35,
            "pricing": 0.25,
            "requirements": 0.20,
            "recency": 0.15,
            "relevance": 0.05,
        }

    def score_policy(self, policy: Dict, criteria: Dict = None) -> Tuple[float, Dict]:
        """
        Score a policy on 0-100 scale.
        
        Args:
            policy: Policy dictionary
            criteria: Optional scoring criteria/weights override
            
        Returns:
            Tuple of (score 0-100, breakdown dict)
        """
        breakdown = {}

        # Calculate individual scores
        coverage_score = self._score_coverage(policy.get("coverage_rules", {}))
        breakdown["coverage"] = coverage_score

        pricing_score = self._score_pricing(policy.get("coverage_rules", {}))
        breakdown["pricing"] = pricing_score

        requirements_score = self._score_requirements(policy.get("coverage_rules", {}))
        breakdown["requirements"] = requirements_score

        recency_score = self._score_recency(policy.get("effective_date", ""))
        breakdown["recency"] = recency_score

        # Weighted total
        total_score = (
            (coverage_score * self.weights["coverage"])
            + (pricing_score * self.weights["pricing"])
            + (requirements_score * self.weights["requirements"])
            + (recency_score * self.weights["recency"])
        )

        # Apply criteria if provided
        if criteria and "relevance_score" in criteria:
            relevance = criteria["relevance_score"] * 100
            breakdown["relevance"] = relevance
            total_score = total_score * 0.95 + (relevance * self.weights["relevance"])

        logger.info(f"Policy {policy.get('id')}: score={total_score:.1f}")

        return total_score, breakdown

    def rank_policies(self, policies: List[Dict], criteria: Dict = None) -> List[Tuple[Dict, float, int]]:
        """
        Score and rank multiple policies.
        
        Args:
            policies: List of policy dicts
            criteria: Optional search criteria for relevance
            
        Returns:
            List of (policy, score, rank) tuples sorted by score descending
        """
        scored = []

        for policy in policies:
            score, _ = self.score_policy(policy, criteria)
            scored.append((policy, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        # Add ranks
        ranked = [(policy, score, rank + 1) for rank, (policy, score) in enumerate(scored)]

        logger.info(f"Ranked {len(policies)} policies")

        return ranked

    def _score_coverage(self, coverage_rules: Dict) -> float:
        """
        Score coverage breadth 0-100.
        More drug classes covered = higher score.
        """
        if not coverage_rules:
            return 20.0

        covered_drugs = len(coverage_rules)
        # Assume 200 common drugs as reference
        coverage_percent = min(100, (covered_drugs / 200) * 100)

        return coverage_percent * 0.8 + 20.0  # Base 20 + up to 80

    def _score_pricing(self, coverage_rules: Dict) -> float:
        """
        Score cost-competitiveness 0-100.
        Fewer restrictions and lower copays = higher score.
        """
        if not coverage_rules:
            return 50.0

        score = 50.0

        # Analyze copay levels (if present)
        copay_levels = []
        for drug_coverage in coverage_rules.values():
            if isinstance(drug_coverage, dict):
                if "copay" in drug_coverage:
                    try:
                        copay_levels.append(float(drug_coverage["copay"]))
                    except (ValueError, TypeError):
                        pass

        if copay_levels:
            avg_copay = sum(copay_levels) / len(copay_levels)
            # Lower copay = higher score (0-50 copay maps to 0-100 score)
            copay_score = max(0, 100 - (avg_copay * 2))
            score = score * 0.5 + copay_score * 0.5

        return score

    def _score_requirements(self, coverage_rules: Dict) -> float:
        """
        Score requirement simplicity 0-100.
        Fewer restrictions and requirements = higher score.
        """
        if not coverage_rules:
            return 60.0

        restriction_count = 0

        for drug_coverage in coverage_rules.values():
            if isinstance(drug_coverage, dict):
                if "prior_auth" in drug_coverage and drug_coverage["prior_auth"]:
                    restriction_count += 1
                if "step_therapy" in drug_coverage and drug_coverage["step_therapy"]:
                    restriction_count += 1
                if "quantity_limit" in drug_coverage and drug_coverage["quantity_limit"]:
                    restriction_count += 1

        total_rules = len(coverage_rules) * 3
        restriction_percent = restriction_count / max(total_rules, 1) * 100
        score = max(20, 100 - restriction_percent)

        return score

    def _score_recency(self, effective_date: str) -> float:
        """
        Score freshness/recency 0-100.
        More recent policies score higher.
        """
        if not effective_date:
            return 50.0

        from datetime import datetime

        try:
            parsed_date = datetime.fromisoformat(effective_date)
            days_old = (datetime.now() - parsed_date).days

            # Policy updated in last 30 days = 100
            # Every 30 days older = -10 points
            score = max(20, 100 - (days_old // 30) * 10)
            return score
        except (ValueError, TypeError):
            return 50.0


# Singleton instance
scoring_engine = ScoringEngine()
