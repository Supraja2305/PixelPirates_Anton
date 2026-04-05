# api/search.py  ── GET /api/search
# ============================================================
from fastapi import APIRouter, Depends, Query
from ..auth.middleware import get_current_user
from ..models.user import TokenData
from ..search.vector_store import search_policies
from ..storage.firestore_client import get_policy_by_id
from ..extractors.claude_extractor import answer_policy_question

router = APIRouter(prefix="/api/search", tags=["Search"])


@router.get("", summary="Semantic search across all policies")
async def semantic_search(
    q: str = Query(..., description="Natural language search query", min_length=3),
    top_k: int = Query(default=5, ge=1, le=20),
    user: TokenData = Depends(get_current_user),
):
    """
    Semantic search: find policies that match your query in meaning,
    not just exact keywords.

    Examples:
      GET /api/search?q=step therapy for biologics
      GET /api/search?q=plans that require prior auth for cancer drugs
      GET /api/search?q=adalimumab site of care restrictions

    Steps:
    1. Convert query to a vector embedding.
    2. Compare against all stored policy embeddings.
    3. Return top-K most similar policies with full details.
    4. Ask Claude to answer the question using these policies.
    """
    # Step 1-3: Find similar policies
    search_results = search_policies(q, top_k=top_k)

    if not search_results:
        return {
            "query": q,
            "results_found": 0,
            "results": [],
            "answer": "No relevant policies found for your query.",
        }

    # Step 4: Fetch full policy details for top results
    full_policies = []
    for result in search_results:
        policy_id = result.get("policy_id")
        policy = get_policy_by_id(policy_id)
        if policy:
            policy["similarity_score"] = result.get("similarity_score")
            full_policies.append(policy)

    # Step 5: Generate AI answer using matching policies as context
    ai_answer = answer_policy_question(q, full_policies[:3])  # Use top 3 for answer

    return {
        "query": q,
        "results_found": len(full_policies),
        "answer": ai_answer,
        "results": full_policies,
    }