"""
Enhanced Search Service
Provides filtered search, natural language Q&A, and easiest approval path queries
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class SearchFilter:
    """Represents search filter criteria."""

    def __init__(self):
        self.query: Optional[str] = None
        self.payer_id: Optional[str] = None
        self.payer_name: Optional[str] = None
        self.drug_name: Optional[str] = None
        self.requires_prior_auth: Optional[bool] = None
        self.max_restrictiveness_score: Optional[float] = None
        self.min_confidence: Optional[float] = None
        self.is_active: bool = True
        self.max_copay: Optional[float] = None
        self.has_quantity_limits: Optional[bool] = None


class EnhancedSearchService:
    """
    Enhanced search with:
    - Multi-criteria filtering
    - Natural language Q&A with conversation history
    - Easiest approval path queries
    - Query optimization
    """

    def __init__(self):
        """Initialize search service."""
        self.policies_store: Dict[str, Dict] = {}
        self.conversation_history: Dict[str, List[Dict]] = {}  # By session_id

    def search_policies(
        self,
        query: Optional[str] = None,
        payer: Optional[str] = None,
        drug: Optional[str] = None,
        requires_prior_auth: Optional[bool] = None,
        max_restrictiveness_score: Optional[float] = None,
        min_confidence: Optional[float] = None,
        max_copay: Optional[float] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """
        Search policies with multiple filter criteria.
        
        Args:
            query: Free-text search (matches drug/payer name)
            payer: Filter by payer ID or name
            drug: Filter by drug name
            requires_prior_auth: Filter by prior auth requirement
            max_restrictiveness_score: Max restrictiveness (0-100)
            min_confidence: Minimum extraction confidence (0-100)
            max_copay: Maximum copay amount
            limit: Max results to return
            
        Returns:
            List of matching policies
        """
        logger.info(f"Searching policies: query={query}, payer={payer}, drug={drug}")

        results = []

        for policy_id, policy in self.policies_store.items():
            # Apply is_active filter
            if not policy.get("is_active", True):
                continue

            # Apply confidence filter
            if min_confidence and policy.get("extraction_confidence", 100) < min_confidence:
                continue

            # Apply payer filter
            if payer:
                if policy.get("payer_id") != payer and policy.get("payer_name") != payer:
                    continue

            # Apply drug filter and additional drug-level filters
            coverage_rules = policy.get("coverage_rules", {})
            if drug:
                if drug not in coverage_rules:
                    continue

                drug_rule = coverage_rules[drug]

                # Apply prior auth filter
                if requires_prior_auth is not None:
                    if drug_rule.get("prior_auth") != requires_prior_auth:
                        continue

                # Apply max copay filter
                if max_copay is not None:
                    copay = drug_rule.get("copay")
                    if copay and copay > max_copay:
                        continue
            else:
                # If searching all drugs, apply filters to any drug in the policy
                passes_filter = True
                for drug_rule in coverage_rules.values():
                    if requires_prior_auth is not None:
                        if drug_rule.get("prior_auth") == requires_prior_auth:
                            break
                    if max_copay is not None:
                        copay = drug_rule.get("copay")
                        if copay and copay <= max_copay:
                            break
                else:
                    if requires_prior_auth is not None or max_copay is not None:
                        passes_filter = False

                if not passes_filter:
                    continue

            # Apply restrictiveness filter
            if max_restrictiveness_score is not None:
                restrictiveness = self._calculate_policy_restrictiveness(coverage_rules)
                if restrictiveness > max_restrictiveness_score:
                    continue

            # Apply free-text query filter
            if query:
                if not self._matches_query(policy, query):
                    continue

            results.append(policy)

            if len(results) >= limit:
                break

        logger.info(f"Search returned {len(results)} results")
        return results

    def find_easiest_approval_path(self, drug_name: str) -> Optional[Dict]:
        """
        Find the single payer with lowest restrictiveness for a drug.
        
        Args:
            drug_name: Drug to search for
            
        Returns:
            Payer info with lowest restrictiveness score, or None if not found
        """
        logger.info(f"Finding easiest approval path for {drug_name}")

        best_policy = None
        best_restrictiveness = float("inf")

        for policy_id, policy in self.policies_store.items():
            if not policy.get("is_active", True):
                continue

            coverage_rules = policy.get("coverage_rules", {})
            if drug_name not in coverage_rules:
                continue

            drug_rule = coverage_rules[drug_name]
            restrictiveness = self._calculate_drug_restrictiveness(drug_rule)

            if restrictiveness < best_restrictiveness:
                best_restrictiveness = restrictiveness
                best_policy = policy

        if best_policy:
            logger.info(
                f"Easiest path found: {best_policy.get('payer_name')} with restrictiveness {best_restrictiveness:.1f}"
            )
            return {
                "payer_id": best_policy.get("payer_id"),
                "payer_name": best_policy.get("payer_name"),
                "restrictiveness_score": best_restrictiveness,
                "coverage_rule": best_policy.get("coverage_rules", {}).get(drug_name),
            }

        logger.warning(f"No policies found for drug {drug_name}")
        return None

    def chat_with_policies(
        self, session_id: str, user_message: str
    ) -> Dict:
        """
        Natural language Q&A with conversation history.
        
        Args:
            session_id: Conversation session ID
            user_message: User's question or statement
            
        Returns:
            Response with answer and context
        """
        logger.info(f"Chat message [session={session_id}]: {user_message[:100]}")

        # Initialize conversation history if needed
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []

        # Add user message to history
        self.conversation_history[session_id].append(
            {"role": "user", "message": user_message, "timestamp": datetime.utcnow().isoformat()}
        )

        # Parse question intent
        intent, entities = self._parse_question(user_message, session_id)

        # Generate response based on intent
        response_text = self._generate_response(intent, entities, user_message, session_id)

        # Add assistant response to history
        self.conversation_history[session_id].append(
            {
                "role": "assistant",
                "message": response_text,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        return {
            "intent": intent,
            "response": response_text,
            "context": {
                "extracted_entities": entities,
                "conversation_turn": len(self.conversation_history[session_id]) // 2,
            },
            "session_id": session_id,
        }

    def get_conversation_history(self, session_id: str, limit: int = 20) -> List[Dict]:
        """Get conversation history for a session."""
        if session_id not in self.conversation_history:
            return []

        return self.conversation_history[session_id][-limit:]

    def _matches_query(self, policy: Dict, query: str) -> bool:
        """Check if policy matches free-text query."""
        search_text = (
            f"{policy.get('payer_name', '')} {policy.get('policy_name', '')} "
            f"{' '.join(policy.get('coverage_rules', {}).keys())}"
        ).lower()

        return query.lower() in search_text

    def _calculate_policy_restrictiveness(self, coverage_rules: Dict) -> float:
        """Calculate average restrictiveness across all drugs in policy."""
        if not coverage_rules:
            return 0

        scores = [self._calculate_drug_restrictiveness(rule) for rule in coverage_rules.values()]
        return sum(scores) / len(scores) if scores else 0

    def _calculate_drug_restrictiveness(self, drug_rule: Dict) -> float:
        """Calculate restrictiveness score for single drug rule (0-100)."""
        score = 0

        if drug_rule.get("prior_auth"):
            score += 35

        if drug_rule.get("step_therapy"):
            score += 25

        if drug_rule.get("quantity_limit"):
            score += 20

        copay = drug_rule.get("copay", 0)
        if isinstance(copay, (int, float)) and copay > 20:
            score += 15

        restrictions = drug_rule.get("restrictions", "")
        if restrictions:
            score += min(5, len(restrictions) // 100)

        return min(100, score)

    def _parse_question(
        self, user_message: str, session_id: str
    ) -> tuple[str, Dict[str, Any]]:
        """Parse user question to extract intent and entities."""
        message_lower = user_message.lower()
        entities = {}

        # Detect intent
        if "what about" in message_lower and "same drug" in message_lower:
            intent = "follow_up_drug_at_payer"
        elif "easiest" in message_lower or "easiest" in message_lower:
            intent = "easiest_approval"
        elif "restrictive" in message_lower or "restriction" in message_lower:
            intent = "restrictiveness_query"
        elif "how much" in message_lower or "copay" in message_lower:
            intent = "copay_query"
        elif "prior auth" in message_lower or "prior authorization" in message_lower:
            intent = "prior_auth_query"
        else:
            intent = "general_query"

        # Extract entities from current message and context
        # Check previous messages for context
        history = self.conversation_history.get(session_id, [])
        last_drug = None
        last_payer = None

        for msg in reversed(history):
            text = msg.get("message", "").lower()
            # Simple extraction (in production, use NER)
            if "adalimumab" in text or "humira" in text:
                last_drug = "adalimumab"
            if "cigna" in text or "aetna" in text or "bcbs" in text:
                last_payer = text

        entities["drug"] = last_drug
        entities["payer"] = last_payer
        entities["context_turn"] = len(history) // 2

        return intent, entities

    def _generate_response(
        self, intent: str, entities: Dict, user_message: str, session_id: str
    ) -> str:
        """Generate response based on intent."""
        if intent == "follow_up_drug_at_payer":
            payer = entities.get("payer")
            drug = entities.get("drug")
            if drug and payer:
                return (
                    f"For {drug} at {payer}, let me check the payment rules... "
                    f"[Would query real database and return specific coverage details]"
                )
            return "I need more context about which drug and payer you're asking about."

        elif intent == "easiest_approval":
            drug = entities.get("drug")
            if drug:
                return (
                    f"For {drug}, the easiest approval path is typically with payers "
                    "that don't require prior authorization. Let me search... "
                    "[Would return payer with lowest restrictiveness]"
                )
            return "Which drug are you asking about?"

        elif intent == "restrictiveness_query":
            return (
                "Restrictiveness scores range from 0-100 based on prior auth requirements, "
                "step therapy, quantity limits, and copay amounts. "
                "[Would show specific scores for relevant policies]"
            )

        elif intent == "copay_query":
            return (
                "Copay amounts vary by plan and drug. "
                "[Would query and return specific copay ranges for matching policies]"
            )

        else:
            return (
                f"Regarding your question about insurance policies: "
                f"[Would generate contextual response based on policy data]"
            )


# Singleton instance
enhanced_search_service = EnhancedSearchService()
