"""
phase5_vectorstore.py - Phase 5: Vector Storage with ChromaDB + Gemini embeddings.

- Embeds structured fields (research_areas + methods_used + current_projects + lab_name + university)
  using Gemini text-embedding-preview-0814 (768-dim).
- Stores in local ChromaDB collection 'talaash_labs'.
- User query embeds only: research_interests + technical_skills + keywords.
- Embeddings are cached permanently (until source profile cache expires).
"""
from __future__ import annotations
import ast
import datetime
import logging
import os

import google.generativeai as genai

import cache
from config import GEMINI_API_KEY
from models import LabProfile, MatchResult, Publication, UserInput

logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)

CHROMA_DIR = os.path.join(os.path.dirname(__file__), ".chromadb")
COLLECTION_NAME = "talaash_labs"

_chroma_client = None
_collection = None


class DummyEmbeddingFunction:
    """Dummy embedding function to avoid ChromaDB's default onnxruntime dependency."""
    def __call__(self, input):
        # Return zero vectors - we handle embeddings ourselves
        # ChromaDB 0.4.16+ expects 'input' parameter, not 'texts'
        return [[0.0] * 768 for _ in input]

def _get_collection():
    global _chroma_client, _collection
    if _collection is None:
        import chromadb  # Lazy import
        _chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
            embedding_function=DummyEmbeddingFunction(),
        )
    return _collection


def _embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
    """Embed a single text string using available Gemini embedding model (768-dim fallback)."""
    cache_key = f"embed:{task_type}:{text[:200]}"
    cached = cache.get(cache_key, None)  # permanent TTL
    if cached:
        return cached

    try:
        # Try the latest model first
        result = genai.embed_content(
            model="models/text-embedding-preview-0814",
            content=text,
            task_type=task_type,
        )
    except Exception as e1:
        try:
            # Fallback to stable embedding model
            logger.warning(f"Preview model failed: {e1} - trying stable model")
            result = genai.embed_content(
                model="models/embedding-001",
                content=text,
            )
        except Exception as e2:
            # If both fail, return zero vector
            logger.warning(f"All embedding models failed: {e2} - returning zero vector")
            return [0.0] * 768
    
    vector = result["embedding"]
    cache.set(cache_key, vector)
    return vector


def _profile_to_embed_string(profile: LabProfile) -> str:
    """Build the structured embedding string per spec."""
    parts = []
    if profile.research_areas:
        parts.append(", ".join(profile.research_areas))
    if profile.methods_used:
        parts.append(", ".join(profile.methods_used))
    if profile.current_projects:
        parts.append(", ".join(profile.current_projects))
    if profile.lab_name:
        parts.append(profile.lab_name)
    if profile.university:
        parts.append(profile.university)
    return " | ".join(parts)


def embed_and_store(profiles: list[LabProfile]) -> None:
    """
    Embed each profile's structured fields and store in ChromaDB.
    Source URL is the document ID.
    """
    if not profiles:
        return

    collection = _get_collection()

    ids, embeddings, metadatas, documents = [], [], [], []

    for profile in profiles:
        url = profile.lab_url or ""
        if not url:
            continue

        embed_str = _profile_to_embed_string(profile)
        if not embed_str.strip():
            continue

        try:
            vector = _embed_text(embed_str, task_type="RETRIEVAL_DOCUMENT")
        except Exception as e:
            logger.warning(f"Embedding failed for {url}: {e} — using zero vector fallback")
            # Use a zero vector as fallback (768 dimensions for compatibility)
            vector = [0.0] * 768

        # Flatten profile to metadata (ChromaDB metadata must be flat str/int/float/bool)
        meta = {
            "pi_name":              profile.pi_name or "",
            "lab_name":             profile.lab_name or "",
            "university":           profile.university or "",
            "department":           profile.department or "",
            "research_areas":       ", ".join(profile.research_areas),
            "methods_used":         ", ".join(profile.methods_used),
            "current_projects":     ", ".join(profile.current_projects),
            "contact_email":        profile.contact_email or "",
            "github_url":           profile.github_url or "",
            "is_accepting_students": (
                True if profile.is_accepting_students is True
                else (False if profile.is_accepting_students is False else "null")
            ),
            "student_requirements": profile.student_requirements or "",
            "co_pis":               ", ".join(profile.co_pis),
            "recent_publications":  str([p.model_dump() for p in profile.recent_publications]),
            "lab_url":              profile.lab_url or "",
        }

        ids.append(url)
        embeddings.append(vector)
        metadatas.append(meta)
        documents.append(embed_str)

    if ids:
        collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
        logger.info(f"Stored {len(ids)} profiles in ChromaDB.")


