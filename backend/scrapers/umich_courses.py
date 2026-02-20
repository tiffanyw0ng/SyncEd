"""
U-M College of Engineering Course Scraper — Academic Stream

Uses Playwright (headless Chromium) to bypass Cloudflare protection on
bulletin.engin.umich.edu, then parses real course data for every CoE major.

Falls back to cached JSON → seed data when Playwright is unavailable.
"""

import json
import os
import re
from dataclasses import dataclass, asdict, field
from pathlib import Path

from bs4 import BeautifulSoup

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "0")

DATA_DIR = Path(__file__).parent.parent / "data"


@dataclass
class Course:
    code: str
    title: str
    description: str
    credits: str
    topics: list[str]
    learning_objectives: list[str]


@dataclass
class Major:
    id: str
    name: str
    prefix: str
    bulletin_url: str
    job_search_queries: list[str] = field(default_factory=list)
    news_search_queries: list[str] = field(default_factory=list)


ENGINEERING_MAJORS: list[Major] = [
    Major("cs", "Computer Science", "EECS",
          "https://bulletin.engin.umich.edu/courses/eecs/",
          ["software engineer", "backend engineer", "frontend developer", "full stack developer",
           "machine learning engineer", "data scientist", "AI engineer", "cloud engineer",
           "DevOps engineer", "site reliability engineer", "cybersecurity analyst"],
          ["software engineering trends", "artificial intelligence industry",
           "computer science careers 2026", "cybersecurity threats",
           "cloud computing AWS Azure", "machine learning engineer demand",
           "tech hiring trends 2026", "LLM AI agents industry"]),
    Major("ce", "Computer Engineering", "EECS",
          "https://bulletin.engin.umich.edu/courses/eecs/",
          ["embedded systems engineer", "firmware engineer", "FPGA engineer", "hardware engineer",
           "computer architect", "ASIC design engineer", "IoT engineer", "systems engineer",
           "verification engineer", "RTL design engineer"],
          ["semiconductor chip industry news", "embedded systems IoT",
           "FPGA ASIC design industry", "hardware engineering trends",
           "computer architecture news", "chip shortage supply chain",
           "edge computing hardware", "RISC-V processor news"]),
    Major("ee", "Electrical Engineering", "EECS",
          "https://bulletin.engin.umich.edu/courses/eecs/",
          ["electrical engineer", "RF engineer", "signal processing engineer", "power systems engineer",
           "analog design engineer", "communications engineer", "control systems engineer",
           "semiconductor engineer", "VLSI engineer", "photonics engineer"],
          ["electrical engineering industry news", "power grid renewable energy",
           "5G 6G telecommunications", "semiconductor manufacturing",
           "electric vehicle battery technology", "signal processing radar",
           "photonics optics industry", "power electronics trends"]),
    Major("me", "Mechanical Engineering", "MECHENG",
          "https://bulletin.engin.umich.edu/courses/me/",
          ["mechanical engineer", "manufacturing engineer", "robotics engineer", "automotive engineer", "HVAC engineer"],
          ["mechanical engineering industry news", "manufacturing automation 2026",
           "automotive engineering electric vehicles", "3D printing additive manufacturing",
           "HVAC sustainable building", "robotics manufacturing industry",
           "mechanical design CAD trends", "smart manufacturing Industry 4.0"]),
    Major("bme", "Biomedical Engineering", "BIOMEDE",
          "https://bulletin.engin.umich.edu/courses/bme/",
          ["biomedical engineer", "medical device engineer", "clinical engineer", "biotech engineer", "tissue engineer"],
          ["biomedical engineering news", "medical device FDA approval",
           "biotechnology drug discovery", "tissue engineering regenerative medicine",
           "wearable health technology", "CRISPR gene therapy",
           "biomedical imaging MRI", "prosthetics bionics innovation"]),
    Major("cee", "Civil & Environmental Engineering", "CEE",
          "https://bulletin.engin.umich.edu/courses/cee/",
          ["civil engineer", "structural engineer", "environmental engineer", "transportation engineer", "water resources engineer"],
          ["civil engineering infrastructure news", "structural engineering bridge construction",
           "environmental engineering water treatment", "smart city transportation",
           "sustainable construction green building", "climate change infrastructure",
           "geotechnical engineering foundation", "transportation autonomous vehicles"]),
    Major("cheme", "Chemical Engineering", "CHE",
          "https://bulletin.engin.umich.edu/courses/che/",
          ["chemical engineer", "process engineer", "materials engineer", "petroleum engineer", "pharmaceutical engineer"],
          ["chemical engineering industry news", "pharmaceutical manufacturing",
           "petroleum refining energy transition", "polymer materials innovation",
           "sustainable chemistry green engineering", "hydrogen fuel cell production",
           "process automation chemical plants", "battery chemistry lithium"]),
    Major("aero", "Aerospace Engineering", "AEROSP",
          "https://bulletin.engin.umich.edu/courses/aero/",
          ["aerospace engineer", "propulsion engineer", "avionics engineer", "flight systems engineer", "satellite engineer"],
          ["aerospace engineering news", "SpaceX NASA rocket launch",
           "satellite constellation Starlink", "aviation electric aircraft",
           "defense aerospace military", "hypersonic flight research",
           "space exploration Mars moon", "drone UAV autonomous flight"]),
    Major("ioe", "Industrial & Operations Engineering", "IOE",
          "https://bulletin.engin.umich.edu/courses/ioe/",
          ["operations engineer", "supply chain analyst", "data analyst", "industrial engineer", "quality engineer"],
          ["industrial engineering operations news", "supply chain logistics automation",
           "warehouse robotics automation", "operations research optimization",
           "manufacturing quality control", "data analytics business intelligence",
           "lean six sigma industry", "workforce planning AI"]),
    Major("matscie", "Materials Science & Engineering", "MATSCIE",
          "https://bulletin.engin.umich.edu/courses/matscie/",
          ["materials engineer", "metallurgical engineer", "semiconductor engineer", "composites engineer"],
          ["materials science engineering news", "nanotechnology research",
           "semiconductor materials innovation", "composites carbon fiber aerospace",
           "advanced ceramics industry", "battery materials solid state",
           "metamaterials research", "sustainable materials recycling"]),
    Major("name", "Naval Architecture & Marine Engineering", "NAVARCH",
          "https://bulletin.engin.umich.edu/courses/name/",
          ["naval architect", "marine engineer", "ocean engineer", "offshore engineer"],
          ["naval architecture ship design news", "marine engineering offshore",
           "shipbuilding industry trends", "offshore wind energy",
           "autonomous underwater vehicles", "ocean engineering renewable energy",
           "maritime shipping decarbonization", "submarine naval defense"]),
    Major("ners", "Nuclear Engineering & Radiological Sciences", "NERS",
          "https://bulletin.engin.umich.edu/courses/ners/",
          ["nuclear engineer", "radiation safety officer", "reactor engineer", "health physicist"],
          ["nuclear engineering reactor news", "nuclear fusion breakthrough",
           "small modular reactor SMR", "nuclear power plant safety",
           "radiation therapy medical", "nuclear waste storage",
           "fusion energy ITER tokamak", "nuclear policy regulation"]),
    Major("climate", "Climate & Space Sciences", "CLIMATE",
          "https://bulletin.engin.umich.edu/courses/clasp/",
          ["atmospheric scientist", "climate researcher", "meteorologist", "remote sensing engineer"],
          ["climate science atmospheric research", "weather prediction modeling",
           "climate change global warming", "remote sensing satellite",
           "space weather solar wind", "carbon capture technology",
           "renewable energy policy", "extreme weather forecasting"]),
    Major("rob", "Robotics", "ROB",
          "https://bulletin.engin.umich.edu/courses/robotics-courses/",
          ["robotics engineer", "controls engineer", "autonomous systems engineer", "computer vision engineer", "motion planning engineer"],
          ["robotics industry news", "autonomous vehicles self driving",
           "humanoid robots Boston Dynamics", "drone delivery autonomous",
           "surgical robotics medical", "warehouse robotics Amazon",
           "computer vision perception", "robot learning reinforcement"]),
    Major("ds", "Data Science", "DATASCI",
          "https://bulletin.engin.umich.edu/courses/datasci/",
          ["data scientist", "data engineer", "machine learning engineer", "analytics engineer",
           "business intelligence analyst", "data analyst", "MLOps engineer", "AI engineer"],
          ["data science industry trends 2026", "machine learning AI careers",
           "big data analytics business", "MLOps data pipeline",
           "generative AI LLM applications", "data engineering cloud platforms",
           "NLP natural language processing", "AI ethics regulation"]),
]


DISPLAY_ABBREVS = {
    "cs": "CS", "ce": "CE", "ee": "EE", "ds": "DS",
    "me": "ME", "bme": "BME", "cee": "CEE", "cheme": "ChE",
    "aero": "AERO", "ioe": "IOE", "matscie": "MSE",
    "name": "NAME", "ners": "NERS", "climate": "CLaSP",
    "rob": "ROB",
}

