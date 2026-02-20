"""
Vectorization & Similarity Engine

Converts course descriptions and job postings into vectors,
then computes cosine similarity to find curriculum gaps.

Works with ANY major — generates recommendations dynamically
based on what skills are missing vs. what the market demands.
"""

from dataclasses import dataclass
from datetime import datetime

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.scrapers.umich_courses import Course
from backend.scrapers.job_postings import (
    JobPosting, SKILL_TAXONOMY,
    MAJOR_RELEVANT_CATEGORIES, MAJOR_EXTRA_SKILLS, INDUSTRY_TOP_SKILLS,
)

SKILL_ALIASES: dict[str, set[str]] = {
    "python": {"python programming", "python3", "cpython"},
    "c++": {"c++ programming", "cpp", "c/c++"},
    "c": {"c programming", "c language"},
    "java": {"java programming"},
    "javascript": {"js", "ecmascript"},
    "typescript": {"ts"},
    "react": {"react.js", "reactjs"},
    "machine learning": {"ml", "machine-learning", "statistical learning"},
    "deep learning": {"dl", "deep-learning", "neural network", "neural networks"},
    "artificial intelligence": {"ai"},
    "computer vision": {"cv", "image processing", "image recognition"},
    "nlp": {"natural language processing", "text mining", "sentiment analysis"},
    "sql": {"database", "databases", "relational database", "query optimization", "relational databases"},
    "docker": {"containerization", "containers"},
    "kubernetes": {"k8s", "container orchestration"},
    "aws": {"amazon web services", "cloud computing", "cloud"},
    "gcp": {"google cloud"},
    "azure": {"microsoft azure"},
    "tensorflow": {"tf"},
    "pytorch": {"torch"},
    "data structures": {"data structure"},
    "algorithms": {"algorithm design", "algorithm analysis", "algorithmic thinking"},
    "operating systems": {"os", "systems programming"},
    "computer architecture": {"processor design", "cpu design", "assembly"},
    "distributed systems": {"distributed computing"},
    "networks": {"networking", "computer networks", "tcp/ip"},
    "security": {"cybersecurity", "network security", "information security", "cryptography", "encryption"},
    "parallel computing": {"parallel programming", "concurrency", "threading", "multithreading"},
    "embedded systems": {"embedded programming", "microcontroller", "firmware"},
    "signal processing": {"dsp", "digital signal processing"},
    "matlab": {"matlab/simulink", "simulink"},
    "verilog": {"verilog hdl"},
    "vhdl": {"vhdl hdl"},
    "fpga": {"fpga design", "fpga programming"},
    "pcb design": {"pcb layout", "circuit board design", "altium", "kicad"},
    "robotics": {"robot", "robotic systems"},
    "control systems": {"controls", "feedback control", "pid control", "control theory"},
    "solidworks": {"solid works", "3d modeling"},
    "autocad": {"auto cad", "2d drafting"},
    "finite element": {"fea", "finite element analysis", "fem"},
    "cfd": {"computational fluid dynamics"},
    "thermodynamics": {"thermo", "heat transfer"},
    "fluid mechanics": {"fluids", "fluid dynamics"},
    "biomechanics": {"bio mechanics", "mechanical biology"},
    "bioinformatics": {"computational biology", "genomics"},
    "structural analysis": {"structural engineering", "structural design"},
    "gis": {"geographic information systems", "geospatial"},
    "manufacturing": {"manufacturing processes", "cnc", "machining"},
    "statistics": {"statistical analysis", "probability", "statistical methods"},
    "linear algebra": {"matrix algebra", "matrices"},
    "optimization": {"mathematical optimization", "linear programming"},
    "regression": {"linear regression", "logistic regression"},
    "data pipeline": {"etl", "data engineering", "data ingestion"},
    "ci/cd": {"continuous integration", "continuous deployment", "devops"},
    "rest api": {"api design", "web services", "api"},
    "git": {"version control", "github"},
    "agile": {"scrum", "project management"},
    "power electronics": {"power conversion", "inverter", "converter"},
    "electromagnetics": {"em theory", "electromagnetic fields"},
    "analog design": {"analog circuits", "analog electronics"},
    "rf design": {"radio frequency", "rf engineering"},
    "semiconductor": {"semiconductor physics", "transistor", "cmos"},
    "antenna design": {"antenna", "antennas"},
    "communications systems": {"wireless communications", "digital communications"},
    "motor control": {"electric motors", "motor drives"},
    "battery management": {"bms", "energy storage"},
    "photonics": {"optics", "optical engineering", "fiber optics"},
    "sustainability": {"sustainable engineering", "green engineering", "environmental"},
    "3d printing": {"additive manufacturing", "rapid prototyping"},
}


