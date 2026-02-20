"""Quick one-shot: scrape student reviews for all majors that don't have them."""
import asyncio, json, sys, os, time
from pathlib import Path

os.environ["PYTHONUNBUFFERED"] = "1"
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, str(Path(__file__).parent))

from backend.scrapers.umich_courses import get_all_majors, get_major, Course
from backend.scrapers.course_reviews import scrape_course_reviews

DATA = Path(__file__).parent / "backend" / "data"


async def main():
    for m in get_all_majors():
        mid = m["id"]
        rev_path = DATA / f"{mid}_reviews.json"

        # Skip if already has reviews (file > 10 bytes means non-empty)
        if rev_path.exists() and rev_path.stat().st_size > 10:
            print(f"[{mid.upper()}] Already has reviews, skipping")
            continue

        courses_path = DATA / f"{mid}_courses.json"
        if not courses_path.exists():
            print(f"[{mid.upper()}] No course data, skipping")
            continue

        with open(courses_path) as f:
            raw = json.load(f)
        courses = [Course(**c) for c in raw]
        codes = [c.code for c in courses]
        major = get_major(mid)
        prefix = major.prefix if major else mid.upper()

        print(f"[{mid.upper()}] Scraping reviews for {len(codes)} courses...")
        t0 = time.time()
        try:
            reviews = await scrape_course_reviews(codes, prefix)
        except Exception as e:
            print(f"[{mid.upper()}] Error: {e}")
            reviews = []

        print(f"[{mid.upper()}] {len(reviews)} reviews in {time.time()-t0:.0f}s")
        with open(rev_path, "w") as f:
            json.dump([r.__dict__ if hasattr(r, "__dict__") else r for r in reviews], f, indent=2)

    print("\nDone!")

if __name__ == "__main__":
    asyncio.run(main())