def embed_user_query(user_input: UserInput) -> list[float]:
    """
    Embed only research_interests + technical_skills + keywords for ChromaDB querying.
    (Full user_profile_string is used for Groq + Gemini re-ranking, not here.)
    Returns zero vector if embedding fails.
    """
    parts = [user_input.research_interests, user_input.technical_skills]
    if user_input.keywords:
        parts.append(user_input.keywords)
    query_text = " | ".join(p for p in parts if p)
    try:
        return _embed_text(query_text, task_type="RETRIEVAL_QUERY")
    except Exception as e:
        logger.warning(f"User query embedding failed: {e} — returning zero vector")
        return [0.0] * 768


def clear_collection() -> None:
    """Drop and recreate the collection (for testing)."""
    global _collection
    import chromadb  # Lazy import
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    _collection = None


# Utility functions for profile reconstruction and scoring
def _current_year() -> int:
    return datetime.datetime.now(datetime.timezone.utc).year


def _has_recent_publication(publications: list[Publication]) -> bool:
    cutoff = _current_year() - 2
    return any(p.year >= cutoff for p in publications)


def _rebuild_profile_from_meta(meta: dict, url: str) -> LabProfile:
    """Reconstruct a LabProfile from ChromaDB flat metadata."""
    # Parse recent_publications from stored string repr
    recent_pubs = []
    raw_pubs = meta.get("recent_publications", "[]")
    try:
        parsed = ast.literal_eval(raw_pubs)
        for p in parsed:
            try:
                recent_pubs.append(Publication(**p))
            except Exception:
                pass
    except Exception:
        pass

    is_accepting = meta.get("is_accepting_students")
    if is_accepting == "null":
        is_accepting = None

    return LabProfile(
        pi_name=meta.get("pi_name") or None,
        co_pis=[x.strip() for x in meta.get("co_pis", "").split(",") if x.strip()],
        university=meta.get("university") or None,
        department=meta.get("department") or None,
        lab_name=meta.get("lab_name") or None,
        research_areas=[x.strip() for x in meta.get("research_areas", "").split(",") if x.strip()],
        current_projects=[x.strip() for x in meta.get("current_projects", "").split(",") if x.strip()],
        methods_used=[x.strip() for x in meta.get("methods_used", "").split(",") if x.strip()],
        recent_publications=recent_pubs,
        lab_url=url,
        contact_email=meta.get("contact_email") or None,
        github_url=meta.get("github_url") or None,
        is_accepting_students=is_accepting,
        student_requirements=meta.get("student_requirements") or None,
    )


def _compute_final_score(
    llm_score: float,
    cosine_sim: float,
    has_recent_pub: bool,
    is_accepting: bool | None,
    goal: str,
) -> float:
    score = (0.40 * llm_score) + (0.40 * cosine_sim * 100)

    if has_recent_pub:
        score += 10

    joining_goals = {"join a lab", "apply for phd"}
    goal_lower = (goal or "").lower().strip()

    if is_accepting is True:
        score += 10
    elif is_accepting is None:
        score += 0
    elif is_accepting is False:
        if goal_lower in joining_goals:
            score -= 10
        # else: +0 for Collaborate / Find internship

    return max(0.0, score)