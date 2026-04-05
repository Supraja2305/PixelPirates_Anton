"""
Analytics and Reporting Service
Handles outlier detection, coverage gap analysis, and quarterly reports
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import statistics
from collections import defaultdict

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Analytics service for:
    - Outlier detection (2+ std dev flagging)
    - Coverage gap detection
    - Quarterly change reports
    - Policy statistics
    """

    def __init__(self):
        """Initialize analytics service."""
        self.policies_store: Dict[str, Dict] = {}
        self.policy_versions_store: Dict[str, List[Dict]] = {}
        self.analytics_snapshots: Dict[str, Dict] = {}

    def detect_outlier_policies(
        self, drug_name: str, metric_name: str = "restrictiveness_score"
    ) -> List[Tuple[str, float, float, float]]:
        """
        Find policies where a metric is 2+ standard deviations from the mean.
        
        Args:
            drug_name: Drug to analyze
            metric_name: Metric to check (e.g., "restrictiveness_score", "copay")
            
        Returns:
            List of (policy_id, metric_value, z_score, avg_value) tuples
        """
        logger.info(f"Detecting outliers for {drug_name} using metric {metric_name}")

        # Collect all policies with this drug
        relevant_policies = []
        for policy_id, policy in self.policies_store.items():
            if not policy.get("is_active", True):
                continue

            coverage = policy.get("coverage_rules", {}).get(drug_name)
            if coverage and metric_name in coverage:
                relevant_policies.append((policy_id, policy, coverage[metric_name]))

        if len(relevant_policies) < 3:
            logger.debug(f"Not enough policies ({len(relevant_policies)}) for outlier detection")
            return []

        # Calculate mean and std dev
        values = [p[2] for p in relevant_policies]
        mean = statistics.mean(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 0

        outliers = []
        for policy_id, policy, value in relevant_policies:
            if stdev > 0:
                z_score = abs((value - mean) / stdev)
                if z_score >= 2.0:  # 2+ standard deviations
                    outliers.append((policy_id, value, z_score, mean))
                    logger.warning(
                        f"Outlier detected: policy {policy_id}, {metric_name}={value:.2f}, z-score={z_score:.2f}"
                    )

        return outliers

    def find_coverage_gaps(
        self, drug_name: str, known_payers: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Find payers that don't have coverage for a drug.
        
        Args:
            drug_name: Drug to check
            known_payers: List of payers we expect to have policies for
            
        Returns:
            List of (payer_id, payer_name, gap_type) for payers missing this drug
        """
        logger.info(f"Scanning coverage gaps for drug: {drug_name}")

        gaps = []

        # Find all payers that DO have this drug
        payers_with_coverage = set()
        for policy_id, policy in self.policies_store.items():
            if not policy.get("is_active", True):
                continue

            coverage_rules = policy.get("coverage_rules", {})
            if drug_name in coverage_rules:
                payers_with_coverage.add(policy.get("payer_id"))

        # If known_payers provided, find missing ones
        if known_payers:
            for payer_id in known_payers:
                if payer_id not in payers_with_coverage:
                    # Check if policy exists but is archived
                    archived_exists = False
                    for policy in self.policies_store.values():
                        if (
                            policy.get("payer_id") == payer_id
                            and not policy.get("is_active", True)
                        ):
                            archived_exists = True
                            break

                    gap_type = "expired_policy" if archived_exists else "not_ingested"
                    gaps.append(
                        {
                            "payer_id": payer_id,
                            "payer_name": f"Payer_{payer_id}",
                            "drug_name": drug_name,
                            "gap_type": gap_type,
                            "last_checked": datetime.utcnow().isoformat(),
                        }
                    )
                    logger.info(f"Coverage gap: {payer_id} missing {drug_name} ({gap_type})")

        return gaps

    def generate_quarterly_report(
        self, year: int, quarter: int
    ) -> Dict:
        """
        Generate comprehensive quarterly change report.
        
        Args:
            year: Year (e.g., 2024)
            quarter: Quarter (1-4)
            
        Returns:
            Report with changes, statistics, and trends
        """
        period_key = f"{year}-Q{quarter}"
        logger.info(f"Generating quarterly report for {period_key}")

        # Calculate date range
        start_month = (quarter - 1) * 3 + 1
        start_date = datetime(year, start_month, 1)
        if quarter == 4:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, start_month + 3, 1) - timedelta(days=1)

        # Collect statistics
        total_policies_ingested = 0
        total_changes = 0
        archived_count = 0
        low_confidence_count = 0
        drug_changes = defaultdict(int)
        payer_changes = defaultdict(int)

        for policy_id, policy in self.policies_store.items():
            created_at = datetime.fromisoformat(policy.get("created_at", ""))
            if start_date <= created_at <= end_date:
                total_policies_ingested += 1
                if policy.get("extraction_confidence", 100) < 70:
                    low_confidence_count += 1

            # Check for deactivations in this period
            deactivated_at = policy.get("deactivated_at")
            if deactivated_at:
                deactivated_date = datetime.fromisoformat(deactivated_at)
                if start_date <= deactivated_date <= end_date:
                    archived_count += 1

        # Most changed drugs (by number of policy modifications)
        for drug_name in set(
            drug
            for policy in self.policies_store.values()
            for drug in policy.get("coverage_rules", {})
        ):
            drug_changes[drug_name] = len(
                [
                    p
                    for p in self.policies_store.values()
                    if drug_name in p.get("coverage_rules", {})
                ]
            )

        report = {
            "period": period_key,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "summary": {
                "total_policies_ingested": total_policies_ingested,
                "total_policy_changes": total_changes,
                "policies_archived": archived_count,
                "low_confidence_extractions": low_confidence_count,
            },
            "changes_by_drug": sorted(
                drug_changes.items(), key=lambda x: x[1], reverse=True
            )[:10],
            "changes_by_payer": sorted(
                payer_changes.items(), key=lambda x: x[1], reverse=True
            )[:10],
            "insights": self._generate_insights(
                total_policies_ingested, archived_count, low_confidence_count
            ),
            "generated_at": datetime.utcnow().isoformat(),
        }

        return report

    def detect_duplicate_extractions(self, document_checksum: str) -> Optional[Dict]:
        """
        Check if a document has been extracted before (by checksum).
        
        Args:
            document_checksum: SHA256 checksum of document text
            
        Returns:
            Previous extraction info if found, None otherwise
        """
        logger.info(f"Checking for duplicate: checksum {document_checksum}")

        # Search for existing policy with same checksum
        for policy_id, policy in self.policies_store.items():
            if policy.get("document_checksum") == document_checksum:
                logger.info(f"Duplicate found: policy {policy_id}")
                return {
                    "is_duplicate": True,
                    "policy_id": policy_id,
                    "original_extraction_date": policy.get("created_at"),
                    "confidence": policy.get("extraction_confidence"),
                }

        return {"is_duplicate": False}

    def get_policy_statistics(self) -> Dict:
        """Get overall statistics about policies in database."""
        total_policies = len(self.policies_store)
        active_policies = sum(1 for p in self.policies_store.values() if p.get("is_active", True))
        archived_policies = total_policies - active_policies

        confidence_scores = [
            p.get("extraction_confidence", 100) for p in self.policies_store.values()
        ]

        payers = set(p.get("payer_id") for p in self.policies_store.values())
        drugs_tracked = set()
        for policy in self.policies_store.values():
            drugs_tracked.update(policy.get("coverage_rules", {}).keys())

        return {
            "total_policies": total_policies,
            "active_policies": active_policies,
            "archived_policies": archived_policies,
            "unique_payers": len(payers),
            "unique_drugs": len(drugs_tracked),
            "average_confidence": (
                statistics.mean(confidence_scores) if confidence_scores else 0
            ),
            "min_confidence": min(confidence_scores) if confidence_scores else 0,
            "max_confidence": max(confidence_scores) if confidence_scores else 0,
            "low_confidence_count": sum(1 for c in confidence_scores if c < 70),
        }

    def get_payer_restrictiveness_ranking(self, limit: int = 10) -> List[Dict]:
        """
        Rank payers by policy restrictiveness (most to least restrictive).
        
        Args:
            limit: Top N payers to return
            
        Returns:
            Ranked list of payers with average restrictiveness score
        """
        logger.info(f"Computing payer restrictiveness ranking (top {limit})")

        payer_scores = defaultdict(list)
        payer_names = {}

        # Collect restrictiveness scores
        for policy_id, policy in self.policies_store.items():
            if not policy.get("is_active", True):
                continue

            payer_id = policy.get("payer_id")
            payer_name = policy.get("payer_name")
            payer_names[payer_id] = payer_name

            # Calculate restrictiveness for this policy
            coverage_rules = policy.get("coverage_rules", {})
            for drug, rules in coverage_rules.items():
                restrictiveness = self._calculate_restrictiveness(rules)
                payer_scores[payer_id].append(restrictiveness)

        # Compute averages
        ranking = []
        for payer_id, scores in payer_scores.items():
            avg_restrictiveness = statistics.mean(scores) if scores else 0
            ranking.append(
                {
                    "payer_id": payer_id,
                    "payer_name": payer_names.get(payer_id, f"Payer_{payer_id}"),
                    "average_restrictiveness": avg_restrictiveness,
                    "policies_tracked": len(scores),
                }
            )

        # Sort by restrictiveness (descending)
        ranking.sort(key=lambda x: x["average_restrictiveness"], reverse=True)
        return ranking[:limit]

    def _calculate_restrictiveness(self, rules: Dict) -> float:
        """Calculate restrictiveness score for coverage rules (0-100)."""
        restrictiveness = 0

        # Prior auth adds 30 points
        if rules.get("prior_auth"):
            restrictiveness += 30

        # Step therapy adds 25 points
        if rules.get("step_therapy"):
            restrictiveness += 25

        # Quantity limits add 20 points
        if rules.get("quantity_limit"):
            restrictiveness += 20

        # High copay (>20) adds 15 points
        copay = rules.get("copay", 0)
        if isinstance(copay, (int, float)) and copay > 20:
            restrictiveness += 15

        # Restrictions text length adds up to 10 points
        restrictions = rules.get("restrictions", "")
        if restrictions:
            restrictiveness += min(10, len(restrictions) // 50)

        return min(100, restrictiveness)

    def _generate_insights(
        self, ingested: int, archived: int, low_confidence: int
    ) -> List[str]:
        """Generate human-readable insights from quarterly data."""
        insights = []

        if ingested > 100:
            insights.append(f"High ingestion activity: {ingested} policies processed")
        if archived > ingested * 0.1:
            insights.append(f"Significant archival: {archived} policies deactivated")
        if low_confidence > ingested * 0.2:
            insights.append(
                f"Quality concern: {low_confidence} extractions below confidence threshold"
            )

        return insights


# Singleton instance
analytics_service = AnalyticsService()