# U-M degree requirements: which course numbers each major requires + can elect.
# Source: bulletin.engin.umich.edu program guides.
# Includes core requirements + common upper-level electives for each program.
REQUIRED_COURSE_NUMBERS: dict[str, set[int]] = {
    # --- EECS sub-majors (share the same bulletin page) ---
    "cs": {
        # Intro + Core
        183, 203, 280, 281, 370, 376, 388,
        # Upper-level CS electives
        441, 442, 445, 449, 467, 470, 476, 478, 480, 481,
        482, 483, 484, 485, 486, 489, 490, 491, 492, 493,
        494, 495, 496, 497, 498,
    },
    "ce": {
        # Core hardware + software
        183, 203, 215, 270, 280, 281, 312, 370, 373, 376,
        # Upper-level CE electives
        388, 398, 427, 461, 470, 473, 478, 482, 483, 492, 498,
    },
    "ee": {
        # Core circuits & signals
        215, 216, 230, 301,
        # Upper-level EE electives
        311, 312, 320, 330, 334, 351, 398,
        414, 421, 425, 430, 438, 452, 453, 460, 461, 462,
        463, 464, 465, 467, 498,
    },
    # --- Mechanical Engineering (MECHENG) ---
    "me": {
        # Core
        211, 235, 240, 320, 350, 360, 382, 395,
        # Upper-level electives
        401, 411, 420, 424, 426, 431, 440, 450, 451, 452,
        455, 456, 460, 461, 463, 466, 467, 481, 482, 489,
        495, 498, 520, 524, 541, 550, 552,
    },
    # --- Biomedical Engineering (BIOMEDE) ---
    "bme": {
        # Core
        211, 221, 231, 241, 332, 350, 458,
        # Upper-level electives
        418, 442, 452, 458, 479, 497, 498, 500, 516, 520,
        528, 561, 580,
    },
    # --- Civil & Environmental Engineering (CEE) ---
    "cee": {
        # Core
        211, 212, 265, 325, 345, 366,
        # Upper-level electives
        375, 402, 415, 422, 425, 432, 440, 450, 451, 460,
        465, 481, 498, 501, 504, 510, 515, 522, 545, 571,
    },
    # --- Chemical Engineering (CHE) ---
    "cheme": {
        # Core
        230, 330, 341, 342, 344, 360,
        # Upper-level electives
        430, 460, 466, 470, 487, 496, 498, 528, 538, 560,
    },
    # --- Aerospace Engineering (AEROSP) ---
    "aero": {
        # Core
        201, 225, 245, 285, 305, 315, 347, 348,
        # Upper-level electives
        423, 450, 455, 471, 495, 498, 510, 525, 535, 545, 550,
    },
    # --- Industrial & Operations Engineering (IOE) ---
    "ioe": {
        # Core
        201, 265, 310, 316, 334, 366, 373,
        # Upper-level electives
        410, 416, 424, 425, 441, 453, 460, 466, 474, 481,
        491, 498, 510, 511, 516, 543, 574,
    },
    # --- Materials Science & Engineering (MATSCIE) ---
    "matscie": {
        # Core
        220, 242, 250, 335, 365,
        # Upper-level electives
        380, 415, 440, 465, 480, 498, 510, 520, 540,
    },
    # --- Naval Architecture & Marine Engineering (NAVARCH) ---
    "name": {
        # Core
        210, 260, 270, 281, 303, 371,
        # Upper-level electives
        410, 431, 450, 461, 481, 490, 498, 510, 530,
    },
    # --- Nuclear Engineering & Radiological Sciences (NERS) ---
    "ners": {
        # Core
        211, 250, 312, 344,
        # Upper-level electives
        425, 442, 462, 471, 498, 521, 531, 551, 575,
    },
    # --- Climate & Space Sciences (CLIMATE) ---
    "climate": {
        # Core
        210, 280, 321, 323,
        # Upper-level electives
        380, 410, 411, 431, 450, 480, 498, 501, 551, 587,
    },
    # --- Robotics (ROB) ---
    "rob": {
        # Core
        101, 201, 320, 330,
        # Upper-level electives
        340, 380, 422, 450, 498, 501, 510, 530, 535, 550,
    },
    # --- Data Science (DATASCI) ---
    "ds": {
        # Core
        101, 206, 306,
        # Upper-level electives
        315, 401, 415, 451, 461, 478, 498,
    },
}


def get_all_majors() -> list[dict]:
    """Return list of available majors for the frontend selector."""
    return [
        {
            "id": m.id,
            "name": m.name,
            "prefix": DISPLAY_ABBREVS.get(m.id, m.prefix),
        }
        for m in ENGINEERING_MAJORS
    ]


def get_major(major_id: str) -> Major | None:
    for m in ENGINEERING_MAJORS:
        if m.id == major_id:
            return m
    return None


async def scrape_major_courses(major_id: str) -> list[Course]:
    """Scrape courses for a given major. Falls back to seed data.

    After scraping, filters the full bulletin list down to only courses
    that are required or available as electives for that degree program
    (each major's bulletin page lists every course under the prefix,
    including graduate/research courses students don't take).
    """
    major = get_major(major_id)
    if not major:
        return []

    cache_path = DATA_DIR / f"{major_id}_courses.json"

    courses = await _scrape_with_playwright(major)

    if courses:
        courses = _filter_by_major(courses, major_id)

    if not courses:
        courses = _load_cache(cache_path)

    if not courses:
        courses = _get_seed_courses(major_id)

    if courses:
        _save_cache(courses, cache_path)

    return courses


def _filter_by_major(courses: list[Course], major_id: str) -> list[Course]:
    """Filter scraped courses to only those in the degree requirements.

    Every department's bulletin lists all courses under the prefix,
    but students only take core + elective courses. This filters to
    the actual degree-relevant set. Falls back to the full list if
    the major has no mapping (shouldn't happen) or filtering yields 0.
    """
    required_numbers = REQUIRED_COURSE_NUMBERS.get(major_id)
    if not required_numbers:
        return courses

    filtered = []
    for c in courses:
        num_match = re.search(r"(\d{3,4})", c.code)
        if num_match and int(num_match.group(1)) in required_numbers:
            filtered.append(c)

    if filtered:
        print(f"[courses] Filtered {len(courses)} → {len(filtered)} courses for {major_id}")
        return filtered

    return courses


async def _scrape_with_playwright(major: Major) -> list[Course]:
    """Use Playwright headless Chromium to bypass Cloudflare and scrape real courses.

    Runs the sync Playwright API in a thread to avoid event-loop conflicts
    with uvicorn / FastAPI.
    """
    import asyncio
    return await asyncio.to_thread(_scrape_with_playwright_sync, major)


def _scrape_with_playwright_sync(major: Major) -> list[Course]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(f"[courses] playwright not installed — skipping live scrape for {major.id}")
        return []

    html = ""
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = ctx.new_page()
            resp = page.goto(
                major.bulletin_url,
                wait_until="domcontentloaded",
                timeout=30_000,
            )
            if resp and resp.status != 200:
                print(f"[courses] {major.id} bulletin HTTP {resp.status}")
                browser.close()
                return []
            page.wait_for_timeout(3000)
            html = page.content()
            browser.close()
    except Exception as exc:
        print(f"[courses] Playwright error for {major.id}: {exc}")
        return []

    if not html or len(html) < 5000:
        return []

    return _parse_bulletin_html(html, major.prefix)


def _parse_bulletin_html(html: str, prefix: str) -> list[Course]:
    """Parse course entries from the real bulletin HTML."""
    soup = BeautifulSoup(html, "lxml")
    main = soup.find("div", class_="entry-content") or soup.find("main") or soup

    courses: list[Course] = []
    code_re = re.compile(rf"^({re.escape(prefix)}\s*\d{{3,4}})\.\s+", re.IGNORECASE)
    title_end_re = re.compile(
        r"(?=\s*(?:"
        r"Advisory\s*(?:Prerequisite|and)"
        r"|Enforced\s*Prerequisite"
        r"|Credit\s*Exclusion"
        r"|Prerequisite\s*:"
        r"|Preceded\s+or\s+accompanied"
        r"|Minimum\s+grade"
        r"|\(\d[\d-]*\s*credits?\)"
        r"))",
        re.IGNORECASE,
    )
    credits_re = re.compile(r"\((\d[\d-]*)\s*credits?\)", re.IGNORECASE)

    for p_tag in main.find_all("p"):
        text = p_tag.get_text(" ", strip=True)

        code_m = code_re.match(text)
        if not code_m:
            continue

        code = re.sub(r"\s+", " ", code_m.group(1).strip().upper())
        rest = text[code_m.end():]

        t_m = title_end_re.search(rest)
        if t_m:
            title = rest[: t_m.start()].strip()
        else:
            title = rest.split(".")[0].strip() if "." in rest[:80] else rest[:80].strip()
        title = re.sub(r"^(\s*\([A-Z]+\s*\d{3,4}\)\s*\.?\s*)+", "", title)
        title = title.rstrip(". ")

        cr_m = credits_re.search(text)
        credits_val = cr_m.group(1) if cr_m else ""

        if cr_m:
            desc = text[cr_m.end():].strip().lstrip(".) ")
        else:
            desc = rest

        if not desc:
            desc = rest

        full_text = f"{title}. {desc}" if desc else title

        topics = _extract_topics(full_text)
        objectives = _extract_objectives(full_text)

        courses.append(Course(
            code=code,
            title=title,
            description=desc[:3000],
            credits=credits_val,
            topics=topics,
            learning_objectives=objectives,
        ))

    print(f"[courses] Scraped {len(courses)} {prefix} courses from bulletin")
    return courses


