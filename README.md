# Market-Sync AI

**Curriculum-Market Synchronization Engine** — A Decision Intelligence platform that analyzes the gap between university curriculum (U-M College of Engineering — all 12 departments) and real-time job market demands using live web scraping.

Built on **Oracle Cloud Infrastructure (OCI)**.

## Architecture

```
┌────────────────────────────────────────────────────────┐
│                   Frontend (React 19 + Vite)           │
│          Strategic Dashboard for Deans & Faculty        │
│     [Major Selector] → Pick any CoE department          │
├────────────────────────────────────────────────────────┤
│                  FastAPI Backend (Python)                │
├──────────────┬────────────────┬────────────────────────┤
│  Academic    │  Intelligence  │  Market Stream          │
│  Stream      │  Engine        │  (Live Web Scraping)    │
│              │                │                         │
│  U-M CoE     │  TF-IDF +     │  RemoteOK JSON API      │
│  Bulletin    │  Cosine        │  HN "Who's Hiring?"     │
│  Scraper     │  Similarity    │  Google News RSS        │
│  (12 majors) │  Gap Analysis  │  TechCrunch RSS         │
│              │                │  Indeed (fallback)       │
├──────────────┴────────────────┴────────────────────────┤
│             Oracle Cloud Infrastructure                 │
│   OCI Compute  │  AI Database 26ai  │  OCI GenAI        │
│   (Scraping)   │  (Vector Storage)  │  (Gap Analysis)   │
└────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# (Optional) Copy and fill in Oracle Cloud credentials for production
cp .env.example .env

# Start the API server (from project root)
cd ..
python -m uvicorn backend.api.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 3. Open the Dashboard

Go to **http://localhost:3000** — the Vite dev server proxies `/api/*` calls to the backend on port 8000.

## What Happens When You Run It

On startup, the backend automatically:

1. **Scrapes real job postings** from RemoteOK (JSON API) and HN "Who's Hiring?" (Algolia API)
2. **Scrapes real tech news** from Google News RSS, TechCrunch RSS, and HN top stories
3. **Loads U-M EECS course data** (tries the U-M bulletin site, falls back to curated seed data)
4. **Vectorizes everything** with TF-IDF and runs cosine similarity to compute alignment scores
5. **Generates gap analysis** and new course recommendations

When you click a different major in the UI, it re-runs steps 1-5 with **major-specific job search queries** (e.g. selecting Mechanical Engineering searches for "mechanical engineer", "robotics engineer", "automotive engineer", etc.).

### Live Scraping Results (actual output from logs)

```
[Job Scraper] Sources tried: ['remoteok', 'hn_hiring', 'indeed']
[Job Scraper] Sources succeeded: ['remoteok (50)', 'hn_hiring (60)']
[Job Scraper] Total postings: 110

[News Scraper] Sources succeeded: ['google_news (40)', 'hackernews (3)', 'techcrunch (20)']
[News Scraper] Total articles: 63
```

## Supported Majors (12 Departments)

| ID | Department | Course Prefix | Job Search Queries |
|----|-----------|---------------|-------------------|
| eecs | Electrical Engineering & Computer Science | EECS | software engineer, ML engineer, data engineer, AI engineer |
| me | Mechanical Engineering | MECHENG | mechanical engineer, manufacturing engineer, robotics engineer |
| bme | Biomedical Engineering | BIOMEDE | biomedical engineer, medical device engineer, biotech engineer |
| cee | Civil & Environmental Engineering | CEE | civil engineer, structural engineer, environmental engineer |
| cheme | Chemical Engineering | CHE | chemical engineer, process engineer, materials engineer |
| aero | Aerospace Engineering | AEROSP | aerospace engineer, propulsion engineer, avionics engineer |
| ioe | Industrial & Operations Engineering | IOE | operations engineer, supply chain analyst, data analyst |
| matscie | Materials Science & Engineering | MATSCIE | materials engineer, semiconductor engineer |
| name | Naval Architecture & Marine Engineering | NAVARCH | naval architect, marine engineer |
| ners | Nuclear Engineering & Radiological Sciences | NERS | nuclear engineer, reactor engineer |
| climate | Climate & Space Sciences | CLIMATE | atmospheric scientist, climate researcher |
| rob | Robotics | ROB | robotics engineer, controls engineer, autonomous systems engineer |

## Key Features

- **Multi-Major Support** — click any of 12 CoE departments to analyze
- **Market Alignment Score** (0-100%) for each course
- **Gap Analysis** — click any course to see covered vs. missing skills, obsolete topics, and recommended additions
- **New Course Recommendations** — dynamically generated per major (e.g. "MECHENG 498 - Digital Twins & Physics-Informed Simulation")
- **2026 Trend Tracking** — emerging skills like Rust, Vector DBs, Agentic AI, Digital Twins
- **Tech News Feed** — live articles from Google News, TechCrunch, and HN with topic detection
- **Live Data Sources** — shows exactly where data was scraped from and how many results
- **Real-time Refresh** — re-scrape and re-analyze on demand with the Refresh button

## How the Scraping Works

### Job Postings (Market Stream)

| Source | Method | Auth | What It Returns |
|--------|--------|------|----------------|
| **RemoteOK** | `GET https://remoteok.com/api` | None (free JSON API) | ~50 remote job postings with title, company, description, tags |
| **HN Who's Hiring** | `GET https://hn.algolia.com/api/v1/...` | None (free Algolia API) | ~60 real job postings from the latest monthly hiring thread |
| **Indeed** | HTML scraping of search results | None (public page, often blocked) | 0-40 postings (Indeed blocks automated requests frequently) |
| **Seed Data** | Hardcoded fallback | N/A | 15 curated postings (only used if ALL live sources fail) |

### Tech News (Trend Signals)

| Source | Method | Auth | What It Returns |
|--------|--------|------|----------------|
| **Google News** | RSS feed: `news.google.com/rss/search?q=...` | None | ~40 articles matching tech/engineering queries |
| **TechCrunch** | RSS feed: `techcrunch.com/feed/` | None | ~20 latest tech articles |
| **Hacker News** | `GET https://hn.algolia.com/api/v1/search?tags=front_page` | None | Top HN stories with tech topic detection |

### University Courses (Academic Stream)

| Source | Method | Auth | What It Returns |
|--------|--------|------|----------------|
| **U-M Bulletin** | HTML scraping of `bulletin.engin.umich.edu/courses/{dept}/` | None | Course codes, titles, descriptions, learning objectives |
| **Seed Data** | Curated per-major fallback | N/A | 9-13 key courses per department (used when bulletin scraping fails) |

## Oracle Autonomous Database 26ai Setup (Step by Step)

This project has **built-in Oracle DB integration**. When you provide your credentials in `.env`, all scraped data (job postings, courses, news, analysis results) is automatically persisted to Oracle Cloud. Without credentials, everything still works using local JSON cache.

### What You Need (4 Keys)

| Key | What It Is | Where to Get It |
|-----|-----------|----------------|
| `ORACLE_DSN` | Connection string to your database | OCI Console → Autonomous Database → DB Connection → Connection Strings |
| `ORACLE_USER` | Database username | Default is `ADMIN` (set during DB creation) |
| `ORACLE_PASSWORD` | Database password | You set this when creating the ADB instance |
| `ORACLE_WALLET_DIR` | Path to your downloaded wallet folder | OCI Console → Autonomous Database → DB Connection → Download Wallet |

### Step 1: Create a Free Oracle Cloud Account

1. Go to **https://cloud.oracle.com/sign-up**
2. Sign up for the **Always Free** tier (no credit card required for free resources)
3. Pick a home region (e.g. `us-ashburn-1` or `us-chicago-1`)
4. Wait for your tenancy to be provisioned (~2 minutes)

### Step 2: Create an Autonomous Database

1. In the OCI Console, go to **Oracle Database → Autonomous Database**
2. Click **Create Autonomous Database**
3. Fill in:
   - **Display name**: `marketsync`
   - **Database name**: `marketsync`
   - **Workload type**: Transaction Processing (or Data Warehouse — both work)
   - **Deployment type**: Serverless
   - **Always Free**: Toggle ON (this is the free tier)
   - **Database version**: 23ai (or latest available)
   - **ADMIN password**: Pick something strong — **this is your `ORACLE_PASSWORD`**
4. Click **Create Autonomous Database**
5. Wait ~2 minutes for it to say "Available"

### Step 3: Download the Wallet

The wallet is a zip file containing TLS certificates that let your code connect securely.

1. On your ADB's detail page, click **DB Connection**
2. Click **Download Wallet**
3. Set a wallet password (can be the same as your ADMIN password)
4. Save the zip file and **unzip it** somewhere, e.g.:

```bash
mkdir -p ~/oracle-wallet
cd ~/oracle-wallet
unzip ~/Downloads/Wallet_marketsync.zip
```

The folder should contain files like `cwallet.sso`, `tnsnames.ora`, `sqlnet.ora`, etc.

**This folder path is your `ORACLE_WALLET_DIR`** — e.g. `/Users/tiffany/oracle-wallet`

### Step 4: Get the Connection String (DSN)

1. On your ADB's detail page, click **DB Connection**
2. Under **Connection Strings**, you'll see entries like `marketsync_high`, `marketsync_tp`, etc.
3. Click **Copy** next to any one (recommend `_high` or `_tp`)
4. **This is your `ORACLE_DSN`**

It looks something like:
```
(description= (retry_count=20)(retry_delay=3)(address=(protocol=tcps)(port=1522)(host=adb.us-ashburn-1.oraclecloud.com))(connect_data=(service_name=abc123_marketsync_high.adb.oraclecloud.com))(security=(ssl_server_dn_match=yes)))
```

### Step 5: Fill in Your `.env`

```bash
cd backend
cp .env.example .env
```

Then edit `.env` and fill in the 4 values:

```env
ORACLE_DSN=(description= (retry_count=20)(...your full connection string...))
ORACLE_USER=ADMIN
ORACLE_PASSWORD=YourStrongPassword123!
ORACLE_WALLET_DIR=/Users/tiffany/oracle-wallet
```

### Step 6: Run the App

```bash
# From project root
python -m uvicorn backend.api.main:app --reload --port 8000
```

You should see in the logs:

```
[Startup] Oracle DB detected — initializing tables...
[Oracle DB] Tables initialized successfully
[Job Scraper] Total postings: 110
[Oracle DB] Saved 110 job postings for eecs
[Oracle DB] Saved 13 courses for eecs
[Oracle DB] Saved analysis for eecs
[News Scraper] Total articles: 63
[Oracle DB] Saved 63 news articles
```

### Step 7: Verify It's Working

Hit the DB status endpoint:

```bash
curl http://localhost:8000/api/db-status
```

You should see:
```json
{
  "configured": true,
  "job_postings": 110,
  "courses": 13,
  "news_articles": 63,
  "analysis_results": 1
}
```

### What Gets Stored in Oracle

| Table | What's In It | Populated By |
|-------|-------------|-------------|
| `job_postings` | Every scraped job (title, company, skills, source URL) | Live scraping from RemoteOK, HN, Indeed |
| `courses` | U-M course catalog (code, title, description, topics) | Bulletin scraping + seed data |
| `news_articles` | Tech news (title, source, summary, detected topics) | Google News RSS, TechCrunch, HN |
| `analysis_results` | Full gap analysis JSON + trends JSON per major | Computed after each scrape |

When you switch majors in the UI, if data already exists in Oracle, it loads instantly from the DB instead of re-scraping.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/majors` | List all 12 engineering departments |
| POST | `/api/majors/{id}/analyze` | Trigger scraping + analysis for a major |
| GET | `/api/dashboard?major=eecs` | Dashboard data (scores, gaps, recommendations) |
| GET | `/api/courses?major=eecs` | All courses with alignment scores |
| GET | `/api/courses/{code}?major=eecs` | Detailed gap analysis for one course |
| GET | `/api/market-trends?major=eecs` | Skill demand data from scraped jobs |
| GET | `/api/recommendations?major=eecs` | New course recommendations |
| GET | `/api/news` | Latest scraped tech news + trending topics |
| POST | `/api/refresh?major=eecs` | Re-scrape everything and re-analyze |

## Tech Stack

- **Backend**: Python 3.13, FastAPI, scikit-learn, BeautifulSoup, httpx, oracledb
- **Frontend**: React 19, Vite 6, Recharts
- **Live Scraping**: RemoteOK API, HN Algolia API, Google News RSS, TechCrunch RSS
- **AI/ML**: TF-IDF vectorization + cosine similarity (local) / OCI GenAI embeddings (production)
- **Cloud**: Oracle Cloud Infrastructure (OCI Functions, AI Database 26ai, OCI GenAI)

## Project Structure

```
ai-hackathon/
├── backend/
│   ├── api/
│   │   └── main.py              # FastAPI routes (per-major endpoints)
│   ├── scrapers/
│   │   ├── umich_courses.py     # U-M bulletin scraper (12 majors + seed data)
│   │   ├── job_postings.py      # Job scraper (RemoteOK, HN, Indeed)
│   │   └── news_trends.py       # News scraper (Google News, TechCrunch, HN)
│   ├── processing/
│   │   └── vectorizer.py        # TF-IDF vectorization + gap analysis engine
│   ├── data/                    # Cached scraping results (auto-generated)
│   ├── config.py                # Settings (OCI credentials, thresholds)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Main app with major selector
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx    # Alignment scores, top gaps, best aligned
│   │   │   ├── CoursesView.jsx  # All courses with drill-down
│   │   │   ├── MarketTrends.jsx # Skill demand charts
│   │   │   ├── Recommendations.jsx  # New course suggestions
│   │   │   └── NewsFeed.jsx     # Live tech news + trending topics
│   │   ├── components/
│   │   │   ├── ScoreRing.jsx    # Circular alignment score visualization
│   │   │   └── CourseDetailPanel.jsx  # Slide-out detail panel
│   │   └── styles/
│   │       └── global.css       # Dark theme UI
│   ├── package.json
│   └── vite.config.js
├── run.sh                       # Start both servers
└── README.md
```
