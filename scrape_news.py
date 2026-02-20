"""Scrape news + compute news_trends for all majors missing them."""
import asyncio, json, os, sys, time
os.environ["PYTHONUNBUFFERED"] = "1"
sys.stdout.reconfigure(line_buffering=True)

from pathlib import Path
DATA = Path("backend/data")

from backend.scrapers.umich_courses import ENGINEERING_MAJORS, get_major
from backend.scrapers.news_trends import scrape_tech_news, compute_trend_signals, NewsArticle


def save(name, data):
    with open(DATA / name, "w") as f:
        json.dump(data, f, default=str)
    print(f"    saved {name} ({len(data) if isinstance(data, (list, dict)) else '?'} items)")


async def main():
    majors = [(m.id, m) for m in ENGINEERING_MAJORS]
    missing = []
    for mid, m in majors:
        news_path = DATA / f"{mid}_news.json"
        if news_path.exists():
            try:
                d = json.load(open(news_path))
                if len(d) > 0:
                    continue
            except Exception:
                pass
        missing.append((mid, m))

    print(f"Majors needing news: {[m[0] for m in missing]}")
    print(f"({len(missing)} of {len(majors)} majors)\n")

    for i, (mid, m) in enumerate(missing):
        print(f"[{i+1}/{len(missing)}] {mid.upper()} — {m.name}")
        nq = m.news_search_queries or None
        try:
            articles = await asyncio.wait_for(
                scrape_tech_news(major_queries=nq), timeout=45
            )
        except asyncio.TimeoutError:
            print(f"    TIMEOUT (45s)")
            articles = []
        except Exception as e:
            print(f"    ERROR: {e}")
            articles = []

        print(f"    got {len(articles)} articles")
        from dataclasses import asdict
        art_dicts = [asdict(a) for a in articles]
        save(f"{mid}_news.json", art_dicts)

        if articles:
            trends = compute_trend_signals(articles)
            save(f"{mid}_news_trends.json", trends)
        else:
            save(f"{mid}_news_trends.json", {})

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
