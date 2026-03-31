"""
phase2_expansion.py - Phase 2: LLM Query Expansion via Groq (llama-3.3-70b).

Input:  user_profile_string (str)
Output: list[str] - 10-12 standalone search queries

Fallback: if Groq call fails for any reason, returns [user_profile_string]
"""
from __future__ import annotations
import json
import re
import logging
from groq import Groq
from config import GROQ_API_KEY

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert academic search assistant. Given a researcher's profile, 
generate 10 to 12 distinct, standalone web search queries to discover relevant research labs and academic groups.

Each query must cover a DIFFERENT angle:
1. Direct synonyms of the stated research interests
2. Sub-fields and specializations
3. Specific methods or techniques commonly used in this area
4. Names of prominent labs or universities known for this research
5. Author-style queries (e.g. "Yoshua Bengio lab Montreal deep learning")
6. Tool/framework-specific queries (e.g. "differential privacy PyTorch research group")

Rules:
- Output ONLY a JSON array of strings. No markdown, no explanation.
- Each string is a standalone search query (not a URL).
- 10 to 12 items, no more, no less.
- Queries should be diverse — do not repeat the same idea.
- Each query should be suitable for searching on Google to find lab pages or faculty profiles.

Example output:
["federated learning research lab", "privacy preserving machine learning group", ...]
"""


def expand_queries(user_profile_string: str) -> list[str]:
    """
    Call Groq llama-3.3-70b to expand user profile into 10-12 search queries.
    Falls back to [user_profile_string] on any failure.
    """
    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set - using profile string as sole query.")
        return [user_profile_string]

    try:
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Researcher profile:\n{user_profile_string}"},
            ],
            temperature=0.7,
            max_tokens=1024,
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown code fences if present
        raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()

        queries = json.loads(raw)

        if not isinstance(queries, list):
            raise ValueError("Response is not a list")

        # Clamp to 10-12
        queries = [str(q).strip() for q in queries if isinstance(q, str) and q.strip()]
        queries = queries[:12]

        if len(queries) < 3:
            raise ValueError(f"Too few queries returned: {len(queries)}")

        logger.info(f"Groq returned {len(queries)} expanded queries.")
        return queries

    except Exception as e:
        logger.warning(f"Groq query expansion failed: {e} — falling back to raw profile string.")
        return [user_profile_string]
