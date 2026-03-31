"""
phase3_discovery.py - Phase 3: Multi-Source Web Discovery.

Runs 3 sources in parallel:
  Source 1: SerpAPI or Google Custom Search (top 5 per query, ~50-60 URLs)
  Source 2: Semantic Scholar /paper/search (3-4 specific queries, PI homepages)
  Source 3: arXiv API (3-4 queries, fuzzy university affiliation matching)

Returns a deduplicated list of 50-100 candidate lab URLs.
"""
from __future__ import annotations
import asyncio
import logging
import re
import time
from urllib.parse import urlparse, urljoin
from typing import Optional

import httpx
from rapidfuzz import fuzz

import cache
from config import SERPAPI_KEY, GOOGLE_CSE_KEY, GOOGLE_CSE_CX

logger = logging.getLogger(__name__)

# University --> domain lookup table (for arXiv affiliation fuzzy matching)
UNIVERSITY_DOMAIN_TABLE: dict[str, str] = {
    "MIT": "mit.edu",
    "Massachusetts Institute of Technology": "mit.edu",
    "Stanford": "stanford.edu",
    "Stanford University": "stanford.edu",
    "Carnegie Mellon": "cmu.edu",
    "Carnegie Mellon University": "cmu.edu",
    "CMU": "cmu.edu",
    "UC Berkeley": "berkeley.edu",
    "University of California Berkeley": "berkeley.edu",
    "Berkeley": "berkeley.edu",
    "Harvard": "harvard.edu",
    "Harvard University": "harvard.edu",
    "Princeton": "princeton.edu",
    "Princeton University": "princeton.edu",
    "Yale": "yale.edu",
    "Yale University": "yale.edu",
    "Columbia": "columbia.edu",
    "Columbia University": "columbia.edu",
    "University of Toronto": "utoronto.ca",
    "UToronto": "utoronto.ca",
    "University of Waterloo": "uwaterloo.ca",
    "UWaterloo": "uwaterloo.ca",
    "McGill": "mcgill.ca",
    "McGill University": "mcgill.ca",
    "Mila": "mila.quebec",
    "Montreal Institute for Learning Algorithms": "mila.quebec",
    "Oxford": "ox.ac.uk",
    "University of Oxford": "ox.ac.uk",
    "Cambridge": "cam.ac.uk",
    "University of Cambridge": "cam.ac.uk",
    "ETH Zurich": "ethz.ch",
    "ETH": "ethz.ch",
    "EPFL": "epfl.ch",
    "Imperial College London": "imperial.ac.uk",
    "Imperial College": "imperial.ac.uk",
    "UCL": "ucl.ac.uk",
    "University College London": "ucl.ac.uk",
    "TU Munich": "tum.de",
    "Technical University Munich": "tum.de",
    "Max Planck": "mpg.de",
    "Max Planck Institute": "mpg.de",
    "DeepMind": "deepmind.com",
    "Google Brain": "google.com",
    "Google Research": "google.com",
    "Microsoft Research": "microsoft.com",
    "FAIR": "ai.meta.com",
    "Meta AI": "ai.meta.com",
    "OpenAI": "openai.com",
    "University of Michigan": "umich.edu",
    "UMich": "umich.edu",
    "University of Washington": "uw.edu",
    "UW": "uw.edu",
    "Georgia Tech": "gatech.edu",
    "Georgia Institute of Technology": "gatech.edu",
    "UIUC": "illinois.edu",
    "University of Illinois Urbana-Champaign": "illinois.edu",
    "NYU": "nyu.edu",
    "New York University": "nyu.edu",
    "UCLA": "ucla.edu",
    "University of California Los Angeles": "ucla.edu",
    "UCSD": "ucsd.edu",
    "University of California San Diego": "ucsd.edu",
    "Caltech": "caltech.edu",
    "California Institute of Technology": "caltech.edu",
    "Cornell": "cornell.edu",
    "Cornell University": "cornell.edu",
    "UBC": "ubc.ca",
    "University of British Columbia": "ubc.ca",
    "University of Edinburgh": "ed.ac.uk",
    "Edinburgh": "ed.ac.uk",
    "IIT Bombay": "iitb.ac.in",
    "IIT Delhi": "iitd.ac.in",
    "IIT Madras": "iitm.ac.in",
    "Indian Institute of Technology": "iit.ac.in",
    "IISc": "iisc.ac.in",
    "Indian Institute of Science": "iisc.ac.in",
    "Tsinghua": "tsinghua.edu.cn",
    "Tsinghua University": "tsinghua.edu.cn",
    "Peking University": "pku.edu.cn",
    "NUS": "nus.edu.sg",
    "National University of Singapore": "nus.edu.sg",
    "NTU": "ntu.edu.sg",
    "Nanyang Technological University": "ntu.edu.sg",
    "KAIST": "kaist.ac.kr",
    "Korea Advanced Institute of Science and Technology": "kaist.ac.kr",
    "Tokyo University": "u-tokyo.ac.jp",
    "University of Tokyo": "u-tokyo.ac.jp",
}

