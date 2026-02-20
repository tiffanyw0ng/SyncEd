"""
Job Market Scraper — Market Stream (10,000+ postings)

Scrapes real job data from multiple public sources at scale:
  1. HN "Who's Hiring" — ALL monthly threads (2023-2026) via Algolia API
  2. RemoteOK — free JSON API, no auth needed
  3. Arbeitnow — free JSON API for remote/hybrid jobs
  4. Jobicy — free JSON API for remote tech jobs
  5. LinkedIn — via Google search index
  6. Glassdoor — via Google search index
  7. Greenhouse — via Google search index
  8. Indeed preview — public search (often blocked)

Target: 10,000+ real job postings per analysis run.
"""

import asyncio
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from html import unescape
from hashlib import md5

import httpx
from bs4 import BeautifulSoup

FALLBACK_DATA = Path(__file__).parent.parent / "data" / "job_postings.json"
HN_SEMAPHORE = asyncio.Semaphore(5)


@dataclass
class JobPosting:
    title: str
    company: str
    location: str
    description: str
    skills: list[str]
    tools: list[str]
    experience_level: str
    source: str
    source_url: str
    scraped_at: str


SKILL_TAXONOMY = {
    "languages": [
        "Python", "JavaScript", "TypeScript", "Rust", "Go", "Java", "C++",
        "C#", "Kotlin", "Swift", "Ruby", "Scala", "R", "Julia", "Zig",
        "MATLAB", "Solidity", "Verilog", "VHDL", "SystemVerilog",
        "LabVIEW", "Fortran",
    ],
    "ai_ml": [
        "machine learning", "deep learning", "NLP", "computer vision",
        "reinforcement learning", "LLM", "large language model",
        "generative AI", "agentic AI", "AI agents", "prompt engineering",
        "RAG", "retrieval augmented generation", "fine-tuning",
        "transformer", "diffusion model", "MLOps",
    ],
    "data": [
        "SQL", "NoSQL", "PostgreSQL", "MongoDB", "Redis", "Elasticsearch",
        "vector database", "Pinecone", "Weaviate", "ChromaDB", "Milvus",
        "Oracle", "data pipeline", "ETL", "Apache Kafka", "Apache Spark",
        "dbt", "Snowflake", "BigQuery", "data engineering",
    ],
    "cloud_infra": [
        "AWS", "Azure", "GCP", "Oracle Cloud", "OCI", "Docker", "Kubernetes",
        "Terraform", "CI/CD", "serverless", "microservices",
    ],
    "web": [
        "React", "Next.js", "Vue", "Angular", "Node.js", "FastAPI",
        "Django", "Flask", "GraphQL", "REST API", "WebSocket",
    ],
    "security": [
        "cybersecurity", "penetration testing", "zero trust",
        "encryption", "IAM", "SOC", "SIEM",
    ],
    "hardware_embedded": [
        "embedded systems", "firmware", "FPGA", "ASIC", "VLSI",
        "microcontroller", "ARM", "RISC-V", "PCB design", "circuit design",
        "RTL", "logic design", "signal processing", "DSP",
        "oscilloscope", "JTAG", "SPI", "I2C", "UART", "CAN bus",
        "RTOS", "bare metal", "device driver", "hardware verification",
        "SystemVerilog", "Verilog", "VHDL", "Cadence", "Synopsys",
        "Xilinx", "Quartus", "Altium", "KiCad",
    ],
    "electrical_power": [
        "power electronics", "power systems", "RF design", "antenna design",
        "electromagnetics", "photonics", "optics", "semiconductor",
        "analog design", "mixed signal", "communications systems",
        "5G", "6G", "telecommunications", "radar", "LiDAR",
        "battery management", "motor control", "inverter",
        "solar", "wind energy", "smart grid",
    ],
    "mechanical_manufacturing": [
        "CAD", "SolidWorks", "CATIA", "AutoCAD", "ANSYS", "COMSOL",
        "finite element", "FEA", "CFD", "Simulink",
        "3D printing", "additive manufacturing", "CNC", "GD&T",
        "thermodynamics", "heat transfer", "fluid mechanics",
        "mechanical design", "injection molding", "die casting",
        "HVAC", "vibration analysis", "fatigue analysis",
        "manufacturing", "lean manufacturing", "six sigma",
        "PLC", "SCADA", "hydraulics", "pneumatics",
    ],
    "biomedical": [
        "biomedical", "medical device", "FDA", "biocompatibility",
        "tissue engineering", "biomechanics", "biomaterials",
        "prosthetics", "imaging", "MRI", "CT scan", "ultrasound",
        "regulatory affairs", "clinical trials", "GMP",
        "bioinformatics", "genomics", "CRISPR",
    ],
    "civil_environmental": [
        "structural analysis", "structural design", "geotechnical",
        "transportation", "water resources", "environmental",
        "surveying", "GIS", "BIM", "Revit", "SAP2000",
        "concrete design", "steel design", "seismic analysis",
        "hydrology", "wastewater", "sustainability",
        "construction management", "project management",
    ],
    "chemical_process": [
        "process engineering", "reactor design", "distillation",
        "heat exchanger", "mass transfer", "thermodynamics",
        "ASPEN Plus", "HYSYS", "process control",
        "polymer", "catalysis", "corrosion", "separation processes",
        "pharmaceutical", "biotechnology", "fermentation",
    ],
    "aerospace_defense": [
        "aerodynamics", "propulsion", "orbital mechanics",
        "flight dynamics", "avionics", "composites",
        "wind tunnel", "rocket", "satellite", "spacecraft",
        "flight control", "navigation", "guidance",
        "defense", "unmanned systems", "UAV", "drone",
    ],
    "robotics_controls": [
        "robotics", "ROS", "control systems", "SLAM",
        "motion planning", "kinematics", "dynamics",
        "sensor fusion", "autonomous systems", "perception",
        "actuators", "servo", "PID control",
        "computer vision", "path planning",
    ],
    "operations_analytics": [
        "operations research", "supply chain", "logistics",
        "optimization", "simulation", "queuing theory",
        "lean", "six sigma", "quality control",
        "ergonomics", "human factors", "Tableau", "Power BI",
        "statistical analysis", "forecasting",
    ],
    "emerging_2026": [
        "agentic AI", "AI agents", "multi-agent systems",
        "vector database", "vector search", "RAG",
        "Rust", "memory-safe programming",
        "LLM orchestration", "LangChain", "LlamaIndex", "CrewAI",
        "edge AI", "on-device ML", "federated learning",
        "quantum computing", "post-quantum cryptography",
        "Web3", "blockchain", "digital twin",
        "autonomous systems", "sustainability", "green engineering",
    ],
}

