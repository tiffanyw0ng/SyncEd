export default function NewsFeed({ data }) {
  if (!data) return <p style={{ color: "var(--text-muted)" }}>Loading news...</p>;

  const trendingTopics = data.trending_topics || [];
  const articles = data.articles || [];
  const topicArticles = data.topic_articles || {};
  const sourceCounts = data.source_counts || {};

  return (
    <>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 24 }}>
        <div className="card">
          <div className="card-header">
            <span className="card-title">Trending Tech Topics</span>
            <span className="card-subtitle">
              From {data.total_articles} articles across{" "}
              {data.sources?.length || 0} sources
            </span>
          </div>
          {trendingTopics.length > 0 ? (
            trendingTopics.map(([topic, count]) => {
              const maxCount = trendingTopics[0]?.[1] || 1;
              return (
                <div key={topic} className="trend-bar">
                  <span className="trend-label">{topic}</span>
                  <div className="trend-fill-container">
                    <div
                      className="trend-fill"
                      style={{
                        width: `${(count / maxCount) * 100}%`,
                        background: "linear-gradient(90deg, #06b6d4, #3b82f6)",
                      }}
                    >
                      {count}
                    </div>
                  </div>
                </div>
              );
            })
          ) : (
            <p style={{ color: "var(--text-muted)" }}>No trending topics detected</p>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">Data Sources</span>
            <span className="card-subtitle">Where we're scraping from</span>
          </div>
          <div style={{ display: "grid", gap: 12 }}>
            {[
              { name: "LinkedIn Jobs", key: "linkedin", desc: "Job listings scraped via Google search index", color: "#0a66c2", type: "jobs" },
              { name: "Glassdoor", key: "glassdoor", desc: "Job listings scraped via Google search index", color: "#0caa41", type: "jobs" },
              { name: "Greenhouse", key: "greenhouse", desc: "Startup/tech job boards via Google search", color: "#24a47f", type: "jobs" },
              { name: "RemoteOK", key: "remoteok", desc: "Remote job postings via public JSON API", color: "#8b5cf6", type: "jobs" },
              { name: "HN Hiring", key: "hackernews", desc: "Monthly 'Who is Hiring' threads via Algolia API", color: "#f59e0b", type: "jobs" },
              { name: "LinkedIn News", key: "LinkedIn News", desc: "Workforce reports & hiring trends via Google News", color: "#0a66c2", type: "news" },
              { name: "LinkedIn via Google News", key: "LinkedIn via Google News", desc: "LinkedIn content indexed by Google News", color: "#0a66c2", type: "news" },
              { name: "Google News", key: "Google News", desc: "Real-time news via RSS feed search (12 queries)", color: "#3b82f6", type: "news" },
              { name: "Hacker News", key: "Hacker News", desc: "Top tech stories from HN front page", color: "#f59e0b", type: "news" },
              { name: "TechCrunch", key: "TechCrunch", desc: "Tech industry news via RSS feed", color: "#10b981", type: "news" },
              { name: "Wired", key: "Wired", desc: "Science & tech news via RSS feed", color: "#1a1a2e", type: "news" },
              { name: "Ars Technica", key: "Ars Technica", desc: "Technology news & analysis via RSS", color: "#ff4e00", type: "news" },
              { name: "MIT Tech Review", key: "MIT Tech Review", desc: "Emerging technology research via RSS", color: "#a31d1d", type: "news" },
              { name: "VentureBeat", key: "VentureBeat", desc: "AI & enterprise tech news via RSS", color: "#e44d26", type: "news" },
              { name: "The Verge", key: "The Verge", desc: "Tech culture & product news via RSS/Atom", color: "#e1127a", type: "news" },
              { name: "IEEE Spectrum", key: "IEEE Spectrum", desc: "Engineering & applied science via RSS", color: "#006699", type: "news" },
              { name: "The Register", key: "The Register", desc: "UK tech news & analysis via Atom feed", color: "#d91f26", type: "news" },
            ].map((source) => {
              const count = sourceCounts[source.key] || 0;
              return (
              <div
                key={source.name}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: "10px 14px",
                  background: "var(--bg-primary)",
                  borderRadius: 8,
                  border: "1px solid var(--border)",
                }}
              >
                <div
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: "50%",
                    background: source.color,
                    flexShrink: 0,
                  }}
                />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>
                    {source.name}
                    <span style={{
                      marginLeft: 6, fontSize: 11, padding: "1px 6px",
                      borderRadius: 8, background: source.type === "jobs" ? "rgba(139,92,246,0.15)" : "rgba(59,130,246,0.15)",
                      color: source.type === "jobs" ? "#8b5cf6" : "#3b82f6",
                    }}>
                      {source.type}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                    {source.desc}
                  </div>
                </div>
                <span
                  style={{
                    fontSize: 11,
                    padding: "3px 8px",
                    borderRadius: 12,
                    background: count > 0 ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.1)",
                    color: count > 0 ? "var(--accent-green)" : "var(--text-muted)",
                    fontWeight: 600,
                    whiteSpace: "nowrap",
                  }}
                >
                  {count > 0 ? `${count} articles` : "READY"}
                </span>
              </div>
            );})}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">
            Latest Articles ({articles.length})
          </span>
          <span className="card-subtitle">Scraped from real RSS feeds & APIs</span>
        </div>
        <div style={{ display: "grid", gap: 12 }}>
          {articles.slice(0, 30).map((article, i) => (
            <a
              key={i}
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: "block",
                padding: "14px 16px",
                background: "var(--bg-primary)",
                borderRadius: 8,
                border: "1px solid var(--border)",
                textDecoration: "none",
                transition: "all 0.2s",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "var(--accent-blue)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "var(--border)";
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  gap: 16,
                }}
              >
                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      fontSize: 14,
                      fontWeight: 600,
                      color: "var(--text-primary)",
                      marginBottom: 4,
                    }}
                  >
                    {article.title}
                  </div>
                  {article.summary && (
                    <div
                      style={{
                        fontSize: 12,
                        color: "var(--text-muted)",
                        lineHeight: 1.5,
                      }}
                    >
                      {article.summary.slice(0, 150)}
                      {article.summary.length > 150 ? "..." : ""}
                    </div>
                  )}
                  {article.topics?.length > 0 && (
                    <div className="skill-tags" style={{ marginTop: 6 }}>
                      {article.topics.map((t) => (
                        <span key={t} className="skill-tag emerging">
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div
                  style={{
                    fontSize: 11,
                    color: "var(--text-muted)",
                    whiteSpace: "nowrap",
                    flexShrink: 0,
                  }}
                >
                  {article.source}
                </div>
              </div>
            </a>
          ))}
        </div>
      </div>
    </>
  );
}
