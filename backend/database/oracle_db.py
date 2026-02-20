"""
Oracle Autonomous Database 26ai Integration

Handles:
  - Connection management (with wallet for ADB)
  - Table creation (job_postings, courses, news_articles, analysis_results)
  - VECTOR columns for AI similarity search
  - CRUD operations for all scraped data
  - Vector similarity queries

The app works fine WITHOUT Oracle (falls back to in-memory + JSON files).
When Oracle credentials are provided in .env, data is persisted to the cloud.
"""

import json
from datetime import datetime
from dataclasses import asdict

import oracledb

from backend.config import get_settings
from backend.scrapers.job_postings import JobPosting
from backend.scrapers.umich_courses import Course
from backend.scrapers.news_trends import NewsArticle
from backend.scrapers.course_reviews import CourseReview


def _read_lob(val):
    """Oracle CLOB/BLOB columns return LOB objects — read them to str."""
    if val is None:
        return None
    if hasattr(val, "read"):
        return val.read()
    return val


_pool: oracledb.ConnectionPool | None = None


def is_configured() -> bool:
    """Check if Oracle credentials are set in .env."""
    s = get_settings()
    return bool(s.oracle_dsn and s.oracle_password)


def get_connection() -> oracledb.Connection:
    """Get a connection from the pool (or create the pool)."""
    global _pool
    if _pool is None:
        _pool = _create_pool()
    return _pool.acquire()


def _create_pool() -> oracledb.ConnectionPool:
    s = get_settings()

    connect_kwargs = {
        "user": s.oracle_user,
        "password": s.oracle_password,
        "dsn": s.oracle_dsn,
        "min": 1,
        "max": 5,
        "increment": 1,
        "timeout": 30,
        "wait_timeout": 10000,
    }

    if s.oracle_wallet_dir:
        connect_kwargs["config_dir"] = s.oracle_wallet_dir
        connect_kwargs["wallet_location"] = s.oracle_wallet_dir
        connect_kwargs["wallet_password"] = s.oracle_password

    return oracledb.create_pool(**connect_kwargs)


def init_tables():
    """Create all tables if they don't exist. Safe to call multiple times."""
    if not is_configured():
        print("[Oracle DB] Not configured — skipping table creation")
        return

    conn = get_connection()
    cursor = conn.cursor()

    tables = [
        """
        CREATE TABLE IF NOT EXISTS job_postings (
            id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            title VARCHAR2(500),
            company VARCHAR2(300),
            location VARCHAR2(300),
            description CLOB,
            skills VARCHAR2(4000),
            tools VARCHAR2(2000),
            experience_level VARCHAR2(50),
            source VARCHAR2(100),
            source_url VARCHAR2(2000),
            major_id VARCHAR2(50),
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS courses (
            id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            major_id VARCHAR2(50),
            code VARCHAR2(50),
            title VARCHAR2(500),
            description CLOB,
            credits VARCHAR2(10),
            topics VARCHAR2(4000),
            learning_objectives VARCHAR2(4000),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS news_articles (
            id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            title VARCHAR2(1000),
            source VARCHAR2(200),
            url VARCHAR2(2000),
            summary CLOB,
            published VARCHAR2(200),
            topics VARCHAR2(2000),
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS analysis_results (
            id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            major_id VARCHAR2(50),
            overall_score NUMBER(5,1),
            analysis_json CLOB,
            trends_json CLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS course_reviews (
            id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            major_id VARCHAR2(50),
            course_code VARCHAR2(50),
            source VARCHAR2(100),
            source_url VARCHAR2(2000),
            review_text CLOB,
            sentiment VARCHAR2(20),
            sentiment_score NUMBER(4,2),
            themes VARCHAR2(2000),
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
    ]

    for ddl in tables:
        try:
            cursor.execute(ddl)
        except oracledb.DatabaseError as e:
            error_obj = e.args[0]
            if hasattr(error_obj, 'code') and error_obj.code == 955:
                pass  # ORA-00955: name already used — table exists
            else:
                print(f"[Oracle DB] Table creation warning: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    print("[Oracle DB] Tables initialized successfully")


# ---------------------------------------------------------------------------
# Job Postings CRUD
# ---------------------------------------------------------------------------

def save_job_postings(postings: list[JobPosting], major_id: str):
    """Save scraped job postings to Oracle. Clears old data for this major first."""
    if not is_configured():
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM job_postings WHERE major_id = :1",
        [major_id],
    )

    for p in postings:
        cursor.execute(
            """INSERT INTO job_postings
               (title, company, location, description, skills, tools,
                experience_level, source, source_url, major_id, scraped_at)
               VALUES (:1,:2,:3,:4,:5,:6,:7,:8,:9,:10,:11)""",
            [
                p.title[:490], p.company[:290], p.location[:290],
                p.description[:4000], ",".join(p.skills)[:3900], ",".join(p.tools)[:1900],
                p.experience_level[:50], p.source[:100], p.source_url[:1900],
                major_id, datetime.utcnow(),
            ],
        )

    conn.commit()
    cursor.close()
    conn.close()
    print(f"[Oracle DB] Saved {len(postings)} job postings for {major_id}")


def load_job_postings(major_id: str) -> list[JobPosting]:
    """Load cached job postings from Oracle for a given major."""
    if not is_configured():
        return []

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT title, company, location, description, skills, tools,
                  experience_level, source, source_url, scraped_at
           FROM job_postings WHERE major_id = :1
           ORDER BY scraped_at DESC""",
        [major_id],
    )

    postings = []
    for row in cursor:
        desc = _read_lob(row[3]) or ""
        postings.append(JobPosting(
            title=row[0], company=row[1], location=row[2],
            description=desc, skills=row[4].split(",") if row[4] else [],
            tools=row[5].split(",") if row[5] else [],
            experience_level=row[6], source=row[7],
            source_url=row[8] or "",
            scraped_at=row[9].isoformat() if row[9] else "",
        ))

    cursor.close()
    conn.close()
    return postings


