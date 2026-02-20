"""
Student Course Reviews Scraper

Scrapes real student opinions from public sources:
  1. Reddit r/uofm — free JSON API, no auth needed
  2. Reddit r/umich — secondary subreddit
  3. Google search — finds reviews from blogs, forums, ratemycourse, etc.

Then runs keyword-based sentiment analysis to extract:
  - Overall satisfaction (positive / negative / neutral)
  - Common complaints (outdated, hard, boring, useless, etc.)
  - Common praise (practical, great prof, useful, etc.)
  - Themes about course content relevance
"""

import asyncio
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from html import unescape

import httpx
from bs4 import BeautifulSoup


@dataclass
class CourseReview:
    course_code: str
    source: str
    source_url: str
    text: str
    sentiment: str          # "positive", "negative", "neutral"
    sentiment_score: float  # -1.0 to 1.0
    themes: list[str]       # ["outdated", "hard", "practical", ...]
    scraped_at: str


NEGATIVE_KEYWORDS = {
    "outdated": ["outdated", "old material", "out of date", "behind the times", "not current",
                 "old-fashioned", "old school", "hasn't been updated", "needs updating"],
    "not practical": ["not practical", "impractical", "useless", "never use", "waste of time",
                      "pointless", "won't use", "not useful", "not applicable", "irrelevant"],
    "too theoretical": ["too theoretical", "all theory", "no hands-on", "no practice",
                        "no real-world", "too abstract", "not enough coding", "no projects"],
    "poor teaching": ["bad professor", "terrible prof", "awful instructor", "bad teaching",
                      "can't teach", "unclear", "confusing lectures", "disorganized",
                      "unhelpful", "doesn't explain"],
    "too difficult": ["extremely hard", "impossible", "way too hard", "unreasonable",
                      "brutal", "killer class", "too much work", "overwhelming"],
    "boring": ["boring", "dry", "tedious", "uninteresting", "dull", "mind-numbing",
               "puts you to sleep", "snooze"],
    "bad assignments": ["bad homework", "terrible projects", "unfair grading",
                        "busywork", "busy work", "meaningless assignments"],
    "needs modernization": ["needs to be updated", "should teach", "should include",
                            "missing", "doesn't cover", "no mention of", "ignores"],
}

POSITIVE_KEYWORDS = {
    "practical": ["practical", "hands-on", "real-world", "applicable", "useful skills",
                  "actually use", "helpful for jobs", "prepares you", "industry relevant"],
    "well taught": ["great professor", "amazing prof", "best instructor", "good teaching",
                    "explains well", "clear lectures", "well organized", "helpful staff"],
    "valuable": ["valuable", "essential", "must take", "highly recommend", "loved it",
                 "favorite class", "best class", "learned a lot", "eye-opening"],
    "good projects": ["great projects", "good assignments", "interesting projects",
                      "fun labs", "cool projects", "meaningful work"],
    "career relevant": ["helped me get a job", "interview prep", "relevant to industry",
                        "companies want", "career", "internship"],
}


def analyze_sentiment(text: str) -> tuple[str, float, list[str]]:
    """Keyword-based sentiment analysis. Returns (sentiment, score, themes)."""
    lower = text.lower()
    themes = []
    neg_score = 0
    pos_score = 0

    for theme, keywords in NEGATIVE_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in lower)
        if hits > 0:
            themes.append(theme)
            neg_score += hits

    for theme, keywords in POSITIVE_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in lower)
        if hits > 0:
            themes.append(theme)
            pos_score += hits

    total = neg_score + pos_score
    if total == 0:
        return "neutral", 0.0, themes

    score = (pos_score - neg_score) / max(total, 1)
    score = max(-1.0, min(1.0, score))

    if score > 0.2:
        sentiment = "positive"
    elif score < -0.2:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return sentiment, round(score, 2), themes


