# extractors/claude_extractor.py
# ============================================================
# Send parsed document text to the Claude API.
# Claude reads the text and returns structured JSON matching
# our policy schema.
#
# This is the core AI brain of the entire system.
# ============================================================

import json
import re
from typing import Optional

import anthropic

from ..config import get_settings
from .prompts import (
    POLICY_EXTRACTION_SYSTEM_PROMPT,
    COMPARE_SUMMARY_PROMPT,
    build_extraction_prompt,
)
from ..utils.error_handler import ExtractionError
from ..utils.schema_validator import validate_extraction_output

settings = get_settings()

# Create the Anthropic client once (reused across requests)
_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


def extract_policy_from_text(document_text: str, payer_name: str) -> dict:
    """
    Send policy document text to Claude and get structured JSON.

    Steps:
    1. Build the prompt using the centralized prompt builder.
    2. Call the Claude API with our extraction system prompt.
    3. Parse the JSON response.
    4. Validate the response against our schema.
    5. Return the validated dict.

    Args:
        document_text: Raw text extracted from PDF/HTML/image.
        payer_name: Name of the health plan (e.g., "UnitedHealthcare").

    Returns:
        A dict matching our policy extraction schema.

    Raises:
        ExtractionError if Claude returns invalid JSON or schema fails.
    """
    if not document_text or len(document_text.strip()) < 100:
        raise ExtractionError("Document text is too short to extract policy data")

    # Build the user message
    user_message = build_extraction_prompt(document_text, payer_name)

    try:
        # ── Call Claude API ──────────────────────────────────
        response = _client.messages.create(
            model=settings.claude_model,
            max_tokens=4096,
            system=POLICY_EXTRACTION_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_message}
            ],
        )
    except anthropic.APIError as e:
        raise ExtractionError(f"Claude API error: {str(e)}")

    # ── Get raw text from response ────────────────────────────
    raw_text = response.content[0].text.strip()

    # ── Parse JSON ────────────────────────────────────────────
    extracted_data = _parse_json_safely(raw_text)

    # ── Validate against schema ───────────────────────────────
    validate_extraction_output(extracted_data)

    return extracted_data


def generate_comparison_summary(policies_data: list[dict]) -> str:
    """
    Generate a natural language comparison summary for multiple policies.

    Steps:
    1. Format the policies as clean JSON text.
    2. Ask Claude to write a comparison paragraph.
    3. Return the summary text.

    Args:
        policies_data: List of policy dicts (already extracted).

    Returns:
        A plain-text paragraph comparing the policies.
    """
    if not policies_data:
        return "No policies provided for comparison."

    policies_json = json.dumps(policies_data, indent=2, default=str)

    try:
        response = _client.messages.create(
            model=settings.claude_model,
            max_tokens=1024,
            system=COMPARE_SUMMARY_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Compare these policies:\n\n{policies_json}"
                }
            ],
        )
        return response.content[0].text.strip()

    except anthropic.APIError as e:
        return f"Could not generate summary: {str(e)}"


def answer_policy_question(question: str, relevant_policies: list[dict]) -> str:
    """
    Answer a natural language question about policies.
    This powers the 'chat' interface.

    Examples:
        "Which plans cover Drug X?"
        "What is the step therapy requirement for Rituximab at Cigna?"

    Args:
        question: User's plain English question.
        relevant_policies: Pre-filtered list of policy dicts from search.

    Returns:
        A plain text answer from Claude.
    """
    context = json.dumps(relevant_policies, indent=2, default=str)

    system = (
        "You are a helpful medical benefits analyst. "
        "Answer the user's question based ONLY on the policy data provided. "
        "If the data doesn't contain enough information, say so. "
        "Be concise and cite specific payers when relevant."
    )

    try:
        response = _client.messages.create(
            model=settings.claude_model,
            max_tokens=1024,
            system=system,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Policy data:\n{context}\n\n"
                        f"Question: {question}"
                    )
                }
            ],
        )
        return response.content[0].text.strip()

    except anthropic.APIError as e:
        raise ExtractionError(f"Claude API error: {str(e)}")


# ── Internal helper ───────────────────────────────────────────

def _parse_json_safely(text: str) -> dict:
    """
    Robustly parse JSON from Claude's response.

    Sometimes Claude wraps output in markdown code blocks.
    We strip those before parsing.

    Tries:
    1. Direct json.loads()
    2. Strip ```json ... ``` markdown fences then try again
    3. Regex to find first { ... } block
    """
    # 1. Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown fences
    cleaned = re.sub(r"```json\s*", "", text)
    cleaned = re.sub(r"```\s*", "", cleaned)
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 3. Try to find the first complete JSON object
    brace_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group())
        except json.JSONDecodeError:
            pass

    raise ExtractionError(
        f"Claude returned invalid JSON. Raw response (first 500 chars): {text[:500]}"
    )


# ── Connection test ───────────────────────────────────────────

def test_claude_connection() -> bool:
    """
    Test Claude API connection.
    
    Returns:
        True if connection successful
    """
    try:
        response = _client.messages.create(
            model=settings.claude_model,
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Say 'OK' only"}
            ],
        )
        return bool(response.content)
    except Exception as e:
        return False