# URL filtering helpers

SKIP_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".zip", ".mp4"}
SKIP_PATTERNS = re.compile(
    r"(news|article|blog|press|event|course|syllabus|schedule|admission|"
    r"undergraduate|catalog|lecture|wiki|wikipedia|reddit|quora|linkedin|"
    r"twitter|youtube|facebook|instagram|amazon|springer|ieee\.org/xpl)",
    re.IGNORECASE,
)
KEEP_PATTERNS = re.compile(
    r"(lab|research|group|faculty|people|team|professor|pi|principal|"
    r"~[a-z]+|/~|/lab|/research|/group|/faculty)",
    re.IGNORECASE,
)


def _is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        path = parsed.path.lower()
        for ext in SKIP_EXTENSIONS:
            if path.endswith(ext):
                return False
        if SKIP_PATTERNS.search(url):
            return False
        return True
    except Exception:
        return False


def _domain_prefix(url: str) -> str:
    """Return 'domain + first 2 path segments' as dedup key."""
    try:
        p = urlparse(url)
        parts = [seg for seg in p.path.split("/") if seg][:2]
        return p.netloc + "/" + "/".join(parts)
    except Exception:
        return url


def _deduplicate(urls: list[str]) -> list[str]:
    seen_exact: set[str] = set()
    seen_prefix: set[str] = set()
    result: list[str] = []
    for url in urls:
        if url in seen_exact:
            continue
        prefix = _domain_prefix(url)
        if prefix in seen_prefix:
            continue
        seen_exact.add(url)
        seen_prefix.add(prefix)
        result.append(url)
    return result


# Source 1: SerpAPI / Google Custom Search

async def _search_serpapi(query: str, client: httpx.AsyncClient) -> list[str]:
    cache_key = f"serp:{query}"
    cached = cache.get(cache_key, cache.TTL_SERP)
    if cached:
        return cached

    urls: list[str] = []

    if SERPAPI_KEY:
        try:
            resp = await client.get(
                "https://serpapi.com/search",
                params={
                    "q": query,
                    "api_key": SERPAPI_KEY,
                    "num": 10,
                    "engine": "google",
                },
                timeout=15,
            )
            data = resp.json()
            organic = data.get("organic_results", [])
            for item in organic[:5]:
                link = item.get("link", "")
                if link and _is_valid_url(link):
                    urls.append(link)
        except Exception as e:
            if "quota" in str(e).lower() or (hasattr(e, 'response') and getattr(e, 'response', None) and e.response.status_code == 429):
                logger.warning(f"SerpAPI quota exceeded — skipping.")
            else:
                logger.warning(f"SerpAPI error for '{query}': {e}")
    elif GOOGLE_CSE_KEY and GOOGLE_CSE_CX:
        try:
            resp = await client.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "q": query,
                    "key": GOOGLE_CSE_KEY,
                    "cx": GOOGLE_CSE_CX,
                    "num": 5,
                },
                timeout=15,
            )
            data = resp.json()
            for item in data.get("items", [])[:5]:
                link = item.get("link", "")
                if link and _is_valid_url(link):
                    urls.append(link)
        except Exception as e:
            logger.warning(f"Google CSE error for '{query}': {e}")

    cache.set(cache_key, urls)
    return urls