ALL_SKILLS = set()
for category_skills in SKILL_TAXONOMY.values():
    for s in category_skills:
        ALL_SKILLS.add(s.lower())


async def scrape_job_postings(search_queries: list[str] | None = None) -> list[JobPosting]:
    """
    Scrape 10,000+ real job postings from multiple public sources.
    search_queries: custom queries based on the selected major's relevant job titles.
    """
    if search_queries is None:
        search_queries = ["software engineer", "data engineer", "AI engineer"]

    postings: list[JobPosting] = []
    sources_tried = []
    sources_succeeded = []

    # Source 1: HN ALL "Who's Hiring" threads (primary volume — thousands of postings)
    try:
        sources_tried.append("hn_hiring_all")
        hn_results = await _scrape_hn_all_hiring_threads(search_queries)
        postings.extend(hn_results)
        if hn_results:
            sources_succeeded.append(f"hn_hiring_all ({len(hn_results)})")
    except Exception as e:
        print(f"[HN All Hiring] Failed: {e}")

    # Source 2: RemoteOK (free, no auth, always works)
    try:
        sources_tried.append("remoteok")
        remoteok_results = await _scrape_remoteok(search_queries)
        postings.extend(remoteok_results)
        if remoteok_results:
            sources_succeeded.append(f"remoteok ({len(remoteok_results)})")
    except Exception as e:
        print(f"[RemoteOK] Failed: {e}")

    # Source 3: Arbeitnow (free JSON API, remote/hybrid jobs)
    try:
        sources_tried.append("arbeitnow")
        arbeitnow_results = await _scrape_arbeitnow(search_queries)
        postings.extend(arbeitnow_results)
        if arbeitnow_results:
            sources_succeeded.append(f"arbeitnow ({len(arbeitnow_results)})")
    except Exception as e:
        print(f"[Arbeitnow] Failed: {e}")

    # Source 4: Jobicy (free JSON API, remote tech jobs)
    try:
        sources_tried.append("jobicy")
        jobicy_results = await _scrape_jobicy(search_queries)
        postings.extend(jobicy_results)
        if jobicy_results:
            sources_succeeded.append(f"jobicy ({len(jobicy_results)})")
    except Exception as e:
        print(f"[Jobicy] Failed: {e}")

    # Source 5: LinkedIn via Google — search ALL queries (not just first 4)
    try:
        sources_tried.append("linkedin")
        linkedin_results = await _scrape_linkedin_via_google(search_queries)
        postings.extend(linkedin_results)
        if linkedin_results:
            sources_succeeded.append(f"linkedin ({len(linkedin_results)})")
    except Exception as e:
        print(f"[LinkedIn] Failed: {e}")

    # Source 6: Glassdoor via Google
    try:
        sources_tried.append("glassdoor")
        glassdoor_results = await _scrape_jobs_via_google(
            search_queries, "glassdoor.com/job-listing", "glassdoor"
        )
        postings.extend(glassdoor_results)
        if glassdoor_results:
            sources_succeeded.append(f"glassdoor ({len(glassdoor_results)})")
    except Exception as e:
        print(f"[Glassdoor] Failed: {e}")

    # Source 7: Greenhouse jobs via Google
    try:
        sources_tried.append("greenhouse")
        gh_results = await _scrape_jobs_via_google(
            search_queries, "boards.greenhouse.io", "greenhouse"
        )
        postings.extend(gh_results)
        if gh_results:
            sources_succeeded.append(f"greenhouse ({len(gh_results)})")
    except Exception as e:
        print(f"[Greenhouse] Failed: {e}")

    # Source 8: Indeed preview (may be blocked)
    try:
        sources_tried.append("indeed")
        indeed_results = await _scrape_indeed_preview(search_queries)
        postings.extend(indeed_results)
        if indeed_results:
            sources_succeeded.append(f"indeed ({len(indeed_results)})")
    except Exception as e:
        print(f"[Indeed] Failed: {e}")

    # Source 9: Google Jobs search — broad search with each query directly
    try:
        sources_tried.append("google_jobs")
        gj_results = await _scrape_google_jobs(search_queries)
        postings.extend(gj_results)
        if gj_results:
            sources_succeeded.append(f"google_jobs ({len(gj_results)})")
    except Exception as e:
        print(f"[Google Jobs] Failed: {e}")

    postings = _deduplicate(postings)

    print(f"[Job Scraper] Sources tried: {sources_tried}")
    print(f"[Job Scraper] Sources succeeded: {sources_succeeded}")
    print(f"[Job Scraper] Total postings (deduplicated): {len(postings)}")

    if not postings:
        print("[Job Scraper] All sources failed, using seed data")
        postings = _get_seed_postings()

    _save_cache(postings)
    return postings


def _deduplicate(postings: list[JobPosting]) -> list[JobPosting]:
    """Remove exact duplicate postings (same title + company + description snippet)."""
    seen: set[str] = set()
    unique: list[JobPosting] = []
    for p in postings:
        desc_snippet = p.description[:200].lower().strip()
        key = md5(f"{p.title.lower().strip()}|{p.company.lower().strip()}|{desc_snippet}".encode()).hexdigest()
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


async def _scrape_remoteok(queries: list[str]) -> list[JobPosting]:
    """
    RemoteOK has a free public JSON API at https://remoteok.com/api
    Returns real, current job postings. No auth needed.
    """
    results = []
    async with httpx.AsyncClient(
        timeout=15,
        headers={
            "User-Agent": "MarketSyncAI/1.0 (Curriculum Analysis Research)",
        },
    ) as client:
        resp = await client.get("https://remoteok.com/api")
        if resp.status_code != 200:
            return results

        data = resp.json()
        if not isinstance(data, list) or len(data) < 2:
            return results

        query_phrases, keywords = _build_match_terms(queries)

        for item in data[1:]:
            title = item.get("position", "")
            company = item.get("company", "Unknown")
            description = item.get("description", "")
            tags = item.get("tags", [])
            url = item.get("url", "")
            date = item.get("date", "")
            location = item.get("location", "Remote")

            if description:
                description = unescape(description)
                description = re.sub(r"<[^>]+>", " ", description)
                description = re.sub(r"\s+", " ", description).strip()

            combined = f"{title} {description} {' '.join(tags)}".lower()

            relevant = (
                any(phrase in combined for phrase in query_phrases)
                or any(kw in combined for kw in keywords)
                or not queries
            )
            if not relevant:
                continue

            skills = _extract_skills(combined)
            tools = _extract_tools(combined)

            results.append(JobPosting(
                title=title,
                company=company,
                location=location or "Remote",
                description=description[:2000],
                skills=skills,
                tools=tools,
                experience_level=_infer_level(title, description),
                source="remoteok",
                source_url=f"https://remoteok.com{url}" if url else "https://remoteok.com",
                scraped_at=datetime.utcnow().isoformat(),
            ))

    return results


