export default function ScoreRing({ score, size = 180, strokeWidth = 10 }) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  const getColor = (s) => {
    if (s >= 70) return "var(--accent-green)";
    if (s >= 45) return "var(--accent-amber)";
    return "var(--accent-red)";
  };

  return (
    <div className="score-ring-container">
      <div className="score-ring" style={{ width: size, height: size }}>
        <svg width={size} height={size}>
          <circle
            className="score-ring-bg"
            cx={size / 2}
            cy={size / 2}
            r={radius}
            strokeWidth={strokeWidth}
          />
          <circle
            className="score-ring-fill"
            cx={size / 2}
            cy={size / 2}
            r={radius}
            strokeWidth={strokeWidth}
            stroke={getColor(score)}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
          />
        </svg>
        <div className="score-ring-text">
          <div className="score-ring-value" style={{ color: getColor(score) }}>
            {Math.round(score)}
          </div>
          <div className="score-ring-label">Market Alignment</div>
        </div>
      </div>
    </div>
  );
}
