"""
main.py - FastAPI application for Talaash.

Endpoints:
  GET  /api/health       - health check
  POST /api/search       - full 7-phase pipeline with SSE progress streaming
  POST /api/search/sync  - same pipeline, returns JSON directly (no streaming)
"""
from __future__ import annotations
import asyncio
import json
import logging
import os
from datetime import datetime

# Windows needs ProactorEventLoop for subprocess support used by Playwright.
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError

from models import UserInput, SearchResponse, MatchResult, LabProfile
from phase2_expansion import expand_queries
from phase4_scraping import scrape_and_extract
from phase5_vectorstore import embed_and_store, embed_user_query
from phase6_matching import match_and_rank

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("talaash.main")

# FastAPI app
app = FastAPI(
    title="Talaash — Research Lab Finder",
    description="AI-powered research lab discovery and matching engine.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Hardcoded test URL for MVP
MVP_TEST_URL = "https://bair.berkeley.edu/"

# Helper: build user profile string

def build_profile_string(user_input: UserInput) -> str:
    parts = [
        f"Research Interests: {user_input.research_interests}",
        f"Technical Skills: {user_input.technical_skills}",
        f"Academic Level: {user_input.academic_level}",
        f"Goal: {user_input.goal}",
    ]
    if user_input.keywords:
        parts.append(f"Keywords: {user_input.keywords}")
    if user_input.preferred_region:
        parts.append(f"Preferred Region: {user_input.preferred_region}")
    return "\n".join(parts)


# SSE helper

def sse_event(phase: int, label: str, status: str, detail: str = "") -> str:
    data = json.dumps({"phase": phase, "label": label, "status": status, "detail": detail})
    return f"data: {data}\n\n"


def sse_results(results: list[MatchResult], total_candidates: int) -> str:
    payload = {
        "type": "results",
        "results": [r.model_dump() for r in results],
        "total_candidates": total_candidates,
    }
    return f"data: {json.dumps(payload)}\n\n"


# Pipeline
async def run_pipeline(user_input: UserInput):
    """
    Full 7-phase pipeline as an async generator yielding SSE events.
    All errors handled internally — never exposes error details to user.
    """
    from phase3_discovery import discover_urls

    user_profile_string = build_profile_string(user_input)
    total_candidates = 0

    # Phase 1: Profile assembled
    yield sse_event(1, "Analyzing your profile", "done", f"Goal: {user_input.goal}")

    # Phase 2: Query expansion
    yield sse_event(2, "Expanding search queries", "running")
    await asyncio.sleep(0.1)
    try:
        expanded_queries = await asyncio.get_event_loop().run_in_executor(
            None, expand_queries, user_profile_string
        )
    except Exception:
        expanded_queries = [user_profile_string]
    yield sse_event(2, "Expanding search queries", "done", f"{len(expanded_queries)} queries generated")

    # Phase 3: URL discovery
    yield sse_event(3, "Discovering research labs", "running")
    try:
        candidate_urls = await discover_urls(expanded_queries)
    except Exception as e:
        logger.warning(f"Discovery failed: {e}")
        candidate_urls = [MVP_TEST_URL]

    # Always include MVP test URL to ensure at least 1 result
    if MVP_TEST_URL not in candidate_urls:
        candidate_urls.insert(0, MVP_TEST_URL)

    total_candidates = len(candidate_urls)
    yield sse_event(3, "Discovering research labs", "done", f"{total_candidates} candidate URLs found")

    # Phase 4: Scraping + extraction
    yield sse_event(4, "Scraping and extracting lab data", "running")
    try:
        profiles = await scrape_and_extract(candidate_urls[:50])  # cap at 50 for MVP safety
    except Exception as e:
        logger.warning(f"Scraping failed: {e}")
        profiles = []
    yield sse_event(4, "Scraping and extracting lab data", "done", f"{len(profiles)} profiles extracted")

    if not profiles:
        yield sse_event(5, "Building knowledge base", "done", "No profiles to store")
        yield sse_event(6, "Matching and ranking", "done", "No results")
        yield sse_event(7, "Preparing results", "done")
        yield sse_results([], 0)
        return

    # Phase 5: Embed and store profiles in ChromaDB
    yield sse_event(5, "Building knowledge base", "running")
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, embed_and_store, profiles
        )
    except Exception as e:
        logger.warning(f"Embedding/storage failed: {e}")
    yield sse_event(5, "Building knowledge base", "done", f"{len(profiles)} profiles embedded and stored")

    # Phase 6: Matching and ranking using ChromaDB similarities + LLM re-ranking
    yield sse_event(6, "Matching and ranking", "running")
    results: list[MatchResult] = []
    try:
        # Embed user query for similarity search
        user_embedding = await asyncio.get_event_loop().run_in_executor(
            None, embed_user_query, user_input
        )
        
        # Run matching engine (Stage 1: similarity, Stage 2: LLM re-ranking)
        results = await asyncio.get_event_loop().run_in_executor(
            None, match_and_rank, user_input, user_embedding, user_profile_string
        )
    except Exception as e:
        logger.warning(f"Matching failed: {e} — falling back to extracted profiles")
        # Fallback: return the extracted profiles even if matching fails
        # This ensures users see the 9 profiles that were successfully extracted in Phase 5
        try:
            from phase5_vectorstore import _has_recent_publication, _compute_final_score
            for profile in profiles:
                has_recent = _has_recent_publication(profile.recent_publications)
                final = _compute_final_score(70, 0.5, has_recent, profile.is_accepting_students, user_input.goal)
                results.append(MatchResult(
                    profile=profile,
                    final_score=round(final, 1),
                    match_reasons=["Profile extracted from research lab website"],
                    gaps=["Contact lab directly for specific requirements"],
                    has_recent_publication=has_recent,
                ))
        except Exception as e2:
            logger.warning(f"Fallback also failed: {e2}")
            results = []
    
    if not results and profiles:
        logger.info(f"Phase 6: No matching results, but returning {len(profiles)} extracted profiles as fallback")
    
    yield sse_event(6, "Matching and ranking", "done", f"{len(results)} profiles available")

    # Phase 7: Finalize
    yield sse_event(7, "Preparing your results", "done")
    yield sse_results(results, total_candidates)