async def scrape_course_reviews(course_codes: list[str], major_prefix: str) -> list[CourseReview]:
    """
    Scrape student reviews for a list of course codes.
    Searches Reddit (multiple subs), Google, and Atlas for real student opinions.
    """
    all_reviews: list[CourseReview] = []
    sources_succeeded = []

    async def _timed(name, coro, timeout=30):
        try:
            result = await asyncio.wait_for(coro, timeout=timeout)
            if result:
                sources_succeeded.append(f"{name} ({len(result)})")
                all_reviews.extend(result)
        except asyncio.TimeoutError:
            print(f"[Reviews/{name}] Timed out ({timeout}s)")
        except Exception as e:
            print(f"[Reviews/{name}] Failed: {e}")

    await _timed("reddit", _scrape_reddit_reviews(course_codes, major_prefix), 40)
    await _timed("google", _scrape_google_reviews(course_codes, major_prefix), 30)
    await _timed("coursicle", _scrape_coursicle(course_codes, major_prefix), 20)
    await _timed("course_evals", _scrape_course_eval_sites(course_codes, major_prefix), 30)

    print(f"[Reviews Scraper] Sources succeeded: {sources_succeeded}")
    print(f"[Reviews Scraper] Total reviews: {len(all_reviews)}")

    return all_reviews


async def _scrape_reddit_reviews(
    course_codes: list[str], major_prefix: str
) -> list[CourseReview]:
    """Search Reddit for course discussions using the public JSON API."""
    results = []

    subreddits = ["uofm", "umich", "csMajors", "EngineeringStudents"]
    search_terms = []
    for code in course_codes[:15]:
        search_terms.append(code)

    search_terms.append(major_prefix)
    search_terms.append(f"{major_prefix} umich")

    async with httpx.AsyncClient(
        timeout=15,
        headers={
            "User-Agent": "MarketSyncAI/1.0 (Educational Research Project)",
        },
    ) as client:
        for sub in subreddits:
            for term in search_terms[:12]:
                url = f"https://www.reddit.com/r/{sub}/search.json"
                params = {
                    "q": term,
                    "restrict_sr": "on",
                    "sort": "relevance",
                    "limit": 15,
                    "t": "all",
                }

                try:
                    resp = await client.get(url, params=params)
                    if resp.status_code != 200:
                        continue

                    data = resp.json()
                    posts = data.get("data", {}).get("children", [])

                    for post in posts:
                        post_data = post.get("data", {})
                        title = post_data.get("title", "")
                        selftext = post_data.get("selftext", "")
                        permalink = post_data.get("permalink", "")
                        num_comments = post_data.get("num_comments", 0)

                        combined = f"{title} {selftext}"
                        if len(combined) < 30:
                            continue

                        matched_code = _match_course_code(combined, course_codes)
                        if not matched_code:
                            continue

                        clean_text = re.sub(r"\s+", " ", combined).strip()
                        sentiment, score, themes = analyze_sentiment(clean_text)

                        results.append(CourseReview(
                            course_code=matched_code,
                            source="reddit",
                            source_url=f"https://reddit.com{permalink}",
                            text=clean_text[:2000],
                            sentiment=sentiment,
                            sentiment_score=score,
                            themes=themes,
                            scraped_at=datetime.utcnow().isoformat(),
                        ))

                        if num_comments > 0:
                            try:
                                comments_url = f"https://www.reddit.com{permalink}.json"
                                cresp = await client.get(
                                    comments_url, params={"limit": 50, "sort": "top"}
                                )
                                if cresp.status_code == 200:
                                    comment_data = cresp.json()
                                    if isinstance(comment_data, list) and len(comment_data) > 1:
                                        comments = comment_data[1].get("data", {}).get("children", [])
                                        for c in comments[:30]:
                                            body = c.get("data", {}).get("body", "")
                                            if len(body) < 30:
                                                continue
                                            body = re.sub(r"\s+", " ", body).strip()
                                            c_sentiment, c_score, c_themes = analyze_sentiment(body)
                                            results.append(CourseReview(
                                                course_code=matched_code,
                                                source="reddit_comment",
                                                source_url=f"https://reddit.com{permalink}",
                                                text=body[:2000],
                                                sentiment=c_sentiment,
                                                sentiment_score=c_score,
                                                themes=c_themes,
                                                scraped_at=datetime.utcnow().isoformat(),
                                            ))
                            except Exception:
                                pass

                except httpx.HTTPError:
                    continue

                await asyncio.sleep(0.3)

    return results