_GENERIC_WORDS = {
    "engineer", "engineering", "developer", "scientist", "analyst",
    "manager", "designer", "architect", "specialist", "technician",
    "officer", "lead", "senior", "junior", "staff", "principal",
    "systems", "system", "design", "data", "machine", "learning",
    "computer", "processing", "control", "signal", "power",
    "communications", "site", "full", "stack", "intelligence",
    "operations", "process", "applied", "research", "science",
    "digital", "advanced", "general", "remote", "hybrid",
}


def _build_match_terms(queries: list[str]) -> tuple[list[str], set[str]]:
    """Build phrase list AND distinctive keywords from query phrases.

    Phrases are matched as-is (multi-word).  Keywords are single
    distinctive words that strongly signal the major — generic terms
    like "systems", "data", "design" are excluded so they don't
    cause every job to match every major.
    """
    phrases = [q.lower().strip() for q in queries]
    keywords = set()
    for q in queries:
        for word in q.lower().split():
            if word not in _GENERIC_WORDS and len(word) >= 4:
                keywords.add(word)
    return phrases, keywords


async def _scrape_hn_all_hiring_threads(queries: list[str]) -> list[JobPosting]:
    """
    Scrape ALL HN 'Who is Hiring?' threads from 2023-2026.
    Matches posts that contain any query phrase OR distinctive keyword.
    """
    results = []
    query_phrases, distinctive_keywords = _build_match_terms(queries)

    async with httpx.AsyncClient(timeout=30) as client:
        search_resp = await client.get(
            "https://hn.algolia.com/api/v1/search",
            params={
                "query": '"Ask HN: Who is hiring?"',
                "tags": "story",
                "hitsPerPage": 50,
                "numericFilters": "created_at_i>1672531200",
            },
        )
        if search_resp.status_code != 200:
            print(f"[HN All] Search failed: HTTP {search_resp.status_code}")
            return results

        stories = search_resp.json().get("hits", [])
        hiring_stories = [
            s for s in stories
            if "who is hiring" in s.get("title", "").lower()
            and "ask hn" in s.get("title", "").lower()
        ]

        print(f"[HN All] Found {len(hiring_stories)} 'Who is Hiring' threads")

        async def _fetch_thread(story):
            async with HN_SEMAPHORE:
                story_id = story["objectID"]
                thread_title = story.get("title", "")
                try:
                    resp = await client.get(
                        f"https://hn.algolia.com/api/v1/items/{story_id}"
                    )
                    if resp.status_code != 200:
                        return []

                    children = resp.json().get("children", [])
                    thread_results = []

                    for comment in children:
                        text = comment.get("text", "")
                        if not text or len(text) < 50:
                            continue

                        clean_text = unescape(text)
                        clean_text = re.sub(r"<[^>]+>", "\n", clean_text)
                        clean_text = re.sub(r"\s+", " ", clean_text).strip()

                        lines = clean_text.split("\n")
                        first_line = lines[0] if lines else clean_text[:100]

                        company = "Unknown"
                        company_match = re.match(r"^([^|]+)\|", first_line)
                        if company_match:
                            company = company_match.group(1).strip()

                        job_title = "Software Engineer"
                        title_patterns = [
                            r"(?:hiring|looking for|seeking)\s+(?:a\s+)?(.+?)(?:\.|,|\||$)",
                            r"^[^|]+\|\s*(.+?)(?:\||$)",
                        ]
                        for pat in title_patterns:
                            m = re.search(pat, first_line, re.IGNORECASE)
                            if m:
                                job_title = m.group(1).strip()[:80]
                                break

                        location = "Remote"
                        loc_match = re.search(
                            r"(?:remote|onsite|hybrid|location)[:\s]*([^|,\n]+)",
                            clean_text, re.IGNORECASE,
                        )
                        if loc_match:
                            location = loc_match.group(1).strip()[:60]

                        lower_text = clean_text.lower()
                        relevant = (
                            any(phrase in lower_text for phrase in query_phrases)
                            or any(kw in lower_text for kw in distinctive_keywords)
                        )
                        if not relevant:
                            continue

                        skills = _extract_skills(lower_text)
                        tools = _extract_tools(lower_text)

                        thread_results.append(JobPosting(
                            title=job_title,
                            company=company,
                            location=location,
                            description=clean_text[:2000],
                            skills=skills,
                            tools=tools,
                            experience_level=_infer_level(job_title, clean_text),
                            source="hackernews",
                            source_url=f"https://news.ycombinator.com/item?id={comment.get('id', story_id)}",
                            scraped_at=datetime.utcnow().isoformat(),
                        ))

                    print(f"[HN All] {thread_title}: {len(thread_results)} postings from {len(children)} comments")
                    return thread_results

                except Exception as e:
                    print(f"[HN All] Error fetching thread {story_id}: {e}")
                    return []

        thread_tasks = [_fetch_thread(story) for story in hiring_stories]
        thread_results = await asyncio.gather(*thread_tasks)

        for batch in thread_results:
            results.extend(batch)

    print(f"[HN All] Total from all threads: {len(results)}")
    return results


async def _scrape_arbeitnow(queries: list[str]) -> list[JobPosting]:
    """Arbeitnow free JSON API — remote/hybrid tech jobs, paginated."""
    results = []

    query_phrases, keywords = _build_match_terms(queries)

    async with httpx.AsyncClient(timeout=15) as client:
        for page in range(1, 11):
            try:
                resp = await client.get(
                    "https://www.arbeitnow.com/api/job-board-api",
                    params={"page": page},
                )
                if resp.status_code != 200:
                    break

                data = resp.json()
                jobs = data.get("data", [])
                if not jobs:
                    break

                for job in jobs:
                    title = job.get("title", "")
                    company = job.get("company_name", "Unknown")
                    location = job.get("location", "Remote")
                    description = job.get("description", "")
                    tags = job.get("tags", [])

                    if description:
                        description = re.sub(r"<[^>]+>", " ", description)
                        description = re.sub(r"\s+", " ", description).strip()

                    combined = f"{title} {description} {' '.join(tags)}".lower()
                    if not (any(phrase in combined for phrase in query_phrases)
                            or any(kw in combined for kw in keywords)):
                        continue

                    skills = _extract_skills(combined)
                    tools = _extract_tools(combined)

                    results.append(JobPosting(
                        title=title,
                        company=company,
                        location=location,
                        description=description[:2000],
                        skills=skills,
                        tools=tools,
                        experience_level=_infer_level(title, description),
                        source="arbeitnow",
                        source_url=job.get("url", "https://www.arbeitnow.com"),
                        scraped_at=datetime.utcnow().isoformat(),
                    ))

            except Exception:
                break

            await asyncio.sleep(0.5)

    return results


