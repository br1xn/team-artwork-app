import React, { useState } from "react";

export function IntakeForm({ onSubmit, loading }) {
  const [logoFile, setLogoFile] = useState(null);

  const handleSubmit = (event) => {
    event.preventDefault();
    // Pass an empty string for teamName so the backend knows to trigger Gemini Vision
    onSubmit({ teamName: "", logoFile });
  };

  // Only disable the button if it's loading OR if the user hasn't uploaded a logo
  const isSubmitDisabled = loading || !logoFile;

  return (
    <form className="panel form-panel" onSubmit={handleSubmit}>
      <div className="field">
        <label htmlFor="logo-upload">Upload Team Logo</label>
        <input
          id="logo-upload"
          type="file"
          accept="image/*"
          onChange={(event) => setLogoFile(event.target.files?.[0] ?? null)}
        />
      </div>
      <button className="primary-button" type="submit" disabled={isSubmitDisabled}>
        {loading ? "Identifying Team..." : "Validate Team Identity"}
      </button>
    </form>
  );
}