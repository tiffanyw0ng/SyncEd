import { useState, useEffect, useCallback } from "react";
import CurriculumAnalysis from "./pages/CurriculumAnalysis";
import StudentReviews from "./pages/StudentReviews";
import MarketNewsTrends from "./pages/MarketNewsTrends";

const TABS = [
  { id: "curriculum", label: "Curriculum Analysis" },
  { id: "market", label: "Market & News" },
  { id: "reviews", label: "Student Reviews" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("curriculum");
  const [majors, setMajors] = useState([]);
  const [selectedMajor, setSelectedMajor] = useState("cs");
  const [dashboardData, setDashboardData] = useState(null);
  const [trendsData, setTrendsData] = useState(null);
  const [recsData, setRecsData] = useState(null);
  const [newsData, setNewsData] = useState(null);
  const [curriculumData, setCurriculumData] = useState(null);
  const [reviewsData, setReviewsData] = useState(null);
  const [scrapeStatus, setScrapeStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const fetchMajorData = useCallback(async (major) => {
    const qs = `?major=${major}`;
    const [dash, trends, recs, curriculum, reviews] = await Promise.all([
      fetch(`/api/dashboard${qs}`).then((r) => r.json()),
      fetch(`/api/market-trends${qs}`).then((r) => r.json()),
      fetch(`/api/recommendations${qs}`).then((r) => r.json()),
      fetch(`/api/curriculum-analysis${qs}`).then((r) => r.json()),
      fetch(`/api/reviews${qs}`).then((r) => r.json()),
    ]);
    setDashboardData(dash);
    setTrendsData(trends);
    setRecsData(recs);
    setCurriculumData(curriculum);
    setReviewsData(reviews);
  }, []);

  const fetchNews = useCallback(async (major) => {
    const data = await fetch(`/api/news?major=${major}`).then((r) => r.json());
    setNewsData(data);
  }, []);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await fetch("/api/scrape-status").then((r) => r.json());
      setScrapeStatus(data);
    } catch {}
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const majorsResp = await fetch("/api/majors").then((r) => r.json());
        setMajors(majorsResp.majors || []);
        await Promise.all([fetchMajorData("cs"), fetchNews("cs"), fetchStatus()]);
      } catch (err) {
        console.error("Failed to fetch data:", err);
      } finally {
        setLoading(false);
      }
    })();
  }, [fetchMajorData, fetchNews, fetchStatus]);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        await Promise.all([fetchMajorData(selectedMajor), fetchNews(selectedMajor), fetchStatus()]);
      } catch {}
    }, 30000);
    return () => clearInterval(interval);
  }, [selectedMajor, fetchMajorData, fetchNews, fetchStatus]);

  const handleMajorChange = async (majorId) => {
    setSelectedMajor(majorId);
    setAnalyzing(true);
    try {
      const dash = await fetch(`/api/dashboard?major=${majorId}`).then((r) => r.json());
      if (dash.error) {
        await fetch(`/api/majors/${majorId}/analyze`, { method: "POST" });
      }
      await Promise.all([fetchMajorData(majorId), fetchNews(majorId)]);
    } catch (err) {
      console.error("Failed to load major:", err);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await fetch(`/api/refresh?major=${selectedMajor}`, { method: "POST" });
      await Promise.all([fetchMajorData(selectedMajor), fetchNews(selectedMajor)]);
    } finally {
      setRefreshing(false);
    }
  };

  const majorObj = majors.find((m) => m.id === selectedMajor);
  const majorName = majorObj?.name || selectedMajor.toUpperCase();

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
        <p style={{ color: "var(--text-secondary)", fontSize: 14, fontWeight: 500 }}>
          Loading SyncEd...
        </p>
      </div>
    );
  }

  const totalPostings = dashboardData?.total_job_postings || trendsData?.total_postings || 0;
  const totalReviews = reviewsData?.total_reviews || 0;
  const totalArticles = newsData?.total_articles || 0;
  const alignScore = dashboardData?.overall_alignment_score;
  const totalCourses = dashboardData?.total_courses || curriculumData?.total_skills_demanded || 0;

  return (
    <div className="app-layout">
      {/* ===== LEFT SIDEBAR ===== */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1 className="sidebar-logo">SyncEd</h1>
          <span className="sidebar-tagline">Curriculum Intelligence</span>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-section-label">Majors</div>
          <div className="sidebar-majors">
            {majors.map((m) => (
              <button
                key={m.id}
                className={`sidebar-major ${selectedMajor === m.id ? "active" : ""}`}
                onClick={() => handleMajorChange(m.id)}
                disabled={analyzing}
              >
                <span className="sidebar-major-abbr">{m.prefix}</span>
                <span className="sidebar-major-name">{m.name}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="sidebar-section" style={{ marginTop: "auto" }}>
          <button
            className="sidebar-refresh"
            onClick={handleRefresh}
            disabled={refreshing || analyzing}
          >
            {refreshing ? "Scraping..." : "Refresh Data"}
          </button>
          {scrapeStatus?.phase === "scraping" && (
            <div className="sidebar-status scraping">
              Scraping {scrapeStatus.current_major?.toUpperCase()}...
            </div>
          )}
          {scrapeStatus?.phase === "done" && (
            <div className="sidebar-status done">
              {scrapeStatus.completed_majors?.length} majors ready
            </div>
          )}
        </div>

        <div className="sidebar-footer">
          U-M College of Engineering
        </div>
      </aside>

      {/* ===== MAIN CONTENT ===== */}
      <main className="main-content">
        {/* Top bar */}
        <div className="topbar">
          <div className="topbar-left">
            <h2 className="topbar-title">{majorName}</h2>
            {analyzing && (
              <span className="topbar-analyzing">
                <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                Analyzing...
              </span>
            )}
          </div>
          <div className="quick-stats">
            {alignScore != null && (
              <div className="quick-stat">
                <span className="quick-stat-value" style={{
                  color: alignScore > 50 ? "var(--accent-green)" : alignScore > 30 ? "var(--accent-amber)" : "var(--accent-red)",
                }}>{alignScore}%</span>
                <span className="quick-stat-label">Alignment</span>
              </div>
            )}
            <div className="quick-stat">
              <span className="quick-stat-value">{totalCourses || "—"}</span>
              <span className="quick-stat-label">Courses</span>
            </div>
            <div className="quick-stat">
              <span className="quick-stat-value">{totalPostings.toLocaleString()}</span>
              <span className="quick-stat-label">Jobs</span>
            </div>
            <div className="quick-stat">
              <span className="quick-stat-value">{totalReviews}</span>
              <span className="quick-stat-label">Reviews</span>
            </div>
            <div className="quick-stat">
              <span className="quick-stat-value">{totalArticles}</span>
              <span className="quick-stat-label">News</span>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <nav className="nav-tabs">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={`nav-tab ${activeTab === tab.id ? "active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {/* Tab Content */}
        <div className="tab-content">
          {activeTab === "curriculum" && (
            <CurriculumAnalysis data={curriculumData} recsData={recsData} majorName={majorName} />
          )}
          {activeTab === "market" && (
            <MarketNewsTrends trendsData={trendsData} newsData={newsData} majorName={majorName} />
          )}
          {activeTab === "reviews" && (
            <StudentReviews data={reviewsData} majorName={majorName} />
          )}
        </div>
      </main>
    </div>
  );
}
