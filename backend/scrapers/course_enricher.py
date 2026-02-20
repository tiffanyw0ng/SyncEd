"""
Course Content Enricher

Enriches short bulletin descriptions with detailed topic/technology
information for better vectorization quality.

Sources (in priority order):
  1. Curated enrichment JSON (backend/data/course_enrichment.json)
  2. Known course websites (eecs280.org, eecs485.org, etc.)
  3. Google search snippets (fallback)
"""

import asyncio
import json
import re
from html import unescape
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).parent.parent / "data"
ENRICHMENT_FILE = DATA_DIR / "course_enrichment.json"

KNOWN_COURSE_SITES: dict[str, str] = {
    "EECS 280": "https://eecs280.org",
    "EECS 285": "https://eecs285.org",
    "EECS 376": "https://eecs376.org",
    "EECS 388": "https://eecs388.org",
    "EECS 441": "https://eecs441.eecs.umich.edu",
    "EECS 481": "https://eecs481.org",
    "EECS 482": "https://eecs482.github.io",
    "EECS 483": "https://eecs483.github.io",
    "EECS 484": "https://eecs484db.github.io",
    "EECS 485": "https://eecs485.org",
    "EECS 486": "https://eecs486.github.io",
    "EECS 489": "https://eecs489.org",
    "EECS 490": "https://eecs490.github.io",
    "EECS 493": "https://eecs493.github.io",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

_enrichment_data: dict | None = None


def _load_enrichment_data() -> dict:
    global _enrichment_data
    if _enrichment_data is None:
        try:
            _enrichment_data = json.loads(ENRICHMENT_FILE.read_text())
        except Exception:
            _enrichment_data = {}
    return _enrichment_data


async def enrich_courses(courses: list, prefix: str = "EECS") -> list:
    """Add detailed content to courses. Modifies in-place and returns them."""
    enrichment = _load_enrichment_data()
    enriched_count = 0

    for course in courses:
        entry = enrichment.get(course.code)
        if entry:
            extra_topics = entry.get("topics", "")
            extra_tech = entry.get("tech", [])

            if extra_topics and extra_topics not in course.description:
                course.description = (
                    course.description.rstrip() + " [Topics] " + extra_topics
                )

            for t in extra_tech:
                if t not in course.topics:
                    course.topics.append(t)

            enriched_count += 1

    print(f"[Enricher] Enriched {enriched_count}/{len(courses)} {prefix} courses from curated data")

    remaining = [
        c for c in courses
        if c.code not in enrichment and len(c.description) < 300
    ]

    if remaining:
        print(f"[Enricher] Attempting web enrichment for {len(remaining)} remaining courses...")
        async with httpx.AsyncClient(timeout=12, follow_redirects=True, headers=HEADERS) as client:
            tasks = []
            for course in remaining:
                if course.code in KNOWN_COURSE_SITES:
                    tasks.append(_enrich_from_site(client, course, KNOWN_COURSE_SITES[course.code]))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    return courses


async def _enrich_from_site(client: httpx.AsyncClient, course, url: str):
    """Scrape a known course website for syllabus content."""
    try:
        resp = await client.get(url)
        if resp.status_code != 200:
            return

        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(" ", strip=True)

        schedule_match = re.search(
            r"(?:Schedule|Syllabus|Topics|Lectures?)(.{200,3000}?)(?:Office Hours|People|Staff|Grading|$)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        extra = ""
        if schedule_match:
            extra = _clean_text(schedule_match.group(1))
        else:
            extra = _clean_text(text[:2000])

        if extra and extra not in course.description:
            course.description = course.description.rstrip() + " " + extra.strip()
            new_topics = _extract_tech_keywords(extra)
            for t in new_topics:
                if t not in course.topics:
                    course.topics.append(t)
    except Exception:
        pass


def _clean_text(text: str) -> str:
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(Office Hours|Staff|People|Grading Policy).*", "", text, flags=re.I)
    text = re.sub(r"https?://\S+", "", text)
    return text.strip()[:2000]


TECH_KEYWORDS = [
    "C++", "Python", "Java", "Rust", "Go", "JavaScript", "TypeScript",
    "React", "Flask", "Django", "REST API", "MapReduce", "SQL", "NoSQL",
    "Docker", "Kubernetes", "AWS", "Linux", "Git",
    "machine learning", "deep learning", "neural network", "transformer",
    "NLP", "computer vision", "reinforcement learning",
    "data structures", "algorithms", "dynamic programming",
    "operating systems", "concurrency", "threading",
    "databases", "distributed systems", "web systems",
    "computer architecture", "assembly", "pipelining", "cache",
    "FPGA", "VLSI", "Verilog", "SystemVerilog",
    "circuits", "signal processing", "control systems",
    "electromagnetics", "RF", "power electronics",
    "TCP/IP", "networking", "sockets", "HTTP",
    "encryption", "authentication", "XSS", "SQL injection",
    "compilers", "parsing", "type systems",
    "graphics", "OpenGL", "rendering",
]


def _extract_tech_keywords(text: str) -> list[str]:
    found = []
    lower = text.lower()
    for kw in TECH_KEYWORDS:
        kw_lower = kw.lower()
        if len(kw_lower) <= 4:
            if re.search(rf"\b{re.escape(kw_lower)}\b", lower):
                found.append(kw)
        else:
            if kw_lower in lower:
                found.append(kw)
    return found
