import { useState } from "react";

const SEVERITY_COLORS = {
  critical: { bg: "rgba(239, 68, 68, 0.12)", border: "rgba(239, 68, 68, 0.3)", text: "#ef4444" },
  high: { bg: "rgba(245, 158, 11, 0.12)", border: "rgba(245, 158, 11, 0.3)", text: "#f59e0b" },
  moderate: { bg: "rgba(59, 130, 246, 0.12)", border: "rgba(59, 130, 246, 0.3)", text: "#3b82f6" },
};

const GRADE_COLORS = {
  A: "#10b981", B: "#06b6d4", C: "#f59e0b", D: "#f97316", F: "#ef4444",
};

export default function CurriculumAnalysis({ data, recsData, majorName }) {
  const [expandedCourse, setExpandedCourse] = useState(null);

  if (!data || data.error) {
    return <p style={{ color: "var(--text-muted)" }}>Loading curriculum analysis...</p>;
  }

  const gradeColor = GRADE_COLORS[data.overall_grade] || "#94a3b8";

  return (
    <>
      {/* Summary Card */}
      <div className="card" style={{ marginBottom: 24, borderLeft: `4px solid ${gradeColor}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          <div style={{
            width: 80, height: 80, borderRadius: 16, display: "flex",
            alignItems: "center", justifyContent: "center",
            background: `${gradeColor}22`, fontSize: 40, fontWeight: 800,
            color: gradeColor,
          }}>
            {data.overall_grade}
          </div>
          <div style={{ flex: 1 }}>
            <h2 style={{ margin: 0, fontSize: 20 }}>
              {majorName} — Curriculum Report Card
            </h2>
            <p style={{ margin: "6px 0 0", color: "var(--text-secondary)", fontSize: 14 }}>
              {data.summary}
            </p>
            <div style={{ display: "flex", gap: 20, marginTop: 12, fontSize: 13 }}>
              <span>
                <strong style={{ color: gradeColor }}>{data.coverage_score}%</strong>{" "}
                market coverage
              </span>
              <span>
                <strong>{data.total_skills_covered}</strong> / {data.total_skills_demanded} demanded skills taught
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Category Coverage + Strengths/Weaknesses Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 24 }}>

        {/* Category Coverage */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Skill Category Coverage</span>
            <span className="card-subtitle">How well each area is covered vs. market demand</span>
          </div>
          {data.category_coverage && Object.entries(data.category_coverage)
            .sort((a, b) => b[1].market_demand - a[1].market_demand)
            .map(([cat, info]) => {
              const coverageColor =
                info.coverage_pct >= 60 ? "#10b981" :
                info.coverage_pct >= 30 ? "#f59e0b" : "#ef4444";
              return (
                <div key={cat} style={{ marginBottom: 14 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, textTransform: "capitalize" }}>
                      {cat.replace(/_/g, " ")}
                    </span>
                    <span style={{ color: "var(--text-muted)" }}>
                      {info.coverage_pct}% covered · {info.market_demand}% demand
                    </span>
                  </div>
                  <div style={{
                    height: 8, borderRadius: 4, background: "var(--bg-primary)",
                    position: "relative", overflow: "hidden",
                  }}>
                    <div style={{
                      height: "100%", borderRadius: 4,
                      background: `linear-gradient(90deg, ${coverageColor}88, ${coverageColor})`,
                      width: `${info.coverage_pct}%`, transition: "width 0.5s",
                    }} />
                  </div>
                  {info.missing.length > 0 && (
                    <div style={{ marginTop: 4, fontSize: 11, color: "var(--text-muted)" }}>
                      Missing: {info.missing.slice(0, 4).join(", ")}
                      {info.missing.length > 4 && ` +${info.missing.length - 4} more`}
                    </div>
                  )}
                </div>
              );
            })}
        </div>

        {/* Strengths */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Curriculum Strengths</span>
            <span className="card-subtitle">High-demand skills your curriculum already covers</span>
          </div>
          {data.strengths?.length > 0 ? data.strengths.map((s) => (
            <div key={s.skill} style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "8px 12px", marginBottom: 6, borderRadius: 8,
              background: "rgba(16, 185, 129, 0.08)", border: "1px solid rgba(16, 185, 129, 0.2)",
            }}>
              <div>
                <span style={{ fontWeight: 600, fontSize: 14 }}>{s.skill}</span>
                <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: 8 }}>
                  {s.covered_by.join(", ")}
                </span>
              </div>
              <span style={{
                fontSize: 12, fontWeight: 700, color: "#10b981",
                background: "rgba(16, 185, 129, 0.15)", padding: "2px 8px", borderRadius: 8,
              }}>
                {s.market_demand}% demand
              </span>
            </div>
          )) : <p style={{ color: "var(--text-muted)" }}>No strong matches found</p>}
        </div>
      </div>

      {/* Weaknesses */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <span className="card-title">Critical Curriculum Weaknesses</span>
          <span className="card-subtitle">
            High-demand skills missing from the curriculum — sorted by market demand
          </span>
        </div>
        <div style={{ display: "grid", gap: 10 }}>
          {data.weaknesses?.map((w) => {
            const sev = SEVERITY_COLORS[w.severity] || SEVERITY_COLORS.moderate;
            return (
              <div key={w.skill} style={{
                padding: "12px 16px", borderRadius: 10,
                background: sev.bg, border: `1px solid ${sev.border}`,
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <span style={{ fontWeight: 700, fontSize: 15, color: sev.text }}>
                      {w.skill}
                    </span>
                    <span style={{
                      marginLeft: 8, fontSize: 11, padding: "2px 8px", borderRadius: 8,
                      background: `${sev.text}22`, color: sev.text, fontWeight: 600,
                      textTransform: "uppercase",
                    }}>
                      {w.severity}
                    </span>
                  </div>
                  <span style={{ fontSize: 13, fontWeight: 700, color: sev.text }}>
                    {w.market_demand}% demand
                  </span>
                </div>
                <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "6px 0 0" }}>
                  {w.recommendation}
                </p>
                {w.could_be_added_to?.length > 0 && (
                  <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
                    Could integrate into: <strong>{w.could_be_added_to.join(", ")}</strong>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Emerging 2026 Gaps */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <span className="card-title">Emerging 2026 Technology Gaps</span>
          <span className="card-subtitle">Cutting-edge technologies not yet in the curriculum</span>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {data.emerging_gaps?.map((g) => (
            <div key={g.skill} style={{
              padding: "8px 14px", borderRadius: 10, fontSize: 13,
              background: g.status === "not_taught"
                ? "rgba(139, 92, 246, 0.12)" : "rgba(100, 116, 139, 0.1)",
              border: `1px solid ${g.status === "not_taught"
                ? "rgba(139, 92, 246, 0.3)" : "rgba(100, 116, 139, 0.2)"}`,
              color: g.status === "not_taught" ? "#8b5cf6" : "var(--text-muted)",
            }}>
              <span style={{ fontWeight: 600 }}>{g.skill}</span>
              <span style={{ marginLeft: 6, opacity: 0.7, fontSize: 11 }}>
                {g.market_demand}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Per-Course Weakness Breakdown */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <span className="card-title">Per-Course Improvement Recommendations</span>
          <span className="card-subtitle">
            Specific suggestions for each course to better align with market needs
          </span>
        </div>
        <div style={{ display: "grid", gap: 8 }}>
          {data.course_weaknesses?.map((cw) => (
            <div
              key={cw.course_code}
              style={{
                padding: "12px 16px", borderRadius: 10,
                background: "var(--bg-primary)", border: "1px solid var(--border)",
                cursor: "pointer",
              }}
              onClick={() => setExpandedCourse(
                expandedCourse === cw.course_code ? null : cw.course_code
              )}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <span style={{ fontWeight: 700, color: "var(--accent-cyan)", fontSize: 14 }}>
                    {cw.course_code}
                  </span>
                  <span style={{ marginLeft: 8, fontSize: 14 }}>{cw.course_title}</span>
                </div>
                <span style={{
                  fontSize: 12, color: "var(--accent-red)", fontWeight: 600,
                  background: "rgba(239, 68, 68, 0.1)", padding: "2px 8px", borderRadius: 8,
                }}>
                  {cw.missing_high_demand.length} gaps
                </span>
              </div>

              {expandedCourse === cw.course_code && (
                <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
                  <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 10 }}>
                    {cw.improvement_suggestion}
                  </div>
                  <div style={{ fontSize: 12, marginBottom: 6, color: "var(--text-muted)", fontWeight: 600 }}>
                    Currently teaches:
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 10 }}>
                    {cw.current_topics.map((t) => (
                      <span key={t} className="skill-tag covered" style={{ fontSize: 11, padding: "2px 8px" }}>
                        {t}
                      </span>
                    ))}
                  </div>
                  <div style={{ fontSize: 12, marginBottom: 6, color: "var(--text-muted)", fontWeight: 600 }}>
                    Should also teach:
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {cw.missing_high_demand.map((m) => (
                      <span key={m.skill} className="skill-tag missing" style={{ fontSize: 11, padding: "2px 8px" }}>
                        {m.skill} ({m.demand}%)
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* New Course Recommendations */}
      {recsData?.recommendations?.length > 0 && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">Suggested New Courses</span>
            <span className="card-subtitle">
              Based on gaps between curriculum and 2026 market demands
            </span>
          </div>
          <div style={{ display: "grid", gap: 12 }}>
            {recsData.recommendations.map((rec, i) => (
              <div key={i} style={{
                padding: "16px 20px", borderRadius: 10,
                background: "var(--bg-primary)", border: "1px solid var(--border)",
                borderLeft: "4px solid var(--accent-purple)",
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <span style={{ fontWeight: 700, color: "var(--accent-cyan)", fontSize: 14 }}>
                      {rec.suggested_code}
                    </span>
                    <span style={{ marginLeft: 8, fontSize: 15, fontWeight: 600 }}>
                      {rec.suggested_title}
                    </span>
                  </div>
                  <span style={{
                    fontSize: 12, fontWeight: 700, color: "var(--accent-purple)",
                    background: "rgba(139, 92, 246, 0.15)", padding: "3px 10px", borderRadius: 8,
                    whiteSpace: "nowrap",
                  }}>
                    Demand: {rec.market_demand_score}
                  </span>
                </div>
                <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "8px 0", lineHeight: 1.6 }}>
                  {rec.justification}
                </p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {rec.target_skills.map((s) => (
                    <span key={s} className="skill-tag emerging" style={{ fontSize: 11, padding: "2px 8px" }}>
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
