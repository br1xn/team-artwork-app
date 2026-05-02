import React, { useState } from "react";

export function IntakeForm({ onSubmit, loading }) {
  const [teamName, setTeamName] = useState("");
  const [logoFile, setLogoFile] = useState(null);

  const handleSubmit = (event) => {
    event.preventDefault();
    onSubmit({ teamName, logoFile });
  };

  return (
    <form className="panel form-panel" onSubmit={handleSubmit}>
      <div className="field">
        <label htmlFor="team-name">Team name</label>
        <input
          id="team-name"
          value={teamName}
          onChange={(event) => setTeamName(event.target.value)}
          placeholder="Los Angeles Lakers"
          required
        />
      </div>
      <div className="field">
        <label htmlFor="logo-upload">Logo upload</label>
        <input
          id="logo-upload"
          type="file"
          accept="image/*"
          onChange={(event) => setLogoFile(event.target.files?.[0] ?? null)}
        />
      </div>
      <button className="primary-button" type="submit" disabled={loading}>
        {loading ? "Processing..." : "Run pipeline"}
      </button>
    </form>
  );
}