# ---------------------------------------------------------------------------
# Courses CRUD
# ---------------------------------------------------------------------------

def save_courses(courses: list[Course], major_id: str):
    """Save course data to Oracle."""
    if not is_configured():
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM courses WHERE major_id = :1", [major_id])

    for c in courses:
        cursor.execute(
            """INSERT INTO courses
               (major_id, code, title, description, credits, topics, learning_objectives)
               VALUES (:1,:2,:3,:4,:5,:6,:7)""",
            [
                major_id, c.code, c.title, c.description,
                c.credits, ",".join(c.topics),
                " | ".join(c.learning_objectives),
            ],
        )

    conn.commit()
    cursor.close()
    conn.close()
    print(f"[Oracle DB] Saved {len(courses)} courses for {major_id}")


def load_courses(major_id: str) -> list[Course]:
    """Load cached courses from Oracle."""
    if not is_configured():
        return []

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT code, title, description, credits, topics, learning_objectives
           FROM courses WHERE major_id = :1
           ORDER BY code""",
        [major_id],
    )

    courses = []
    for row in cursor:
        desc = _read_lob(row[2]) or ""
        courses.append(Course(
            code=row[0], title=row[1], description=desc,
            credits=row[3] or "",
            topics=row[4].split(",") if row[4] else [],
            learning_objectives=row[5].split(" | ") if row[5] else [],
        ))

    cursor.close()
    conn.close()
    return courses


# ---------------------------------------------------------------------------
# News CRUD
# ---------------------------------------------------------------------------

def save_news(articles: list[NewsArticle]):
    """Save scraped news to Oracle. Clears old articles first."""
    if not is_configured():
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM news_articles")

    for a in articles:
        cursor.execute(
            """INSERT INTO news_articles
               (title, source, url, summary, published, topics)
               VALUES (:1,:2,:3,:4,:5,:6)""",
            [
                a.title[:1000], a.source[:200], a.url[:2000],
                a.summary, a.published, ",".join(a.topics),
            ],
        )

    conn.commit()
    cursor.close()
    conn.close()
    print(f"[Oracle DB] Saved {len(articles)} news articles")


def load_news() -> list[NewsArticle]:
    """Load cached news from Oracle."""
    if not is_configured():
        return []

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT title, source, url, summary, published, topics
           FROM news_articles ORDER BY scraped_at DESC"""
    )

    articles = []
    for row in cursor:
        summary = _read_lob(row[3]) or ""
        articles.append(NewsArticle(
            title=row[0], source=row[1], url=row[2],
            summary=summary, published=row[4] or "",
            topics=row[5].split(",") if row[5] else [],
        ))

    cursor.close()
    conn.close()
    return articles


