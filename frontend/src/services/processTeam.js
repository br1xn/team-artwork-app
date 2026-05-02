const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export async function processTeam(data) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 90000);
  const teamName = data.teamName?.trim() || data.logoFile?.name?.replace(/\.[^.]+$/, "") || "";

  const formData = new FormData();
  formData.append("team_name", teamName);
  if (data.logoFile) {
    formData.append("logo", data.logoFile);
  }

  try {
    const response = await fetch(`${API_BASE_URL}/process-team`, {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || "Processing failed. Try another team name or logo.");
    }
    return normalizeResponse(payload);
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Processing timed out. The app can retry with fallback data.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function normalizeResponse(payload) {
  return {
    validation: payload.validation || null,
    players: Array.isArray(payload.players) ? payload.players : [],
    artwork: payload.artwork || null,
  };
}

export function assetUrl(path) {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${API_BASE_URL}${path}`;
}
