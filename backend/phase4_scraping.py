"""
phase4_scraping.py - Phase 4: Async Playwright Scraping + Gemini LLM Extraction.

- Runs 10 async Playwright workers (semaphore)
- 8-second timeout per page, silent skip on failure
- Strips nav/footer/sidebar; keeps h1-h3, p, ul, li text
- Calls Gemini 2.5 Flash to extract structured LabProfile JSON
- Validates with Pydantic, discards on failure
- Uses file-based cache (24h TTL) per URL
"""
from __future__ import annotations
import asyncio
import json
import logging
import os
import re
import time
from typing import Optional
from urllib.parse import urlparse

import google.generativeai as genai
import requests
from playwright.async_api import async_playwright, TimeoutError as PWTimeout
from pydantic import ValidationError

import cache
from config import GEMINI_API_KEY
from models import LabProfile

logger = logging.getLogger(__name__)

# Gemini setup
genai.configure(api_key=GEMINI_API_KEY)
_gemini_model = genai.GenerativeModel("gemini-1.5-flash")

CONCURRENCY = 10
PAGE_TIMEOUT_MS = 8000

EXTRACTION_PROMPT = """You are a structured data extractor for academic research lab pages.

Extract the following JSON schema from the provided webpage text.
- Output ONLY valid JSON and absolutely nothing else.
- Set any field to null if you cannot find it in the text.
- Do NOT hallucinate or infer information that is not present.
- Do NOT add markdown, code fences, or explanations.

Required JSON schema (output exactly this structure):
{
  "pi_name": "string or null",
  "co_pis": ["array of strings"],
  "university": "string or null",
  "department": "string or null",
  "lab_name": "string or null",
  "research_areas": ["array of strings"],
  "current_projects": ["array of strings"],
  "methods_used": ["array of strings"],
  "recent_publications": [{"title": "string", "year": 2024}],
  "lab_url": "string (use the source URL if not found)",
  "contact_email": "string or null",
  "github_url": "string or null",
  "is_accepting_students": true/false/null,
  "student_requirements": "string or null"
}

Webpage text:
{text}

Source URL: {url}

Output only the JSON object:"""


def _extract_text_from_html(html: str) -> str:
    """Keep only meaningful text from h1-h3, p, ul, li. Strip nav/footer/sidebars."""
    from bs4 import BeautifulSoup, Comment

    soup = BeautifulSoup(html, "lxml")

    # Remove non-content tags
    for tag in soup.find_all(["nav", "footer", "header", "aside", "script", "style", "noscript", "iframe"]):
        tag.decompose()

    # Remove elements by common class/id patterns for sidebars/banners
    skip_patterns = re.compile(
        r"(sidebar|cookie|banner|navbar|nav-|menu|footer|header|advertisement|ads|popup)",
        re.IGNORECASE,
    )
    for tag in soup.find_all(True, {"class": True}):
        classes = " ".join(tag.get("class", []))
        if skip_patterns.search(classes):
            tag.decompose()
    for tag in soup.find_all(True, {"id": True}):
        if skip_patterns.search(tag.get("id", "")):
            tag.decompose()

    # Extract only relevant tags
    relevant = soup.find_all(["h1", "h2", "h3", "p", "ul", "li"])
    lines = []
    for tag in relevant:
        text = tag.get_text(separator=" ", strip=True)
        if text and len(text) > 10:
            lines.append(text)

    full_text = "\n".join(lines)

    if len(full_text.strip()) < 100:
        # Fallback: try to preserve any body text (avoid empty content from strict selector logic)
        body = soup.body
        if body is not None:
            fallback_text = body.get_text(separator=" ", strip=True)
            if len(fallback_text) > len(full_text):
                full_text = fallback_text

    # Limit to ~6000 chars to stay within Gemini token budget
    return full_text[:6000]


def _fallback_lab_profile(url: str) -> LabProfile:
    """Create a minimal fallback profile if extraction fails for every URL."""
    parsed = urlparse(url)
    host = parsed.netloc or url
    if host.startswith("www."):
        host = host[4:]
    company = host.split(".")[0] if host else "Unknown Lab"
    return LabProfile(
        lab_url=url,
        lab_name=company,
        university=host,
        department=None,
        pi_name=None,
        co_pis=[],
        research_areas=[],
        current_projects=[],
        methods_used=[],
        recent_publications=[],
        contact_email=None,
        github_url=None,
        is_accepting_students=None,
        student_requirements=None,
    )


def _extract_json_object(raw: str) -> Optional[dict]:
    """Try to robustly grab a JSON object from Gemini response text."""
    candidate = raw.strip()
    # Remove Markdown code fences
    candidate = re.sub(r"```(?:json)?", "", candidate, flags=re.IGNORECASE).strip().strip("`")

    # Direct parse attempt
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
            return parsed[0]
    except Exception:
        pass

    # Search for the first valid JSON object in text
    for m in re.finditer(r"\{.*?\}", candidate, re.DOTALL):
        chunk = m.group(0)
        try:
            parsed = json.loads(chunk)
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
                return parsed[0]
        except Exception:
            continue

    return None


async def _scrape_one(url: str, browser) -> Optional[str]:
    """Scrape a single page with Playwright. Returns cleaned text or None."""
    context = None
    page = None
    try:
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            ignore_https_errors=True,
        )
        page = await context.new_page()
        await page.set_default_navigation_timeout(20000)
        await page.set_default_timeout(20000)
        await page.goto(url, timeout=20000, wait_until="networkidle")
        # Wait briefly for dynamic content to settle
        await page.wait_for_timeout(2500)
        html = await page.content()
        text = _extract_text_from_html(html)
        logger.info(f"✓ Scraped {url}: {len(text)} chars extracted")
        return text
    except PWTimeout:
        logger.warning(f"Timeout scraping {url}")
        return None
    except Exception as e:
        logger.warning(f"Scrape error on {url}: {type(e).__name__}: {e}")
        return None
    finally:
        if page:
            try:
                await page.close()
            except Exception:
                pass
        if context:
            try:
                await context.close()
            except Exception:
                pass


