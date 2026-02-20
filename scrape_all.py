"""
One-shot scrape: jobs scraped ONCE, then reused for all 15 majors.
Courses scraped per major. Everything saved to JSON.

Usage:  python -u scrape_all.py
"""

import asyncio, json, time, sys, os
from dataclasses import asdict
from pathlib import Path

os.environ["PYTHONUNBUFFERED"] = "1"
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, str(Path(__file__).parent))

from backend.scrapers.umich_courses import (
    scrape_major_courses, get_all_majors, get_major,
)
from backend.scrapers.job_postings import (
    scrape_job_postings, get_market_skill_trends, JobPosting,
)
from backend.scrapers.news_trends import scrape_tech_news, compute_trend_signals
from backend.scrapers.course_reviews import scrape_course_reviews, aggregate_reviews
from backend.scrapers.course_enricher import enrich_courses
from backend.processing.vectorizer import CurriculumAnalyzer
from backend.database import oracle_db

DATA = Path(__file__).parent / "backend" / "data"
DATA.mkdir(parents=True, exist_ok=True)


def save(name, data):
    with open(DATA / name, "w") as f:
        json.dump(data, f, indent=2)
    print(f"    -> {name}")


async def main():
    all_majors = get_all_majors()
    ids = [m["id"] for m in all_majors]
    print(f"Scraping {len(ids)} majors: {', '.join(ids)}")
    print(f"Oracle DB: {'yes' if oracle_db.is_configured() else 'no (JSON only)'}\n")

    # ============================================================
    # STEP 1: Scrape job postings ONCE (same sources for all majors)
    # ============================================================
    jp_path = DATA / "job_postings.json"
    jp_age = (time.time() - jp_path.stat().st_mtime) if jp_path.exists() else 99999
    if jp_path.exists() and jp_age < 3600:
        print("=" * 60)
        print(f"  STEP 1: Reusing job_postings.json ({jp_age:.0f}s old)")
        print("=" * 60)
        with open(jp_path) as f:
            raw = json.load(f)
        all_postings = [JobPosting(**r) for r in raw]
        print(f"  {len(all_postings)} postings from cache")
    else:
        print("=" * 60)
        print("  STEP 1: Scraping job postings (one time)...")
        print("=" * 60)
        t0 = time.time()
        all_postings = await scrape_job_postings()
        print(f"  {len(all_postings)} total postings in {time.time()-t0:.0f}s")
        save("job_postings.json", [asdict(p) for p in all_postings])

    # ============================================================
    # STEP 2: Per-major — courses, analysis, reviews, news
    # ============================================================
    total_t0 = time.time()

    for mid in ids:
        major = get_major(mid)
        if not major:
            continue

        # Skip if already scraped this run
        weakness_path = DATA / f"{mid}_curriculum_weakness.json"
        news_path = DATA / f"{mid}_news.json"
        if weakness_path.exists() and news_path.exists():
            mod_age = time.time() - weakness_path.stat().st_mtime
            if mod_age < 600:  # less than 10 min old = just scraped
                print(f"\n  [{mid.upper()}] Already fresh ({mod_age:.0f}s old), skipping")
                continue

        print(f"\n{'='*60}")
        print(f"  [{mid.upper()}] {major.name}")
        print(f"{'='*60}")
        mt0 = time.time()

        # --- Courses ---
        print(f"  Courses...")
        courses = await scrape_major_courses(mid)
        if courses:
            await enrich_courses(courses, prefix=major.prefix)
        print(f"    {len(courses)} courses")
        save(f"{mid}_courses.json", [asdict(c) for c in courses])

        # --- Analysis (reuse global postings) ---
        print(f"  Analysis...")
        analyzer = CurriculumAnalyzer()
        analysis = analyzer.analyze(courses, all_postings, major_prefix=major.prefix)
        save(f"{mid}_analysis.json", analysis)

        trends = get_market_skill_trends(all_postings, major_id=mid)
        save(f"{mid}_trends.json", trends)

        weakness = analyzer.analyze_curriculum_weaknesses(
            courses, all_postings, major.name, major_id=mid
        )
        save(f"{mid}_curriculum_weakness.json", weakness)

        # --- Reviews (quick, skip if slow) ---
        print(f"  Reviews...")
        try:
            codes = [c.code for c in courses]
            reviews = await asyncio.wait_for(
                scrape_course_reviews(codes, major.prefix), timeout=60
            )
        except asyncio.TimeoutError:
            print("    reviews timed out (60s), skipping")
            reviews = []
        except Exception as e:
            print(f"    reviews error: {e}")
            reviews = []
        print(f"    {len(reviews)} reviews")
        save(f"{mid}_reviews.json",
             [r.__dict__ if hasattr(r, "__dict__") else r for r in reviews])

        # --- News ---
        print(f"  News...")
        try:
            nq = major.news_search_queries or None
            articles = await asyncio.wait_for(
                scrape_tech_news(major_queries=nq), timeout=45
            )
        except asyncio.TimeoutError:
            print("    news timed out (45s), skipping")
            articles = []
        except Exception as e:
            print(f"    news error: {e}")
            articles = []
        nt = compute_trend_signals(articles)
        print(f"    {len(articles)} articles")
        save(f"{mid}_news.json",
             [a.__dict__ if hasattr(a, "__dict__") else a for a in articles])
        save(f"{mid}_news_trends.json", nt)

        print(f"  [{mid.upper()}] done in {time.time()-mt0:.0f}s")

    print(f"\n{'='*60}")
    print(f"  ALL DONE — {len(ids)} majors in {time.time()-total_t0:.0f}s")
    print(f"  Data: {DATA}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
