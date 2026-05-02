import React from "react";
import { AlertTriangle, BadgeCheck } from "lucide-react";

export function ValidationResult({ validation }) {
  if (!validation) {
    return (
      <section className="instrument-card result-card">
        <p className="eyebrow">Validation</p>
        <h2 className="panel-title">Team-only mode</h2>
        <p className="microcopy">No logo was uploaded, so online visual matching was skipped.</p>
      </section>
    );
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
        <div><dt>Sources</dt><dd>{validation.matched_sources?.length || 0}</dd></div>
      </dl>
      <div className="transparency-panel" style={{ marginTop: '1rem', padding: '0.75rem', background: 'rgba(255, 255, 255, 0.05)', borderRadius: '6px', fontSize: '0.85rem' }}>
        {validation.validation_evidence && (
          <p style={{ marginBottom: '0.5rem', lineHeight: '1.4', color: '#E2E8F0' }}>
            {validation.validation_evidence}
          </p>
        )}
        <p><strong>Model:</strong> {validation.validation_model}</p>
        <p><strong>Provider:</strong> {validation.validation_provider}</p>
        <p><strong>Formula:</strong> {validation.scoring_formula}</p>
        <p><strong>Checked:</strong> {validation.sources_checked?.length || 0} source candidates</p>
      </div>
      {validation.sources_checked?.length ? (
        <div className="source-list">
          {validation.sources_checked.slice(0, 5).map((source) => (
            <a href={source} target="_blank" rel="noreferrer" key={source}>{source}</a>
          ))}
        </div>
      ) : null}
      {validation.error ? <p className="error-note">{validation.error}</p> : null}
    </section>
  );
}