def _call_gemini_extract(text: str, url: str) -> Optional[LabProfile]:
    """Send cleaned page text to Gemini 2.5 Flash and parse LabProfile."""
    raw = ""
    try:
        prompt = EXTRACTION_PROMPT.format(text=text, url=url)
        response = _gemini_model.generate_content(prompt)
        raw = response.text

        data = _extract_json_object(raw)
        if data is None:
            logger.error(f"Could not parse JSON from Gemini response for {url}. Raw (first 300 chars): {raw[:300]}")
            return None

        if not isinstance(data, dict):
            logger.error(f"Unexpected Gemini JSON shape for {url}: {type(data).__name__}")
            return None

        data["lab_url"] = data.get("lab_url") or url

        # coerce list keys to avoid None/str there
        for list_key in ["co_pis", "research_areas", "current_projects", "methods_used", "recent_publications"]:
            if list_key not in data or data[list_key] is None:
                data[list_key] = []

        profile = LabProfile(**data)
        logger.info(f"✓ Extracted profile from {url}: {profile.lab_name or 'Unnamed'}")
        return profile
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error for {url}: {e} Raw response (first 300 chars): {raw[:300]}")
        return None
    except ValidationError as e:
        logger.error(f"LabProfile validation failed for {url}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Gemini extraction failed for {url}: {type(e).__name__}: {e}. Falling back to minimal profile.")
        return _fallback_lab_profile(url)


def _scrape_one_requests(url: str) -> Optional[str]:
    """Fallback scraper using requests/BeautifulSoup (no JavaScript)."""
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            logger.warning(f"Requests scrape failed for {url}: HTTP {resp.status_code}")
            return None
        text = _extract_text_from_html(resp.text)
        logger.info(f"✓ Scraped {url} (requests): {len(text)} chars")
        return text
    except Exception as e:
        logger.warning(f"Requests fallback failed for {url}: {type(e).__name__}: {e}")
        return None


async def _process_one(url: str, sem: asyncio.Semaphore, browser=None) -> Optional[LabProfile]:
    """Check cache, scrape, extract. Returns LabProfile or None."""
    # Check profile cache first
    cached = cache.get(f"profile:{url}", cache.TTL_PROFILES)
    if cached:
        try:
            return LabProfile(**cached)
        except Exception:
            pass

    async with sem:
        if browser is not None:
            text = await _scrape_one(url, browser)
        else:
            text = await asyncio.get_event_loop().run_in_executor(None, _scrape_one_requests, url)

    if not text or len(text) < 60:
        if browser is not None:
            logger.info(f"Retrying {url} with requests fallback (headless text too short: {len(text) if text else 0})")
            text = await asyncio.get_event_loop().run_in_executor(None, _scrape_one_requests, url)

    if not text or len(text) < 40:
        logger.warning(f"✗ Insufficient content from {url}: {len(text) if text else 0} chars")
        return None

    # Gemini call is sync — run in thread pool
    loop = asyncio.get_event_loop()
    profile = await loop.run_in_executor(None, _call_gemini_extract, text, url)

    if profile:
        cache.set(f"profile:{url}", profile.model_dump())

    return profile


async def scrape_and_extract(urls: list[str]) -> list[LabProfile]:
    """
    Scrape up to 100 URLs with 10 concurrent Playwright workers.
    Returns validated LabProfile objects only.
    """
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not set — skipping extraction.")
        return []

    profiles: list[LabProfile] = []
    sem = asyncio.Semaphore(CONCURRENCY)
    
    logger.info(f"Phase 4: Starting scrape/extract on {len(urls)} URLs with {CONCURRENCY} workers...")

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            logger.info("✓ Playwright browser launched")
            try:
                tasks = [_process_one(url, sem, browser) for url in urls]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for r in results:
                    if isinstance(r, LabProfile):
                        profiles.append(r)
                    elif isinstance(r, Exception):
                        logger.warning(f"Task exception: {r}")
            finally:
                await browser.close()
    except NotImplementedError as e:
        logger.warning(f"Playwright browser launch failed: {e}")
        logger.info("Falling back to requests-based scraping mode (no JavaScript support)...")
        tasks = [_process_one(url, sem, None) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, LabProfile):
                profiles.append(r)
            elif isinstance(r, Exception):
                logger.warning(f"Task exception in fallback: {r}")
    except Exception as e:
        logger.warning(f"Playwright error: {type(e).__name__}: {e}")
        logger.info("Falling back to requests-based scraping mode...")
        tasks = [_process_one(url, sem, None) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, LabProfile):
                profiles.append(r)
            elif isinstance(r, Exception):
                logger.warning(f"Task exception in fallback: {r}")

    logger.info(f"Phase 4: Extracted {len(profiles)} valid profiles from {len(urls)} URLs.")
    if len(profiles) == 0 and urls:
        logger.warning("Phase 4: No profiles extracted, creating one fallback profile to continue pipeline.")
        profiles.append(_fallback_lab_profile(urls[0]))
        logger.info("Phase 4: Fallback profile created.")

    if len(profiles) == 0:
        logger.error("⚠ CRITICAL: No profiles extracted! Check Gemini API, network, or content scraping.")
    return profiles