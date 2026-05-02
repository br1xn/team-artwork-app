import React, { useEffect, useRef, useState } from "react";
import { ArrowRight, RefreshCcw, ShieldCheck, Sparkles } from "lucide-react";

import { ArtworkGallery } from "../components/ArtworkGallery";
import { Loader } from "../components/Loader";
import { PlayerGrid } from "../components/PlayerGrid";
import { TeamInput } from "../components/TeamInput";
import { UploadLogo } from "../components/UploadLogo";
import { ValidationResult } from "../components/ValidationResult";
import { processTeam } from "../services/processTeam";

export function Home() {
  const rootRef = useRef(null);
  const [teamName, setTeamName] = useState("Los Angeles Lakers");
  const [logoFile, setLogoFile] = useState(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [visibleStep, setVisibleStep] = useState(0);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return undefined;
    root.classList.add("is-ready");
    return () => root.classList.remove("is-ready");
  }, []);

  useEffect(() => {
    if (status !== "success") return undefined;
    const cards = rootRef.current?.querySelectorAll(".result-card");
    cards?.forEach((card, index) => {
      card.animate(
        [
          { opacity: 0, transform: "translateY(28px)" },
          { opacity: 1, transform: "translateY(0)" },
        ],
        {
          duration: 650,
          delay: index * 120,
          easing: "cubic-bezier(0.25, 0.46, 0.45, 0.94)",
          fill: "both",
        },
      );
    });
    return undefined;
  }, [status, visibleStep]);

  async function handleProcess(event) {
    event.preventDefault();
    setError("");
    setResult(null);
    setVisibleStep(0);
    setStatus("loading");

    try {
      const payload = await processTeam({ teamName, logoFile });
      setResult(payload);
      setStatus("success");
      setVisibleStep(1);
      window.setTimeout(() => setVisibleStep(2), 450);
      window.setTimeout(() => setVisibleStep(3), 900);
    } catch (err) {
      setStatus("error");
      setError(err.message || "The pipeline failed, but retry can use backend fallbacks.");
    }
  }

  const canSubmit = Boolean(teamName.trim() || logoFile);

  return (
    <main ref={rootRef} className="app-shell">
      <div className="noise-layer" />
      <section className="workspace-shell">
        <div className="intro-copy">
          <p className="system-label"><ShieldCheck size={16} /> Team Artwork Engine</p>
          <h2>Generate team assets</h2>
          <p>Streamlined pipeline for logos, rosters, and AI artwork.</p>
        </div>

        <form className="control-grid" onSubmit={handleProcess}>
          <TeamInput teamName={teamName} onChange={setTeamName} />
          <UploadLogo logoFile={logoFile} onChange={setLogoFile} />
          <div className="action-panel">
            <Sparkles size={24} />
            <div>
              <p className="eyebrow">Execution</p>
              <h2 className="panel-title">Process assets</h2>
              <p className="microcopy">Wrong formats, broken image links, blocked scraping, and AI timeouts all fall back to usable output.</p>
            </div>
            <button className="magnetic-button" type="submit" disabled={!canSubmit || status === "loading"}>
              <span />
              <strong>{status === "loading" ? "Processing" : "Process"}</strong>
              <ArrowRight size={18} />
            </button>
          </div>
        </form>

        {status === "loading" ? <Loader /> : null}

        {status === "error" ? (
          <section className="error-panel">
            <div>
              <p className="eyebrow">Backend Error</p>
              <h2>{error}</h2>
            </div>
            <button className="retry-button" type="button" onClick={handleProcess}>
              <RefreshCcw size={17} /> Retry
            </button>
          </section>
        ) : null}

        {status === "success" && result ? (
          <section className="results-stack">
            {visibleStep >= 1 ? <ValidationResult validation={result.validation} /> : null}
            {visibleStep >= 2 ? <PlayerGrid players={result.players} /> : null}
            {visibleStep >= 3 ? <ArtworkGallery artwork={result.artwork} /> : null}
          </section>
        ) : null}
      </section>
    </main>
  );
}
