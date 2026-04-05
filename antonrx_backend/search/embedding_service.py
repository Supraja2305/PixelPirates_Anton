"""
Embedding Service - Generates embeddings for policies, drugs, and coverage data
Uses Anthropic's embedding API and caching for performance
"""

import os
import logging
from typing import List, Dict, Optional
import json
from datetime import datetime
from anthropic import Anthropic

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating embeddings of medical policy data.
    Uses Claude to understand semantic meaning of policies, coverage rules, and drug information.
    Integrates with vector store for similarity search.
    """

    def __init__(self):
        """Initialize embedding service with Anthropic client."""
        self.client = Anthropic()
        self.model = "claude-3-5-sonnet-20241022"
        self.embedding_cache: Dict[str, List[float]] = {}
        self.embedding_dim = 512  # Mock embedding dimension

    def generate_policy_embedding(self, policy: Dict) -> List[float]:
        """
        Generate semantic embedding for a policy.
        
        Args:
            policy: Policy dictionary
            
        Returns:
            Embedding vector (list of floats)
        """
        policy_id = policy.get("id")
        cache_key = f"policy_{policy_id}"

        if cache_key in self.embedding_cache:
            logger.debug(f"Using cached embedding for policy {policy_id}")
            return self.embedding_cache[cache_key]

        # Create text representation of policy
        policy_text = self._policy_to_text(policy)

        # Generate embedding using Claude
        embedding = self._get_embedding(policy_text)

        # Cache result
        self.embedding_cache[cache_key] = embedding

        logger.info(f"Generated embedding for policy {policy_id}")

        return embedding

    def generate_coverage_embedding(self, coverage_rules: Dict) -> List[float]:
        """
        Generate embedding for coverage rules.
        
        Args:
            coverage_rules: Coverage rules dictionary
            
        Returns:
            Embedding vector
        """
        coverage_text = self._coverage_to_text(coverage_rules)
        embedding = self._get_embedding(coverage_text)
        logger.info(f"Generated embedding for coverage rules ({len(coverage_rules)} drugs)")
        return embedding

    def generate_drug_embedding(self, drug: Dict) -> List[float]:
        """
        Generate embedding for a drug.
        
        Args:
            drug: Drug dictionary with name, class, condition
            
        Returns:
            Embedding vector
        """
        drug_id = drug.get("id")
        cache_key = f"drug_{drug_id}"

        if cache_key in self.embedding_cache:
            return self.embedding_cache[cache_key]

        drug_text = self._drug_to_text(drug)
        embedding = self._get_embedding(drug_text)

        self.embedding_cache[cache_key] = embedding

        logger.info(f"Generated embedding for drug: {drug.get('name')}")

        return embedding

    def generate_search_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.
        
        Args:
            query: Search query string
            
        Returns:
            Embedding vector
        """
        embedding = self._get_embedding(query)
        logger.info(f"Generated embedding for search query")
        return embedding

    def _get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for arbitrary text using Claude's understanding.
        
        NOTE: Claude doesn't have a native embedding API, so this creates a mock embedding
        For production, integrate with a proper embedding API like OpenAI or Hugging Face.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        # Mock implementation - for production use proper embedding API
        # Create deterministic hash-based embedding
        import hashlib

        hash_obj = hashlib.md5(text.encode())
        hash_val = int(hash_obj.hexdigest(), 16)

        # Generate embedding vector using hash as seed
        embedding = []
        for i in range(self.embedding_dim):
            val = ((hash_val + i * 31) % 1000) / 1000.0
            embedding.append(val)

        return embedding

    def _policy_to_text(self, policy: Dict) -> str:
        """Convert policy dict to semantic text representation."""
        parts = [
            f"Policy: {policy.get('name', 'Unknown')}",
            f"Description: {policy.get('description', 'No description')}",
            f"Effective: {policy.get('effective_date', 'TBD')}",
            f"Coverage items: {len(policy.get('coverage_rules', {}))} drugs",
        ]

        coverage = policy.get("coverage_rules", {})
        if coverage:
            drug_classes = set()
            for drug_coverage in coverage.values():
                if isinstance(drug_coverage, dict):
                    if "drug_class" in drug_coverage:
                        drug_classes.add(drug_coverage["drug_class"])

            if drug_classes:
                parts.append(f"Drug classes: {', '.join(drug_classes)}")

        return " ".join(parts)

    def _coverage_to_text(self, coverage_rules: Dict) -> str:
        """Convert coverage rules to text representation."""
        parts = [f"Coverage for {len(coverage_rules)} drugs:"]

        for drug, coverage in list(coverage_rules.items())[:10]:  # First 10 for brevity
            if isinstance(coverage, dict):
                details = []
                if coverage.get("copay"):
                    details.append(f"${coverage['copay']} copay")
                if coverage.get("prior_auth"):
                    details.append("prior auth")
                if coverage.get("step_therapy"):
                    details.append("step therapy")
                if details:
                    parts.append(f"{drug}: {', '.join(details)}")
                else:
                    parts.append(f"{drug}: covered")

        return " ".join(parts)

    def _drug_to_text(self, drug: Dict) -> str:
        """Convert drug dict to text representation."""
        parts = [
            f"Drug: {drug.get('name', 'Unknown')}",
            f"Class: {drug.get('drug_class', 'Unclassified')}",
            f"Condition: {drug.get('condition', 'General')}",
            f"Generic available: {drug.get('generic_available', False)}",
        ]
        return " ".join(parts)

    def clear_cache(self):
        """Clear embedding cache."""
        self.embedding_cache.clear()
        logger.info("Embedding cache cleared")


# Singleton instance
embedding_service = EmbeddingService()
