import React from "react";
import { AlertTriangle, BadgeCheck } from "lucide-react";

export function ValidationResult({ validation }) {
  if (!validation) {
    return null;
  }

  const confidence = Math.round((validation.confidence || 0) * 100);
  const isStrong = validation.confidence > 0.85;

  return (
    <section className="instrument-card result-card">
      <div className="result-heading">
        <div>
          <p className="eyebrow">Validation</p>
          <h2 className="panel-title">{validation.team}</h2>
        </div>
        {isStrong ? <BadgeCheck className="text-emerald-500" /> : <AlertTriangle className="text-clay" />}
      </div>
      <div className="confidence-row">
        <span>{confidence}%</span>
        <span>{validation.status}</span>
      </div>
      <div className="confidence-track">
        <span className={isStrong ? "confidence-fill strong" : "confidence-fill weak"} style={{ width: `${confidence}%` }} />
      </div>
      <dl className="metrics-grid">
        <div><dt>Visual</dt><dd>{Math.round((validation.visual_match || 0) * 100)}%</dd></div>
        <div><dt>Color</dt><dd>{Math.round((validation.color_match || 0) * 100)}%</dd></div>
        <div><dt>Sources Checked</dt><dd>{validation.sources_checked?.length || 0}</dd></div>
      </dl>

      {/* Updated to show the Top 3 Matched Sources instead of everything checked */}
      {validation.matched_sources?.length ? (
        <div className="source-list" style={{ marginTop: '1rem' }}>
          <p className="text-xs text-neutral-400 mb-2 font-medium">TOP OFFICIAL MATCHES</p>
          {validation.matched_sources.map((source, index) => {
            // A quick formatting trick to make the URLs look nicer in the UI
            const cleanUrl = new URL(source).hostname.replace('www.', '');
            return (
              <a href={source} target="_blank" rel="noreferrer" key={index} style={{ display: 'block', marginBottom: '4px', color: '#0EA5E9' }}>
                Match {index + 1}: {cleanUrl}
              </a>
            );
          })}
        </div>
      ) : null}

      {validation.error ? <p className="error-note">{validation.error}</p> : null}
    </section>
  );
}