async def _scrape_jobicy(queries: list[str]) -> list[JobPosting]:
    """Jobicy free JSON API — remote tech jobs."""
    results = []

    query_phrases, keywords = _build_match_terms(queries)

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                "https://jobicy.com/api/v2/remote-jobs",
                params={"count": 50, "geo": "usa", "industry": "tech"},
            )
            if resp.status_code != 200:
                return results

            data = resp.json()
            jobs = data.get("jobs", [])

            for job in jobs:
                title = job.get("jobTitle", "")
                company = job.get("companyName", "Unknown")
                location = job.get("jobGeo", "Remote")
                description = job.get("jobDescription", "")
                job_type = job.get("jobType", "")

                if description:
                    description = re.sub(r"<[^>]+>", " ", description)
                    description = re.sub(r"\s+", " ", description).strip()

                combined = f"{title} {description} {job_type}".lower()
                if not (any(phrase in combined for phrase in query_phrases)
                        or any(kw in combined for kw in keywords)):
                    continue

                skills = _extract_skills(combined)
                tools = _extract_tools(combined)

                results.append(JobPosting(
                    title=title,
                    company=company,
                    location=location,
                    description=description[:2000],
                    skills=skills,
                    tools=tools,
                    experience_level=_infer_level(title, description),
                    source="jobicy",
                    source_url=job.get("url", "https://jobicy.com"),
                    scraped_at=datetime.utcnow().isoformat(),
                ))

        except Exception:
            pass

    return results


async def _scrape_linkedin_via_google(queries: list[str]) -> list[JobPosting]:
    """
    Scrape LinkedIn job postings through Google Search.

    LinkedIn public job listings are indexed by Google. We search
    Google for 'site:linkedin.com/jobs "job title"' and parse the
    results. This is legal — we're reading Google's index, not
    scraping LinkedIn directly.
    """
    results = []

    async with httpx.AsyncClient(
        timeout=15,
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        },
    ) as client:
        for query in queries[:8]:
            google_query = f'site:linkedin.com/jobs "{query}" 2026'
            url = f"https://www.google.com/search?q={google_query.replace(' ', '+')}&num=15"

            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "lxml")

                for g_div in soup.select("div.g, div[data-hveid]"):
                    link_el = g_div.select_one("a[href*='linkedin.com/jobs']")
                    if not link_el:
                        continue

                    href = link_el.get("href", "")
                    if "linkedin.com/jobs" not in href:
                        continue

                    title_el = g_div.select_one("h3")
                    snippet_el = g_div.select_one(
                        "div[data-sncf], div.VwiC3b, span.aCOpRe, div[style='-webkit-line-clamp:2']"
                    )

                    if not title_el:
                        continue

                    raw_title = title_el.get_text(strip=True)

                    job_title = raw_title
                    company = "Unknown"
                    location = "Unknown"

                    for sep in [" - ", " | ", " at ", " – "]:
                        if sep in raw_title:
                            parts = raw_title.split(sep)
                            job_title = parts[0].strip()
                            if len(parts) > 1:
                                company = parts[1].strip()
                            if len(parts) > 2:
                                location = parts[2].strip()
                            break

                    job_title = re.sub(
                        r"\s*\|?\s*LinkedIn\s*$", "", job_title, flags=re.IGNORECASE
                    ).strip()
                    company = re.sub(
                        r"\s*\|?\s*LinkedIn\s*$", "", company, flags=re.IGNORECASE
                    ).strip()

                    description = ""
                    if snippet_el:
                        description = snippet_el.get_text(" ", strip=True)

                    combined = f"{job_title} {description} {company}".lower()
                    skills = _extract_skills(combined)
                    tools = _extract_tools(combined)

                    results.append(JobPosting(
                        title=job_title[:200],
                        company=company[:200],
                        location=location[:200],
                        description=description[:1500],
                        skills=skills,
                        tools=tools,
                        experience_level=_infer_level(job_title, description),
                        source="linkedin",
                        source_url=href,
                        scraped_at=datetime.utcnow().isoformat(),
                    ))

            except httpx.HTTPError:
                continue

            await asyncio.sleep(1.5)

    return results


async def _scrape_jobs_via_google(
    queries: list[str], site_domain: str, source_name: str
) -> list[JobPosting]:
    """
    Generic Google search scraper for job boards.
    Searches Google for site:<domain> "<query>" and parses the results.
    Works for Glassdoor, Greenhouse, Wellfound, etc.
    """
    results = []

    async with httpx.AsyncClient(
        timeout=15,
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        },
    ) as client:
        for query in queries[:6]:
            google_query = f'site:{site_domain} "{query}" 2025 OR 2026'
            url = f"https://www.google.com/search?q={google_query.replace(' ', '+')}&num=15"

            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "lxml")

                for g_div in soup.select("div.g, div[data-hveid]"):
                    link_el = g_div.select_one("a")
                    if not link_el:
                        continue

                    href = link_el.get("href", "")
                    if site_domain not in href:
                        continue

                    title_el = g_div.select_one("h3")
                    snippet_el = g_div.select_one(
                        "div[data-sncf], div.VwiC3b, span.aCOpRe"
                    )

                    if not title_el:
                        continue

                    raw_title = title_el.get_text(strip=True)
                    job_title = raw_title
                    company = "Unknown"
                    location = "Unknown"

                    for sep in [" - ", " | ", " at ", " – ", " — "]:
                        if sep in raw_title:
                            parts = raw_title.split(sep)
                            job_title = parts[0].strip()
                            if len(parts) > 1:
                                company = parts[1].strip()
                            if len(parts) > 2:
                                location = parts[2].strip()
                            break

                    for noise in [source_name, "Glassdoor", "Greenhouse", "Wellfound"]:
                        job_title = re.sub(
                            rf"\s*\|?\s*{noise}\s*$", "", job_title, flags=re.IGNORECASE
                        ).strip()
                        company = re.sub(
                            rf"\s*\|?\s*{noise}\s*$", "", company, flags=re.IGNORECASE
                        ).strip()

                    description = ""
                    if snippet_el:
                        description = snippet_el.get_text(" ", strip=True)

                    combined = f"{job_title} {description} {company}".lower()
                    skills = _extract_skills(combined)
                    tools = _extract_tools(combined)

                    results.append(JobPosting(
                        title=job_title[:200],
                        company=company[:200],
                        location=location[:200],
                        description=description[:1500],
                        skills=skills,
                        tools=tools,
                        experience_level=_infer_level(job_title, description),
                        source=source_name,
                        source_url=href,
                        scraped_at=datetime.utcnow().isoformat(),
                    ))

            except httpx.HTTPError:
                continue

            await asyncio.sleep(1.5)

    return results