TOPIC_KEYWORDS = [
    "C++", "Python", "Java", "Rust", "Go", "MATLAB", "SQL",
    "machine learning", "deep learning", "artificial intelligence",
    "data structures", "algorithms", "operating systems", "computer vision",
    "web systems", "databases", "networks", "compilers", "embedded",
    "NLP", "robotics", "parallel computing", "distributed systems",
    "security", "cryptography", "signal processing", "VLSI", "digital logic",
    "linear algebra", "probability", "optimization", "reinforcement learning",
    "software engineering", "version control", "testing", "memory management",
    "pointers", "object-oriented", "CAD", "finite element", "FEA",
    "thermodynamics", "fluid mechanics", "heat transfer", "dynamics",
    "statics", "materials science", "biomechanics", "biomaterials",
    "medical devices", "tissue engineering", "drug delivery", "imaging",
    "structural analysis", "geotechnical", "hydrology", "transportation",
    "environmental engineering", "sustainability", "renewable energy",
    "chemical kinetics", "reactor design", "mass transfer", "polymers",
    "aerodynamics", "propulsion", "orbital mechanics", "flight dynamics",
    "control systems", "automation", "supply chain", "operations research",
    "statistics", "simulation", "manufacturing", "3D printing",
    "additive manufacturing", "composites", "semiconductors", "nanotechnology",
    "nuclear physics", "radiation", "reactor physics", "plasma",
    "climate modeling", "remote sensing", "atmospheric science",
    "computer-aided design", "mechatronics", "sensors", "actuators",
    "motion planning", "SLAM", "perception", "autonomous systems",
]


def _extract_topics(text: str) -> list[str]:
    found = []
    lower = text.lower()
    for kw in TOPIC_KEYWORDS:
        kw_lower = kw.lower()
        if len(kw_lower) <= 4:
            if re.search(rf"\b{re.escape(kw_lower)}\b", lower):
                found.append(kw)
        else:
            if kw_lower in lower:
                found.append(kw)
    return found


