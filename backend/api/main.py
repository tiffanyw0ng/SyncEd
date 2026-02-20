"""
Market-Sync AI — FastAPI Backend

Decision Intelligence API for Curriculum-Market Synchronization.
Supports all U-M College of Engineering majors.

When Oracle DB credentials are set in .env, all scraped data is
persisted to Oracle Autonomous Database 26ai. Without credentials,
everything works in-memory + JSON file cache (no Oracle needed).
"""

import asyncio
import json
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.scrapers.umich_courses import (
    scrape_major_courses, get_all_majors, get_major, Course,
)
from backend.scrapers.job_postings import (
    scrape_job_postings, get_market_skill_trends, JobPosting,
)
from backend.scrapers.news_trends import scrape_tech_news, compute_trend_signals
from backend.scrapers.course_reviews import scrape_course_reviews, aggregate_reviews, CourseReview
from backend.scrapers.course_enricher import enrich_courses
from backend.processing.vectorizer import CurriculumAnalyzer
from backend.database import oracle_db

DATA_DIR = Path(__file__).parent.parent / "data"

_state: dict = {
    "analyses": {},
    "courses": {},
    "postings": {},
    "trends": {},
    "reviews": {},
    "review_summaries": {},
    "news": {},
    "news_trends": {},
    "active_major": "cs",
}


def _load_global_postings():
    """Load the shared job_postings.json once (used by all majors)."""
    if _state.get("_global_postings_loaded"):
        return
    jp_path = DATA_DIR / "job_postings.json"
    if jp_path.exists():
        try:
            with open(jp_path) as f:
                raw = json.load(f)
            _state["_global_postings"] = [
                JobPosting(**r) if isinstance(r, dict) else r for r in raw
            ]
            print(f"[Cache] Loaded {len(_state['_global_postings'])} global job postings")
        except Exception as e:
            print(f"[Cache] Failed to load job_postings.json: {e}")
            _state["_global_postings"] = []
    _state["_global_postings_loaded"] = True


def _load_cached_major_from_json(major_id: str) -> bool:
    """Load a major from local JSON only (fast, no DB)."""
    loaded = False

    if major_id not in _state["courses"]:
        courses_path = DATA_DIR / f"{major_id}_courses.json"
        if courses_path.exists():
            try:
                with open(courses_path) as f:
                    raw = json.load(f)
                _state["courses"][major_id] = [
                    Course(**c) if isinstance(c, dict) else c for c in raw
                ]
                loaded = True
            except Exception as e:
                print(f"[Cache] Failed to load courses for {major_id}: {e}")

    if major_id not in _state["postings"]:
        per_major_path = DATA_DIR / f"{major_id}_postings.json"
        if per_major_path.exists():
            try:
                with open(per_major_path) as f:
                    raw = json.load(f)
                _state["postings"][major_id] = [
                    JobPosting(**r) if isinstance(r, dict) else r for r in raw
                ]
                loaded = True
            except Exception as e:
                print(f"[Cache] Failed to load postings for {major_id}: {e}")
        else:
            _load_global_postings()
            if _state.get("_global_postings"):
                _state["postings"][major_id] = _state["_global_postings"]
                loaded = True

    if major_id not in _state["news"]:
        news_path = DATA_DIR / f"{major_id}_news.json"
        if news_path.exists():
            try:
                from backend.scrapers.news_trends import NewsArticle
                with open(news_path) as f:
                    raw = json.load(f)
                _state["news"][major_id] = [
                    NewsArticle(**a) if isinstance(a, dict) else a for a in raw
                ]
                loaded = True
            except Exception as e:
                print(f"[Cache] Failed to load news for {major_id}: {e}")
        news_trends_path = DATA_DIR / f"{major_id}_news_trends.json"
        if news_trends_path.exists():
            try:
                with open(news_trends_path) as f:
                    _state["news_trends"][major_id] = json.load(f)
                loaded = True
            except Exception:
                pass

    if major_id not in _state["analyses"]:
        json_path = DATA_DIR / f"{major_id}_analysis.json"
        if json_path.exists():
            with open(json_path) as f:
                _state["analyses"][major_id] = json.load(f)
            loaded = True

    if major_id not in _state["trends"]:
        trends_path = DATA_DIR / f"{major_id}_trends.json"
        if trends_path.exists():
            with open(trends_path) as f:
                _state["trends"][major_id] = json.load(f)
            loaded = True

    if major_id not in _state["reviews"]:
        rev_path = DATA_DIR / f"{major_id}_reviews.json"
        if rev_path.exists():
            try:
                with open(rev_path) as f:
                    raw = json.load(f)
                reviews = [
                    CourseReview(**r) if isinstance(r, dict) else r for r in raw
                ]
                _state["reviews"][major_id] = reviews
                _state["review_summaries"][major_id] = aggregate_reviews(reviews)
                loaded = True
            except Exception as e:
                print(f"[Cache] Failed to load reviews for {major_id}: {e}")

    if loaded:
        print(f"[Cache] Loaded {major_id} from local JSON")

    return major_id in _state["analyses"] or major_id in _state["trends"]