async def _scrape_indeed_preview(queries: list[str]) -> list[JobPosting]:
    """Attempt to scrape Indeed public search. Often blocked but worth trying."""
    results = []

    async with httpx.AsyncClient(
        timeout=15,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
    ) as client:
        for query in queries[:3]:
            q = query.replace(" ", "+")
            url = f"https://www.indeed.com/jobs?q={q}&l=United+States&sort=date&fromage=7"
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "lxml")
                cards = soup.select(".job_seen_beacon, .jobsearch-ResultsList > li")

                for card in cards[:10]:
                    title_el = card.select_one("h2 a, .jobTitle a, h2 span")
                    company_el = card.select_one("[data-testid='company-name'], .companyName")
                    location_el = card.select_one("[data-testid='text-location'], .companyLocation")
                    desc_el = card.select_one(".job-snippet, td.snip")

                    if not title_el:
                        continue

                    title = title_el.get_text(strip=True)
                    company = company_el.get_text(strip=True) if company_el else "Unknown"
                    location = location_el.get_text(strip=True) if location_el else "Remote"
                    description = desc_el.get_text(" ", strip=True) if desc_el else ""

                    skills = _extract_skills(f"{title} {description}")
                    tools = _extract_tools(f"{title} {description}")

                    results.append(JobPosting(
                        title=title, company=company, location=location,
                        description=description[:1500], skills=skills, tools=tools,
                        experience_level=_infer_level(title, description),
                        source="indeed", source_url=url,
                        scraped_at=datetime.utcnow().isoformat(),
                    ))
            except httpx.HTTPError:
                continue

    return results


async def _scrape_google_jobs(queries: list[str]) -> list[JobPosting]:
    """Search Google for job postings with each query phrase directly.
    Uses Google News RSS to find recent job-related articles and postings."""
    results = []

    async with httpx.AsyncClient(timeout=15) as client:
        for query in queries[:8]:
            gquery = f'{query}+jobs+hiring+2026'
            url = f"https://news.google.com/rss/search?q={gquery.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue

                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.text)
                for item in root.findall(".//item")[:8]:
                    title = item.findtext("title", "")
                    link = item.findtext("link", "")
                    pub_date = item.findtext("pubDate", "")
                    description = item.findtext("description", "")

                    clean_desc = re.sub(r"<[^>]+>", " ", description or "")
                    clean_desc = re.sub(r"\s+", " ", clean_desc).strip()

                    combined = f"{title} {clean_desc}".lower()
                    skills = _extract_skills(combined)
                    tools = _extract_tools(combined)

                    job_title = query
                    company = "Various"
                    for sep in [" - ", " | ", " at "]:
                        if sep in title:
                            parts = title.split(sep)
                            job_title = parts[0].strip()
                            if len(parts) > 1:
                                company = parts[1].strip()
                            break

                    results.append(JobPosting(
                        title=job_title[:200],
                        company=company[:200],
                        location="Various",
                        description=clean_desc[:2000],
                        skills=skills,
                        tools=tools,
                        experience_level=_infer_level(title, clean_desc),
                        source="google_jobs",
                        source_url=link,
                        scraped_at=datetime.utcnow().isoformat(),
                    ))
            except Exception:
                continue
            await asyncio.sleep(0.5)

    return results


_SHORT_SKILLS = {s for s in ALL_SKILLS if len(s) <= 3}
_LONG_SKILLS = ALL_SKILLS - _SHORT_SKILLS

import re as _re
_SHORT_SKILL_PATTERNS = {
    s: _re.compile(rf"\b{_re.escape(s)}\b", _re.IGNORECASE)
    for s in _SHORT_SKILLS
}


def _extract_skills(text: str) -> list[str]:
    found = []
    lower = text.lower()
    for skill in _LONG_SKILLS:
        if skill in lower:
            found.append(skill)
    for skill, pattern in _SHORT_SKILL_PATTERNS.items():
        if pattern.search(text):
            found.append(skill)
    return list(set(found))


def _extract_tools(text: str) -> list[str]:
    tool_patterns = [
        "Docker", "Kubernetes", "Git", "Jenkins", "Terraform",
        "Ansible", "Prometheus", "Grafana", "Jira", "Figma",
        "VS Code", "IntelliJ", "PyTorch", "TensorFlow", "Hugging Face",
        "LangChain", "LlamaIndex", "Weights & Biases", "MLflow",
        "Airflow", "dbt", "Tableau", "Power BI",
        "SolidWorks", "CATIA", "AutoCAD", "ANSYS", "COMSOL",
        "Simulink", "LabVIEW", "ROS", "Gazebo",
        "Cadence", "Synopsys", "Xilinx", "Quartus", "Altium", "KiCad",
        "HSPICE", "ModelSim", "Vivado",
        "Abaqus", "Nastran", "Creo", "NX", "Inventor",
        "ASPEN Plus", "HYSYS", "ChemCAD",
        "SAP2000", "ETABS", "Revit", "Civil 3D",
        "STK", "GMAT",
    ]
    found = []
    lower = text if text == text.lower() else text.lower()
    for tool in tool_patterns:
        if tool.lower() in lower:
            found.append(tool)
    return list(set(found))


def _infer_level(title: str, desc: str) -> str:
    combined = f"{title} {desc}".lower()
    if any(w in combined for w in ["senior", "sr.", "lead", "principal", "staff"]):
        return "senior"
    if any(w in combined for w in ["junior", "jr.", "entry", "new grad", "intern"]):
        return "entry"
    return "mid"