async def _scrape_coursicle(
    course_codes: list[str], major_prefix: str
) -> list[CourseReview]:
    """Scrape reviews from Coursicle for UMich courses."""
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
        for code in course_codes[:30]:
            parts = code.strip().split()
            if len(parts) != 2:
                continue
            prefix_part, number_part = parts[0], parts[1]

            url = f"https://www.coursicle.com/umich/courses/{prefix_part}/{number_part}/"

            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "lxml")

                review_divs = soup.select(
                    "div.review, div[class*='review'], div[class*='Review']"
                )
                if not review_divs:
                    review_divs = soup.find_all(
                        "div", string=re.compile(r".{40,}", re.DOTALL)
                    )

                page_text = soup.get_text(" ", strip=True)

                review_blocks = re.findall(
                    r'(?:Prof\.|Professor|Junior|Senior|Sophomore|Freshman|COMP|ENG|SCI|MATH)'
                    r'(.{50,600}?)(?=(?:Prof\.|Professor|Junior|Senior|Sophomore|Freshman'
                    r'|Read all|Recent Professors|Recent Semesters|$))',
                    page_text,
                    re.DOTALL,
                )

                if not review_blocks:
                    paragraphs = soup.find_all("p")
                    for p in paragraphs:
                        text = p.get_text(" ", strip=True)
                        if len(text) >= 50 and any(kw in text.lower() for kw in
                            ["class", "professor", "course", "homework", "exam",
                             "lecture", "project", "grade", "learn", "teach"]):
                            review_blocks.append(text)

                for block in review_blocks[:15]:
                    text = re.sub(r"\s+", " ", block).strip()
                    if len(text) < 40:
                        continue

                    sentiment, score, themes = analyze_sentiment(text)

                    results.append(CourseReview(
                        course_code=code,
                        source="coursicle",
                        source_url=url,
                        text=text[:2000],
                        sentiment=sentiment,
                        sentiment_score=score,
                        themes=themes,
                        scraped_at=datetime.utcnow().isoformat(),
                    ))

            except httpx.HTTPError:
                continue

            await asyncio.sleep(0.5)

    return results


async def _scrape_google_reviews(
    course_codes: list[str], major_prefix: str
) -> list[CourseReview]:
    """Search Google for course review pages."""
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
        for code in course_codes[:8]:
            query = f'"{code}" umich review OR opinion OR experience OR thoughts'
            url = f"https://www.google.com/search?q={query.replace(' ', '+')}&num=8"

            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "lxml")

                for g_div in soup.select("div.g, div[data-hveid]"):
                    snippet_el = g_div.select_one(
                        "div[data-sncf], div.VwiC3b, span.aCOpRe"
                    )
                    link_el = g_div.select_one("a")
                    if not snippet_el or not link_el:
                        continue

                    snippet = snippet_el.get_text(" ", strip=True)
                    href = link_el.get("href", "")

                    if len(snippet) < 40:
                        continue

                    sentiment, score, themes = analyze_sentiment(snippet)

                    results.append(CourseReview(
                        course_code=code,
                        source="google",
                        source_url=href,
                        text=snippet[:2000],
                        sentiment=sentiment,
                        sentiment_score=score,
                        themes=themes,
                        scraped_at=datetime.utcnow().isoformat(),
                    ))

            except httpx.HTTPError:
                continue

            await asyncio.sleep(1.5)

    return results


async def _scrape_course_eval_sites(
    course_codes: list[str], major_prefix: str
) -> list[CourseReview]:
    """Search Google for Atlas, RateMyProfessors, and course evaluation results."""
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
        search_queries = []
        for code in course_codes[:12]:
            search_queries.append(f'"{code}" umich atlas course evaluation')
            search_queries.append(f'"{code}" umich student reviews difficult easy')

        for query in search_queries:
            url = f"https://www.google.com/search?q={query.replace(' ', '+')}&num=10"

            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "lxml")

                for g_div in soup.select("div.g, div[data-hveid]"):
                    snippet_el = g_div.select_one(
                        "div[data-sncf], div.VwiC3b, span.aCOpRe"
                    )
                    link_el = g_div.select_one("a")
                    if not snippet_el or not link_el:
                        continue

                    snippet = snippet_el.get_text(" ", strip=True)
                    href = link_el.get("href", "")

                    if len(snippet) < 30:
                        continue

                    matched_code = _match_course_code(snippet + " " + query, course_codes)
                    if not matched_code:
                        continue

                    sentiment, score, themes = analyze_sentiment(snippet)

                    source_name = "course_eval"
                    if "atlas" in href.lower() or "atlas" in snippet.lower():
                        source_name = "atlas"
                    elif "ratemyprofessor" in href.lower():
                        source_name = "ratemyprofessor"

                    results.append(CourseReview(
                        course_code=matched_code,
                        source=source_name,
                        source_url=href,
                        text=snippet[:2000],
                        sentiment=sentiment,
                        sentiment_score=score,
                        themes=themes,
                        scraped_at=datetime.utcnow().isoformat(),
                    ))

            except httpx.HTTPError:
                continue

            await asyncio.sleep(1.5)

    return results