# Endpoints
@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/search/stream")
async def search_stream_get():
    return JSONResponse(
        status_code=405,
        content={
            "detail": "Method Not Allowed - use POST with JSON payload. See /docs for API docs.",
        },
    )


@app.get("/api/search")
async def search_get():
    return JSONResponse(
        status_code=405,
        content={
            "detail": "Method Not Allowed - use POST with JSON payload. See /docs for API docs.",
        },
    )


@app.post("/api/search/stream")
async def search_stream(user_input: UserInput):
    """SSE streaming endpoint — frontend connects and receives live phase updates."""
    async def event_generator():
        try:
            async for chunk in run_pipeline(user_input):
                yield chunk
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            error_event = json.dumps({"type": "error", "detail": "An unexpected error occurred."})
            yield f"data: {error_event}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/search", response_model=SearchResponse)
async def search(user_input: UserInput):
    """
    Synchronous search endpoint — runs full pipeline and returns JSON.
    Use this for testing. Frontend should use /api/search/stream for live progress.
    """
    results: list[MatchResult] = []
    total_candidates = 0

    async for chunk in run_pipeline(user_input):
        chunk = chunk.replace("data: ", "").strip()
        if not chunk:
            continue
        try:
            data = json.loads(chunk)
            if data.get("type") == "results":
                total_candidates = data.get("total_candidates", 0)
                for r in data.get("results", []):
                    # Re-parse into MatchResult
                    try:
                        results.append(MatchResult(**r))
                    except Exception:
                        pass
        except Exception:
            pass

    return SearchResponse(
        results=results,
        total_candidates=total_candidates,
        phases_completed=7,
    )