# Category-level filtering per major (excludes "languages" for non-CS majors
# because the full languages list includes web/app languages irrelevant to hardware).
MAJOR_RELEVANT_CATEGORIES: dict[str, set[str]] = {
    "cs":      {"languages", "ai_ml", "data", "cloud_infra", "web", "security", "emerging_2026"},
    "ds":      {"languages", "ai_ml", "data", "cloud_infra", "emerging_2026"},
    "ce":      {"hardware_embedded", "robotics_controls", "emerging_2026"},
    "ee":      {"electrical_power", "hardware_embedded", "robotics_controls", "emerging_2026"},
    "me":      {"mechanical_manufacturing", "robotics_controls", "emerging_2026"},
    "bme":     {"biomedical", "ai_ml", "data", "emerging_2026"},
    "cee":     {"civil_environmental", "data", "emerging_2026"},
    "cheme":   {"chemical_process", "data", "emerging_2026"},
    "aero":    {"aerospace_defense", "mechanical_manufacturing", "robotics_controls", "emerging_2026"},
    "ioe":     {"operations_analytics", "ai_ml", "data", "emerging_2026"},
    "matscie": {"mechanical_manufacturing", "chemical_process", "emerging_2026"},
    "name":    {"mechanical_manufacturing", "aerospace_defense", "robotics_controls", "emerging_2026"},
    "ners":    {"chemical_process", "mechanical_manufacturing", "data", "emerging_2026"},
    "climate": {"data", "ai_ml", "emerging_2026"},
    "rob":     {"robotics_controls", "ai_ml", "hardware_embedded", "emerging_2026"},
}

# Per-major extra individual skills to include (languages + tools actually used
# in that discipline), on top of the category filter above.
MAJOR_EXTRA_SKILLS: dict[str, set[str]] = {
    "cs":      set(),  # already has full "languages" category
    "ds":      set(),  # already has full "languages" category
    "ce":      {"python", "c++", "c", "matlab", "rust", "verilog", "vhdl", "systemverilog"},
    "ee":      {"python", "c++", "c", "matlab", "verilog", "vhdl", "systemverilog", "labview", "fortran"},
    "me":      {"python", "c++", "matlab", "fortran", "labview"},
    "bme":     {"python", "r", "matlab", "java", "c++"},
    "cee":     {"python", "r", "matlab", "c++", "fortran"},
    "cheme":   {"python", "matlab", "r", "fortran"},
    "aero":    {"python", "c++", "matlab", "fortran", "julia"},
    "ioe":     {"python", "r", "java", "sql", "julia", "matlab"},
    "matscie": {"python", "matlab", "r", "fortran"},
    "name":    {"python", "matlab", "c++", "fortran"},
    "ners":    {"python", "matlab", "fortran", "c++"},
    "climate": {"python", "r", "julia", "matlab", "fortran"},
    "rob":     {"python", "c++", "rust", "julia", "matlab", "ros"},
}


# Curated top industry skills per major (2026 market data).
# Used to rank and weight extracted skills so the display reflects
# the actual demand landscape, not just the raw scrape pool.
INDUSTRY_TOP_SKILLS: dict[str, list[str]] = {
    "cs": [
        "python", "typescript", "react", "aws", "docker", "kubernetes",
        "machine learning", "rust", "go", "java", "postgresql", "terraform",
        "llm", "ci/cd", "generative ai", "node.js", "next.js", "graphql",
        "redis", "gcp", "azure", "sql", "mongodb", "microservices",
        "agentic ai", "rag", "deep learning", "javascript", "c++", "scala",
    ],
    "ds": [
        "python", "sql", "r", "machine learning", "deep learning",
        "tensorflow", "pytorch", "postgresql", "apache spark", "llm",
        "data pipeline", "etl", "snowflake", "bigquery", "tableau",
        "aws", "docker", "generative ai", "rag", "nlp",
        "julia", "pandas", "dbt", "apache kafka", "mlops",
        "statistical analysis", "forecasting", "power bi", "java", "scala",
    ],
    "ce": [
        "verilog", "systemverilog", "vhdl", "fpga", "asic", "c++",
        "python", "embedded systems", "firmware", "rtl", "arm", "risc-v",
        "pcb design", "signal processing", "rtos", "device driver",
        "logic design", "cadence", "synopsys", "matlab",
        "hardware verification", "spi", "i2c", "uart", "can bus",
        "xilinx", "quartus", "bare metal", "microcontroller", "jtag",
    ],
    "ee": [
        "matlab", "python", "verilog", "vhdl", "power electronics",
        "rf design", "analog design", "signal processing", "c++",
        "semiconductor", "pcb design", "labview", "5g", "antenna design",
        "fpga", "mixed signal", "photonics", "electromagnetics",
        "communications systems", "power systems", "motor control",
        "battery management", "solar", "radar", "lidar",
        "smart grid", "dsp", "altium", "kicad", "cadence",
    ],
    "me": [
        "solidworks", "catia", "autocad", "ansys", "matlab", "python",
        "finite element", "cfd", "simulink", "3d printing",
        "thermodynamics", "heat transfer", "fluid mechanics", "gd&t",
        "cnc", "manufacturing", "lean manufacturing", "six sigma",
        "mechanical design", "hvac", "plc", "comsol",
        "vibration analysis", "fatigue analysis", "cad",
        "injection molding", "hydraulics", "pneumatics", "robotics", "c++",
    ],
    "bme": [
        "python", "matlab", "r", "medical device", "fda",
        "biocompatibility", "tissue engineering", "biomechanics",
        "imaging", "mri", "ultrasound", "machine learning",
        "bioinformatics", "genomics", "regulatory affairs",
        "clinical trials", "gmp", "biomaterials", "prosthetics",
        "deep learning", "ct scan", "crispr", "java", "c++",
        "sql", "data pipeline", "biomedical", "statistical analysis",
        "computer vision", "generative ai",
    ],
    "cee": [
        "autocad", "revit", "python", "structural analysis", "gis",
        "bim", "matlab", "sap2000", "geotechnical", "hydrology",
        "concrete design", "steel design", "seismic analysis",
        "water resources", "environmental", "transportation",
        "construction management", "project management", "sustainability",
        "r", "surveying", "wastewater", "sql", "structural design",
        "statistical analysis", "fortran", "c++", "data pipeline",
        "remote sensing", "digital twin",
    ],
    "cheme": [
        "aspen plus", "hysys", "matlab", "python", "process engineering",
        "reactor design", "process control", "distillation",
        "heat exchanger", "mass transfer", "thermodynamics",
        "polymer", "catalysis", "pharmaceutical", "biotechnology",
        "fermentation", "separation processes", "corrosion",
        "r", "six sigma", "lean manufacturing", "sql",
        "data pipeline", "statistical analysis", "sustainability",
        "manufacturing", "fortran", "digital twin", "simulation",
        "machine learning",
    ],
    "aero": [
        "matlab", "python", "ansys", "catia", "solidworks",
        "aerodynamics", "propulsion", "flight dynamics", "avionics",
        "composites", "cfd", "simulink", "c++", "fortran",
        "orbital mechanics", "wind tunnel", "satellite", "spacecraft",
        "flight control", "navigation", "guidance", "defense",
        "uav", "drone", "unmanned systems", "rocket",
        "finite element", "digital twin", "autonomous systems",
        "robotics",
    ],
    "ioe": [
        "python", "r", "sql", "operations research", "supply chain",
        "optimization", "simulation", "machine learning", "tableau",
        "power bi", "lean", "six sigma", "quality control",
        "ergonomics", "human factors", "statistical analysis",
        "forecasting", "data pipeline", "java", "matlab",
        "logistics", "queuing theory", "apache spark",
        "bigquery", "postgresql", "julia", "aws",
        "generative ai", "llm", "deep learning",
    ],
    "rob": [
        "python", "c++", "ros", "matlab", "robotics", "slam",
        "computer vision", "machine learning", "control systems",
        "motion planning", "sensor fusion", "deep learning",
        "perception", "autonomous systems", "path planning",
        "kinematics", "dynamics", "rust", "embedded systems",
        "firmware", "rtos", "pid control", "actuators",
        "lidar", "reinforcement learning", "edge ai",
        "generative ai", "julia", "fpga", "arm",
    ],
    "matscie": [
        "matlab", "python", "ansys", "comsol", "thermodynamics",
        "finite element", "solidworks", "manufacturing", "3d printing",
        "additive manufacturing", "polymer", "catalysis",
        "corrosion", "r", "machine learning", "cad",
        "six sigma", "lean manufacturing", "fortran",
        "sustainability", "digital twin", "simulation",
        "crystallography", "spectroscopy", "statistical analysis",
        "c++", "semiconductor", "biomaterials", "cnc", "heat transfer",
    ],
    "name": [
        "matlab", "python", "ansys", "solidworks", "cfd",
        "fluid mechanics", "thermodynamics", "finite element",
        "catia", "simulink", "composites", "manufacturing",
        "marine systems", "propulsion", "c++", "fortran",
        "robotics", "autonomous systems", "defense",
        "cad", "gd&t", "3d printing", "hvac",
        "vibration analysis", "hydraulics", "sustainability",
        "digital twin", "simulation", "plc", "labview",
    ],
    "ners": [
        "matlab", "python", "ansys", "comsol", "fortran",
        "thermodynamics", "heat transfer", "reactor design",
        "monte carlo", "radiation", "nuclear", "c++",
        "finite element", "process control", "r",
        "machine learning", "data pipeline", "statistical analysis",
        "simulation", "manufacturing", "sustainability",
        "regulatory affairs", "six sigma", "safety analysis",
        "digital twin", "cad", "labview", "sql",
        "gmp", "corrosion",
    ],
    "climate": [
        "python", "r", "matlab", "machine learning", "data pipeline",
        "gis", "remote sensing", "statistical analysis",
        "deep learning", "julia", "sql", "postgresql",
        "fortran", "climate modeling", "atmospheric science",
        "sustainability", "bigquery", "apache spark",
        "computer vision", "forecasting", "generative ai",
        "simulation", "aws", "docker",
        "digital twin", "edge ai", "nlp",
        "tableau", "power bi", "snowflake",
    ],
}


