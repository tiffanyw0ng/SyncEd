import ScoreRing from "../components/ScoreRing";
import CourseDetailPanel from "../components/CourseDetailPanel";
import { useState } from "react";

export default function Dashboard({ data, majorName }) {
  const [selected, setSelected] = useState(null);

  if (!data) return <p>No data available.</p>;

  const getAlignmentClass = (score) => {
    if (score >= 70) return "alignment-high";
    if (score >= 45) return "alignment-medium";
    return "alignment-low";
  };

  return (
    <>
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-value">{data.overall_alignment_score}%</div>
          <div className="stat-label">Overall Alignment</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{data.total_courses_analyzed}</div>
          <div className="stat-label">Courses Analyzed</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{data.total_job_postings}</div>
          <div className="stat-label">Job Postings Scraped</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {data.new_course_recommendations?.length || 0}
          </div>
          <div className="stat-label">New Courses Suggested</div>
        </div>
      </div>

      {data.scraping_sources && Object.keys(data.scraping_sources).length > 0 && (
        <div className="sources-bar">
          <span className="sources-label">Live data from:</span>
          {Object.entries(data.scraping_sources).map(([src, count]) => (
            <span key={src} className="source-badge">
              {src} ({count})
            </span>
          ))}
        </div>
      )}

      <div className="dashboard-grid">
        <div className="card">
          <div className="card-header">
            <span className="card-title">Alignment Score</span>
          </div>
          <ScoreRing score={data.overall_alignment_score} />
          <p
            style={{
              textAlign: "center",
              marginTop: 16,
              fontSize: 13,
              color: "var(--text-secondary)",
            }}
          >
            How well {majorName}
            <br />
            matches 2026 job market
          </p>
        </div>

        <div>
          <div className="card" style={{ marginBottom: 24 }}>
            <div className="card-header">
              <span className="card-title">Biggest Curriculum Gaps</span>
              <span className="card-subtitle">Lowest alignment scores</span>
            </div>
            <div className="courses-grid">
              {data.top_gaps?.map((gap) => (
                <div
                  key={gap.course_code}
                  className="course-row"
                  onClick={() => setSelected(gap)}
                >
                  <span className="course-code">{gap.course_code}</span>
                  <span className="course-title">{gap.course_title}</span>
                  <span
                    className={`alignment-badge ${getAlignmentClass(gap.alignment_score)}`}
                  >
                    {gap.alignment_score}%
                  </span>
                  <div className="score-bar">
                    <div
                      className="score-bar-fill"
                      style={{
                        width: `${gap.alignment_score}%`,
                        background:
                          gap.alignment_score >= 70
                            ? "var(--accent-green)"
                            : gap.alignment_score >= 45
                              ? "var(--accent-amber)"
                              : "var(--accent-red)",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">Best Aligned Courses</span>
              <span className="card-subtitle">Highest alignment scores</span>
            </div>
            <div className="courses-grid">
              {data.top_aligned?.map((gap) => (
                <div
                  key={gap.course_code}
                  className="course-row"
                  onClick={() => setSelected(gap)}
                >
                  <span className="course-code">{gap.course_code}</span>
                  <span className="course-title">{gap.course_title}</span>
                  <span
                    className={`alignment-badge ${getAlignmentClass(gap.alignment_score)}`}
                  >
                    {gap.alignment_score}%
                  </span>
                  <div className="score-bar">
                    <div
                      className="score-bar-fill"
                      style={{
                        width: `${gap.alignment_score}%`,
                        background:
                          gap.alignment_score >= 70
                            ? "var(--accent-green)"
                            : gap.alignment_score >= 45
                              ? "var(--accent-amber)"
                              : "var(--accent-red)",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {selected && (
        <CourseDetailPanel course={selected} onClose={() => setSelected(null)} />
      )}
    </>
  );
}
