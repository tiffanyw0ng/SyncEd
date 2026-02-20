"""
Tech News & Trends Scraper

Scrapes real news from public RSS feeds and APIs:
  1. Google News RSS — free, no auth, real-time news
  2. Hacker News top stories — free Algolia API
  3. TechCrunch RSS — free, no auth

Extracts trending topics, technologies, and industry signals
to complement job posting data for market analysis.
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from datetime import datetime
from html import unescape

import httpx


@dataclass
class NewsArticle:
    title: str
    source: str
    url: str
    summary: str
    published: str
    topics: list[str]


TECH_TOPICS = {
    "agentic AI": ["agentic ai", "ai agent", "ai agents", "autonomous agent"],
    "LLM": ["large language model", "llm", "gpt", "claude", "gemini", "llama"],
    "generative AI": ["generative ai", "genai", "gen ai", "text-to-image", "diffusion model"],
    "Rust": ["rust programming", "rust lang", "rustlang", "memory safe"],
    "vector database": ["vector database", "vector db", "vector search", "pinecone", "weaviate"],
    "RAG": ["retrieval augmented", "rag pipeline", "rag system"],
    "robotics": ["robotics", "robot", "autonomous vehicle", "self-driving"],
    "quantum computing": ["quantum computing", "quantum computer", "qubit"],
    "sustainability": ["sustainability", "green energy", "clean energy", "climate tech", "carbon"],
    "cybersecurity": ["cybersecurity", "cyber attack", "data breach", "zero trust", "ransomware"],
    "edge AI": ["edge ai", "on-device", "edge computing", "tinyml"],
    "blockchain": ["blockchain", "web3", "cryptocurrency", "defi"],
    "cloud computing": ["cloud computing", "aws", "azure", "gcp", "oracle cloud"],
    "semiconductor": ["semiconductor", "chip", "nvidia", "tsmc", "intel", "arm"],
    "biotech": ["biotech", "biotechnology", "gene therapy", "crispr", "drug discovery"],
    "3D printing": ["3d printing", "additive manufacturing", "3d-printed"],
    "digital twin": ["digital twin", "simulation", "iot"],
    "autonomous systems": ["autonomous system", "self-driving", "drone", "uav"],
    "nuclear energy": ["nuclear energy", "nuclear power", "fusion", "small modular reactor", "smr"],
    "aerospace": ["aerospace", "spacex", "nasa", "satellite", "rocket", "orbital"],
    "electric vehicles": ["electric vehicle", "ev battery", "battery technology", "lithium", "solid state battery", "tesla"],
    "renewable energy": ["solar energy", "wind energy", "renewable", "hydrogen fuel", "green hydrogen"],
    "smart manufacturing": ["industry 4.0", "smart factory", "smart manufacturing", "industrial iot"],
    "materials science": ["metamaterial", "graphene", "nanomaterial", "advanced materials", "composites"],
    "civil infrastructure": ["infrastructure", "smart city", "bridge", "construction tech"],
    "marine engineering": ["marine engineering", "ocean energy", "offshore wind", "shipbuilding"],
    "data science": ["data science", "big data", "data engineering", "analytics", "data pipeline"],
    "5G/6G": ["5g", "6g", "telecommunications", "wireless network"],
    "AR/VR": ["augmented reality", "virtual reality", "mixed reality", "metaverse", "spatial computing"],
    "DevOps/MLOps": ["devops", "mlops", "kubernetes", "docker", "ci/cd", "infrastructure as code"],
    "climate science": ["climate change", "global warming", "atmospheric", "weather prediction", "climate model"],
    "biomedical devices": ["medical device", "wearable health", "prosthetic", "implant", "biomedical"],
    "supply chain": ["supply chain", "logistics", "warehouse automation", "last mile"],
}


async def scrape_tech_news(major_queries: list[str] | None = None) -> list[NewsArticle]:
    """Scrape news tailored to a specific major.
    When major_queries provided, ONLY scrape major-specific sources so each major
    gets distinct, relevant articles instead of the same generic tech feed.
    """
    articles: list[NewsArticle] = []
    sources_succeeded = []

    # Major-specific Google News (always runs, uses major queries when available)
    try:
        google_results = await _scrape_google_news_rss(extra_queries=major_queries)
        articles.extend(google_results)
        if google_results:
            sources_succeeded.append(f"google_news ({len(google_results)})")
    except Exception as e:
        print(f"[Google News] Failed: {e}")

    # HN by topic — uses major-specific topics when available
    try:
        hn_recent = await _scrape_hn_by_topic(extra_topics=major_queries)
        articles.extend(hn_recent)
        if hn_recent:
            sources_succeeded.append(f"hn_topics ({len(hn_recent)})")
    except Exception as e:
        print(f"[HN Topics] Failed: {e}")

    # Only add generic RSS feeds when NO major queries (fallback mode)
    if not major_queries:
        generic_feeds = [
            ("https://www.wired.com/feed/rss", "Wired"),
            ("https://feeds.arstechnica.com/arstechnica/index", "Ars Technica"),
            ("https://www.technologyreview.com/feed/", "MIT Tech Review"),
            ("https://venturebeat.com/feed/", "VentureBeat"),
            ("https://www.theverge.com/rss/index.xml", "The Verge"),
            ("https://www.theregister.com/headlines.atom", "The Register"),
            ("https://newatlas.com/index.rss", "New Atlas"),
            ("https://phys.org/rss-feed/technology-news/", "Phys.org"),
            ("https://www.nature.com/subjects/engineering.rss", "Nature"),
        ]
        for url, name in generic_feeds:
            try:
                feed_results = await _scrape_rss_feed(url, name)
                articles.extend(feed_results)
                if feed_results:
                    sources_succeeded.append(f"{name} ({len(feed_results)})")
            except Exception:
                pass

        try:
            hn_results = await _scrape_hn_top_stories()
            articles.extend(hn_results)
            if hn_results:
                sources_succeeded.append(f"hackernews ({len(hn_results)})")
        except Exception:
            pass

        try:
            tc_results = await _scrape_techcrunch_rss()
            articles.extend(tc_results)
            if tc_results:
                sources_succeeded.append(f"techcrunch ({len(tc_results)})")
        except Exception:
            pass

    print(f"[News Scraper] Sources succeeded: {sources_succeeded}")
    print(f"[News Scraper] Total articles: {len(articles)}")

    return articles


async def _scrape_google_news_rss(extra_queries: list[str] | None = None) -> list[NewsArticle]:
    """Scrape Google News RSS. Uses ONLY major-specific queries when provided."""
    results = []

    if extra_queries:
        queries = [q.replace(" ", "+") for q in extra_queries]
    else:
        queries = [
            "technology+engineering+jobs",
            "engineering+education+curriculum",
            "hiring+trends+engineering+2026",
            "artificial+intelligence+industry",
            "software+engineering+trends+2026",
            "robotics+autonomous+systems",
            "semiconductor+chip+industry+news",
            "aerospace+defense+engineering",
            "biotech+medical+device+innovation",
            "climate+tech+clean+energy+engineering",
            "mechanical+engineering+manufacturing",
            "civil+engineering+infrastructure",
            "chemical+engineering+industry",
            "nuclear+energy+engineering+news",
        ]

    async with httpx.AsyncClient(timeout=15) as client:
        for query in queries:
            url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue

                root = ET.fromstring(resp.text)
                for item in root.findall(".//item")[:10]:
                    title = item.findtext("title", "")
                    link = item.findtext("link", "")
                    pub_date = item.findtext("pubDate", "")
                    description = item.findtext("description", "")

                    clean_desc = unescape(re.sub(r"<[^>]+>", " ", description or ""))
                    clean_desc = re.sub(r"\s+", " ", clean_desc).strip()

                    topics = _extract_news_topics(f"{title} {clean_desc}")

                    results.append(NewsArticle(
                        title=unescape(title),
                        source="Google News",
                        url=link,
                        summary=clean_desc[:500],
                        published=pub_date,
                        topics=topics,
                    ))
            except Exception:
                continue

    return results


async def _scrape_hn_top_stories() -> list[NewsArticle]:
    """Scrape top Hacker News stories for tech trends."""
    results = []

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://hn.algolia.com/api/v1/search",
            params={"tags": "front_page", "hitsPerPage": 50},
        )
        if resp.status_code != 200:
            return results

        for hit in resp.json().get("hits", []):
            title = hit.get("title", "")
            url = hit.get("url", f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}")
            points = hit.get("points", 0)

            if points < 20:
                continue

            topics = _extract_news_topics(title)
            if not topics:
                continue

            results.append(NewsArticle(
                title=title,
                source="Hacker News",
                url=url,
                summary=f"{title} ({points} points on HN)",
                published=hit.get("created_at", ""),
                topics=topics,
            ))

    return results


async def _scrape_hn_by_topic(extra_topics: list[str] | None = None) -> list[NewsArticle]:
    """Search HN for stories on key topics. Uses major-specific topics if provided."""
    results = []
    topics = extra_topics[:8] if extra_topics else [
        "machine learning", "robotics", "semiconductor", "aerospace",
        "biotech", "nuclear", "renewable energy", "cybersecurity",
        "quantum computing", "manufacturing", "civil engineering",
        "autonomous", "electric vehicle", "data science",
    ]

    async with httpx.AsyncClient(timeout=15) as client:
        for topic in topics:
            try:
                resp = await client.get(
                    "https://hn.algolia.com/api/v1/search_by_date",
                    params={"query": topic, "tags": "story", "hitsPerPage": 10},
                )
                if resp.status_code != 200:
                    continue

                for hit in resp.json().get("hits", []):
                    title = hit.get("title", "")
                    if not title:
                        continue
                    url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                    points = hit.get("points", 0) or 0
                    found_topics = _extract_news_topics(title)
                    if not found_topics:
                        found_topics = [topic]
                    results.append(NewsArticle(
                        title=title,
                        source="Hacker News",
                        url=url,
                        summary=f"{title} ({points} points on HN)",
                        published=hit.get("created_at", ""),
                        topics=found_topics,
                    ))
            except Exception:
                continue

    return results


async def _scrape_techcrunch_rss() -> list[NewsArticle]:
    """Scrape TechCrunch RSS feed."""
    results = []

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get("https://techcrunch.com/feed/")
        if resp.status_code != 200:
            return results

        root = ET.fromstring(resp.text)
        ns = {"content": "http://purl.org/rss/1.0/modules/content/"}

        for item in root.findall(".//item")[:20]:
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            pub_date = item.findtext("pubDate", "")
            description = item.findtext("description", "")

            clean_desc = unescape(re.sub(r"<[^>]+>", " ", description or ""))
            clean_desc = re.sub(r"\s+", " ", clean_desc).strip()

            topics = _extract_news_topics(f"{title} {clean_desc}")

            results.append(NewsArticle(
                title=unescape(title),
                source="TechCrunch",
                url=link,
                summary=clean_desc[:500],
                published=pub_date,
                topics=topics,
            ))

    return results


async def _scrape_linkedin_news_via_google() -> list[NewsArticle]:
    """
    Scrape LinkedIn articles and industry news via Google News RSS.
    Searches for LinkedIn content about tech industry, hiring trends, etc.
    """
    results = []
    queries = [
        "site:linkedin.com+artificial+intelligence+hiring+trends",
        "site:linkedin.com+engineering+jobs+market+2026",
        "site:linkedin.com+tech+industry+layoffs+hiring",
        "linkedin+workforce+report+engineering",
        "linkedin+jobs+on+the+rise+2026",
        "site:linkedin.com+computer+science+careers+2026",
        "site:linkedin.com+mechanical+engineering+industry",
        "site:linkedin.com+biomedical+engineering+jobs",
        "site:linkedin.com+aerospace+engineering+hiring",
        "site:linkedin.com+data+science+skills+demand",
    ]

    async with httpx.AsyncClient(timeout=15) as client:
        for query in queries:
            url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue

                root = ET.fromstring(resp.text)
                for item in root.findall(".//item")[:5]:
                    title = item.findtext("title", "")
                    link = item.findtext("link", "")
                    pub_date = item.findtext("pubDate", "")
                    description = item.findtext("description", "")

                    clean_desc = unescape(re.sub(r"<[^>]+>", " ", description or ""))
                    clean_desc = re.sub(r"\s+", " ", clean_desc).strip()

                    topics = _extract_news_topics(f"{title} {clean_desc}")

                    source_name = "LinkedIn News"
                    if "linkedin.com" not in link.lower():
                        source_name = "LinkedIn via Google News"

                    results.append(NewsArticle(
                        title=unescape(title),
                        source=source_name,
                        url=link,
                        summary=clean_desc[:500],
                        published=pub_date,
                        topics=topics,
                    ))
            except Exception:
                continue

    return results


async def _scrape_rss_feed(feed_url: str, source_name: str, max_items: int = 25) -> list[NewsArticle]:
    """Generic RSS feed scraper — works for any standard RSS/Atom feed."""
    results = []

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(feed_url)
        if resp.status_code != 200:
            return results

        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError:
            return results

        items = root.findall(".//item")
        if not items:
            items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

        for item in items[:max_items]:
            title = (
                item.findtext("title", "")
                or item.findtext("{http://www.w3.org/2005/Atom}title", "")
            )
            link = (
                item.findtext("link", "")
                or (item.find("{http://www.w3.org/2005/Atom}link") or {}).get("href", "")
            )
            pub_date = (
                item.findtext("pubDate", "")
                or item.findtext("{http://www.w3.org/2005/Atom}published", "")
                or item.findtext("{http://www.w3.org/2005/Atom}updated", "")
            )
            description = (
                item.findtext("description", "")
                or item.findtext("{http://www.w3.org/2005/Atom}summary", "")
                or item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded", "")
            )

            title = unescape(title) if title else ""
            clean_desc = unescape(re.sub(r"<[^>]+>", " ", description or ""))
            clean_desc = re.sub(r"\s+", " ", clean_desc).strip()

            if not title:
                continue

            topics = _extract_news_topics(f"{title} {clean_desc}")

            results.append(NewsArticle(
                title=title,
                source=source_name,
                url=link or "",
                summary=clean_desc[:500],
                published=pub_date or "",
                topics=topics,
            ))

    return results


def _extract_news_topics(text: str) -> list[str]:
    found = []
    lower = text.lower()
    for topic, keywords in TECH_TOPICS.items():
        if any(kw in lower for kw in keywords):
            found.append(topic)
    return found


def compute_trend_signals(articles: list[NewsArticle]) -> dict:
    """Aggregate news into trend signals for the market analysis."""
    topic_counts: dict[str, int] = {}
    topic_articles: dict[str, list[dict]] = {}

    for article in articles:
        for topic in article.topics:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
            if topic not in topic_articles:
                topic_articles[topic] = []
            if len(topic_articles[topic]) < 3:
                topic_articles[topic].append({
                    "title": article.title,
                    "source": article.source,
                    "url": article.url,
                })

    sorted_trends = sorted(topic_counts.items(), key=lambda x: -x[1])

    return {
        "trending_topics": sorted_trends,
        "topic_articles": topic_articles,
        "total_articles_scanned": len(articles),
        "sources": list(set(a.source for a in articles)),
    }