def get_market_skill_trends(postings: list[JobPosting], major_id: str = "cs") -> dict:
    skill_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}

    for posting in postings:
        source_counts[posting.source] = source_counts.get(posting.source, 0) + 1
        for skill in posting.skills:
            skill_counts[skill] = skill_counts.get(skill, 0) + 1

    total = len(postings) or 1
    category_counts: dict[str, int] = {}
    for category, skills in SKILL_TAXONOMY.items():
        cat_total = sum(skill_counts.get(s.lower(), 0) for s in skills)
        category_counts[category] = cat_total

    relevant_cats = MAJOR_RELEVANT_CATEGORIES.get(major_id, set(SKILL_TAXONOMY.keys()))
    relevant_skills: set[str] = set()
    for cat in relevant_cats:
        for s in SKILL_TAXONOMY.get(cat, []):
            relevant_skills.add(s.lower())
    for extra in MAJOR_EXTRA_SKILLS.get(major_id, set()):
        relevant_skills.add(extra.lower())

    industry_order = INDUSTRY_TOP_SKILLS.get(major_id, [])
    if industry_order:
        ranked: list[tuple[str, int]] = []
        seen: set[str] = set()
        for skill_name in industry_order:
            key = skill_name.lower()
            count = skill_counts.get(key, 0)
            if count > 0:
                ranked.append((key, count))
            seen.add(key)
        for skill, count in sorted(skill_counts.items(), key=lambda x: -x[1]):
            if skill not in seen and skill in relevant_skills and count > 0:
                ranked.append((skill, count))
                seen.add(skill)
        ranked.sort(key=lambda x: -x[1])
    else:
        ranked = [
            (skill, count) for skill, count in skill_counts.items()
            if skill in relevant_skills and count > 0
        ]
        ranked.sort(key=lambda x: -x[1])

    return {
        "top_skills": ranked[:30],
        "category_demand": category_counts,
        "total_postings": len(postings),
        "sources": source_counts,
        "emerging_2026_demand": {
            s.lower(): skill_counts.get(s.lower(), 0)
            for s in SKILL_TAXONOMY["emerging_2026"]
        },
    }


def _save_cache(postings: list[JobPosting]):
    FALLBACK_DATA.parent.mkdir(parents=True, exist_ok=True)
    with open(FALLBACK_DATA, "w") as f:
        json.dump([asdict(p) for p in postings], f, indent=2)


