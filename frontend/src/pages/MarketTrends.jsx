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
  engineering_specific: "#ec4899",
  emerging_2026: "#a855f7",
};

const CATEGORY_LABELS = {
  ai_ml: "AI / Machine Learning",
  languages: "Programming Languages",
  data: "Data & Databases",
  cloud_infra: "Cloud & Infrastructure",
  web: "Web Development",
  security: "Security",
  engineering_specific: "Engineering Tools",
  emerging_2026: "Emerging 2026 Tech",
};

export default function MarketTrends({ data }) {
  if (!data) return <p>No trends data available.</p>;

  const categoryData = Object.entries(data.category_demand || {})
    .map(([key, val]) => ({
      name: CATEGORY_LABELS[key] || key,
      demand: Math.round(val * 100) / 100,
      color: CATEGORY_COLORS[key] || "#64748b",
    }))
    .sort((a, b) => b.demand - a.demand);

  const topSkills = (data.top_skills || []).slice(0, 20);
  const maxCount = topSkills.length > 0 ? topSkills[0][1] : 1;

  const emergingData = Object.entries(data.emerging_2026 || {})
    .filter(([, count]) => count > 0)
    .sort((a, b) => b[1] - a[1]);

  const sources = data.sources || {};

  return (
    <>
      {Object.keys(sources).length > 0 && (
        <div className="sources-bar" style={{ marginBottom: 20 }}>
          <span className="sources-label">Job data scraped from:</span>
          {Object.entries(sources).map(([src, count]) => (
            <span key={src} className="source-badge">
              {src} ({count} postings)
            </span>
          ))}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 24 }}>
        <div className="card">
          <div className="card-header">
            <span className="card-title">Demand by Category</span>
            <span className="card-subtitle">
              Across {data.total_postings} job postings
            </span>
          </div>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={categoryData} layout="vertical" margin={{ left: 140 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a3555" />
              <XAxis type="number" stroke="#64748b" />
              <YAxis type="category" dataKey="name" stroke="#94a3b8" tick={{ fontSize: 12 }} width={130} />
              <Tooltip
                contentStyle={{
                  background: "#1a2035",
                  border: "1px solid #2a3555",
                  borderRadius: 8,
                  color: "#f1f5f9",
                }}
              />
              <Bar dataKey="demand" radius={[0, 4, 4, 0]}>
                {categoryData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">2026 Emerging Technologies</span>
            <span className="card-subtitle">High-growth skill areas</span>
          </div>
          {emergingData.length > 0 ? (
            emergingData.map(([skill, count]) => (
              <div key={skill} className="trend-bar">
                <span className="trend-label">{skill}</span>
                <div className="trend-fill-container">
                  <div
                    className="trend-fill"
                    style={{
                      width: `${(count / maxCount) * 100}%`,
                      background: "linear-gradient(90deg, #8b5cf6, #ec4899)",
                    }}
                  >
                    {count}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <p style={{ color: "var(--text-muted)" }}>No emerging tech data</p>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">Top 20 In-Demand Skills</span>
          <span className="card-subtitle">Ranked by frequency in job postings</span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {topSkills.map(([skill, count], i) => (
            <div key={skill} className="trend-bar">
              <span
                className="trend-label"
                style={{ width: 200, display: "flex", gap: 8, alignItems: "center" }}
              >
                <span
                  style={{
                    color: "var(--text-muted)",
                    fontSize: 11,
                    width: 20,
                    textAlign: "right",
                  }}
                >
                  {i + 1}.
                </span>
                {skill}
              </span>
              <div className="trend-fill-container">
                <div
                  className="trend-fill"
                  style={{
                    width: `${(count / maxCount) * 100}%`,
                    background:
                      i < 5
                        ? "linear-gradient(90deg, #3b82f6, #8b5cf6)"
                        : "var(--accent-blue)",
                  }}
                >
                  {count}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