def _load_cached_major(major_id: str) -> bool:
    """Try to load a major from Oracle DB or local JSON. Returns True if data found."""
    if major_id in _state["analyses"]:
        return True

    if oracle_db.is_configured():
        try:
            analysis, trends = oracle_db.load_analysis(major_id)
            if analysis and trends:
                _state["analyses"][major_id] = analysis
                _state["trends"][major_id] = trends
                _state["courses"][major_id] = oracle_db.load_courses(major_id)
                _state["postings"][major_id] = oracle_db.load_job_postings(major_id)
                cached_reviews = oracle_db.load_reviews(major_id)
                if cached_reviews:
                    _state["reviews"][major_id] = cached_reviews
                    _state["review_summaries"][major_id] = aggregate_reviews(cached_reviews)
                print(f"[Cache] Loaded {major_id} from Oracle DB")
                return True
        except Exception as e:
            print(f"[Cache] Oracle load failed: {e}")

    return _load_cached_major_from_json(major_id)


def _load_cached_news() -> bool:
    """Kept for backward compat — news is now per-major."""
    return bool(_state["news"])


_bg_task: asyncio.Task | None = None
_bg_status: dict = {"phase": "idle", "current_major": None, "completed": [], "total": 0}


async def _load_from_oracle_bg():
    """Load data from Oracle DB in background — doesn't block server startup."""
    await asyncio.sleep(1)
    try:
        def _do_oracle_load():
            loaded = []
            for m in get_all_majors():
                mid = m["id"]
                if mid in _state.get("analyses", {}) and mid in _state.get("courses", {}):
                    continue
                try:
                    analysis, trends = oracle_db.load_analysis(mid)
                    if analysis:
                        _state["analyses"][mid] = analysis
                        if trends:
                            _state["trends"][mid] = trends
                        courses = oracle_db.load_courses(mid)
                        if courses:
                            _state["courses"][mid] = courses
                        postings = oracle_db.load_job_postings(mid)
                        if postings:
                            _state["postings"][mid] = postings
                        reviews = oracle_db.load_reviews(mid)
                        if reviews:
                            _state["reviews"][mid] = reviews
                            _state["review_summaries"][mid] = aggregate_reviews(reviews)
                        loaded.append(mid)
                except Exception as e:
                    print(f"[Oracle BG] Failed for {mid}: {e}")
            return loaded

        loaded = await asyncio.wait_for(
            asyncio.to_thread(_do_oracle_load), timeout=60
        )
        if loaded:
            print(f"[Oracle BG] Loaded {len(loaded)} majors: {loaded}")
    except asyncio.TimeoutError:
        print("[Oracle BG] Timed out after 60s — using JSON cache")
    except Exception as e:
        print(f"[Oracle BG] Error: {e}")


