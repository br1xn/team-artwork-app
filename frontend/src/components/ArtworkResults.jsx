import React from "react";

export function ArtworkResults({ data, loading }) {
  if (loading) {
    return <section className="panel">Working through validation, scraping, and artwork generation...</section>;
  }

  if (!data) {
    return <section className="panel muted">Results will appear here after you run the pipeline.</section>;
  }

  return (
    <section className="results-grid">
      <article className="panel">
        <h2>Validation</h2>
        <p><strong>Team:</strong> {data.validation?.team || "No logo submitted"}</p>
        <p><strong>Status:</strong> {data.validation?.status || "skipped"}</p>
        <p><strong>Confidence:</strong> {data.validation?.confidence ?? "n/a"}</p>
        <p><strong>Visual:</strong> {data.validation?.visual_match ?? "n/a"}</p>
        <p><strong>Color:</strong> {data.validation?.color_match ?? "n/a"}</p>
        {data.validation?.matched_sources?.[0] ? (
          <a href={data.validation.matched_sources[0]} target="_blank" rel="noreferrer">
            Matched source
          </a>
        ) : null}
      </article>

      <article className="panel">
        <h2>Artwork</h2>
        {data.artwork?.thumbnail ? <img className="art-preview" src={`http://localhost:8000${data.artwork.thumbnail}`} alt="Generated thumbnail" /> : null}
        <ul className="simple-list">
          {(data.artwork?.variants || []).map((variant) => (
            <li key={variant}>
              <a href={`http://localhost:8000${variant}`} target="_blank" rel="noreferrer">
                Artwork slice
              </a>
            </li>
          ))}
        </ul>
      </article>

      <article className="panel full-width">
        <h2>Players</h2>
        <div className="player-grid">
          {data.players.map((player) => (
            <div className="player-card" key={player.name}>
              <div>
                <h3>{player.name}</h3>
                <p>{player.role || "Unknown role"}</p>
              </div>
              {player.processed_image_path ? (
                <img className="headshot" src={`http://localhost:8000${player.processed_image_path}`} alt={player.name} />
              ) : null}
            </div>
          ))}
        </div>
      </article>
    </section>
  );
}
