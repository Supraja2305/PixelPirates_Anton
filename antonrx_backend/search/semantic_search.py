# search/semantic_search.py
# ============================================================
# Semantic search using Claude embeddings and vector similarity
# Includes caching, filtering, and ranking
# ============================================================

import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from ..config import get_settings
from ..utils.error_handler import log_error, ExternalAPIError
from ..extractors.claude_extractor import extract_policy_from_text


logger = logging.getLogger(__name__)


class SemanticSearchEngine:
    """
    Perform semantic search on drug policies using embeddings.
    Features:
    - Claude embeddings for semantic understanding
    - Vector similarity search
    - Result filtering and ranking
    - Cache management for performance
    """
    
    def __init__(self):
        """Initialize search engine."""
        self.config = get_settings()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.embed_cache = {}  # In-memory cache: text -> embedding
        
    def create_embedding(self, text: str, cache_key: Optional[str] = None) -> List[float]:
        """
        Create embedding for text using Claude semantic understanding.
        With optional caching.
        
        Args:
            text: Text to embed
            cache_key: Optional cache key (defaults to text hash)
        
        Returns:
            List of float embeddings (768 dimensions for Claude embeddings)
        """
        try:
            # Use cache if available
            if not cache_key:
                import hashlib
                cache_key = hashlib.md5(text.encode()).hexdigest()
            
            if cache_key in self.embed_cache:
                return self.embed_cache[cache_key]
            
            # Create embedding via OpenAI
            client = self.extractor.client
            response = client.embeddings.create(
                model="text-embedding-3-small",  # Fast, cheap: 1536 dims
                input=text,
                encoding_format="float"
            )
            
            embedding = response.data[0].embedding
            
            # Cache result (keep max 10k embeddings)
            if len(self.embed_cache) < 10000:
                self.embed_cache[cache_key] = embedding
            
            return embedding
            
        except Exception as e:
            error_msg = f"Embedding generation failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            log_error(error_msg)
            raise ExternalAPIError(error_msg)

    def semantic_search(
        self,
        query: str,
        policies: List[Dict[str, Any]],
        top_k: int = 5,
        similarity_threshold: float = 0.3,
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search policies semantically by similarity to query.
        
        Args:
            query: Search query text
            policies: List of policy dicts with 'text' or 'extracted_text' field
            top_k: Return top K results
            similarity_threshold: Min similarity score (0.0-1.0)
        
        Returns:
            List of (policy, similarity_score) tuples, sorted by score descending
        """
        try:
            if not policies:
                return []
            
            # Get query embedding
            query_embedding = self.create_embedding(query)
            
            # Score each policy
            scored_policies = []
            for policy in policies:
                # Get policy text
                text = policy.get("text") or policy.get("extracted_text") or ""
                if not text:
                    continue
                
                # Get policy embedding
                policy_embedding = self.create_embedding(
                    text[:500],  # Use first 500 chars for efficiency
                    cache_key=policy.get("id")
                )
                
                # Calculate similarity (cosine)
                similarity = self._cosine_similarity(query_embedding, policy_embedding)
                
                if similarity >= similarity_threshold:
                    scored_policies.append((policy, similarity))
            
            # Sort by similarity descending
            scored_policies.sort(key=lambda x: x[1], reverse=True)
            
            return scored_policies[:top_k]
            
        except Exception as e:
            error_msg = f"Semantic search failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)

    def hybrid_search(
        self,
        query: str,
        policies: List[Dict[str, Any]],
        keywords: Optional[List[str]] = None,
        drug_name: Optional[str] = None,
        payer_name: Optional[str] = None,
        top_k: int = 5,
        semantic_weight: float = 0.6,
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Hybrid search combining semantic and keyword/filter matching.
        
        Args:
            query: Semantic search query
            policies: All policies to search
            keywords: Optional keywords that must appear
            drug_name: Optional drug filter
            payer_name: Optional payer filter
            top_k: Return top K results
            semantic_weight: Weight for semantic score (0-1, keywords get 1-weight)
        
        Returns:
            Ranked list of (policy, combined_score) tuples
        """
        # First apply filters
        filtered_policies = policies
        
        if drug_name:
            filtered_policies = [
                p for p in filtered_policies
                if drug_name.lower() in (p.get("drug_name") or "").lower()
            ]
        
        if payer_name:
            filtered_policies = [
                p for p in filtered_policies
                if payer_name.lower() in (p.get("payer_name") or "").lower()
            ]
        
        # Semantic search
        semantic_results = {}
        if query:
            results = self.semantic_search(query, filtered_policies, top_k=len(filtered_policies))
            semantic_results = {p["id"]: score for p, score in results}
        
        # Keyword matching
        keyword_scores = {}
        if keywords:
            for policy in filtered_policies:
                text = (policy.get("text") or "").lower()
                matches = sum(1 for kw in keywords if kw.lower() in text)
                keyword_scores[policy["id"]] = matches / len(keywords) if keywords else 0
        
        # Combine scores
        combined_scores = []
        for policy in filtered_policies:
            policy_id = policy["id"]
            semantic_score = semantic_results.get(policy_id, 0.5)
            keyword_score = keyword_scores.get(policy_id, 0.5)
            
            combined_score = (
                semantic_score * semantic_weight +
                keyword_score * (1 - semantic_weight)
            )
            
            combined_scores.append((policy, combined_score))
        
        # Sort and return top_k
        combined_scores.sort(key=lambda x: x[1], reverse=True)
        return combined_scores[:top_k]

    def clear_cache(self) -> None:
        """Clear embedding cache to free memory."""
        self.embed_cache.clear()
        self.logger.info("Embedding cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache usage statistics."""
        return {
            "cached_embeddings": len(self.embed_cache),
            "cache_size_approx_mb": len(self.embed_cache) * 1536 * 4 / (1024 * 1024),
            "max_cache_size": 10000,
        }