async def _background_scrape_missing():
    """One-time background scrape for majors with no data. Runs once, not in a loop."""
    await asyncio.sleep(3)
    all_majors = get_all_majors()
    missing = [m["id"] for m in all_majors if m["id"] not in _state["analyses"]]

    if not missing:
        print("[Background] All majors already loaded — nothing to scrape")
        _bg_status["phase"] = "done"
        return

    _bg_status["total"] = len(missing)
    _bg_status["phase"] = "scraping"
    _bg_status["completed"] = []
    print(f"[Background] Scraping {len(missing)} missing majors: {missing}")

    for mid in missing:
        try:
            _bg_status["current_major"] = mid
            print(f"[Background] Scraping {mid}...")
            await _refresh_major(mid)
            _bg_status["completed"].append(mid)
            print(f"[Background] {mid} done")
        except Exception as e:
            print(f"[Background] {mid} error: {e}")

    _bg_status["phase"] = "done"
    _bg_status["current_major"] = None
    print(f"[Background] Done — scraped {len(_bg_status['completed'])} majors")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bg_task

    # 1. Quick load from local JSON first (instant)
    json_loaded = []
    for m in get_all_majors():
        if _load_cached_major_from_json(m["id"]):
            json_loaded.append(m["id"])
    print(f"[Startup] JSON cache: {len(json_loaded)} majors")

    # 2. Try Oracle DB in background (don't block startup)
    if oracle_db.is_configured():
        asyncio.create_task(_load_from_oracle_bg())

    print(f"[Startup] Server ready — {len(json_loaded)} majors loaded")

    # 3. Background scrape missing majors (one time, not a loop)
    _bg_task = asyncio.create_task(_background_scrape_missing())

    yield

    if _bg_task and not _bg_task.done():
        _bg_task.cancel()
    try:
        oracle_db.close_pool()
    except Exception:
        pass


app = FastAPI(
    title="Market-Sync AI",
    description="Curriculum-Market Synchronization Engine — U-M College of Engineering",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _refresh_major(major_id: str):
    """Scrape & analyze a specific major including major-specific news."""
    major = get_major(major_id)
    if not major:
        return

    courses = await scrape_major_courses(major_id)
    await enrich_courses(courses, prefix=major.prefix)

    postings = await scrape_job_postings(search_queries=major.job_search_queries)

    analyzer = CurriculumAnalyzer()
    analysis = analyzer.analyze(courses, postings, major_prefix=major.prefix)
    trends = get_market_skill_trends(postings, major_id=major_id)

    course_codes = [c.code for c in courses]
    reviews = await scrape_course_reviews(course_codes, major.prefix)
    review_summary = aggregate_reviews(reviews)

    # Scrape major-specific news
    news_queries = major.news_search_queries if major.news_search_queries else None
    articles = await scrape_tech_news(major_queries=news_queries)
    news_trends = compute_trend_signals(articles)

    _state["courses"][major_id] = courses
    _state["postings"][major_id] = postings
    _state["analyses"][major_id] = analysis
    _state["trends"][major_id] = trends
    _state["reviews"][major_id] = reviews
    _state["review_summaries"][major_id] = review_summary
    _state["news"][major_id] = articles
    _state["news_trends"][major_id] = news_trends
    _state["active_major"] = major_id

    print(f"[{major_id}] {len(courses)} courses, {len(postings)} postings, "
          f"{len(reviews)} reviews, {len(articles)} news articles")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / f"{major_id}_analysis.json", "w") as f:
        json.dump(analysis, f, indent=2)
    with open(DATA_DIR / f"{major_id}_trends.json", "w") as f:
        json.dump(trends, f, indent=2)
    with open(DATA_DIR / f"{major_id}_reviews.json", "w") as f:
        json.dump([r.__dict__ if hasattr(r, '__dict__') else r for r in reviews], f, indent=2)

    if oracle_db.is_configured():
        asyncio.create_task(_save_to_oracle(major_id, postings, courses, analysis, trends, reviews))


async def _save_to_oracle(major_id, postings, courses, analysis, trends, reviews):
    """Save all data to Oracle DB in a background thread."""
    def _do_save():
        try:
            oracle_db.save_job_postings(postings, major_id)
            oracle_db.save_courses(courses, major_id)
            oracle_db.save_analysis(major_id, analysis, trends)
            oracle_db.save_reviews(reviews, major_id)
            print(f"[Oracle DB] Saved all data for {major_id}")
        except Exception as e:
            print(f"[Oracle DB] Save error (data still in memory & JSON): {e}")

    try:
        await asyncio.wait_for(asyncio.to_thread(_do_save), timeout=120)
    except asyncio.TimeoutError:
        print(f"[Oracle DB] Save timed out for {major_id} — data still in memory & JSON")


async def _refresh_news_global():
    """Scrape generic tech news (fallback)."""
    articles = await scrape_tech_news()
    _state["news"]["_global"] = articles
    _state["news_trends"]["_global"] = compute_trend_signals(articles)


