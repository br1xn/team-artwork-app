import React from "react";
import { Search } from "lucide-react";

export function TeamInput({ teamName, onChange }) {
  return (
    <div className="instrument-card">
      <p className="eyebrow">Team Mapping</p>
      <label className="panel-title" htmlFor="team-name">Team name</label>
      <div className="input-shell">
        <Search size={18} />
        <input
          id="team-name"
          value={teamName}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Los Angeles Lakers"
          autoComplete="off"
        />
      </div>
      <p className="microcopy">If scraping is blocked or empty, fallback roster data keeps the pipeline moving.</p>
    </div>
  );
}