@dataclass
class GapAnalysis:
    course_code: str
    course_title: str
    alignment_score: float
    covered_skills: list[str]
    missing_skills: list[str]
    obsolete_topics: list[str]
    recommended_additions: list[str]
    most_relevant_jobs: list[str]


@dataclass
class NewCourseRecommendation:
    suggested_code: str
    suggested_title: str
    justification: str
    target_skills: list[str]
    market_demand_score: float
    related_existing_courses: list[str]


SIMILARITY_SAMPLE_SIZE = 3000


class CurriculumAnalyzer:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=3000,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )

    def analyze(
        self,
        courses: list[Course],
        postings: list[JobPosting],
        threshold: float = 0.65,
        major_prefix: str = "DEPT",
    ) -> dict:
        market_skills = self._aggregate_market_skills(postings)

        sim_postings = postings
        if len(postings) > SIMILARITY_SAMPLE_SIZE:
            rng = np.random.default_rng(42)
            indices = rng.choice(len(postings), size=SIMILARITY_SAMPLE_SIZE, replace=False)
            sim_postings = [postings[i] for i in indices]
            print(f"[Vectorizer] Sampled {SIMILARITY_SAMPLE_SIZE}/{len(postings)} postings for similarity")

        course_texts = [self._course_to_text(c) for c in courses]
        posting_texts = [self._posting_to_text(p) for p in sim_postings]

        all_texts = course_texts + posting_texts
        tfidf_matrix = self.vectorizer.fit_transform(all_texts)

        n_courses = len(courses)
        course_vectors = tfidf_matrix[:n_courses]
        posting_vectors = tfidf_matrix[n_courses:]

        sim_matrix = cosine_similarity(course_vectors, posting_vectors)

        gaps = []
        for i, course in enumerate(courses):
            gap = self._analyze_course_gap(
                course, sim_matrix[i], sim_postings, market_skills, threshold
            )
            gaps.append(gap)

        new_courses = self._recommend_new_courses(courses, market_skills, major_prefix)
        overall_score = self._compute_overall_alignment(gaps)

        print(f"[Vectorizer] Analysis complete: {len(courses)} courses, {len(postings)} total postings, score={overall_score}")

        return {
            "overall_alignment_score": overall_score,
            "course_gaps": [self._gap_to_dict(g) for g in gaps],
            "new_course_recommendations": [self._rec_to_dict(r) for r in new_courses],
            "market_skill_summary": market_skills,
            "total_postings_analyzed": len(postings),
            "analysis_timestamp": datetime.utcnow().isoformat(),
        }

    def _course_to_text(self, course: Course) -> str:
        return " ".join([
            course.title, course.description,
            " ".join(course.topics), " ".join(course.learning_objectives),
        ])

    def _posting_to_text(self, posting: JobPosting) -> str:
        return " ".join([
            posting.title, posting.description,
            " ".join(posting.skills), " ".join(posting.tools),
        ])

    def _aggregate_market_skills(self, postings: list[JobPosting]) -> dict:
        skill_freq: dict[str, int] = {}
        for p in postings:
            for s in p.skills:
                skill_freq[s] = skill_freq.get(s, 0) + 1

        total = len(postings) or 1
        skill_demand = {s: count / total for s, count in skill_freq.items()}
        sorted_skills = sorted(skill_demand.items(), key=lambda x: -x[1])

        category_demand = {}
        for cat, skills in SKILL_TAXONOMY.items():
            cat_total = sum(skill_freq.get(s.lower(), 0) for s in skills)
            category_demand[cat] = cat_total / total

        return {
            "skill_demand": dict(sorted_skills),
            "category_demand": category_demand,
        }

    def _analyze_course_gap(
        self,
        course: Course,
        similarities: np.ndarray,
        postings: list[JobPosting],
        market_skills: dict,
        threshold: float,
    ) -> GapAnalysis:
        avg_sim = float(np.mean(similarities))
        max_sim = float(np.max(similarities))
        alignment = min(100, (avg_sim * 0.4 + max_sim * 0.6) * 200)

        top_job_indices = np.argsort(similarities)[-5:][::-1]
        most_relevant_jobs = [postings[i].title for i in top_job_indices]

        relevant_postings = [postings[i] for i in top_job_indices]
        job_skills = set()
        for p in relevant_postings:
            job_skills.update(s.lower() for s in p.skills)

        course_skills = set(t.lower() for t in course.topics)

        covered = course_skills & job_skills
        missing = job_skills - course_skills

        high_demand = {s for s, d in market_skills["skill_demand"].items() if d > 0.3}
        critical_missing = missing & high_demand

        obsolete = self._detect_obsolete(course, job_skills)

        recommended = sorted(
            critical_missing,
            key=lambda s: market_skills["skill_demand"].get(s, 0),
            reverse=True,
        )

        return GapAnalysis(
            course_code=course.code,
            course_title=course.title,
            alignment_score=round(alignment, 1),
            covered_skills=sorted(covered),
            missing_skills=sorted(missing),
            obsolete_topics=obsolete,
            recommended_additions=recommended[:8],
            most_relevant_jobs=most_relevant_jobs,
        )

    def _detect_obsolete(self, course: Course, job_skills: set[str]) -> list[str]:
        obsolete = []

        OBSOLESCENCE_MAP = {
            "pointers": ("rust", "memory-safe programming", "market shifting to Rust / memory-safe languages"),
            "manual memory management": ("rust", "memory-safe programming", "market shifting to Rust / memory-safe languages"),
            "sql": ("vector database", "vector search", "market increasingly using vector databases alongside SQL"),
        }

        for topic in course.topics:
            key = topic.lower()
            if key in OBSOLESCENCE_MAP:
                replacement, alt, reason = OBSOLESCENCE_MAP[key]
                if replacement in job_skills or alt in job_skills:
                    obsolete.append(f"{topic} ({reason})")

        return obsolete

    def _recommend_new_courses(
        self,
        courses: list[Course],
        market_skills: dict,
        major_prefix: str,
    ) -> list[NewCourseRecommendation]:
        all_course_topics = set()
        for c in courses:
            all_course_topics.update(t.lower() for t in c.topics)

        demand = market_skills["skill_demand"]
        gaps: dict[str, float] = {}
        for skill, score in demand.items():
            if skill not in all_course_topics and score > 0.1:
                gaps[skill] = score

        if not gaps:
            return []

        recommendations = []
        used_skills: set[str] = set()

        COURSE_TEMPLATES = [
            {
                "skills": {"agentic ai", "ai agents", "multi-agent systems", "llm orchestration", "langchain", "crewai"},
                "title": "Agentic Systems & LLM Orchestration",
                "justification": "High market demand for autonomous AI agents and multi-agent orchestration. Students need hands-on experience building AI systems that can reason, plan, and execute complex tasks.",
                "related_pattern": ["machine learning", "artificial intelligence", "deep learning"],
            },
            {
                "skills": {"rust", "memory-safe programming"},
                "title": "Systems Programming in Rust",
                "justification": "Industry is rapidly adopting Rust for infrastructure, networking, and safety-critical systems. Memory-safe systems languages are increasingly required.",
                "related_pattern": ["c++", "operating systems", "embedded"],
            },
            {
                "skills": {"vector database", "vector search", "rag", "retrieval augmented generation"},
                "title": "AI-Native Data Systems: Vector Search & RAG",
                "justification": "Modern AI systems require vector search and RAG pipelines for knowledge retrieval. Traditional database courses focus on relational models.",
                "related_pattern": ["sql", "databases", "data structures"],
            },
            {
                "skills": {"edge ai", "on-device ml", "federated learning"},
                "title": "Edge AI & On-Device Machine Learning",
                "justification": "Growing demand for deploying ML models on edge devices with constraints on compute, memory, and power.",
                "related_pattern": ["machine learning", "embedded", "sensors"],
            },
            {
                "skills": {"digital twin", "simulation"},
                "title": "Digital Twins & Physics-Informed Simulation",
                "justification": "Industry demand for digital twin platforms combining IoT sensor data with physics-based simulation and ML for predictive maintenance.",
                "related_pattern": ["simulation", "cad", "sensors", "manufacturing"],
            },
            {
                "skills": {"autonomous systems", "slam", "motion planning", "perception"},
                "title": "Autonomous Systems Engineering",
                "justification": "Surging demand for engineers who can build autonomous vehicles, drones, and robotic systems with perception and planning capabilities.",
                "related_pattern": ["robotics", "control systems", "computer vision"],
            },
            {
                "skills": {"sustainability", "renewable energy", "green engineering"},
                "title": "Sustainable Engineering & Clean Technology",
                "justification": "Industry increasingly requires engineers with sustainability expertise. Life-cycle assessment, renewable energy, and green manufacturing are critical.",
                "related_pattern": ["thermodynamics", "manufacturing", "environmental engineering"],
            },
            {
                "skills": {"3d printing", "additive manufacturing"},
                "title": "Advanced Additive Manufacturing",
                "justification": "Additive manufacturing is transforming prototyping and production across aerospace, medical, and automotive. Students need design-for-AM skills.",
                "related_pattern": ["manufacturing", "cad", "materials science"],
            },
            {
                "skills": {"machine learning", "deep learning", "python"},
                "title": "Applied Machine Learning for Engineers",
                "justification": "ML is becoming essential across all engineering disciplines. Engineers need data-driven modeling skills beyond traditional analytical methods.",
                "related_pattern": ["matlab", "statistics", "optimization", "simulation"],
            },
        ]

        for template in COURSE_TEMPLATES:
            matching_skills = template["skills"] & set(gaps.keys())
            if not matching_skills or matching_skills & used_skills:
                continue

            template_demand = sum(gaps.get(s, 0) for s in matching_skills)
            if template_demand < 0.1:
                continue

            related = []
            for c in courses:
                course_topics_lower = {t.lower() for t in c.topics}
                if course_topics_lower & set(template["related_pattern"]):
                    related.append(c.code)

            recommendations.append(NewCourseRecommendation(
                suggested_code=f"{major_prefix} 498",
                suggested_title=template["title"],
                justification=template["justification"],
                target_skills=sorted(matching_skills),
                market_demand_score=round(template_demand * 100 / max(len(matching_skills), 1), 1),
                related_existing_courses=related[:4],
            ))

            used_skills.update(matching_skills)

        recommendations.sort(key=lambda r: -r.market_demand_score)
        return recommendations[:6]

    def _compute_overall_alignment(self, gaps: list[GapAnalysis]) -> float:
        if not gaps:
            return 0.0
        return round(sum(g.alignment_score for g in gaps) / len(gaps), 1)

    def _gap_to_dict(self, gap: GapAnalysis) -> dict:
        return {
            "course_code": gap.course_code,
            "course_title": gap.course_title,
            "alignment_score": gap.alignment_score,
            "covered_skills": gap.covered_skills,
            "missing_skills": gap.missing_skills,
            "obsolete_topics": gap.obsolete_topics,
            "recommended_additions": gap.recommended_additions,
            "most_relevant_jobs": gap.most_relevant_jobs,
        }

    def _rec_to_dict(self, rec: NewCourseRecommendation) -> dict:
        return {
            "suggested_code": rec.suggested_code,
            "suggested_title": rec.suggested_title,
            "justification": rec.justification,
            "target_skills": rec.target_skills,
            "market_demand_score": rec.market_demand_score,
            "related_existing_courses": rec.related_existing_courses,
        }

    def analyze_curriculum_weaknesses(
        self,
        courses: list[Course],
        postings: list[JobPosting],
        major_name: str = "Unknown",
        major_id: str = "cs",
    ) -> dict:
        """
        Deep curriculum analysis using the curated INDUSTRY_TOP_SKILLS list
        as the primary benchmark (30 skills per major). This gives a realistic
        grade because it measures what matters most, not every niche tool.
        """
        market_skills = self._aggregate_market_skills(postings)

        all_course_topics = set()
        all_course_text = ""
        for c in courses:
            all_course_topics.update(t.lower() for t in c.topics)
            all_course_text += f" {c.title} {c.description} {' '.join(c.topics)} {' '.join(c.learning_objectives)} "
        all_course_text = all_course_text.lower()

        full_demand = market_skills["skill_demand"]
        cat_demand = market_skills["category_demand"]

        curated = INDUSTRY_TOP_SKILLS.get(major_id, [])
        demand = {}
        for skill in curated:
            sl = skill.lower()
            score = full_demand.get(sl, 0)
            if score < 0.005:
                score = max(0.01, 0.30 - 0.008 * curated.index(skill))
            demand[sl] = score

        def _skill_is_covered(skill: str) -> bool:
            if skill in all_course_topics:
                return True
            if len(skill) >= 3 and skill in all_course_text:
                return True
            aliases = SKILL_ALIASES.get(skill, set())
            for alias in aliases:
                if alias in all_course_topics or (len(alias) >= 3 and alias in all_course_text):
                    return True
            for topic in all_course_topics:
                if topic in SKILL_ALIASES and skill in SKILL_ALIASES[topic]:
                    return True
                if len(topic) >= 3 and len(skill) >= 3:
                    if topic in skill or skill in topic:
                        return True
            return False

        relevant_cats = MAJOR_RELEVANT_CATEGORIES.get(major_id, set(SKILL_TAXONOMY.keys()))

        # --- Category coverage (only relevant categories) ---
        category_coverage = {}
        for cat in relevant_cats:
            skills = SKILL_TAXONOMY.get(cat, [])
            cat_skills_lower = {s.lower() for s in skills}
            covered = {s for s in cat_skills_lower if _skill_is_covered(s)}
            total_in_cat = len(cat_skills_lower)
            pct = round(len(covered) / max(total_in_cat, 1) * 100, 1)
            category_coverage[cat] = {
                "coverage_pct": pct,
                "covered": sorted(covered),
                "missing": sorted(cat_skills_lower - covered),
                "market_demand": round(cat_demand.get(cat, 0) * 100, 1),
            }

        # --- Strengths ---
        strengths = []
        for skill, score in sorted(demand.items(), key=lambda x: -x[1]):
            if _skill_is_covered(skill):
                covering_courses = [
                    c.code for c in courses
                    if skill in {t.lower() for t in c.topics}
                    or skill in f"{c.title} {c.description} {' '.join(c.topics)}".lower()
                ]
                strengths.append({
                    "skill": skill,
                    "market_demand": round(score * 100, 1),
                    "covered_by": covering_courses[:4],
                })

        # --- Weaknesses ---
        weaknesses = []
        for skill, score in sorted(demand.items(), key=lambda x: -x[1]):
            if not _skill_is_covered(skill):
                closest_courses = []
                for c in courses:
                    topic_set = {t.lower() for t in c.topics}
                    cat_for_skill = None
                    for cat, cat_skills in SKILL_TAXONOMY.items():
                        if skill in {s.lower() for s in cat_skills}:
                            cat_for_skill = cat
                            break
                    if cat_for_skill:
                        related = {s.lower() for s in SKILL_TAXONOMY[cat_for_skill]}
                        if topic_set & related:
                            closest_courses.append(c.code)
                weaknesses.append({
                    "skill": skill,
                    "market_demand": round(score * 100, 1),
                    "severity": "critical" if score > 0.15 else "high" if score > 0.08 else "moderate",
                    "could_be_added_to": closest_courses[:3],
                    "recommendation": self._weakness_recommendation(skill),
                })

        # --- Emerging 2026 gaps ---
        emerging_gaps = []
        for skill_name in SKILL_TAXONOMY.get("emerging_2026", []):
            s = skill_name.lower()
            if not _skill_is_covered(s):
                d = demand.get(s, 0) or full_demand.get(s, 0)
                emerging_gaps.append({
                    "skill": skill_name,
                    "market_demand": round(d * 100, 1),
                    "status": "not_taught" if d > 0.02 else "emerging",
                })

        # --- Per-course weakness breakdown ---
        course_weaknesses = []
        for c in courses:
            c_topics = {t.lower() for t in c.topics}
            c_text = f"{c.title} {c.description} {' '.join(c.topics)}".lower()
            c_missing_high_demand = []
            for skill, score in demand.items():
                if skill not in c_topics and skill not in c_text and score > 0.03:
                    for cat, cat_skills in SKILL_TAXONOMY.items():
                        if skill in {s.lower() for s in cat_skills}:
                            if c_topics & {s.lower() for s in cat_skills}:
                                c_missing_high_demand.append({
                                    "skill": skill,
                                    "demand": round(score * 100, 1),
                                })
                                break

            if c_missing_high_demand:
                course_weaknesses.append({
                    "course_code": c.code,
                    "course_title": c.title,
                    "current_topics": c.topics,
                    "missing_high_demand": sorted(
                        c_missing_high_demand, key=lambda x: -x["demand"]
                    )[:5],
                    "improvement_suggestion": self._course_improvement(c, c_missing_high_demand),
                })

        # --- Overall grade ---
        total_demanded = len(demand)
        total_covered = len([s for s in demand if _skill_is_covered(s)])
        coverage_grade = round(total_covered / max(total_demanded, 1) * 100, 1)

        grade_letter = (
            "A"  if coverage_grade >= 80 else
            "B+" if coverage_grade >= 70 else
            "B"  if coverage_grade >= 60 else
            "B-" if coverage_grade >= 52 else
            "C+" if coverage_grade >= 44 else
            "C"  if coverage_grade >= 36 else
            "C-" if coverage_grade >= 28 else
            "D"  if coverage_grade >= 20 else "F"
        )

        return {
            "major_name": major_name,
            "overall_grade": grade_letter,
            "coverage_score": coverage_grade,
            "total_skills_demanded": total_demanded,
            "total_skills_covered": total_covered,
            "category_coverage": category_coverage,
            "strengths": strengths[:15],
            "weaknesses": weaknesses[:15],
            "emerging_gaps": emerging_gaps,
            "course_weaknesses": course_weaknesses,
            "summary": self._generate_summary(
                major_name, grade_letter, coverage_grade, strengths, weaknesses, emerging_gaps
            ),
        }

    def _weakness_recommendation(self, skill: str) -> str:
        recs = {
            "rust": "Add a Rust module to systems programming courses, or create a dedicated 'Systems Programming in Rust' elective",
            "agentic ai": "Create a special topics course on AI Agents and autonomous systems with hands-on LangChain/CrewAI projects",
            "ai agents": "Incorporate multi-agent system design into existing AI/ML courses",
            "vector database": "Add vector search and embedding storage to database courses alongside traditional SQL",
            "rag": "Include RAG pipeline design in NLP or information retrieval courses",
            "llm": "Integrate LLM API usage and prompt engineering into existing ML/AI courses",
            "docker": "Add containerization labs to software engineering or systems courses",
            "kubernetes": "Include container orchestration in cloud computing or distributed systems courses",
            "terraform": "Add infrastructure-as-code modules to cloud/DevOps coursework",
            "edge ai": "Create course modules on deploying ML models to resource-constrained devices",
            "digital twin": "Integrate digital twin concepts into simulation or IoT courses",
            "sustainability": "Add sustainability metrics and green engineering principles across design courses",
            "3d printing": "Expand manufacturing courses to include additive manufacturing design rules",
        }
        return recs.get(skill, f"Consider adding {skill} coverage to relevant existing courses or create a new special topics elective")

    def _course_improvement(self, course: Course, missing: list[dict]) -> str:
        skills = [m["skill"] for m in missing[:3]]
        return (
            f"{course.code} currently teaches {', '.join(course.topics[:3])}. "
            f"To improve market alignment, consider adding modules on: {', '.join(skills)}. "
            f"These skills appear in {missing[0]['demand']}% of relevant job postings."
        )

    def _generate_summary(
        self, major_name, grade, score, strengths, weaknesses, emerging_gaps
    ) -> str:
        top_strengths = ", ".join(s["skill"] for s in strengths[:3]) or "limited coverage"
        top_weaknesses = ", ".join(w["skill"] for w in weaknesses[:3]) or "none identified"
        top_emerging = ", ".join(g["skill"] for g in emerging_gaps[:3]) or "none identified"

        if grade.startswith("A"):
            tone = f"The {major_name} curriculum shows strong market alignment (Grade {grade}, {score}% coverage)."
        elif grade.startswith("B"):
            tone = f"The {major_name} curriculum has good market alignment (Grade {grade}, {score}% coverage) with some areas for improvement."
        elif grade.startswith("C"):
            tone = f"The {major_name} curriculum has moderate market alignment (Grade {grade}, {score}% coverage) with room for improvement."
        else:
            tone = f"The {major_name} curriculum needs updates (Grade {grade}, {score}% coverage) to better meet current market demands."

        return (
            f"{tone} "
            f"Key strengths include {top_strengths}. "
            f"Critical gaps exist in {top_weaknesses}. "
            f"Emerging 2026 technologies not yet addressed: {top_emerging}."
        )