# ---- Major selection ----

@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "Market-Sync AI",
        "version": "2.0.0",
        "oracle_db": "connected" if oracle_db.is_configured() else "not configured (using local cache)",
    }


@app.get("/api/majors")
async def list_majors():
    """List all available engineering majors."""
    majors = get_all_majors()
    analyzed = list(_state["analyses"].keys())
    return {
        "majors": majors,
        "analyzed_majors": analyzed,
        "active_major": _state["active_major"],
    }


@app.post("/api/majors/{major_id}/analyze")
async def analyze_major(major_id: str):
    """Trigger scraping + analysis for a specific major."""
    major = get_major(major_id)
    if not major:
        return {"error": f"Unknown major: {major_id}"}

    await _refresh_major(major_id)

    return {
        "status": "analyzed",
        "major": major.name,
        "courses": len(_state["courses"].get(major_id, [])),
        "postings": len(_state["postings"].get(major_id, [])),
        "scraping_sources": _state["trends"].get(major_id, {}).get("sources", {}),
        "oracle_db": "saved" if oracle_db.is_configured() else "not configured",
    }


# ---- Dashboard & analysis (per major) ----

@app.get("/api/dashboard")
async def get_dashboard(major: str = "cs"):
    """Main dashboard data for a given major."""
    _load_cached_major(major)

    analysis = _state["analyses"].get(major)
    if not analysis:
        return {"error": "No data yet — click Refresh Data or select a major to scrape."}

    course_gaps = analysis["course_gaps"]
    sorted_gaps = sorted(course_gaps, key=lambda g: g["alignment_score"])
    postings = _state["postings"].get(major, [])
    trends = _state["trends"].get(major, {})

    return {
        "major_id": major,
        "major_name": (get_major(major) or type("", (), {"name": major})).name,
        "overall_alignment_score": analysis["overall_alignment_score"],
        "total_courses_analyzed": len(course_gaps),
        "total_job_postings": len(postings),
        "scraping_sources": trends.get("sources", {}),
        "top_gaps": sorted_gaps[:5],
        "top_aligned": sorted(course_gaps, key=lambda g: -g["alignment_score"])[:5],
        "new_course_recommendations": analysis["new_course_recommendations"],
        "analysis_timestamp": analysis["analysis_timestamp"],
        "data_source": "oracle_db" if oracle_db.is_configured() else "local_cache",
    }


@app.get("/api/courses")
async def get_courses(major: str = "cs"):
    """All analyzed courses for a given major."""
    _load_cached_major(major)
    analysis = _state["analyses"].get(major)
    if not analysis:
        return {"courses": []}
    return {"courses": analysis["course_gaps"]}


@app.get("/api/courses/{course_code}")
async def get_course_detail(course_code: str, major: str = "cs"):
    """Detailed gap analysis for a specific course."""
    analysis = _state["analyses"].get(major)
    if not analysis:
        return {"error": "Analysis not available"}

    code = course_code.upper().replace("-", " ")
    for gap in analysis["course_gaps"]:
        if gap["course_code"].upper() == code:
            course_data = None
            for c in _state["courses"].get(major, []):
                if c.code.upper() == code:
                    course_data = {
                        "code": c.code, "title": c.title,
                        "description": c.description, "credits": c.credits,
                        "topics": c.topics, "learning_objectives": c.learning_objectives,
                    }
                    break
            return {"gap_analysis": gap, "course_info": course_data}

    return {"error": f"Course {course_code} not found"}


def _reorder_skills(raw_skills: list, major_id: str) -> list:
    """Reorder cached skill list according to curated industry priority."""
    from backend.scrapers.job_postings import INDUSTRY_TOP_SKILLS
    industry_order = INDUSTRY_TOP_SKILLS.get(major_id, [])
    if not industry_order:
        return raw_skills[:30]

    skill_map = {s[0].lower() if isinstance(s, (list, tuple)) else s.lower(): s for s in raw_skills}
    count_map = {}
    for s in raw_skills:
        name = s[0].lower() if isinstance(s, (list, tuple)) else s.lower()
        count_map[name] = s[1] if isinstance(s, (list, tuple)) else 0

    result = []
    seen = set()
    for skill_name in industry_order:
        key = skill_name.lower()
        count = count_map.get(key, 0)
        result.append([key, max(count, 1)])
        seen.add(key)

    for s in raw_skills:
        name = s[0].lower() if isinstance(s, (list, tuple)) else s.lower()
        if name not in seen:
            result.append([name, s[1] if isinstance(s, (list, tuple)) else 0])
            seen.add(name)

    return result[:30]