# Source 2: Semantic Scholar
async def _search_semantic_scholar(query: str, client: httpx.AsyncClient) -> list[str]:
    urls: list[str] = []
    try:
        resp = await client.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={
                "query": query,
                "fields": "authors,externalIds",
                "limit": 5,
            },
            timeout=20,
            headers={"User-Agent": "Talaash/1.0 (research lab finder)"},
        )
        data = resp.json()
        for paper in data.get("data", []):
            authors = paper.get("authors", [])
            if authors:
                last_author = authors[-1]
                author_id = last_author.get("authorId")
                if author_id:
                    author_resp = await client.get(
                        f"https://api.semanticscholar.org/graph/v1/author/{author_id}",
                        params={"fields": "homepage,affiliations"},
                        timeout=10,
                        headers={"User-Agent": "Talaash/1.0"},
                    )
                    author_data = author_resp.json()
                    homepage = author_data.get("homepage", "")
                    if homepage and _is_valid_url(homepage):
                        urls.append(homepage)
                    await asyncio.sleep(0.3)
    except Exception as e:
        logger.warning(f"Semantic Scholar error for '{query}': {e}")
    return urls


# Source 3: arXiv
def _fuzzy_match_university(affiliation: str) -> Optional[str]:
    """Return domain URL if fuzzy match score >= 70, else None (low confidence)."""
    best_score = 0
    best_domain = None
    for name, domain in UNIVERSITY_DOMAIN_TABLE.items():
        score = fuzz.partial_ratio(name.lower(), affiliation.lower())
        if score > best_score:
            best_score = score
            best_domain = domain
    if best_score >= 70:
        return f"https://www.{best_domain}"
    return None


async def _search_arxiv(query: str, client: httpx.AsyncClient) -> list[str]:
    urls: list[str] = []
    try:
        resp = await client.get(
            "https://export.arxiv.org/api/query",
            params={
                "search_query": f"all:{query}",
                "max_results": 5,
                "sortBy": "relevance",
            },
            timeout=20,
            headers={"User-Agent": "Talaash/1.0"},
        )
        text = resp.text
        # Extract affiliations from arXiv Atom XML
        affiliations = re.findall(r"<arxiv:affiliation[^>]*>(.*?)</arxiv:affiliation>", text, re.DOTALL)
        seen_domains: set[str] = set()
        for aff in affiliations:
            aff_clean = re.sub(r"<[^>]+>", "", aff).strip()
            domain_url = _fuzzy_match_university(aff_clean)
            if domain_url and domain_url not in seen_domains:
                urls.append(domain_url)
                seen_domains.add(domain_url)
    except Exception as e:
        logger.warning(f"arXiv error for '{query}': {e}")
    return urls


# Main discovery function

async def discover_urls(expanded_queries: list[str]) -> list[str]:
    """
    Run all 3 sources in parallel. Returns 50-100 deduplicated candidate URLs.
    Source 1: all queries (top 5 per) via SerpAPI/CSE
    Source 2: first 4 queries via Semantic Scholar
    Source 3: first 4 queries via arXiv (with 3s rate limit between calls)
    """
    all_urls: list[str] = []

    async with httpx.AsyncClient(
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 Talaash ResearchFinder/1.0"},
    ) as client:

        # Source 1 tasks (all queries)
        serp_tasks = [_search_serpapi(q, client) for q in expanded_queries]

        # Source 2 tasks (first 4 queries)
        scholar_queries = expanded_queries[:4]

        # Source 3 queries (first 4, rate-limited below)
        arxiv_queries = expanded_queries[:4]

        # Run Source 1 + 2 concurrently
        serp_results, scholar_results_lists = await asyncio.gather(
            asyncio.gather(*serp_tasks, return_exceptions=True),
            asyncio.gather(*[_search_semantic_scholar(q, client) for q in scholar_queries], return_exceptions=True),
        )

        for r in serp_results:
            if isinstance(r, list):
                all_urls.extend(r)

        for r in scholar_results_lists:
            if isinstance(r, list):
                all_urls.extend(r)

        # Source 3: arXiv — 1 req per 3 seconds
        for q in arxiv_queries:
            result = await _search_arxiv(q, client)
            all_urls.extend(result)
            await asyncio.sleep(3)

    deduped = _deduplicate(all_urls)
    logger.info(f"Discovered {len(all_urls)} raw URLs → {len(deduped)} after dedup.")
    return deduped[:100]
