import React from "react";

export function TeamInput() {
  return (
    <div className="instrument-card">
      <p className="eyebrow">Team Mapping</p>
      <h2 className="panel-title">AI Team Identification Active</h2>
      <p className="microcopy" style={{ marginTop: '1rem' }}>
        Manual team entry is disabled. Drop a logo in the upload zone, and our Gemini Vision model will automatically identify the franchise for you.
      </p>
    </div>
  );
}