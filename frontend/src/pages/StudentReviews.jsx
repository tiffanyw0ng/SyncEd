import { useState } from "react";

const RISK_COLORS = {
  critical: { bg: "rgba(239, 68, 68, 0.12)", border: "rgba(239, 68, 68, 0.35)", text: "#ef4444", label: "CRITICAL" },
  high: { bg: "rgba(245, 158, 11, 0.12)", border: "rgba(245, 158, 11, 0.35)", text: "#f59e0b", label: "HIGH RISK" },
  moderate: { bg: "rgba(59, 130, 246, 0.12)", border: "rgba(59, 130, 246, 0.35)", text: "#3b82f6", label: "WATCH" },
};

const SENTIMENT_COLORS = { positive: "#10b981", negative: "#ef4444", neutral: "#94a3b8" };

export default function StudentReviews({ data, majorName }) {
  const [expandedCourse, setExpandedCourse] = useState(null);

  if (!data || data.error) {
    return (
      <div className="card">
        <p style={{ color: "var(--text-muted)" }}>
          No student review data yet. Click <strong>Refresh Data</strong> to scrape reviews from Reddit and Google.
        </p>
      </div>
    );
  }

  const atRisk = data.courses_at_risk || [];
  const allCourses = data.course_summaries || [];
  const themes = data.overall_themes || [];

  return (
    <>
      {/* At-Risk Courses Banner */}
      {atRisk.length > 0 && (
        <div className="card" style={{ marginBottom: 24, borderLeft: "4px solid #ef4444" }}>
          <div className="card-header">
            <span className="card-title">
              Courses at Risk ({atRisk.length})
            </span>
            <span className="card-subtitle">
              Courses where students are unhappy AND/OR market alignment is low — these need urgent attention
            </span>
          </div>
          <div style={{ display: "grid", gap: 10 }}>
            {atRisk.map((c) => {
              const risk = RISK_COLORS[c.risk_level] || RISK_COLORS.moderate;
              return (
                <div key={c.course_code} style={{
                  padding: "14px 18px", borderRadius: 10,
                  background: risk.bg, border: `1px solid ${risk.border}`,
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                      <span style={{ fontWeight: 700, fontSize: 15, color: risk.text }}>
                        {c.course_code}
                      </span>
                      <span style={{
                        marginLeft: 8, fontSize: 11, padding: "2px 8px", borderRadius: 8,
                        background: `${risk.text}22`, color: risk.text, fontWeight: 700,
                        textTransform: "uppercase", letterSpacing: 0.5,
                      }}>
                        {risk.label}
                      </span>
                    </div>
                    <div style={{ display: "flex", gap: 12, fontSize: 12 }}>
                      <span>
                        Sentiment: <strong style={{ color: c.avg_sentiment < 0 ? "#ef4444" : "#10b981" }}>
                          {c.avg_sentiment > 0 ? "+" : ""}{c.avg_sentiment}
                        </strong>
                      </span>
                      {c.alignment_score != null && (
                        <span>
                          Market: <strong style={{
                            color: c.alignment_score < 50 ? "#ef4444" : "#10b981"
                          }}>
                            {c.alignment_score}%
                          </strong>
                        </span>
                      )}
                    </div>
                  </div>
                  <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "8px 0 0" }}>
                    {c.reason}
                  </p>
                  {c.top_complaints?.length > 0 && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 8 }}>
                      {c.top_complaints.map(([theme, count]) => (
                        <span key={theme} style={{
                          fontSize: 11, padding: "2px 8px", borderRadius: 6,
                          background: "rgba(239,68,68,0.1)", color: "#ef4444", fontWeight: 600,
                        }}>
                          {theme} ({count})
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Stats + Themes Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 24 }}>
        {/* Review Stats */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Review Overview</span>
            <span className="card-subtitle">
              {data.total_reviews} reviews from {data.sources?.join(", ") || "multiple sources"}
            </span>
          </div>
          <div className="stat-row" style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
            <div className="stat-card" style={{ textAlign: "center", padding: 16 }}>
              <div className="stat-number" style={{ color: "#10b981" }}>
                {allCourses.reduce((s, c) => s + c.positive, 0)}
              </div>
              <div className="stat-label">Positive</div>
            </div>
            <div className="stat-card" style={{ textAlign: "center", padding: 16 }}>
              <div className="stat-number" style={{ color: "#ef4444" }}>
                {allCourses.reduce((s, c) => s + c.negative, 0)}
              </div>
              <div className="stat-label">Negative</div>
            </div>
            <div className="stat-card" style={{ textAlign: "center", padding: 16 }}>
              <div className="stat-number" style={{ color: "#94a3b8" }}>
                {allCourses.reduce((s, c) => s + c.neutral, 0)}
              </div>
              <div className="stat-label">Neutral</div>
            </div>
          </div>
        </div>

        {/* Themes */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Common Themes</span>
            <span className="card-subtitle">What students are saying across all courses</span>
          </div>
          {themes.length > 0 ? themes.slice(0, 10).map((t) => {
            const isNeg = t.type === "negative";
            const maxCount = themes[0]?.count || 1;
            return (
              <div key={t.theme} style={{ marginBottom: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                  <span style={{ fontWeight: 600, color: isNeg ? "#ef4444" : "#10b981" }}>
                    {t.theme}
                  </span>
                  <span style={{ color: "var(--text-muted)" }}>{t.count} mentions</span>
                </div>
                <div style={{
                  height: 6, borderRadius: 3, background: "var(--bg-primary)",
                  overflow: "hidden", marginTop: 3,
                }}>
                  <div style={{
                    height: "100%", borderRadius: 3,
                    background: isNeg
                      ? "linear-gradient(90deg, #ef444488, #ef4444)"
                      : "linear-gradient(90deg, #10b98188, #10b981)",
                    width: `${(t.count / maxCount) * 100}%`,
                  }} />
                </div>
              </div>
            );
          }) : <p style={{ color: "var(--text-muted)" }}>No themes detected</p>}
        </div>
      </div>

      {/* Per-Course Review Breakdown */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Per-Course Student Sentiment</span>
          <span className="card-subtitle">Click any course to see student quotes</span>
        </div>
        <div style={{ display: "grid", gap: 8 }}>
          {allCourses.map((cs) => {
            const sentColor = cs.avg_sentiment > 0.1 ? "#10b981" : cs.avg_sentiment < -0.1 ? "#ef4444" : "#94a3b8";
            const pctPos = cs.total_reviews > 0 ? Math.round(cs.positive / cs.total_reviews * 100) : 0;
            const pctNeg = cs.total_reviews > 0 ? Math.round(cs.negative / cs.total_reviews * 100) : 0;
            const isExpanded = expandedCourse === cs.course_code;

            return (
              <div key={cs.course_code} style={{
                padding: "12px 16px", borderRadius: 10,
                background: "var(--bg-primary)", border: "1px solid var(--border)",
                cursor: "pointer",
              }} onClick={() => setExpandedCourse(isExpanded ? null : cs.course_code)}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontWeight: 700, color: "var(--accent-cyan)", fontSize: 14 }}>
                      {cs.course_code}
                    </span>
                    <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                      {cs.total_reviews} reviews
                    </span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    {/* Mini sentiment bar */}
                    <div style={{
                      width: 80, height: 8, borderRadius: 4, background: "#94a3b822",
                      display: "flex", overflow: "hidden",
                    }}>
                      <div style={{ width: `${pctPos}%`, background: "#10b981" }} />
                      <div style={{ width: `${pctNeg}%`, background: "#ef4444" }} />
                    </div>
                    <span style={{ fontSize: 13, fontWeight: 700, color: sentColor }}>
                      {cs.avg_sentiment > 0 ? "+" : ""}{cs.avg_sentiment}
                    </span>
                  </div>
                </div>

                {/* Complaint/Praise tags */}
                {(cs.top_complaints?.length > 0 || cs.top_praises?.length > 0) && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 6 }}>
                    {cs.top_complaints?.map(([t, c]) => (
                      <span key={t} style={{
                        fontSize: 10, padding: "1px 6px", borderRadius: 4,
                        background: "rgba(239,68,68,0.1)", color: "#ef4444",
                      }}>
                        {t}
                      </span>
                    ))}
                    {cs.top_praises?.map(([t, c]) => (
                      <span key={t} style={{
                        fontSize: 10, padding: "1px 6px", borderRadius: 4,
                        background: "rgba(16,185,129,0.1)", color: "#10b981",
                      }}>
                        {t}
                      </span>
                    ))}
                  </div>
                )}

                {/* Expanded: sample quotes */}
                {isExpanded && (
                  <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
                    {cs.sample_negative?.length > 0 && (
                      <div style={{ marginBottom: 10 }}>
                        <div style={{ fontSize: 12, color: "#ef4444", fontWeight: 600, marginBottom: 6 }}>
                          Negative Reviews:
                        </div>
                        {cs.sample_negative.map((r, i) => (
                          <div key={i} style={{
                            fontSize: 12, color: "var(--text-secondary)",
                            padding: "8px 10px", marginBottom: 4, borderRadius: 6,
                            background: "rgba(239,68,68,0.05)", borderLeft: "3px solid #ef4444",
                          }}>
                            "{r.text}"
                            <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 3 }}>
                              — {r.source}
                              {r.url && <a href={r.url} target="_blank" rel="noopener noreferrer"
                                style={{ marginLeft: 6, color: "var(--accent-cyan)" }}>link</a>}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    {cs.sample_positive?.length > 0 && (
                      <div>
                        <div style={{ fontSize: 12, color: "#10b981", fontWeight: 600, marginBottom: 6 }}>
                          Positive Reviews:
                        </div>
                        {cs.sample_positive.map((r, i) => (
                          <div key={i} style={{
                            fontSize: 12, color: "var(--text-secondary)",
                            padding: "8px 10px", marginBottom: 4, borderRadius: 6,
                            background: "rgba(16,185,129,0.05)", borderLeft: "3px solid #10b981",
                          }}>
                            "{r.text}"
                            <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 3 }}>
                              — {r.source}
                              {r.url && <a href={r.url} target="_blank" rel="noopener noreferrer"
                                style={{ marginLeft: 6, color: "var(--accent-cyan)" }}>link</a>}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    {(!cs.sample_negative?.length && !cs.sample_positive?.length) && (
                      <p style={{ fontSize: 12, color: "var(--text-muted)" }}>No detailed quotes available</p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}
