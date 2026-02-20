export default function CourseDetailPanel({ course, onClose }) {
  if (!course) return null;

  const getScoreColor = (s) => {
    if (s >= 70) return "var(--accent-green)";
    if (s >= 45) return "var(--accent-amber)";
    return "var(--accent-red)";
  };

  return (
    <>
      <div className="detail-panel-backdrop" onClick={onClose} />
      <div className="detail-panel open">
        <button className="detail-close" onClick={onClose}>
          ×
        </button>

        <h2 style={{ marginBottom: 4 }}>
          <span style={{ color: "var(--accent-cyan)" }}>
            {course.course_code}
          </span>{" "}
          {course.course_title}
        </h2>
        <div
          style={{
            fontSize: 48,
            fontWeight: 800,
            color: getScoreColor(course.alignment_score),
            margin: "16px 0",
          }}
        >
          {course.alignment_score}%
          <span
            style={{
              fontSize: 14,
              color: "var(--text-secondary)",
              marginLeft: 8,
            }}
          >
            alignment
          </span>
        </div>

        <div className="detail-section">
          <h4>Skills Covered by Course</h4>
          <div className="skill-tags">
            {course.covered_skills.length > 0 ? (
              course.covered_skills.map((s) => (
                <span key={s} className="skill-tag covered">
                  {s}
                </span>
              ))
            ) : (
              <span style={{ color: "var(--text-muted)", fontSize: 13 }}>
                No overlapping skills detected
              </span>
            )}
          </div>
        </div>

        <div className="detail-section">
          <h4>Missing from Market Demand</h4>
          <div className="skill-tags">
            {course.missing_skills.length > 0 ? (
              course.missing_skills.map((s) => (
                <span key={s} className="skill-tag missing">
                  {s}
                </span>
              ))
            ) : (
              <span style={{ color: "var(--text-muted)", fontSize: 13 }}>
                Fully aligned
              </span>
            )}
          </div>
        </div>

        {course.obsolete_topics?.length > 0 && (
          <div className="detail-section">
            <h4>Industry-Obsolete Topics</h4>
            {course.obsolete_topics.map((t, i) => (
              <div
                key={i}
                style={{
                  background: "rgba(239, 68, 68, 0.1)",
                  border: "1px solid rgba(239, 68, 68, 0.2)",
                  borderRadius: 8,
                  padding: "10px 14px",
                  marginBottom: 8,
                  fontSize: 13,
                  color: "var(--accent-red)",
                }}
              >
                {t}
              </div>
            ))}
          </div>
        )}

        <div className="detail-section">
          <h4>Recommended Additions</h4>
          <div className="skill-tags">
            {course.recommended_additions.length > 0 ? (
              course.recommended_additions.map((s) => (
                <span key={s} className="skill-tag emerging">
                  {s}
                </span>
              ))
            ) : (
              <span style={{ color: "var(--text-muted)", fontSize: 13 }}>
                No urgent additions
              </span>
            )}
          </div>
        </div>

        <div className="detail-section">
          <h4>Most Relevant Job Titles</h4>
          {course.most_relevant_jobs.map((j, i) => (
            <div
              key={i}
              style={{
                padding: "8px 0",
                borderBottom: "1px solid var(--border)",
                fontSize: 14,
                color: "var(--text-secondary)",
              }}
            >
              {j}
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