@app.get("/api/market-trends")
async def get_market_trends(major: str = "cs"):
    """Current job market skill trends for a given major."""
    _load_cached_major(major)

    postings = _state["postings"].get(major, [])
    if postings:
        trends = get_market_skill_trends(postings, major_id=major)
        return {
            "top_skills": trends["top_skills"],
            "category_demand": trends["category_demand"],
            "total_postings": trends["total_postings"],
            "sources": trends.get("sources", {}),
            "emerging_2026": trends["emerging_2026_demand"],
        }

    trends = _state["trends"].get(major)
    if not trends:
        return {"error": "No data yet — click Refresh Data to scrape."}

    return {
        "top_skills": _reorder_skills(trends.get("top_skills", []), major),
        "category_demand": trends.get("category_demand", {}),
        "total_postings": trends.get("total_postings", 0),
        "sources": trends.get("sources", {}),
        "emerging_2026": trends.get("emerging_2026_demand", trends.get("emerging_2026", {})),
    }


@app.get("/api/recommendations")
async def get_recommendations(major: str = "cs"):
    """New course recommendations for a given major."""
    _load_cached_major(major)
    analysis = _state["analyses"].get(major)
    if not analysis:
        return {"recommendations": []}
    return {"recommendations": analysis["new_course_recommendations"]}


# ---- Student Reviews + Cross-Reference ----

@app.get("/api/reviews")
async def get_reviews(major: str = "cs"):
    """Student reviews with sentiment analysis, cross-referenced with market alignment."""
    _load_cached_major(major)

    if major not in _state["review_summaries"]:
        return {"error": "No review data — click Refresh Data to scrape.", "courses_at_risk": []}

    summary = _state["review_summaries"][major]
    analysis = _state["analyses"].get(major, {})
    course_gaps = {
        g["course_code"]: g for g in analysis.get("course_gaps", [])
    }

    courses_at_risk = []
    for cs in summary.get("course_summaries", []):
        gap = course_gaps.get(cs["course_code"])
        alignment = gap["alignment_score"] if gap else None

        is_unhappy = cs["avg_sentiment"] < -0.1 or cs["negative"] > cs["positive"]
        is_misaligned = alignment is not None and alignment < 50

        if is_unhappy or is_misaligned:
            risk_level = "critical" if (is_unhappy and is_misaligned) else "high" if is_unhappy else "moderate"
            courses_at_risk.append({
                **cs,
                "alignment_score": alignment,
                "risk_level": risk_level,
                "reason": _risk_reason(is_unhappy, is_misaligned, cs, alignment),
            })

    courses_at_risk.sort(key=lambda x: (
        {"critical": 0, "high": 1, "moderate": 2}.get(x["risk_level"], 3),
        x["avg_sentiment"],
    ))

    return {
        **summary,
        "courses_at_risk": courses_at_risk,
        "major": major,
    }


def _risk_reason(is_unhappy: bool, is_misaligned: bool, cs: dict, alignment) -> str:
    if is_unhappy and is_misaligned:
        complaints = ", ".join(t for t, _ in cs.get("top_complaints", [])[:2]) or "general dissatisfaction"
        return (
            f"Students report {complaints} AND this course has only "
            f"{alignment}% market alignment. Urgent overhaul recommended."
        )
    if is_unhappy:
        complaints = ", ".join(t for t, _ in cs.get("top_complaints", [])[:2]) or "general dissatisfaction"
        return f"Students report {complaints}. Course content may need refreshing."
    return f"Only {alignment}% aligned with current job market demands."


# ---- Curriculum Weakness Analysis ----