def _match_course_code(text: str, codes: list[str]) -> str | None:
    """Check if text mentions any of the course codes."""
    upper = text.upper()
    for code in codes:
        if code.upper() in upper:
            return code
        no_space = code.replace(" ", "")
        if no_space.upper() in upper:
            return code
    return None


def aggregate_reviews(reviews: list[CourseReview]) -> dict:
    """
    Aggregate reviews per course. Returns summary with sentiment distribution,
    top complaints, top praises, and flagged courses.
    """
    by_course: dict[str, list[CourseReview]] = {}
    for r in reviews:
        by_course.setdefault(r.course_code, []).append(r)

    course_summaries = []
    for code, revs in by_course.items():
        pos = [r for r in revs if r.sentiment == "positive"]
        neg = [r for r in revs if r.sentiment == "negative"]
        neu = [r for r in revs if r.sentiment == "neutral"]

        avg_score = sum(r.sentiment_score for r in revs) / max(len(revs), 1)

        theme_counts: dict[str, int] = {}
        for r in revs:
            for t in r.themes:
                theme_counts[t] = theme_counts.get(t, 0) + 1

        neg_themes = {t: c for t, c in theme_counts.items() if t in NEGATIVE_KEYWORDS}
        pos_themes = {t: c for t, c in theme_counts.items() if t in POSITIVE_KEYWORDS}

        top_complaints = sorted(neg_themes.items(), key=lambda x: -x[1])[:5]
        top_praises = sorted(pos_themes.items(), key=lambda x: -x[1])[:5]

        sample_negative = [
            {"text": r.text[:300], "source": r.source, "url": r.source_url}
            for r in sorted(neg, key=lambda r: r.sentiment_score)[:3]
        ]
        sample_positive = [
            {"text": r.text[:300], "source": r.source, "url": r.source_url}
            for r in sorted(pos, key=lambda r: -r.sentiment_score)[:3]
        ]

        course_summaries.append({
            "course_code": code,
            "total_reviews": len(revs),
            "positive": len(pos),
            "negative": len(neg),
            "neutral": len(neu),
            "avg_sentiment": round(avg_score, 2),
            "satisfaction_pct": round(len(pos) / max(len(revs), 1) * 100, 1),
            "top_complaints": top_complaints,
            "top_praises": top_praises,
            "sample_negative": sample_negative,
            "sample_positive": sample_positive,
        })

    course_summaries.sort(key=lambda x: x["avg_sentiment"])

    flagged = [
        cs for cs in course_summaries
        if cs["avg_sentiment"] < -0.1 or (
            cs["total_reviews"] >= 2 and cs["negative"] > cs["positive"]
        )
    ]

    total_reviews = len(reviews)
    sources = list(set(r.source for r in reviews))

    return {
        "total_reviews": total_reviews,
        "sources": sources,
        "courses_reviewed": len(course_summaries),
        "course_summaries": course_summaries,
        "flagged_courses": flagged,
        "overall_themes": _overall_themes(reviews),
    }


def _overall_themes(reviews: list[CourseReview]) -> list[dict]:
    """Aggregate all themes across all reviews."""
    theme_counts: dict[str, int] = {}
    for r in reviews:
        for t in r.themes:
            theme_counts[t] = theme_counts.get(t, 0) + 1

    return [
        {
            "theme": t,
            "count": c,
            "type": "negative" if t in NEGATIVE_KEYWORDS else "positive",
        }
        for t, c in sorted(theme_counts.items(), key=lambda x: -x[1])
    ]