def _get_seed_postings() -> list[JobPosting]:
    """Curated seed data covering multiple engineering disciplines."""
    now = datetime.utcnow().isoformat()
    seed = [
        JobPosting("Senior AI/ML Engineer", "Meta", "Menlo Park, CA",
                    "Build and deploy large-scale ML systems. Experience with LLMs, RAG pipelines, and agentic AI frameworks required. Python and PyTorch required. Vector databases and LLM orchestration (LangChain) preferred.",
                    ["python", "machine learning", "deep learning", "llm", "rag", "agentic ai", "ai agents"],
                    ["PyTorch", "LangChain", "Docker", "Kubernetes"], "senior", "seed", "https://careers.meta.com", now),
        JobPosting("Backend Engineer (Rust)", "Cloudflare", "Remote",
                    "Design and implement high-performance network services in Rust. Build memory-safe, concurrent systems at global scale.",
                    ["rust", "memory-safe programming", "microservices", "serverless"],
                    ["Docker", "Kubernetes", "Git", "Terraform"], "senior", "seed", "https://cloudflare.com/careers", now),
        JobPosting("Mechanical Design Engineer", "Tesla", "Austin, TX",
                    "Design and optimize automotive components using CAD/CAE tools. SolidWorks, CATIA, FEA/CFD analysis. Experience with manufacturing processes including CNC, injection molding, and die casting.",
                    ["cad", "finite element", "fea", "manufacturing", "solidworks", "3d printing"],
                    ["SolidWorks", "ANSYS", "CATIA"], "mid", "seed", "https://tesla.com/careers", now),
        JobPosting("Biomedical Device Engineer", "Medtronic", "Minneapolis, MN",
                    "Design and develop Class II/III medical devices. Biomaterials selection, biocompatibility testing, tissue engineering applications. FDA regulatory experience preferred.",
                    ["medical devices", "biomaterials", "tissue engineering", "testing", "manufacturing"],
                    ["SolidWorks", "ANSYS"], "mid", "seed", "https://medtronic.com/careers", now),
        JobPosting("Robotics Software Engineer", "Boston Dynamics", "Waltham, MA",
                    "Develop perception and motion planning algorithms for mobile robots. C++, Python, ROS2. Experience with SLAM, computer vision, and reinforcement learning.",
                    ["robotics", "slam", "computer vision", "motion planning", "c++", "python", "ros", "perception", "autonomous systems"],
                    ["ROS", "Docker", "Git", "PyTorch"], "mid", "seed", "https://bostondynamics.com/careers", now),
        JobPosting("Structural Engineer", "AECOM", "Chicago, IL",
                    "Design and analyze structural systems for commercial buildings. FEA modeling, steel and concrete design, seismic analysis. Revit and SAP2000.",
                    ["structural analysis", "finite element", "fea", "cad", "sustainability"],
                    ["ANSYS", "AutoCAD"], "mid", "seed", "https://aecom.com/careers", now),
        JobPosting("Chemical Process Engineer", "Dow Chemical", "Midland, MI",
                    "Design and optimize chemical manufacturing processes. ASPEN Plus simulation, reactor design, heat exchanger networks. Lean manufacturing and sustainability initiatives.",
                    ["reactor design", "chemical kinetics", "optimization", "mass transfer", "heat transfer", "sustainability", "manufacturing"],
                    ["ANSYS"], "mid", "seed", "https://dow.com/careers", now),
        JobPosting("Aerospace Systems Engineer", "SpaceX", "Hawthorne, CA",
                    "Design propulsion and flight control systems for launch vehicles. Orbital mechanics, flight dynamics, and control systems. MATLAB/Simulink. Python for data analysis.",
                    ["propulsion", "flight dynamics", "control systems", "orbital mechanics", "matlab", "python", "aerodynamics", "simulation"],
                    ["ANSYS", "Simulink", "Git"], "senior", "seed", "https://spacex.com/careers", now),
        JobPosting("Data Platform Engineer", "Databricks", "Remote",
                    "Build next-generation data platforms. Apache Spark, Kafka, modern data stack (dbt, Snowflake). Vector databases for AI workloads. Strong SQL and Python.",
                    ["python", "sql", "apache spark", "apache kafka", "data pipeline", "data engineering", "vector database", "dbt", "snowflake"],
                    ["Docker", "Terraform", "Airflow", "dbt", "Git"], "mid", "seed", "https://databricks.com/careers", now),
        JobPosting("AI Agent Developer", "Salesforce", "San Francisco, CA",
                    "Build autonomous AI agents for enterprise automation. Multi-agent systems using LangChain, CrewAI. LLMs, tool use, chain-of-thought reasoning.",
                    ["python", "llm", "agentic ai", "ai agents", "multi-agent systems", "llm orchestration", "langchain", "crewai", "prompt engineering", "rag"],
                    ["LangChain", "LlamaIndex", "Docker", "Git"], "mid", "seed", "https://salesforce.com/careers", now),
        JobPosting("Autonomous Vehicle Engineer", "Waymo", "Mountain View, CA",
                    "Develop perception and planning systems for self-driving cars. Deep learning, sensor fusion (LiDAR, camera, radar), motion planning, simulation.",
                    ["autonomous systems", "computer vision", "deep learning", "python", "c++", "motion planning", "perception", "slam", "simulation"],
                    ["PyTorch", "TensorFlow", "Docker", "Git", "ROS"], "senior", "seed", "https://waymo.com/careers", now),
        JobPosting("Nuclear Systems Engineer", "NuScale Power", "Portland, OR",
                    "Design and analyze nuclear reactor systems. Reactor physics, thermal-hydraulics, safety analysis. MATLAB and Python for simulation.",
                    ["reactor design", "reactor physics", "simulation", "matlab", "python", "radiation", "nuclear physics"],
                    ["ANSYS", "Simulink"], "mid", "seed", "https://nuscalepower.com/careers", now),
        JobPosting("Sustainability Engineer", "Apple", "Cupertino, CA",
                    "Lead sustainability initiatives for product lifecycle. Life-cycle assessment, renewable energy integration, materials selection for environmental impact reduction. Data analysis with Python.",
                    ["sustainability", "renewable energy", "materials science", "python", "statistics", "manufacturing"],
                    ["Tableau", "Python"], "mid", "seed", "https://apple.com/careers", now),
        JobPosting("Digital Twin Engineer", "Siemens", "Remote",
                    "Build digital twin platforms for industrial equipment. IoT sensor integration, physics-based simulation, machine learning for predictive maintenance.",
                    ["digital twin", "simulation", "machine learning", "python", "sensors", "manufacturing", "automation"],
                    ["ANSYS", "Docker", "Git", "Kubernetes"], "mid", "seed", "https://siemens.com/careers", now),
        JobPosting("Supply Chain Data Scientist", "Amazon", "Seattle, WA",
                    "Optimize global supply chain operations using ML and operations research. Demand forecasting, inventory optimization, network design. Python, SQL.",
                    ["supply chain", "machine learning", "optimization", "python", "sql", "statistics", "operations research", "simulation"],
                    ["Docker", "Airflow", "Git"], "mid", "seed", "https://amazon.com/careers", now),
    ]
    _save_cache(seed)
    return seed
