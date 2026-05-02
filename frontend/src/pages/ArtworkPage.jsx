import React, { useState } from "react";

import { ArtworkResults } from "../components/ArtworkResults";
import { IntakeForm } from "../components/IntakeForm";
import { submitArtworkRequest } from "../services/api";

export function ArtworkPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async ({ teamName, logoFile }) => {
    setLoading(true);
    setError("");
    try {
      const response = await submitArtworkRequest(teamName, logoFile);
      setData(response);
    } catch (err) {
      setError(err.message || "Something went wrong.");
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="app-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">Team Asset Pipeline</p>
          <h1>Validate logos, scrape rosters, and generate fallback artwork.</h1>
          <p className="lede">
            Submit a team name with an optional logo upload and get structured validation,
            player data, image fallbacks, and artwork outputs in one pass.
          </p>
        </div>
      </section>
      <section className="workspace">
        <IntakeForm onSubmit={handleSubmit} loading={loading} />
        {error ? <div className="error-banner">{error}</div> : null}
        <ArtworkResults data={data} loading={loading} />
      </section>
    </main>
  );
}
