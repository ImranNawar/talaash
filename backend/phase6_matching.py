"""
phase6_matching.py - Phase 6: Two-Stage Matching Engine.

Stage 1: ChromaDB top-20 cosine similarity (threshold 0.4, retry at 0.3)
Stage 2: Gemini 1.5 Flash re-ranking (trimmed profiles, score 0-100, reasons, gaps)
Final scoring formula per Logic.md (exact, clamped >= 0).
"""
from __future__ import annotations
import ast
import datetime
import json
import logging
import re

import google.generativeai as genai
from pydantic import ValidationError

from config import GEMINI_API_KEY
from models import LabProfile, MatchResult, Publication, UserInput
from phase5_vectorstore import _get_collection

logger = logging.getLogger(__name__)
genai.configure(api_key=GEMINI_API_KEY)
_gemini_model = genai.GenerativeModel("gemini-1.5-flash")

RERANKER_PROMPT = """You are an academic research group matching expert.

Given a researcher's profile and a list of research lab candidates, score how well each lab matches.

For EACH candidate, you must:
1. Score the match from 0 to 100 (100 = perfect match)
2. List 2 to 4 specific reasons why this group matches the researcher
3. List 1 to 2 specific gaps or skills the researcher would need to develop

Output ONLY a valid JSON array. No markdown, no explanation. Example structure:
[
  {
    "lab_url": "https://example.com/lab",
    "score": 85,
    "match_reasons": ["Strong overlap in federated learning research", "Uses PyTorch which matches skills"],
    "gaps": ["Requires Rust experience", "Focuses on hardware which is secondary interest"]
  }
]

Researcher Profile:
{user_profile}

Lab Candidates:
{candidates_json}

Output only the JSON array:"""


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


def _trim_for_reranking(profile: LabProfile) -> dict:
    """Trim profile to only fields needed by re-ranker + 2 most recent pubs."""
    sorted_pubs = sorted(profile.recent_publications, key=lambda p: p.year, reverse=True)
    top_pubs = [{"title": p.title, "year": p.year} for p in sorted_pubs[:2]]
    return {
        "lab_url": profile.lab_url,
        "pi_name": profile.pi_name,
        "university": profile.university,
        "lab_name": profile.lab_name,
        "research_areas": profile.research_areas,
        "methods_used": profile.methods_used,
        "current_projects": profile.current_projects,
        "is_accepting_students": profile.is_accepting_students,
        "recent_publications": top_pubs,
    }


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


def _gemini_rerank(candidates: list[LabProfile], user_profile_string: str) -> list[dict] | None:
    """Call Gemini 2.5 Flash to re-rank. Returns list of {lab_url, score, match_reasons, gaps}."""
    trimmed = [_trim_for_reranking(p) for p in candidates]
    prompt = RERANKER_PROMPT.format(
        user_profile=user_profile_string,
        candidates_json=json.dumps(trimmed, indent=2),
    )
    try:
        response = _gemini_model.generate_content(prompt)
        raw = response.text.strip()
        raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
        results = json.loads(raw)
        if not isinstance(results, list):
            raise ValueError("Not a list")
        return results
    except Exception as e:
        logger.warning(f"Gemini re-ranker failed: {e}")
        return None