def _extract_objectives(text: str) -> list[str]:
    objectives = []
    patterns = [
        r"(?:students?\s+will\s+(?:learn|be able|understand|develop|gain))[^.]*\.",
        r"(?:objectives?|outcomes?)\s*:?\s*([^.]+\.)",
        r"(?:covers?|introduces?|focuses?\s+on)\s+([^.]+\.)",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            objectives.append(m.group(0).strip())
    return objectives[:10]


def _save_cache(courses: list[Course], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump([asdict(c) for c in courses], f, indent=2)


def _load_cache(path: Path) -> list[Course]:
    if path.exists():
        with open(path) as f:
            return [Course(**c) for c in json.load(f)]
    return []


# ---------------------------------------------------------------------------
# Seed data per major (fallback for when scraping doesn't work)
# ---------------------------------------------------------------------------

def _get_seed_courses(major_id: str) -> list[Course]:
    seeds = {
        "cs": _seed_eecs,
        "ce": _seed_ce,
        "ee": _seed_ee,
        "eecs": _seed_eecs,
        "me": _seed_me,
        "bme": _seed_bme,
        "cee": _seed_cee,
        "cheme": _seed_cheme,
        "aero": _seed_aero,
        "ioe": _seed_ioe,
        "matscie": _seed_matscie,
        "rob": _seed_rob,
        "name": _seed_name,
        "ners": _seed_ners,
        "climate": _seed_climate,
        "ds": _seed_ds,
    }
    builder = seeds.get(major_id)
    if builder:
        return builder()
    return [Course("DEPT 101", "Introduction to the Major",
                   "Introductory course covering fundamentals of the field.",
                   "4", ["fundamentals"], ["Students will learn core concepts."])]


def _seed_eecs() -> list[Course]:
    return [
        Course("EECS 203", "Discrete Mathematics",
               "Introduction to the mathematical foundations of computer science. Topics include propositional and predicate logic, sets, functions, sequences, summation, mathematical induction, recursion, counting, relations, graphs and trees.",
               "4", ["discrete mathematics", "logic", "proofs", "algorithms"], ["Students will learn mathematical reasoning and proof techniques."]),
        Course("EECS 280", "Programming and Introductory Data Structures",
               "Techniques and algorithm development and effective programming, top-down analysis, structured programming, testing, and program correctness. Program language syntax and static and runtime semantics. Scope, procedure instantiation, recursion, abstract data types, and parameter passing methods. Structured data types, pointers, linked data structures, stacks, queues, arrays, records, and trees. C++ is the primary language.",
               "4", ["C++", "data structures", "pointers", "memory management", "object-oriented", "testing"],
               ["Students will learn structured programming in C++.", "Students will understand memory management and pointers."]),
        Course("EECS 281", "Data Structures and Algorithms",
               "Introduction to the algorithm analysis and O-notation. Fundamental data structures including lists, stacks, queues, priority queues, hash tables, binary trees, search trees, balanced trees, and graphs. Searching and sorting algorithms. Algorithm design paradigms including greedy, divide-and-conquer, and dynamic programming.",
               "4", ["algorithms", "data structures", "C++", "optimization"],
               ["Students will learn algorithm design and analysis.", "Students will understand fundamental data structures."]),
        Course("EECS 370", "Introduction to Computer Organization",
               "Basic concepts of computer organization and hardware. Instructions executed by a processor and how to use these instructions in simple assembly-language programs. Stored-program concept. Datapath and control for multiple implementations of a processor. Performance evaluation, pipelining, caches, virtual memory, and I/O.",
               "4", ["assembly", "computer architecture", "memory management", "caches"],
               ["Students will understand how processors execute instructions."]),
        Course("EECS 376", "Foundations of Computer Science",
               "Introduction to theory of computation. Models of computation: finite state machines, Turing machines. Decidable and undecidable problems. Polynomial time computability and NP-completeness.",
               "4", ["algorithms", "computational complexity", "NP-completeness"],
               ["Students will understand computational limits and complexity theory."]),
        Course("EECS 388", "Introduction to Computer Security",
               "Concepts and principles of computer and network security. Security analysis and design techniques. Application-layer, transport-layer, and network-layer security. Cryptography, authentication, access control, software security, web security.",
               "4", ["security", "cryptography", "networks", "web systems"],
               ["Students will learn fundamental computer security principles."]),
        Course("EECS 442", "Computer Vision",
               "The goal of computer vision is to compute properties of the three-dimensional world from digital images. Image formation, image features, feature matching, stereo vision, motion estimation, object recognition, deep learning for vision.",
               "4", ["computer vision", "deep learning", "Python", "machine learning"],
               ["Students will learn computational approaches to visual recognition."]),
        Course("EECS 445", "Introduction to Machine Learning",
               "Theory and implementation of state-of-the-art machine learning algorithms for large-scale real-world applications. Topics include supervised learning, unsupervised learning, regularization, kernel methods, neural networks, Bayesian methods, and PAC learning.",
               "4", ["machine learning", "Python", "deep learning", "algorithms", "linear algebra", "probability"],
               ["Students will learn the theory behind modern ML algorithms."]),
        Course("EECS 482", "Introduction to Operating Systems",
               "Operating system design and implementation. Concurrency, process scheduling, inter-process communication, deadlock, virtual memory, file systems, networking, and security. C++ is the primary programming language.",
               "4", ["operating systems", "C++", "memory management", "parallel computing"],
               ["Students will understand concurrent programming and synchronization."]),
        Course("EECS 484", "Database Management Systems",
               "Concepts and methods for the design and implementation of database systems. Topics include data models, query languages (SQL, relational algebra), database design, storage structures, query processing and optimization, transaction management, and database security.",
               "4", ["SQL", "databases", "data structures", "optimization"],
               ["Students will learn relational database design and SQL."]),
        Course("EECS 485", "Web Systems",
               "Concepts surrounding web systems, including web applications, web services, and distributed systems. Topics include client and server-side web development, REST APIs, databases, scalability, MapReduce, and search engines.",
               "4", ["web systems", "Python", "SQL", "databases", "distributed systems"],
               ["Students will learn full-stack web development."]),
        Course("EECS 486", "Information Retrieval",
               "Theory and practice of information retrieval. Topics include text processing, indexing, query processing, retrieval models, evaluation, classification, clustering, web search, and recommendation systems.",
               "4", ["NLP", "algorithms", "Python", "machine learning"],
               ["Students will learn information retrieval models and evaluation."]),
        Course("EECS 498", "Special Topics",
               "Topics of current interest in EECS. Recent offerings include Conversational AI, Deep Learning for Computer Vision, Reinforcement Learning, and Large Language Models.",
               "4", ["deep learning", "artificial intelligence", "machine learning", "reinforcement learning"],
               ["Students will explore cutting-edge topics in computer science."]),
    ]


def _seed_ce() -> list[Course]:
    """Seed courses for Computer Engineering: digital logic, embedded systems, FPGA/VLSI, computer architecture, hardware-software interface."""
    return [
        Course("EECS 270", "Introduction to Logic Design",
               "Combinational and sequential logic design. Boolean algebra, Karnaugh maps, finite state machines, and hardware description languages. Design of digital systems from specification to implementation. Laboratory with FPGAs.",
               "4", ["digital logic", "VLSI", "FPGA", "embedded"], ["Students will design and implement digital logic systems."]),
        Course("EECS 312", "Digital Integrated Circuits",
               "Design and analysis of digital CMOS circuits. MOSFET operation, inverter and logic gate design, timing, power dissipation, and layout. Introduction to fabrication and design rules.",
               "4", ["VLSI", "digital logic", "semiconductors"], ["Students will understand CMOS digital circuit design."]),
        Course("EECS 370", "Introduction to Computer Organization",
               "Basic concepts of computer organization and hardware. Instructions executed by a processor, assembly-language programming, stored-program concept, datapath and control, pipelining, caches, virtual memory, and I/O.",
               "4", ["computer architecture", "assembly", "memory management", "caches"], ["Students will understand how processors execute instructions."]),
        Course("EECS 373", "Design of Microprocessor-Based Systems",
               "Hardware-software interface for embedded systems. Microcontroller architecture, interrupts, timers, ADC/DAC, serial interfaces (UART, SPI, I2C), and real-time operating systems. Hands-on projects with development boards.",
               "4", ["embedded", "microcontrollers", "IoT", "sensors", "actuators"], ["Students will design microprocessor-based embedded systems."]),
        Course("EECS 398", "Special Topics in Computer Engineering",
               "Topics may include FPGA design with Verilog/VHDL, hardware security, or embedded Linux. Content varies by term.",
               "3", ["FPGA", "embedded", "digital logic"], ["Students will explore advanced computer engineering topics."]),
        Course("EECS 427", "VLSI Design I",
               "Full-custom VLSI design. CMOS fabrication, layout design, design rules, parasitic extraction, and simulation. Design of datapath and control blocks. Use of industry-standard CAD tools.",
               "4", ["VLSI", "digital logic", "CAD", "semiconductors"], ["Students will design full-custom VLSI circuits."]),
        Course("EECS 470", "Computer Architecture",
               "Advanced processor design. Pipelining, out-of-order execution, branch prediction, superscalar and VLIW architectures, memory hierarchies, and multiprocessor systems. Performance evaluation and trade-offs.",
               "4", ["computer architecture", "parallel computing", "memory management", "caches"], ["Students will understand advanced processor and memory system design."]),
        Course("EECS 473", "Advanced Embedded Systems",
               "Real-time and resource-constrained embedded systems. Real-time scheduling, low-power design, wireless connectivity (BLE, Zigbee), sensors and signal conditioning, and embedded software architecture. Project-based.",
               "4", ["embedded", "IoT", "sensors", "real-time systems"], ["Students will build advanced embedded and IoT systems."]),
        Course("EECS 478", "Logic Circuit Synthesis and Optimization",
               "Automated synthesis and optimization of digital circuits. Two-level and multilevel logic minimization, technology mapping, sequential synthesis, and verification. Introduction to formal equivalence checking.",
               "4", ["digital logic", "VLSI", "algorithms", "optimization"], ["Students will learn logic synthesis and verification methods."]),
        Course("EECS 492", "Introduction to Artificial Intelligence",
               "Foundations of AI with applications in embedded and cyber-physical systems. Search, knowledge representation, planning, and machine learning basics. Emphasis on resource-efficient algorithms for hardware.",
               "4", ["artificial intelligence", "algorithms", "embedded", "machine learning"], ["Students will apply AI concepts in hardware and embedded contexts."]),
        Course("EECS 498", "FPGA and ASIC Design",
               "Design of digital systems using FPGAs and ASIC flows. RTL design with Verilog/SystemVerilog, synthesis, place-and-route, timing closure, and verification. Labs on FPGA boards and ASIC design flow.",
               "4", ["FPGA", "VLSI", "digital logic", "embedded", "testing"], ["Students will design and verify FPGA and ASIC systems."]),
        Course("EECS 498", "Hardware Verification and Validation",
               "Verification methodologies for digital systems. Simulation, assertion-based verification, formal methods, coverage-driven verification, and UVM-style testbenches. Introduction to emulation and prototyping.",
               "4", ["VLSI", "testing", "digital logic", "algorithms"], ["Students will learn hardware verification techniques."]),
        Course("EECS 498", "Computer-Aided Design of VLSI Circuits",
               "CAD algorithms and tools for VLSI. Placement, routing, timing analysis, power analysis, and design for manufacturability. Scripting and automation for design flows.",
               "4", ["VLSI", "CAD", "algorithms", "optimization"], ["Students will use and understand VLSI CAD tools."]),
        Course("EECS 498", "IoT Systems and Applications",
               "End-to-end IoT system design. Edge devices, gateways, cloud connectivity, protocols (MQTT, CoAP), security, and data analytics. Projects with sensors, microcontrollers, and cloud backends.",
               "4", ["IoT", "embedded", "sensors", "distributed systems", "security"], ["Students will design and deploy IoT systems."]),
        Course("EECS 498", "Real-Time and Embedded Operating Systems",
               "Operating system concepts for embedded and real-time systems. Task scheduling, priority inversion, memory management in constrained environments, and board support packages. RTOS usage and porting.",
               "4", ["operating systems", "embedded", "real-time systems", "memory management"], ["Students will understand real-time and embedded OS design."]),
    ]


def _seed_ee() -> list[Course]:
    """Seed courses for Electrical Engineering: circuits, signals & systems, electromagnetics, power, communications, control, RF, photonics."""
    return [
        Course("EECS 215", "Introduction to Electronic Circuits",
               "Analysis and design of analog electronic circuits. Diodes, BJTs, MOSFETs, single-stage amplifiers, frequency response, and operational amplifiers. Introduction to feedback and stability.",
               "4", ["circuits", "semiconductors", "signal processing"], ["Students will analyze and design basic analog circuits."]),
        Course("EECS 216", "Signals and Systems",
               "Continuous- and discrete-time signals and systems. Linear time-invariant systems, convolution, Fourier series and transform, Laplace and z-transforms, sampling, and filter design. Applications to communications and control.",
               "4", ["signal processing", "control systems", "communications"], ["Students will understand signals and systems theory."]),
        Course("EECS 230", "Electromagnetic Fields and Waves",
               "Maxwell's equations, electrostatics, magnetostatics, electromagnetic waves, propagation, reflection and transmission, transmission lines, and waveguides. Introduction to antennas and radiation.",
               "4", ["electromagnetics", "communications"], ["Students will understand electromagnetic theory and wave propagation."]),
        Course("EECS 301", "Probability and Random Processes",
               "Probability theory, random variables, expectation, correlation, and random processes. Applications to communications, signal processing, and control. Spectral analysis and estimation.",
               "4", ["probability", "signal processing", "communications", "statistics"], ["Students will apply probability to engineering systems."]),
        Course("EECS 311", "Electronic Circuits II",
               "Advanced analog circuit design. Multi-stage amplifiers, differential pairs, current mirrors, frequency response, feedback, stability, oscillators, and data converters. Design-oriented approach.",
               "4", ["circuits", "semiconductors", "signal processing"], ["Students will design advanced analog circuits."]),
        Course("EECS 320", "Electromagnetic Fields and Waves II",
               "Advanced electromagnetics. Waveguides, cavity resonators, antennas and radiation patterns, Friis equation, and scattering parameters. Introduction to numerical methods (FDTD, MoM) for EM problems.",
               "4", ["electromagnetics", "communications"], ["Students will understand advanced EM and antenna theory."]),
        Course("EECS 330", "Introduction to Communication Systems",
               "Modulation and demodulation (AM, FM, digital). Noise in communication systems, SNR, channel capacity, and coding. Introduction to wireless and wired communication systems.",
               "4", ["communications", "signal processing", "probability"], ["Students will understand communication system principles."]),
        Course("EECS 334", "Semiconductor Devices",
               "Physics of semiconductor devices. Carrier transport, p-n junctions, BJTs, MOSFETs, and optoelectronic devices. Device modeling and introduction to fabrication technology.",
               "4", ["semiconductors", "VLSI", "nanotechnology"], ["Students will understand semiconductor device physics."]),
        Course("EECS 414", "Introduction to Machine Learning",
               "Machine learning with applications in signal processing and communications. Regression, classification, neural networks, and reinforcement learning. Implementation in MATLAB or Python.",
               "4", ["machine learning", "signal processing", "Python", "MATLAB"], ["Students will apply ML to signals and systems."]),
        Course("EECS 460", "Control Systems Analysis and Design",
               "Analysis and design of feedback control systems. Transfer functions, state-space models, stability, root locus, frequency response, PID design, and digital control. Applications to electrical and mechanical systems.",
               "4", ["control systems", "MATLAB", "signal processing", "automation"], ["Students will design and analyze control systems."]),
        Course("EECS 463", "Power Electronics",
               "Analysis and design of power electronic converters. Diode and thyristor circuits, DC-DC converters, inverters, rectifiers, and motor drives. Magnetics, losses, and thermal design.",
               "4", ["power systems", "circuits", "semiconductors"], ["Students will design power electronic systems."]),
        Course("EECS 465", "Radio Frequency and Microwave Circuit Design",
               "RF and microwave circuit design. S-parameters, matching networks, amplifiers, oscillators, mixers, and passive components. Introduction to RF system design and measurement.",
               "4", ["electromagnetics", "circuits", "communications"], ["Students will design RF and microwave circuits."]),
        Course("EECS 498", "Photonics and Optical Systems",
               "Optics and photonics for engineers. Ray and wave optics, optical fibers, lasers, detectors, modulators, and optical communication systems. Introduction to integrated photonics.",
               "4", ["signal processing", "communications", "semiconductors"], ["Students will understand photonics and optical system design."]),
        Course("EECS 498", "Digital Signal Processing",
               "Discrete-time signals and systems, z-transform, DFT/FFT, digital filter design (IIR and FIR), multirate systems, and applications in audio, image, and communications.",
               "4", ["signal processing", "algorithms", "MATLAB"], ["Students will design and implement digital signal processing systems."]),
        Course("EECS 498", "Power Systems Analysis",
               "Analysis of electric power systems. Per-unit representation, load flow, fault analysis, stability, and protection. Introduction to renewable integration and smart grids.",
               "4", ["power systems", "simulation", "optimization", "sustainability"], ["Students will analyze and design power system components."]),
    ]


def _seed_me() -> list[Course]:
    return [
        Course("MECHENG 211", "Introduction to Solid Mechanics",
               "Stress, strain, and deformation of solids. Axial loading, torsion, bending, and combined loading. Failure theories and design applications.",
               "4", ["statics", "materials science", "structural analysis"], ["Students will learn stress analysis and deformation of solids."]),
        Course("MECHENG 235", "Thermodynamics I",
               "Fundamental concepts of classical thermodynamics. Properties of pure substances, first and second laws, entropy, and applications to engineering systems including heat engines and refrigeration cycles.",
               "4", ["thermodynamics", "heat transfer"], ["Students will understand the laws of thermodynamics and their engineering applications."]),
        Course("MECHENG 240", "Introduction to Dynamics and Vibrations",
               "Kinematics and kinetics of particles and rigid bodies. Energy and momentum methods. Free and forced vibrations of single-degree-of-freedom systems.",
               "4", ["dynamics", "statics", "simulation"], ["Students will learn particle and rigid body dynamics."]),
        Course("MECHENG 320", "Fluid Mechanics I",
               "Fundamental principles of fluid mechanics. Hydrostatics, conservation laws, Bernoulli equation, dimensional analysis, viscous flow, boundary layers, and introduction to turbulence.",
               "4", ["fluid mechanics", "simulation", "MATLAB"], ["Students will understand fundamental fluid mechanics principles."]),
        Course("MECHENG 350", "Design and Manufacturing I",
               "Principles of engineering design and manufacturing. CAD modeling, tolerancing, material selection, machining, casting, forming, and joining processes. Design for manufacturing.",
               "4", ["CAD", "manufacturing", "computer-aided design", "3D printing"], ["Students will learn manufacturing processes and design principles."]),
        Course("MECHENG 360", "Modeling, Analysis and Control of Dynamic Systems",
               "Mathematical modeling of mechanical, electrical, fluid, and thermal systems. Transfer functions, state-space models, stability analysis, and feedback control system design.",
               "4", ["control systems", "MATLAB", "simulation", "dynamics"], ["Students will learn to model and control dynamic systems."]),
        Course("MECHENG 382", "Mechanical Behavior of Materials",
               "Mechanical behavior of engineering materials including metals, ceramics, polymers, and composites. Deformation mechanisms, fracture, fatigue, and creep.",
               "4", ["materials science", "composites", "manufacturing"], ["Students will understand material behavior under mechanical loading."]),
        Course("MECHENG 395", "Laboratory I",
               "Experimental methods in mechanical engineering. Measurement systems, data acquisition, signal processing, uncertainty analysis, and technical communication.",
               "4", ["sensors", "testing", "statistics", "MATLAB"], ["Students will learn experimental methods and data analysis."]),
        Course("MECHENG 450", "Design and Manufacturing III",
               "Capstone design experience. Open-ended design projects addressing real engineering problems with industry sponsors. Prototyping, testing, and iteration.",
               "4", ["CAD", "manufacturing", "3D printing", "additive manufacturing", "testing"], ["Students will complete a comprehensive design project."]),
        Course("MECHENG 461", "Automatic Control",
               "Analysis and design of feedback control systems. Root locus, frequency response, and state-space methods. Digital control, PID controllers, and robustness.",
               "4", ["control systems", "MATLAB", "automation", "robotics"], ["Students will design and analyze feedback control systems."]),
        Course("MECHENG 481", "Manufacturing Processes",
               "Advanced manufacturing processes including CNC machining, laser processing, additive manufacturing, micro/nano fabrication, and smart manufacturing with Industry 4.0 concepts.",
               "4", ["manufacturing", "3D printing", "additive manufacturing", "automation", "CAD"], ["Students will learn advanced manufacturing technologies."]),
        Course("MECHENG 552", "Machine Learning for Mechanical Engineers",
               "Applications of machine learning in mechanical engineering. Data-driven modeling, neural networks, physics-informed ML, and surrogate modeling for engineering design and analysis.",
               "4", ["machine learning", "Python", "deep learning", "optimization", "MATLAB"], ["Students will apply ML techniques to mechanical engineering problems."]),
    ]


def _seed_bme() -> list[Course]:
    return [
        Course("BIOMEDE 211", "Circuits, Systems & Signals for Biomedical Engineering",
               "Electrical circuits, linear systems theory, and signal processing with biomedical applications. Biosignal analysis including ECG, EEG, and EMG.",
               "4", ["signal processing", "sensors", "MATLAB"], ["Students will learn biomedical signal analysis."]),
        Course("BIOMEDE 221", "Biophysical Chemistry and Thermodynamics",
               "Chemical thermodynamics and kinetics applied to biological systems. Molecular interactions, binding equilibria, and transport phenomena in biological contexts.",
               "4", ["thermodynamics", "chemical kinetics"], ["Students will understand biophysical chemistry fundamentals."]),
        Course("BIOMEDE 231", "Introduction to Biomechanics",
               "Mechanics of biological tissues and systems. Stress-strain behavior of bone, soft tissue, and cartilage. Musculoskeletal biomechanics and movement analysis.",
               "4", ["biomechanics", "statics", "dynamics", "materials science"], ["Students will learn the mechanical behavior of biological tissues."]),
        Course("BIOMEDE 241", "Biomedical Instrumentation and Design",
               "Design of biomedical instruments and devices. Transducers, amplifiers, filters, and data acquisition systems for physiological measurements.",
               "4", ["sensors", "medical devices", "signal processing", "embedded"], ["Students will design biomedical measurement systems."]),
        Course("BIOMEDE 332", "Introduction to Biomedical Imaging",
               "Physics and engineering of medical imaging. X-ray, CT, MRI, ultrasound, nuclear medicine, and optical imaging. Image reconstruction algorithms and processing.",
               "4", ["imaging", "signal processing", "algorithms", "MATLAB"], ["Students will understand medical imaging physics and engineering."]),
        Course("BIOMEDE 350", "Introduction to Biotransport",
               "Mass and heat transfer in biological systems. Diffusion, convection, membrane transport, and pharmacokinetic modeling.",
               "4", ["mass transfer", "heat transfer", "simulation", "MATLAB"], ["Students will learn transport phenomena in biological systems."]),
        Course("BIOMEDE 418", "Quantitative Cell Biology",
               "Quantitative approaches to cell biology. Mathematical modeling of cell signaling, gene regulatory networks, and cell mechanics.",
               "4", ["simulation", "statistics", "Python", "MATLAB"], ["Students will apply quantitative methods to cell biology."]),
        Course("BIOMEDE 442", "Introduction to Biomaterials",
               "Engineering biomaterials for medical applications. Polymers, metals, ceramics, and composites for implants, drug delivery, and tissue engineering scaffolds.",
               "4", ["biomaterials", "tissue engineering", "drug delivery", "polymers"], ["Students will learn to design biomaterials for medical use."]),
        Course("BIOMEDE 458", "Biomedical Data Science",
               "Data science and machine learning for biomedical applications. Electronic health records, genomic data analysis, medical image classification, and clinical decision support.",
               "4", ["machine learning", "Python", "statistics", "deep learning", "imaging"], ["Students will apply data science to biomedical problems."]),
        Course("BIOMEDE 479", "Tissue Engineering",
               "Principles of tissue engineering. Scaffold design, cell sourcing, bioreactor systems, and clinical applications for regenerating tissues and organs.",
               "4", ["tissue engineering", "biomaterials", "3D printing"], ["Students will learn tissue engineering principles and methods."]),
    ]


def _seed_cee() -> list[Course]:
    return [
        Course("CEE 211", "Statics and Dynamics",
               "Forces, moments, equilibrium of rigid bodies, trusses, frames. Kinematics and kinetics of particles.",
               "4", ["statics", "dynamics", "structural analysis"], ["Students will learn equilibrium analysis and basic dynamics."]),
        Course("CEE 212", "Solid and Structural Mechanics",
               "Stress, strain, deformation of structural elements. Beam theory, column buckling, and introduction to structural design.",
               "4", ["structural analysis", "statics", "materials science"], ["Students will understand structural mechanics."]),
        Course("CEE 265", "Sustainability and the Environment",
               "Environmental engineering fundamentals. Water quality, air pollution, waste management, life-cycle assessment, and sustainable design principles.",
               "4", ["environmental engineering", "sustainability"], ["Students will learn environmental engineering principles."]),
        Course("CEE 325", "Fluid Mechanics",
               "Fluid properties, hydrostatics, conservation laws for fluid flow, pipe flow, open channel flow, and groundwater flow.",
               "4", ["fluid mechanics", "hydrology", "simulation"], ["Students will understand fluid mechanics for civil engineering."]),
        Course("CEE 345", "Geotechnical Engineering",
               "Soil mechanics, site investigation, soil classification, seepage, consolidation, shear strength, and foundation design.",
               "4", ["geotechnical", "materials science", "testing"], ["Students will learn geotechnical engineering fundamentals."]),
        Course("CEE 366", "Structural Analysis",
               "Analysis of determinate and indeterminate structures. Force and displacement methods, influence lines, and introduction to matrix structural analysis.",
               "4", ["structural analysis", "algorithms", "MATLAB", "simulation"], ["Students will learn structural analysis methods."]),
        Course("CEE 375", "Sensors, Circuits and Data Science for CEE",
               "Sensing technologies, data acquisition, and machine learning for infrastructure monitoring. IoT sensors, signal processing, and predictive analytics.",
               "4", ["sensors", "machine learning", "Python", "signal processing", "statistics"], ["Students will apply data science to infrastructure monitoring."]),
        Course("CEE 432", "Water Resources Engineering",
               "Hydrologic cycle, rainfall-runoff analysis, flood frequency, reservoir design, and climate change impacts on water resources.",
               "4", ["hydrology", "sustainability", "simulation", "climate modeling", "statistics"], ["Students will learn water resources engineering."]),
        Course("CEE 450", "Introduction to Transportation Engineering",
               "Transportation system planning, traffic flow theory, highway design, traffic signal design, and intelligent transportation systems.",
               "4", ["transportation", "statistics", "optimization", "simulation"], ["Students will understand transportation engineering fundamentals."]),
        Course("CEE 515", "Computational Methods in CEE",
               "Numerical methods for civil engineering. Finite element analysis, optimization, machine learning for structural health monitoring, and digital twins.",
               "4", ["finite element", "FEA", "Python", "machine learning", "simulation", "optimization"], ["Students will learn computational methods for civil engineering."]),
    ]


def _seed_cheme() -> list[Course]:
    return [
        Course("CHE 230", "Material and Energy Balances",
               "Conservation of mass and energy applied to chemical processes. Stoichiometry, phase equilibria, and process flow diagrams.",
               "4", ["thermodynamics", "chemical kinetics", "mass transfer"], ["Students will learn material and energy balance calculations."]),
        Course("CHE 330", "Chemical Engineering Thermodynamics",
               "Laws of thermodynamics applied to chemical systems. Phase equilibria, fugacity, activity coefficients, and chemical reaction equilibria.",
               "4", ["thermodynamics", "chemical kinetics", "optimization"], ["Students will understand thermodynamic principles for chemical systems."]),
        Course("CHE 341", "Fluid Mechanics",
               "Fluid statics and dynamics for chemical engineers. Pipe flow, pumps, filtration, and fluidization.",
               "4", ["fluid mechanics", "simulation"], ["Students will learn fluid mechanics for chemical processes."]),
        Course("CHE 342", "Heat and Mass Transfer",
               "Conduction, convection, radiation heat transfer. Mass transfer by diffusion and convection. Heat exchanger and mass transfer equipment design.",
               "4", ["heat transfer", "mass transfer", "simulation", "optimization"], ["Students will understand heat and mass transfer."]),
        Course("CHE 344", "Chemical Reaction Engineering",
               "Kinetics of homogeneous and heterogeneous reactions. Design of ideal and non-ideal reactors. Catalysis and catalyst deactivation.",
               "4", ["reactor design", "chemical kinetics", "optimization", "MATLAB"], ["Students will learn chemical reactor design."]),
        Course("CHE 360", "Chemical Engineering Laboratory",
               "Experimental methods in chemical engineering. Unit operations experiments, data analysis, and technical communication.",
               "4", ["testing", "statistics", "MATLAB"], ["Students will learn experimental chemical engineering methods."]),
        Course("CHE 460", "Process Design and Optimization",
               "Design of chemical processes. Process simulation, economic analysis, environmental impact, and optimization. ASPEN Plus and MATLAB.",
               "4", ["optimization", "simulation", "sustainability", "MATLAB"], ["Students will design and optimize chemical processes."]),
        Course("CHE 487", "Polymer Science and Engineering",
               "Polymer chemistry, physics, and processing. Structure-property relationships, characterization, and applications of polymeric materials.",
               "4", ["polymers", "materials science", "manufacturing"], ["Students will understand polymer science and engineering."]),
        Course("CHE 496", "Data Science for Chemical Engineers",
               "Machine learning and data science for chemical engineering. Process analytics, predictive modeling, and computational approaches to molecular design.",
               "4", ["machine learning", "Python", "statistics", "deep learning", "optimization"], ["Students will apply data science to chemical engineering."]),
    ]


def _seed_aero() -> list[Course]:
    return [
        Course("AEROSP 201", "Introduction to Aerospace Engineering",
               "Overview of aerospace engineering. Aerodynamics, propulsion, structures, flight dynamics, orbital mechanics, and aerospace design.",
               "4", ["aerodynamics", "propulsion", "dynamics"], ["Students will learn aerospace engineering fundamentals."]),
        Course("AEROSP 225", "Introduction to Gas Dynamics",
               "Compressible flow fundamentals. Isentropic flow, normal and oblique shock waves, expansion waves, and nozzle flow.",
               "4", ["aerodynamics", "fluid mechanics", "thermodynamics"], ["Students will understand compressible fluid flow."]),
        Course("AEROSP 285", "Aerospace Structures",
               "Structural analysis of aerospace vehicles. Thin-walled structures, stress analysis, buckling, and composite materials.",
               "4", ["structural analysis", "composites", "materials science", "statics"], ["Students will learn aerospace structural analysis."]),
        Course("AEROSP 305", "Aerospace Aerodynamics",
               "Subsonic and supersonic aerodynamics. Potential flow, thin airfoil theory, finite wing theory, and computational methods.",
               "4", ["aerodynamics", "fluid mechanics", "MATLAB", "simulation"], ["Students will understand aerodynamic theory and computation."]),
        Course("AEROSP 315", "Aircraft and Spacecraft Propulsion",
               "Principles of jet propulsion. Gas turbine engines, rocket propulsion, and electric propulsion for spacecraft.",
               "4", ["propulsion", "thermodynamics", "fluid mechanics"], ["Students will learn propulsion system principles."]),
        Course("AEROSP 347", "Space Flight Mechanics",
               "Orbital mechanics and spacecraft trajectory design. Two-body problem, orbit transfers, interplanetary trajectories, and mission design.",
               "4", ["orbital mechanics", "flight dynamics", "MATLAB", "simulation"], ["Students will learn orbital mechanics and mission design."]),
        Course("AEROSP 348", "Flight Dynamics and Control",
               "Equations of motion for aircraft. Stability derivatives, longitudinal and lateral-directional dynamics, and autopilot design.",
               "4", ["flight dynamics", "control systems", "MATLAB"], ["Students will understand aircraft dynamics and control."]),
        Course("AEROSP 450", "Senior Design",
               "Capstone aerospace design project. Conceptual and preliminary design of an aerospace vehicle or system with industry collaboration.",
               "4", ["CAD", "optimization", "simulation", "testing"], ["Students will complete an aerospace design project."]),
        Course("AEROSP 495", "Multidisciplinary Design Optimization",
               "Optimization techniques for aerospace systems. Gradient-based methods, surrogate modeling, machine learning for design, and multi-objective optimization.",
               "4", ["optimization", "machine learning", "Python", "MATLAB", "simulation"], ["Students will learn optimization methods for aerospace design."]),
    ]


def _seed_ioe() -> list[Course]:
    return [
        Course("IOE 201", "Economic Decision Making",
               "Engineering economic analysis. Time value of money, project evaluation, depreciation, and decision-making under uncertainty.",
               "4", ["optimization", "statistics"], ["Students will learn engineering economic analysis."]),
        Course("IOE 265", "Probability and Statistics for Engineers",
               "Probability theory, random variables, statistical inference, hypothesis testing, regression analysis, and design of experiments.",
               "4", ["probability", "statistics", "MATLAB"], ["Students will learn probability and statistical methods."]),
        Course("IOE 310", "Introduction to Optimization Methods",
               "Linear programming, simplex method, integer programming, network flows, and introduction to nonlinear optimization.",
               "4", ["optimization", "algorithms", "MATLAB", "linear algebra"], ["Students will learn optimization methods."]),
        Course("IOE 316", "Introduction to Markov Processes",
               "Discrete and continuous-time Markov chains. Queueing theory, simulation, and applications to service systems and manufacturing.",
               "4", ["probability", "simulation", "statistics", "optimization"], ["Students will understand stochastic processes and queueing."]),
        Course("IOE 366", "Linear Statistical Models",
               "Multiple regression, ANOVA, experimental design, and model selection. Applications to engineering data analysis.",
               "4", ["statistics", "linear algebra", "optimization", "Python"], ["Students will learn statistical modeling methods."]),
        Course("IOE 373", "Data and Decision Analytics",
               "Data-driven decision making. Data visualization, machine learning for prediction and classification, text analytics, and recommendation systems.",
               "4", ["machine learning", "Python", "statistics", "NLP", "optimization"], ["Students will apply analytics to engineering problems."]),
        Course("IOE 425", "Lean Manufacturing",
               "Lean manufacturing principles. Value stream mapping, waste reduction, kanban systems, and continuous improvement methodologies.",
               "4", ["manufacturing", "supply chain", "optimization", "automation"], ["Students will learn lean manufacturing methods."]),
        Course("IOE 474", "Simulation",
               "Discrete-event simulation. Random number generation, input modeling, output analysis, and simulation optimization. Arena and Python.",
               "4", ["simulation", "statistics", "Python", "optimization"], ["Students will learn simulation modeling and analysis."]),
        Course("IOE 491", "Operations Research in Practice",
               "Real-world operations research projects with industry sponsors. Mathematical modeling, optimization, data analysis, and stakeholder communication.",
               "4", ["optimization", "operations research", "Python", "statistics", "machine learning"], ["Students will apply OR methods to real problems."]),
    ]


def _seed_matscie() -> list[Course]:
    return [
        Course("MATSCIE 220", "Introduction to Materials and their Properties",
               "Structure-property relationships of engineering materials. Crystal structures, defects, phase diagrams, and mechanical properties of metals, ceramics, polymers, and composites.",
               "4", ["materials science", "composites", "polymers"], ["Students will understand material structure-property relationships."]),
        Course("MATSCIE 242", "Physics of Materials",
               "Quantum mechanics foundations for materials science. Electronic structure, band theory, and optical/electrical properties of materials.",
               "4", ["semiconductors", "nanotechnology", "linear algebra"], ["Students will learn the physics of electronic materials."]),
        Course("MATSCIE 250", "Principles of Engineering Materials",
               "Thermodynamics and kinetics of materials. Phase transformations, diffusion, nucleation, and growth in engineering materials.",
               "4", ["thermodynamics", "materials science", "chemical kinetics"], ["Students will understand materials thermodynamics."]),
        Course("MATSCIE 335", "Materials Processing",
               "Manufacturing and processing of materials. Casting, deformation processing, powder metallurgy, additive manufacturing, and thin film deposition.",
               "4", ["manufacturing", "additive manufacturing", "3D printing", "semiconductors"], ["Students will learn materials processing methods."]),
        Course("MATSCIE 365", "Structure of Materials",
               "Advanced structural characterization. X-ray diffraction, electron microscopy, spectroscopy, and scanning probe techniques.",
               "4", ["nanotechnology", "materials science", "imaging"], ["Students will learn materials characterization techniques."]),
        Course("MATSCIE 440", "Computational Materials Science",
               "Computational methods for materials design. Density functional theory, molecular dynamics, machine learning for materials discovery, and high-throughput screening.",
               "4", ["simulation", "machine learning", "Python", "optimization", "nanotechnology"], ["Students will learn computational materials science."]),
    ]


def _seed_rob() -> list[Course]:
    return [
        Course("ROB 101", "Computational Linear Algebra",
               "Linear algebra for robotics. Vectors, matrices, linear transformations, eigenvalues, and applications to robotic systems. Julia programming language.",
               "4", ["linear algebra", "algorithms", "Python"], ["Students will learn linear algebra for robotics."]),
        Course("ROB 201", "Introduction to Robotics",
               "Fundamentals of robotics. Forward and inverse kinematics, dynamics, control, sensors, actuators, and robot programming.",
               "4", ["robotics", "control systems", "sensors", "actuators", "Python"], ["Students will learn fundamental robotics concepts."]),
        Course("ROB 320", "Robot Mechanics and Kinematics",
               "Rigid body mechanics for robotic systems. Forward and inverse kinematics, velocity kinematics, dynamics, and trajectory planning.",
               "4", ["robotics", "dynamics", "control systems", "linear algebra", "MATLAB"], ["Students will learn robot mechanics and kinematics."]),
        Course("ROB 330", "Localization, Mapping, and Navigation",
               "Robot localization and mapping. Probabilistic methods, SLAM, path planning, and navigation algorithms for mobile robots.",
               "4", ["SLAM", "perception", "algorithms", "probability", "Python"], ["Students will learn robot localization and mapping."]),
        Course("ROB 340", "Human-Robot Interaction",
               "Design and evaluation of human-robot systems. Social robotics, collaborative robots, shared autonomy, and safety in human-robot teams.",
               "4", ["robotics", "autonomous systems", "sensors"], ["Students will learn human-robot interaction principles."]),
        Course("ROB 422", "Robot Ethics",
               "Ethical, legal, and societal implications of robotics and AI. Autonomous weapons, algorithmic bias, privacy, and responsible innovation.",
               "4", ["autonomous systems", "artificial intelligence"], ["Students will explore ethical issues in robotics."]),
        Course("ROB 450", "Introduction to Robot Learning",
               "Machine learning for robotic systems. Reinforcement learning, imitation learning, sim-to-real transfer, and learning-based control.",
               "4", ["machine learning", "reinforcement learning", "deep learning", "Python", "robotics", "autonomous systems"],
               ["Students will learn ML methods for robotic systems."]),
        Course("ROB 501", "Mathematics for Robotics",
               "Advanced mathematical foundations. Lie groups, optimization on manifolds, probabilistic graphical models, and estimation theory.",
               "4", ["optimization", "probability", "linear algebra", "algorithms"], ["Students will learn advanced math for robotics."]),
        Course("ROB 530", "Mobile Robotics",
               "State estimation, SLAM, motion planning, and autonomous navigation. Sensor fusion with cameras, LiDAR, and IMUs.",
               "4", ["SLAM", "perception", "autonomous systems", "sensors", "computer vision", "motion planning", "Python"],
               ["Students will learn mobile robotics methods."]),
        Course("ROB 535", "Self-Driving Cars",
               "Perception, prediction, planning, and control for autonomous vehicles. Deep learning for perception, behavior prediction, and end-to-end driving.",
               "4", ["autonomous systems", "deep learning", "computer vision", "control systems", "Python", "motion planning", "perception"],
               ["Students will learn autonomous driving systems."]),
    ]


def _seed_name() -> list[Course]:
    return [
        Course("NAVARCH 210", "Introduction to Naval Architecture",
               "Basic principles of ship design. Hull form, hydrostatics, stability, resistance, and propulsion. Introduction to marine systems.",
               "4", ["fluid mechanics", "CAD", "dynamics"], ["Students will learn ship design fundamentals."]),
        Course("NAVARCH 270", "Ship Resistance and Propulsion",
               "Ship resistance components, propeller theory, cavitation, and propulsive efficiency. Computational methods and model testing.",
               "4", ["fluid mechanics", "simulation", "MATLAB", "optimization"], ["Students will understand ship propulsion systems."]),
        Course("NAVARCH 281", "Principles of Marine Engineering",
               "Marine power plants and auxiliary systems. Diesel engines, gas turbines, steam plants, and emerging electric/hybrid propulsion systems.",
               "4", ["thermodynamics", "manufacturing", "sustainability"], ["Students will learn marine engineering systems."]),
        Course("NAVARCH 303", "Structural Analysis of Marine Systems",
               "Structural mechanics of ships and offshore platforms. Plate and shell theory, fatigue, fracture mechanics, and classification rules.",
               "4", ["structural analysis", "finite element", "FEA", "materials science"], ["Students will learn marine structural analysis."]),
        Course("NAVARCH 371", "Marine Hydrodynamics",
               "Potential flow theory for marine vehicles. Wave-body interaction, seakeeping, maneuvering, and added resistance in waves.",
               "4", ["fluid mechanics", "dynamics", "simulation", "MATLAB"], ["Students will understand marine hydrodynamics."]),
        Course("NAVARCH 410", "Design of Ocean Systems",
               "Offshore platform design. Fixed and floating structures, mooring systems, risers, and subsea equipment. Environmental loads and response analysis.",
               "4", ["structural analysis", "CAD", "optimization", "simulation"], ["Students will design offshore systems."]),
        Course("NAVARCH 450", "Senior Design Project",
               "Capstone ship or marine system design project. Concept design through preliminary design with computational and experimental validation.",
               "4", ["CAD", "optimization", "simulation", "testing"], ["Students will complete a marine design project."]),
        Course("NAVARCH 481", "Autonomous Marine Vehicles",
               "Design and control of autonomous surface and underwater vehicles. Navigation, path planning, sensor integration, and communication systems.",
               "4", ["autonomous systems", "robotics", "control systems", "sensors", "Python"], ["Students will learn autonomous marine vehicle systems."]),
    ]


def _seed_ners() -> list[Course]:
    return [
        Course("NERS 211", "Introduction to Nuclear Engineering and Radiological Sciences",
               "Overview of nuclear science and engineering. Nuclear physics, radioactivity, radiation interactions with matter, and applications in energy, medicine, and security.",
               "4", ["nuclear physics", "radiation"], ["Students will learn nuclear science fundamentals."]),
        Course("NERS 250", "Nuclear Reactor Design and Analysis",
               "Nuclear reactor theory. Neutron diffusion, criticality, reactor kinetics, and core design. Light water reactors and advanced reactor concepts.",
               "4", ["reactor physics", "simulation", "MATLAB"], ["Students will understand nuclear reactor design."]),
        Course("NERS 312", "Nuclear Measurements Laboratory",
               "Radiation detection and measurement. Detector physics, pulse processing, spectroscopy, and nuclear instrumentation. Statistical analysis of counting data.",
               "4", ["radiation", "sensors", "statistics", "signal processing"], ["Students will learn nuclear measurement techniques."]),
        Course("NERS 344", "Nuclear Reactor Theory",
               "Advanced reactor physics. Neutron transport, diffusion theory, multi-group methods, perturbation theory, and numerical reactor analysis.",
               "4", ["reactor physics", "algorithms", "simulation", "linear algebra"], ["Students will learn advanced reactor physics."]),
        Course("NERS 425", "Nuclear Materials",
               "Behavior of materials in nuclear environments. Radiation damage, creep, swelling, embrittlement, and corrosion. Advanced materials for fusion and fission.",
               "4", ["materials science", "nanotechnology", "radiation"], ["Students will understand nuclear materials behavior."]),
        Course("NERS 442", "Nuclear Power Engineering",
               "Nuclear power plant systems. Thermal hydraulics, safety analysis, plant operations, and advanced reactor designs including SMRs and molten salt reactors.",
               "4", ["reactor design", "thermodynamics", "heat transfer", "simulation"], ["Students will learn nuclear power plant engineering."]),
        Course("NERS 462", "Radiological Health Engineering",
               "Radiation protection principles. Dosimetry, shielding design, waste management, regulatory framework, and environmental monitoring.",
               "4", ["radiation", "statistics", "sustainability"], ["Students will learn radiation protection engineering."]),
        Course("NERS 471", "Nuclear Plasma Engineering",
               "Plasma physics for fusion energy. Magnetic confinement, plasma diagnostics, heating methods, and progress toward commercial fusion.",
               "4", ["plasma", "nuclear physics", "simulation", "MATLAB"], ["Students will understand plasma physics for fusion."]),
        Course("NERS 521", "Computational Methods in Nuclear Engineering",
               "Numerical methods for nuclear engineering. Monte Carlo methods, deterministic transport, CFD for nuclear thermal hydraulics, and machine learning for reactor analysis.",
               "4", ["simulation", "algorithms", "machine learning", "Python", "optimization"], ["Students will learn computational nuclear engineering."]),
    ]


def _seed_climate() -> list[Course]:
    return [
        Course("CLIMATE 210", "Introduction to Climate and Weather",
               "Physical processes governing Earth's climate and weather. Atmospheric thermodynamics, radiation balance, circulation patterns, and climate variability.",
               "4", ["climate modeling", "atmospheric science", "thermodynamics"], ["Students will understand climate and weather fundamentals."]),
        Course("CLIMATE 280", "Introduction to Space Sciences",
               "The near-Earth space environment. Solar wind, magnetosphere, ionosphere, space weather, and impacts on technology and society.",
               "4", ["remote sensing", "atmospheric science", "simulation"], ["Students will learn space science fundamentals."]),
        Course("CLIMATE 321", "Physical Meteorology",
               "Atmospheric radiation, cloud physics, precipitation processes, and remote sensing of the atmosphere.",
               "4", ["atmospheric science", "remote sensing", "statistics"], ["Students will understand atmospheric physics."]),
        Course("CLIMATE 323", "Atmospheric Dynamics",
               "Equations of motion for the atmosphere. Geostrophic balance, vorticity, instability theory, and general circulation.",
               "4", ["fluid mechanics", "dynamics", "climate modeling", "MATLAB"], ["Students will learn atmospheric dynamics."]),
        Course("CLIMATE 410", "Climate Change Science",
               "Physics of climate change. Greenhouse effect, carbon cycle, paleoclimate, climate models, and future projections. Adaptation and mitigation strategies.",
               "4", ["climate modeling", "sustainability", "statistics", "simulation"], ["Students will understand the science of climate change."]),
        Course("CLIMATE 431", "Atmospheric Chemistry",
               "Chemistry of the troposphere and stratosphere. Air pollution, ozone depletion, aerosols, and chemical transport modeling.",
               "4", ["atmospheric science", "chemical kinetics", "simulation"], ["Students will learn atmospheric chemistry."]),
        Course("CLIMATE 450", "Climate Data Analysis",
               "Statistical methods for climate data. Time series analysis, EOF analysis, spectral methods, and machine learning for climate prediction.",
               "4", ["statistics", "machine learning", "Python", "climate modeling", "remote sensing"], ["Students will apply data analysis to climate science."]),
        Course("CLIMATE 480", "Space Environment and Effects",
               "Space environment impacts on spacecraft and technology. Single event effects, charging, drag, and radiation belts. Design considerations for space missions.",
               "4", ["remote sensing", "simulation", "radiation"], ["Students will understand space environmental effects."]),
    ]


def _seed_ds() -> list[Course]:
    return [
        Course("DATASCI 101", "Introduction to Data Science",
               "Foundations of data science. Data manipulation, visualization, exploratory data analysis, and reproducible research using Python and Jupyter.",
               "4", ["Python", "statistics", "machine learning"], ["Students will learn data science fundamentals."]),
        Course("DATASCI 206", "Data Science Programming",
               "Software engineering for data science. Python programming, version control, testing, data structures, and computational thinking.",
               "4", ["Python", "version control", "software engineering", "testing"], ["Students will learn programming for data science."]),
        Course("DATASCI 306", "Statistical Learning",
               "Supervised and unsupervised learning methods. Regression, classification, tree-based methods, clustering, and dimensionality reduction.",
               "4", ["machine learning", "statistics", "Python", "linear algebra"], ["Students will learn statistical learning methods."]),
        Course("DATASCI 315", "Data Mining",
               "Knowledge discovery from data. Association rules, clustering, classification, anomaly detection, and text mining. Scalable algorithms for large datasets.",
               "4", ["algorithms", "machine learning", "Python", "NLP", "databases"], ["Students will learn data mining techniques."]),
        Course("DATASCI 401", "Applied Machine Learning",
               "Practical machine learning. Feature engineering, model selection, hyperparameter tuning, ensemble methods, and deep learning fundamentals.",
               "4", ["machine learning", "deep learning", "Python", "optimization"], ["Students will apply ML to real-world problems."]),
        Course("DATASCI 415", "Deep Learning",
               "Neural network architectures. CNNs, RNNs, transformers, generative models, and transfer learning. PyTorch implementation and training at scale.",
               "4", ["deep learning", "machine learning", "Python", "computer vision", "NLP"], ["Students will learn deep learning architectures."]),
        Course("DATASCI 451", "Causal Inference",
               "Methods for causal reasoning from data. Randomized experiments, observational studies, propensity scores, instrumental variables, and regression discontinuity.",
               "4", ["statistics", "probability", "Python"], ["Students will learn causal inference methods."]),
        Course("DATASCI 461", "Big Data Analytics",
               "Processing and analyzing large-scale data. Distributed computing with Spark, cloud platforms, data pipelines, and streaming analytics.",
               "4", ["distributed systems", "Python", "SQL", "databases", "machine learning"], ["Students will learn big data processing methods."]),
        Course("DATASCI 478", "Natural Language Processing",
               "Computational methods for language. Tokenization, embeddings, sequence models, transformers, large language models, and text generation.",
               "4", ["NLP", "deep learning", "Python", "machine learning", "artificial intelligence"], ["Students will learn NLP methods."]),
        Course("DATASCI 498", "Data Science Capstone",
               "End-to-end data science project with industry partner. Problem formulation, data collection, modeling, evaluation, deployment, and communication.",
               "4", ["machine learning", "Python", "software engineering", "statistics", "testing"], ["Students will complete a data science project."]),
    ]
