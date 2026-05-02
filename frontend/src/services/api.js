const API_BASE_URL = "http://localhost:8000";

export async function submitArtworkRequest(teamName, logoFile) {
  const formData = new FormData();
  formData.append("team_name", teamName);
  if (logoFile) {
    formData.append("logo", logoFile);
  }

  const response = await fetch(`${API_BASE_URL}/process-team`, {
    method: "POST",
    body: formData,
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "API request failed.");
  }
  return payload;
}
