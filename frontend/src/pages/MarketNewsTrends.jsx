import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from "recharts";

const CATEGORY_COLORS = {
  ai_ml: "#8b5cf6",
  languages: "#3b82f6",
  data: "#06b6d4",
  cloud_infra: "#10b981",
  web: "#f59e0b",
  security: "#ef4444",
  hardware_embedded: "#ec4899",
  electrical_power: "#f97316",
  mechanical_manufacturing: "#84cc16",
  biomedical: "#14b8a6",
  civil_environmental: "#78716c",
  chemical_process: "#e879f9",
  aerospace_defense: "#38bdf8",
  robotics_controls: "#fb923c",
  operations_analytics: "#a3e635",
  emerging_2026: "#a855f7",
};

const CATEGORY_LABELS = {
  ai_ml: "AI / ML",
  languages: "Languages",
  data: "Data & DBs",
  cloud_infra: "Cloud & Infra",
  web: "Web Dev",
  security: "Security",
  hardware_embedded: "Hardware / Embedded",
  electrical_power: "Electrical / Power",
  mechanical_manufacturing: "Mech / Manufacturing",
  biomedical: "Biomedical",
  civil_environmental: "Civil / Environmental",
  chemical_process: "Chemical / Process",
  aerospace_defense: "Aerospace / Defense",
  robotics_controls: "Robotics / Controls",
  operations_analytics: "Operations / Analytics",
  emerging_2026: "Emerging 2026",
};

export default function MarketNewsTrends({ trendsData, newsData, majorName }) {
  if (!trendsData && !newsData) {
    return <p style={{ color: "var(--text-muted)" }}>Loading market & news data...</p>;
  }

  const topSkills = (trendsData?.top_skills || [])
    .slice()
    .sort((a, b) => b[1] - a[1])
    .slice(0, 15);
  const maxSkillCount = topSkills.length > 0
    ? Math.max(...topSkills.map((s) => s[1]))
    : 1;
  const totalPostings = trendsData?.total_postings || 0;

  const categoryData = Object.entries(trendsData?.category_demand || {})
    .map(([key, val]) => ({
      name: CATEGORY_LABELS[key] || key,
      value: val,
      color: CATEGORY_COLORS[key] || "#64748b",
    }))
    .filter((d) => d.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);

  const emergingData = Object.entries(trendsData?.emerging_2026 || {})
    .filter(([, count]) => count > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 12);

  const articles = newsData?.articles || [];
  const trendingTopics = newsData?.trending_topics || [];

  const sources = trendsData?.sources || {};

  return (
    <>
      {Object.keys(sources).length > 0 && (
        <div className="sources-bar">
          <span className="sources-label">Data from:</span>
          {Object.entries(sources).map(([src, count]) => (
            <span key={src} className="source-badge">
              {src} <strong>{count.toLocaleString()}</strong>
            </span>
          ))}
          <span className="source-badge" style={{
            background: "rgba(6, 182, 212, 0.12)", color: "#06b6d4",
            borderColor: "rgba(6, 182, 212, 0.25)",
          }}>
            news <strong>{newsData?.total_articles || 0}</strong>
          </span>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 24 }}>
        <div className="card">
          <div className="card-header">
            <span className="card-title">Top Skills for {majorName}</span>
            <span className="card-subtitle">
              From {totalPostings.toLocaleString()} job postings
            </span>
          </div>
          {topSkills.map(([skill, count], i) => {
            const pct = ((count / totalPostings) * 100).toFixed(1);
            return (
              <div key={skill} className="skill-row">
                <span className="skill-row-rank">{i + 1}</span>
                <span className="skill-row-name">{skill}</span>
                <div className="skill-row-bar-wrap">
                  <div
                    className="skill-row-bar"
                    style={{
                      width: `${(count / maxSkillCount) * 100}%`,
                      background: i < 3
                        ? "linear-gradient(90deg, #3b82f6, #8b5cf6)"
                        : i < 7
                        ? "linear-gradient(90deg, #06b6d4, #3b82f6)"
                        : "var(--accent-blue)",
                    }}
                  />
                </div>
                <span className="skill-row-pct">{pct}%</span>
              </div>
            );
          })}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <div className="card" style={{ flex: "0 0 auto" }}>
            <div className="card-header">
              <span className="card-title">Demand by Category</span>
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={categoryData} layout="vertical" margin={{ left: 80 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a3555" />
                <XAxis type="number" stroke="#64748b" fontSize={11} />
                <YAxis type="category" dataKey="name" stroke="#94a3b8" tick={{ fontSize: 11 }} width={75} />
                <Tooltip contentStyle={{ background: "#1a2035", border: "1px solid #2a3555", borderRadius: 8, color: "#f1f5f9" }} />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {categoryData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="card" style={{ flex: 1 }}>
            <div className="card-header">
              <span className="card-title">Emerging 2026 Tech</span>
              <span className="card-subtitle">Hot skills in job postings</span>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {emergingData.map(([skill, count]) => (
                <span key={skill} className="emerging-chip">
                  {skill}
                  <span className="emerging-chip-count">{count}</span>
                </span>
              ))}
              {emergingData.length === 0 && (
                <p style={{ color: "var(--text-muted)", fontSize: 13 }}>No emerging tech data yet</p>
              )}
            </div>
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 24 }}>
        <div className="card">
          <div className="card-header" style={{ flexDirection: "column", alignItems: "flex-start", gap: 4 }}>
            <span className="card-title">News Trends for {majorName}</span>
            <span className="card-subtitle">
              {newsData?.total_articles || 0} articles scraped
            </span>
          </div>
          {trendingTopics.length > 0 ? trendingTopics.slice(0, 15).map(([topic, count]) => {
            const maxC = trendingTopics[0]?.[1] || 1;
            return (
              <div key={topic} style={{ marginBottom: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                  <span style={{ fontWeight: 600 }}>{topic}</span>
                  <span style={{ color: "var(--text-muted)" }}>{count}</span>
                </div>
                <div style={{
                  height: 6, borderRadius: 3, background: "var(--bg-primary)",
                  overflow: "hidden", marginTop: 3,
                }}>
                  <div style={{
                    height: "100%", borderRadius: 3,
                    background: "linear-gradient(90deg, #06b6d488, #3b82f6)",
                    width: `${(count / maxC) * 100}%`,
                  }} />
                </div>
              </div>
            );
          }) : (
            <p style={{ color: "var(--text-muted)", fontSize: 13 }}>
              No news trends yet -- data is being scraped in the background.
            </p>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">
              {majorName} News ({articles.length})
            </span>
          </div>
          <div style={{ display: "grid", gap: 8, maxHeight: 600, overflowY: "auto" }}>
            {articles.length > 0 ? articles.slice(0, 50).map((article, i) => (
              <a
                key={i}
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="article-card"
              >
                <div style={{ flex: 1 }}>
                  <div className="article-title">{article.title}</div>
                  {article.topics?.length > 0 && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 4 }}>
                      {article.topics.map((t) => (
                        <span key={t} className="topic-chip">{t}</span>
                      ))}
                    </div>
                  )}
                </div>
                <span className="article-source">{article.source}</span>
              </a>
            )) : (
              <p style={{ color: "var(--text-muted)", fontSize: 13, padding: 16 }}>
                No articles yet. Data is being scraped in the background.
              </p>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