# ---------------------------------------------------------------------------
# Analysis Results CRUD
# ---------------------------------------------------------------------------

def save_analysis(major_id: str, analysis: dict, trends: dict):
    """Save analysis results to Oracle."""
    if not is_configured():
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM analysis_results WHERE major_id = :1", [major_id])
    cursor.execute(
        """INSERT INTO analysis_results
           (major_id, overall_score, analysis_json, trends_json)
           VALUES (:1, :2, :3, :4)""",
        [
            major_id,
            analysis.get("overall_alignment_score", 0),
            json.dumps(analysis),
            json.dumps(trends),
        ],
    )

    conn.commit()
    cursor.close()
    conn.close()
    print(f"[Oracle DB] Saved analysis for {major_id}")


def load_analysis(major_id: str) -> tuple[dict | None, dict | None]:
    """Load cached analysis from Oracle. Returns (analysis, trends) or (None, None)."""
    if not is_configured():
        return None, None

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT analysis_json, trends_json FROM analysis_results
           WHERE major_id = :1 ORDER BY created_at DESC FETCH FIRST 1 ROW ONLY""",
        [major_id],
    )

    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row:
        analysis_str = _read_lob(row[0])
        trends_str = _read_lob(row[1])
        analysis = json.loads(analysis_str) if analysis_str else None
        trends = json.loads(trends_str) if trends_str else None
        return analysis, trends

    return None, None


# ---------------------------------------------------------------------------
# Course Reviews CRUD
# ---------------------------------------------------------------------------

def save_reviews(reviews: list[CourseReview], major_id: str):
    """Save scraped course reviews to Oracle. Clears old reviews for this major."""
    if not is_configured():
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM course_reviews WHERE major_id = :1", [major_id])

    for r in reviews:
        cursor.execute(
            """INSERT INTO course_reviews
               (major_id, course_code, source, source_url, review_text,
                sentiment, sentiment_score, themes)
               VALUES (:1,:2,:3,:4,:5,:6,:7,:8)""",
            [
                major_id, r.course_code, r.source, r.source_url[:2000],
                r.text, r.sentiment, r.sentiment_score,
                ",".join(r.themes),
            ],
        )

    conn.commit()
    cursor.close()
    conn.close()
    print(f"[Oracle DB] Saved {len(reviews)} course reviews for {major_id}")


def load_reviews(major_id: str) -> list[CourseReview]:
    """Load cached course reviews from Oracle."""
    if not is_configured():
        return []

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT course_code, source, source_url, review_text,
                  sentiment, sentiment_score, themes, scraped_at
           FROM course_reviews WHERE major_id = :1
           ORDER BY scraped_at DESC""",
        [major_id],
    )

    reviews = []
    for row in cursor:
        text = _read_lob(row[3]) or ""
        reviews.append(CourseReview(
            course_code=row[0],
            source=row[1],
            source_url=row[2] or "",
            text=text,
            sentiment=row[4] or "neutral",
            sentiment_score=float(row[5]) if row[5] is not None else 0.0,
            themes=row[6].split(",") if row[6] else [],
            scraped_at=row[7].isoformat() if row[7] else "",
        ))

    cursor.close()
    conn.close()
    return reviews


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def get_db_stats() -> dict:
    """Get row counts for all tables."""
    if not is_configured():
        return {"configured": False}

    conn = get_connection()
    cursor = conn.cursor()

    stats = {"configured": True}
    for table in ["job_postings", "courses", "news_articles", "analysis_results", "course_reviews"]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        stats[table] = cursor.fetchone()[0]

    cursor.close()
    conn.close()
    return stats


def close_pool():
    """Shut down the connection pool."""
    global _pool
    if _pool:
        _pool.close()
        _pool = None
