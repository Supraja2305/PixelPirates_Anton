"""
Vector Store - Stores and retrieves embeddings for semantic search
Currently uses in-memory storage; can be extended for vector DB (Pinecone, Weaviate, etc.)
"""

import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class VectorRecord:
    """A single vector record in the store."""
    id: str
    item_type: str  # "policy", "drug", "coverage"
    item_id: str
    embedding: List[float]
    metadata: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def similarity_to(self, other_embedding: List[float]) -> float:
        """Compute cosine similarity to another embedding."""
        if not self.embedding or not other_embedding:
            return 0.0

        # Cosine similarity
        dot_product = sum(a * b for a, b in zip(self.embedding, other_embedding))
        magnitude_1 = sum(a * a for a in self.embedding) ** 0.5
        magnitude_2 = sum(b * b for b in other_embedding) ** 0.5

        if magnitude_1 == 0 or magnitude_2 == 0:
            return 0.0

        return dot_product / (magnitude_1 * magnitude_2)


class VectorStore:
    """
    In-memory vector store for embeddings.
    Provides semantic search via similarity computation.
    
    Can be extended to use external vector databases like Pinecone or Weaviate.
    """

    def __init__(self):
        """Initialize vector store."""
        self.records: Dict[str, VectorRecord] = {}
        self.index_by_type: Dict[str, List[str]] = {}
        self.index_by_item_id: Dict[str, List[str]] = {}

    def add(
        self,
        id: str,
        item_type: str,
        item_id: str,
        embedding: List[float],
        metadata: Dict = None,
    ) -> None:
        """
        Add a vector record to the store.
        
        Args:
            id: Unique record ID
            item_type: Type of item ("policy", "drug", "coverage")
            item_id: ID of the item
            embedding: Embedding vector
            metadata: Optional metadata dict
        """
        record = VectorRecord(
            id=id,
            item_type=item_type,
            item_id=item_id,
            embedding=embedding,
            metadata=metadata or {},
        )

        self.records[id] = record

        # Update indexes
        if item_type not in self.index_by_type:
            self.index_by_type[item_type] = []
        self.index_by_type[item_type].append(id)

        if item_id not in self.index_by_item_id:
            self.index_by_item_id[item_id] = []
        self.index_by_item_id[item_id].append(id)

        logger.debug(f"Added vector record: {id} (type: {item_type}, item: {item_id})")

    def search(
        self, query_embedding: List[float], top_k: int = 10, item_type: Optional[str] = None
    ) -> List[Tuple[VectorRecord, float]]:
        """
        Search for similar embeddings.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of top results to return
            item_type: Optional filter by item type
            
        Returns:
            List of (record, similarity_score) tuples sorted by similarity descending
        """
        results = []

        # Determine which records to search
        records_to_search = self.records.values()
        if item_type:
            record_ids = self.index_by_type.get(item_type, [])
            records_to_search = [self.records[rid] for rid in record_ids if rid in self.records]

        # Compute similarities
        for record in records_to_search:
            similarity = record.similarity_to(query_embedding)
            results.append((record, similarity))

        # Sort by similarity descending and take top_k
        results.sort(key=lambda x: x[1], reverse=True)
        results = results[:top_k]

        logger.info(f"Search completed: returned {len(results)} results (filtered by type: {item_type})")

        return results

    def get_by_id(self, record_id: str) -> Optional[VectorRecord]:
        """Get a single record by ID."""
        return self.records.get(record_id)

    def get_by_item_id(self, item_id: str) -> List[VectorRecord]:
        """Get all records for a specific item."""
        record_ids = self.index_by_item_id.get(item_id, [])
        return [self.records[rid] for rid in record_ids if rid in self.records]

    def delete(self, record_id: str) -> bool:
        """
        Delete a record from the store.
        
        Args:
            record_id: ID of record to delete
            
        Returns:
            True if deleted, False if not found
        """
        if record_id not in self.records:
            return False

        record = self.records.pop(record_id)

        # Update indexes
        if record.item_type in self.index_by_type:
            self.index_by_type[record.item_type].remove(record_id)

        if record.item_id in self.index_by_item_id:
            self.index_by_item_id[record.item_id].remove(record_id)

        logger.debug(f"Deleted vector record: {record_id}")

        return True

    def clear(self) -> None:
        """Clear all records from the store."""
        self.records.clear()
        self.index_by_type.clear()
        self.index_by_item_id.clear()
        logger.info("Vector store cleared")

    def get_statistics(self) -> Dict:
        """Get statistics about the store."""
        stats = {
            "total_records": len(self.records),
            "by_type": {item_type: len(ids) for item_type, ids in self.index_by_type.items()},
            "memory_usage_mb": len(self.records) * 2,  # Rough estimate
        }
        return stats


# Singleton instance
vector_store = VectorStore()
