import React from "react";

export function Loader() {
  return (
    <div className="loader-panel" role="status" aria-live="polite">
      <div className="spinner" />
      <div>
        <p className="eyebrow">Pipeline Active</p>
        <h2>Analyzing Logo...</h2>
        <p>Validating sources, scraping players, processing headshots, and preparing artwork fallbacks.</p>
      </div>
    </div>
  );
}
