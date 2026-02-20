import { useState } from "react";
import CourseDetailPanel from "../components/CourseDetailPanel";

export default function CoursesView({ data }) {
  const [selected, setSelected] = useState(null);
  const [sortBy, setSortBy] = useState("score-asc");

  if (!data?.courses) return <p>No course data available.</p>;

  const sorted = [...data.courses].sort((a, b) => {
    if (sortBy === "score-asc") return a.alignment_score - b.alignment_score;
    if (sortBy === "score-desc") return b.alignment_score - a.alignment_score;
    if (sortBy === "code") return a.course_code.localeCompare(b.course_code);
    return 0;
  });

  const getAlignmentClass = (score) => {
    if (score >= 70) return "alignment-high";
    if (score >= 45) return "alignment-medium";
    return "alignment-low";
  };

  return (
    <>
      <div className="card" style={{ marginBottom: 20 }}>
        <div
          style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}
        >
          <div>
            <span className="card-title">
              All EECS Courses ({sorted.length})
            </span>
            <p className="card-subtitle" style={{ marginTop: 4 }}>
              Click any course to see detailed gap analysis
            </p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {[
              { id: "score-asc", label: "Worst First" },
              { id: "score-desc", label: "Best First" },
              { id: "code", label: "By Code" },
            ].map((opt) => (
              <button
                key={opt.id}
                className={`nav-tab ${sortBy === opt.id ? "active" : ""}`}
                style={{ padding: "6px 14px", fontSize: 12 }}
                onClick={() => setSortBy(opt.id)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="courses-grid">
        {sorted.map((course) => (
          <div
            key={course.course_code}
            className="course-row"
            onClick={() => setSelected(course)}
          >
            <span className="course-code">{course.course_code}</span>
            <div>
              <span className="course-title">{course.course_title}</span>
              <div className="skill-tags" style={{ marginTop: 8 }}>
                {course.missing_skills.slice(0, 4).map((s) => (
                  <span key={s} className="skill-tag missing">
                    {s}
                  </span>
                ))}
                {course.missing_skills.length > 4 && (
                  <span className="skill-tag missing">
                    +{course.missing_skills.length - 4} more
                  </span>
                )}
              </div>
            </div>
            <span
              className={`alignment-badge ${getAlignmentClass(course.alignment_score)}`}
            >
              {course.alignment_score}%
            </span>
            <div className="score-bar">
              <div
                className="score-bar-fill"
                style={{
                  width: `${course.alignment_score}%`,
                  background:
                    course.alignment_score >= 70
                      ? "var(--accent-green)"
                      : course.alignment_score >= 45
                        ? "var(--accent-amber)"
                        : "var(--accent-red)",
                }}
              />
            </div>
          </div>
        ))}
      </div>

      {selected && (
        <CourseDetailPanel course={selected} onClose={() => setSelected(null)} />
      )}
    </>
  );
}
