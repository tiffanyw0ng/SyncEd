export default function Recommendations({ data }) {
  if (!data?.recommendations?.length) {
    return <p style={{ color: "var(--text-muted)" }}>No recommendations available yet.</p>;
  }

  return (
    <>
      <div className="card" style={{ marginBottom: 24 }}>
        <span className="card-title">
          Suggested New Courses for U-M EECS
        </span>
        <p className="card-subtitle" style={{ marginTop: 4 }}>
          AI-generated recommendations based on gaps between current curriculum and
          2026 market demands
        </p>
      </div>

      {data.recommendations.map((rec, i) => (
        <div key={i} className="rec-card">
          <h3>
            <span className="rec-code">{rec.suggested_code}</span>
            {rec.suggested_title}
          </h3>
          <div
            style={{
              display: "inline-block",
              background: "rgba(139, 92, 246, 0.15)",
              color: "var(--accent-purple)",
              padding: "4px 12px",
              borderRadius: 12,
              fontSize: 13,
              fontWeight: 600,
              marginTop: 8,
            }}
          >
            Market Demand Score: {rec.market_demand_score}
          </div>

          <p className="rec-justification">{rec.justification}</p>

          <div style={{ marginBottom: 12 }}>
            <span
              style={{
                fontSize: 12,
                color: "var(--text-muted)",
                textTransform: "uppercase",
                letterSpacing: 0.5,
              }}
            >
              Target Skills
            </span>
            <div className="skill-tags" style={{ marginTop: 6 }}>
              {rec.target_skills.map((s) => (
                <span key={s} className="skill-tag emerging">
                  {s}
                </span>
              ))}
            </div>
          </div>

          <div className="rec-meta">
            <span>
              Related existing:{" "}
              {rec.related_existing_courses.join(", ")}
            </span>
          </div>
        </div>
      ))}
    </>
  );
}