@app.get("/api/curriculum-analysis")
async def get_curriculum_analysis(major: str = "cs"):
    """Deep curriculum weakness analysis for a given major (cached after first compute)."""
    _load_cached_major(major)

    cache_key = f"_curriculum_weakness_{major}"
    if cache_key in _state:
        return _state[cache_key]

    cached_path = DATA_DIR / f"{major}_curriculum_weakness.json"
    if cached_path.exists():
        try:
            with open(cached_path) as f:
                result = json.load(f)
            _state[cache_key] = result
            return result
        except Exception:
            pass

    courses = _state["courses"].get(major, [])
    postings = _state["postings"].get(major, [])
    major_obj = get_major(major)
    major_name = major_obj.name if major_obj else major.upper()

    if not courses or not postings:
        return {"error": "No data yet — click Refresh Data to scrape."}

    analyzer = CurriculumAnalyzer()
    result = analyzer.analyze_curriculum_weaknesses(courses, postings, major_name, major_id=major)

    _state[cache_key] = result
    try:
        with open(cached_path, "w") as f:
            json.dump(result, f, indent=2)
    except Exception:
        pass

    return result


# ---- News ----

@app.get("/api/news")
async def get_news(major: str = "cs"):
    """News tailored to the selected major."""
    articles = _state["news"].get(major, [])
    news_trends = _state["news_trends"].get(major, {})

    source_counts = {}
    for a in articles:
        source_counts[a.source] = source_counts.get(a.source, 0) + 1

    return {
        "articles": [
            {"title": a.title, "source": a.source, "url": a.url,
             "summary": a.summary, "published": a.published, "topics": a.topics}
            for a in articles[:100]
        ],
        "trending_topics": news_trends.get("trending_topics", []),
        "topic_articles": news_trends.get("topic_articles", {}),
        "total_articles": news_trends.get("total_articles_scanned", len(articles)),
        "sources": news_trends.get("sources", []),
        "source_counts": source_counts,
        "major": major,
    }


# ---- Oracle DB Status ----

@app.get("/api/db-status")
async def db_status():
    """Check Oracle DB connection status and row counts."""
    return oracle_db.get_db_stats()


@app.get("/api/scrape-status")
async def scrape_status():
    """Check background scraping pipeline progress."""
    return {
        "phase": _bg_status["phase"],
        "current_major": _bg_status["current_major"],
        "completed_majors": _bg_status["completed"],
        "total_majors": _bg_status["total"],
        "analyzed_majors": list(_state["analyses"].keys()),
    }


# ---- Refresh ----

@app.post("/api/refresh-reviews-all")
async def refresh_reviews_all():
    """Scrape student reviews for ALL majors concurrently (reviews only, fast)."""
    all_majors = get_all_majors()
    results = {}

    async def _scrape_reviews_for(mid: str):
        major = get_major(mid)
        if not major:
            return mid, 0
        courses = _state["courses"].get(mid)
        if not courses:
            courses = await scrape_major_courses(mid)
            _state["courses"][mid] = courses
        codes = [c.code for c in courses]
        reviews = await scrape_course_reviews(codes, major.prefix)
        _state["reviews"][mid] = reviews
        _state["review_summaries"][mid] = aggregate_reviews(reviews)

        rev_path = DATA_DIR / f"{mid}_reviews.json"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(rev_path, "w") as f:
            json.dump([r.__dict__ if hasattr(r, '__dict__') else r for r in reviews], f, indent=2)

        print(f"[Reviews All] {mid}: {len(reviews)} reviews scraped")
        return mid, len(reviews)

    batch_size = 3
    major_ids = [m["id"] for m in all_majors]
    for i in range(0, len(major_ids), batch_size):
        batch = major_ids[i:i + batch_size]
        tasks = [_scrape_reviews_for(mid) for mid in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in batch_results:
            if isinstance(r, Exception):
                print(f"[Reviews All] Error: {r}")
            else:
                mid, count = r
                results[mid] = count

    return {"status": "done", "reviews_per_major": results}


@app.post("/api/refresh")
async def refresh_data(major: str = "cs"):
    """Re-scrape and re-analyze a major (including its news)."""
    await _refresh_major(major)

    return {
        "status": "refreshed",
        "major": major,
        "courses": len(_state["courses"].get(major, [])),
        "postings": len(_state["postings"].get(major, [])),
        "news_articles": len(_state["news"].get(major, [])),
        "oracle_db": "saved" if oracle_db.is_configured() else "not configured",
    }