def match_and_rank(user_input: UserInput, user_embedding: list[float] | None, user_profile_string: str) -> list[MatchResult]:
    """
    Stage 1: ChromaDB top-20 by cosine similarity (threshold 0.4, retry 0.3).
    Stage 2: Gemini Flash re-ranking.
    Returns top 10 MatchResult, sorted by final_score descending.
    
    If embeddings fail, falls back to text-based matching on all stored profiles.
    """
    collection = _get_collection()
    count = collection.count()
    if count == 0:
        logger.warning("ChromaDB collection is empty — no profiles stored.")
        return []

    candidates_with_sim: list[tuple[LabProfile, float]] = []
    
    # Check if embeddings are effectively unavailable (None, empty, or all zeros)
    embeddings_unavailable = (
        user_embedding is None or 
        len(user_embedding) == 0 or 
        all(x == 0.0 for x in user_embedding)
    )
    
    if embeddings_unavailable:
        # Fallback: get all profiles without embedding similarity
        logger.info("Embeddings not available — using all stored profiles for text-based matching.")
        try:
            all_results = collection.get(include=["metadatas"])
            ids = all_results.get("ids", [])
            metas = all_results.get("metadatas", [])
            
            for url, meta in zip(ids, metas):
                profile = _rebuild_profile_from_meta(meta, url)
                candidates_with_sim.append((profile, 0.5))  # Default similarity score
        except Exception as e:
            logger.warning(f"Failed to get profiles from ChromaDB: {e}")
            return []
    else:
        # Normal flow: use embeddings
        n_results = min(20, count)

        # Stage 1: retrieve top-20
        query_results = collection.query(
            query_embeddings=[user_embedding],
            n_results=n_results,
            include=["metadatas", "distances"],
        )

        ids     = query_results.get("ids", [[]])[0]
        metas   = query_results.get("metadatas", [[]])[0]
        dists   = query_results.get("distances", [[]])[0]

        THRESHOLD = 0.4

        for url, meta, dist in zip(ids, metas, dists):
            cosine_sim = 1.0 - dist  # ChromaDB cosine distance → similarity
            if cosine_sim >= THRESHOLD:
                profile = _rebuild_profile_from_meta(meta, url)
                candidates_with_sim.append((profile, cosine_sim))

        # If fewer than 5 pass threshold, lower to 0.3 and retry
        if len(candidates_with_sim) < 5:
            logger.info("Fewer than 5 results at 0.4 — retrying with threshold 0.3.")
            THRESHOLD = 0.3
            candidates_with_sim = []
            for url, meta, dist in zip(ids, metas, dists):
                cosine_sim = 1.0 - dist
                if cosine_sim >= THRESHOLD:
                    profile = _rebuild_profile_from_meta(meta, url)
                    candidates_with_sim.append((profile, cosine_sim))

        if not candidates_with_sim:
            logger.info("No candidates passed similarity threshold.")
            return []

    profiles_only = [p for p, _ in candidates_with_sim]
    sim_map = {p.lab_url: s for p, s in candidates_with_sim}

    # Stage 2: Gemini re-ranking
    rerank_data = _gemini_rerank(profiles_only, user_profile_string)

    results: list[MatchResult] = []

    if rerank_data is None:
        # Fallback: return all profiles with default scores (no LLM re-ranking)
        logger.info("Gemini re-ranking failed — returning all profiles with default scores.")
        for profile, sim in candidates_with_sim[:10]:  # Limit to top 10
            has_recent = _has_recent_publication(profile.recent_publications)
            final = _compute_final_score(60, sim, has_recent, profile.is_accepting_students, user_input.goal)
            results.append(MatchResult(
                profile=profile,
                final_score=round(final, 1),
                match_reasons=["Profile extracted from research lab website"],
                gaps=["Contact the lab directly for specific requirements"],
                has_recent_publication=has_recent,
            ))
    else:
        # Build lookup from re-ranker data
        rerank_map = {item.get("lab_url", ""): item for item in rerank_data if isinstance(item, dict)}

        for profile, sim in candidates_with_sim:
            rdata = rerank_map.get(profile.lab_url, {})
            llm_score = float(rdata.get("score", 50))
            match_reasons = rdata.get("match_reasons", [])[:4]
            gaps = rdata.get("gaps", [])[:2]
            has_recent = _has_recent_publication(profile.recent_publications)
            final = _compute_final_score(llm_score, sim, has_recent, profile.is_accepting_students, user_input.goal)

            results.append(MatchResult(
                profile=profile,
                final_score=round(final, 1),
                match_reasons=match_reasons,
                gaps=gaps,
                has_recent_publication=has_recent,
            ))

    # Sort by final_score descending, return top 10
    results.sort(key=lambda r: r.final_score, reverse=True)
    return results[:10]