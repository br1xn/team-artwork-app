import React, { useState, useEffect, useRef } from "react";
import { ShieldCheck, Search, Image as ImageIcon, Sparkles, AlertCircle, Download, Upload } from "lucide-react";
import { ValidationResult } from "../components/ValidationResult";
import { ArtworkGallery } from "../components/ArtworkGallery";

const API_BASE = "http://127.0.0.1:8000/api";

export function Home() {
  const [activeTab, setActiveTab] = useState("logo");

  // LOGO VALIDATION STATE
  const [logoFile, setLogoFile] = useState(null);
  const [logoPreview, setLogoPreview] = useState("");
  const [valStatus, setValStatus] = useState("idle");
  const [valError, setValError] = useState("");
  const [validationData, setValidationData] = useState(null);

  // PLAYER HEADSHOTS STATE
  const [playerName, setPlayerName] = useState("");
  const [indSearchStatus, setIndSearchStatus] = useState("idle");
  const [individualPlayer, setIndividualPlayer] = useState(null);

  const [rosterStatus, setRosterStatus] = useState("idle");
  const [rosterPlayers, setRosterPlayers] = useState([]);
  const fileInputRef = useRef(null);

  // BACKGROUND GENERATOR STATE
  const [artStatus, setArtStatus] = useState("idle");
  const [artworkData, setArtworkData] = useState(null);

  useEffect(() => {
    if (logoFile) {
      const url = URL.createObjectURL(logoFile);
      setLogoPreview(url);
      return () => URL.revokeObjectURL(url);
    } else {
      setLogoPreview("");
    }
  }, [logoFile]);

  // 1. LOGO VALIDATION SUBMIT
  async function handleValidate(e) {
    e.preventDefault();
    if (!logoFile) {
      setValError("Please upload a logo to identify.");
      return;
    }
    setValStatus("loading");
    setValError("");
    setValidationData(null);
    setArtworkData(null);

    const formData = new FormData();
    formData.append("logo", logoFile);

    try {
      const res = await fetch(`${API_BASE}/validate-logo`, { method: "POST", body: formData });
      if (!res.ok) {
        const data = await res.json();
        const errorMessage = Array.isArray(data.detail) ? data.detail[0].msg : data.detail;
        throw new Error(errorMessage || "Validation failed.");
      }
      const data = await res.json();
      setValidationData(data);
      setValStatus("success");
    } catch (err) {
      setValStatus("error");
      setValError(err.message);
    }
  }

  // 2. INDIVIDUAL PLAYER SEARCH
  async function handlePlayerSearch(e) {
    e.preventDefault();
    if (!playerName.trim()) return;
    setIndSearchStatus("loading");
    setIndividualPlayer(null);
    try {
      const res = await fetch(`${API_BASE}/players/search?name=${encodeURIComponent(playerName)}`);
      if (!res.ok) throw new Error("Player not found");
      const data = await res.json();
      setIndividualPlayer(data.player);
      setIndSearchStatus("success");
    } catch (err) {
      setIndSearchStatus("error");
    }
  }

  // 3a. TEAM ROSTER SEARCH (Auto-Scrape)
  async function handleTeamRosterSearch() {
    const targetTeam = validationData ? validationData.team : "";
    if (!targetTeam) return;
    setRosterStatus("loading");
    setRosterPlayers([]);
    try {
      const res = await fetch(`${API_BASE}/players?team_name=${encodeURIComponent(targetTeam)}`);
      if (!res.ok) throw new Error("Could not fetch roster");
      const data = await res.json();
      setRosterPlayers(data.players || []);
      setRosterStatus("success");
    } catch (err) {
      setRosterStatus("error");
    }
  }

  // 3b. TEAM ROSTER SEARCH (CSV Upload)
  async function handleCsvUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    setRosterStatus("loading");
    setRosterPlayers([]);

    try {
      const text = await file.text();
      // Simple parser: split by newline, grab first column, ignore empty rows
      const rows = text.split('\n').map(r => r.trim()).filter(Boolean);
      let names = rows.map(r => r.split(',')[0].replace(/["']/g, '').trim());

      // Skip header if the first row says 'name' or 'player'
      if (names.length > 0 && (names[0].toLowerCase().includes('name') || names[0].toLowerCase().includes('player'))) {
        names = names.slice(1);
      }

      const fetchedPlayers = [];
      // Fetch sequentially to prevent overwhelming the server/API
      for (const name of names) {
        if (!name) continue;
        try {
          const res = await fetch(`${API_BASE}/players/search?name=${encodeURIComponent(name)}`);
          if (res.ok) {
            const data = await res.json();
            if (data.player) fetchedPlayers.push(data.player);
          }
        } catch (err) {
          console.error("Failed to fetch data for:", name);
        }
      }
      setRosterPlayers(fetchedPlayers);
      setRosterStatus("success");
    } catch (error) {
      console.error("CSV Parse Error:", error);
      setRosterStatus("error");
    }
    // Reset file input so the same file can be uploaded again if needed
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  // EXPORT TEAM DATA
  function exportTeamData() {
    if (rosterPlayers.length === 0) return;
    const csvContent = "data:text/csv;charset=utf-8,"
      + "Name,Role,Image_URL\n"
      + rosterPlayers.map(e => `"${e.name}","${e.role || 'N/A'}","${e.image_url || ''}"`).join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    const targetTeam = validationData ? validationData.team : "Team";
    link.setAttribute("download", `${targetTeam.replace(/\s+/g, '_')}_Roster.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  // 4. GENERATE BACKGROUND
  async function handleGenerateBackground() {
    if (!validationData || !logoFile) return;
    setArtStatus("loading");
    const formData = new FormData();
    formData.append("team_name", validationData.team);

    // Pass the actual file object, NOT just the string name
    formData.append("logo", logoFile);

    // Explicitly tell the backend which filename we are dealing with
    if (validationData.uploaded_filename) {
      formData.append("filename", validationData.uploaded_filename);
    }

    try {
      const res = await fetch(`${API_BASE}/artwork`, { method: "POST", body: formData });
      if (!res.ok) throw new Error("Failed to generate background");
      const data = await res.json();
      setArtworkData(data.artwork);
      setArtStatus("success");
      setActiveTab("generator");
    } catch (err) {
      setArtStatus("error");
    }
  }

  // OVERRIDE LOGO
  async function handleOverrideLogo(sourceUrl) {
    try {
      const res = await fetch(sourceUrl);
      const blob = await res.blob();
      const file = new File([blob], "trusted-logo.png", { type: blob.type });
      setLogoFile(file);
      setValidationData(null);
      setValStatus("idle");
    } catch (e) {
      alert("Failed to fetch trusted logo.");
    }
  }

  return (
    <main className="min-h-screen bg-neutral-950 text-neutral-100 font-sans selection:bg-blue-500/30">
      <div className="max-w-6xl mx-auto px-6 py-12">

        {/* Header */}
        <header className="mb-12 border-b border-white/10 pb-8">
          <div className="flex items-center gap-3 mb-2">
            <Sparkles className="text-blue-400" size={24} />
            <h1 className="text-3xl font-bold tracking-tight">Team Artwork Engine</h1>
          </div>
          <p className="text-neutral-400">Professional dynamic pipeline for logo validation, roster extraction, and Figma-style composition.</p>
        </header>

        {/* Tab Navigation */}
        <div className="flex space-x-2 bg-neutral-900 p-1 rounded-lg w-fit mb-8 border border-white/5">
          <button
            onClick={() => setActiveTab("logo")}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-md text-sm font-medium transition-all ${activeTab === "logo" ? "bg-blue-600 text-white shadow-lg" : "text-neutral-400 hover:text-white hover:bg-white/5"}`}
          >
            <ShieldCheck size={16} /> Logo Validation
          </button>
          <button
            onClick={() => setActiveTab("players")}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-md text-sm font-medium transition-all ${activeTab === "players" ? "bg-blue-600 text-white shadow-lg" : "text-neutral-400 hover:text-white hover:bg-white/5"}`}
          >
            <Search size={16} /> Player Headshots
          </button>
          <button
            onClick={() => setActiveTab("generator")}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-md text-sm font-medium transition-all ${activeTab === "generator" ? "bg-blue-600 text-white shadow-lg" : "text-neutral-400 hover:text-white hover:bg-white/5"}`}
          >
            <ImageIcon size={16} /> Background Generator
          </button>
        </div>

        {/* Tab Content */}
        <div className="bg-neutral-900/50 border border-white/10 rounded-2xl p-8 backdrop-blur-xl">

          {/* LOGO VALIDATION TAB */}
          {activeTab === "logo" && (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <h2 className="text-xl font-semibold mb-6 flex items-center gap-2"><ShieldCheck className="text-blue-400" /> Logo Validation & Analysis</h2>

              <form onSubmit={handleValidate} className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-neutral-400 mb-2">Upload Team Logo</label>
                    <input
                      type="file"
                      required
                      accept="image/*"
                      onChange={e => setLogoFile(e.target.files[0])}
                      className="w-full bg-black/50 border border-white/10 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-blue-500 transition-colors file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700 cursor-pointer"
                    />
                  </div>
                  {valError && <p className="text-red-400 text-sm">{valError}</p>}
                  <button
                    type="submit"
                    disabled={valStatus === "loading" || !logoFile}
                    className="w-full mt-4 bg-blue-600 hover:bg-blue-500 text-white font-semibold py-3 px-4 rounded-lg transition-colors flex justify-center items-center gap-2 disabled:opacity-50"
                  >
                    {valStatus === "loading" ? (
                      <span className="animate-spin h-5 w-5 border-2 border-white/20 border-t-white rounded-full" />
                    ) : (
                      "Identify & Validate Team"
                    )}
                  </button>
                </div>

                <div className="bg-black/30 rounded-xl p-6 border border-white/5 flex flex-col items-center justify-center min-h-[200px]">
                  <h3 className="text-sm font-medium text-neutral-400 mb-3 uppercase tracking-wider w-full text-left">Uploaded Image Preview</h3>
                  {logoPreview ? (
                    <img src={logoPreview} alt="Preview" className="max-h-48 max-w-full object-contain drop-shadow-2xl rounded-lg" />
                  ) : (
                    <div className="flex flex-col items-center text-neutral-600">
                      <ImageIcon size={48} className="mb-2 opacity-50" />
                      <p className="text-sm">No image uploaded</p>
                    </div>
                  )}
                </div>
              </form>

              {valStatus === "loading" && (
                <div className="py-12 flex flex-col items-center justify-center text-neutral-400">
                  <div className="animate-spin h-8 w-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full mb-4" />
                  <p>Identifying team via AI & executing validation...</p>
                </div>
              )}

              {valStatus === "success" && validationData && (
                <div className="mt-8 border-t border-white/10 pt-8 animate-in fade-in">
                  <ValidationResult validation={validationData} />

                  <div className="mt-8 bg-blue-900/20 border border-blue-500/30 rounded-xl p-6 flex items-center justify-between">
                    <div>
                      <h4 className="font-semibold text-lg mb-1 flex items-center gap-2"><ImageIcon size={20} className="text-blue-400" /> Next Step</h4>
                      <p className="text-neutral-400 text-sm">Validation complete! You can now generate the Figma-style Background Image based on the extracted colors and validated logo.</p>
                    </div>
                    <button
                      onClick={handleGenerateBackground}
                      disabled={artStatus === "loading"}
                      className="bg-blue-600 hover:bg-blue-500 px-6 py-3 rounded-lg font-semibold flex items-center gap-2 transition-colors disabled:opacity-50"
                    >
                      {artStatus === "loading" ? <span className="animate-spin h-5 w-5 border-2 border-white/20 border-t-white rounded-full" /> : "Generate Background"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* PLAYER HEADSHOTS TAB */}
          {activeTab === "players" && (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <h2 className="text-xl font-semibold mb-6 flex items-center gap-2"><Search className="text-blue-400" /> Player Headshots Engine</h2>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* 1. Individual Search (Span 4 columns) */}
                <div className="lg:col-span-4 bg-black/30 rounded-xl p-6 border border-white/5 flex flex-col h-fit">
                  <h3 className="text-lg font-medium mb-2 flex items-center gap-2"><span className="bg-blue-500/20 text-blue-400 rounded-full w-6 h-6 flex items-center justify-center text-xs">1</span> Individual Search</h3>
                  <p className="text-sm text-neutral-400 mb-4">Fetch an individual headshot.</p>

                  <form onSubmit={handlePlayerSearch} className="flex gap-3 mb-6">
                    <input
                      type="text"
                      placeholder="e.g. LeBron James"
                      value={playerName}
                      onChange={e => setPlayerName(e.target.value)}
                      className="flex-1 w-full bg-black/50 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
                    />
                    <button type="submit" disabled={indSearchStatus === "loading"} className="bg-neutral-800 hover:bg-neutral-700 px-4 py-2 rounded-lg font-medium transition-colors">
                      {indSearchStatus === "loading" ? <span className="animate-spin h-5 w-5 border-2 border-white/20 border-t-white rounded-full mx-auto" /> : "Search"}
                    </button>
                  </form>

                  {indSearchStatus === "error" && <p className="text-red-400 text-sm flex items-center gap-1"><AlertCircle size={14} /> Player not found.</p>}

                  {individualPlayer && (
                    <div className="flex items-center gap-4 bg-neutral-900 p-5 rounded-xl border border-white/10 mt-2 shadow-xl">
                      <div className="w-16 h-16 rounded-full bg-neutral-800 border-2 border-white/10 overflow-hidden flex-shrink-0">
                        {individualPlayer.image_url ? (
                          <img src={individualPlayer.image_url} alt={individualPlayer.name} className="w-full h-full object-cover" />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-xs text-neutral-500">N/A</div>
                        )}
                      </div>
                      <div>
                        <p className="font-bold text-lg text-white leading-tight">{individualPlayer.name}</p>
                        <p className="text-blue-400 text-sm font-medium">{individualPlayer.role || "Player"}</p>
                      </div>
                    </div>
                  )}
                </div>

                {/* 2. Team Roster Builder (Span 8 columns) */}
                <div className="lg:col-span-8 bg-black/30 rounded-xl p-6 border border-white/5 flex flex-col min-h-[400px]">
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h3 className="text-lg font-medium flex items-center gap-2"><span className="bg-blue-500/20 text-blue-400 rounded-full w-6 h-6 flex items-center justify-center text-xs">2</span> Roster Builder</h3>
                      <p className="text-sm text-neutral-400 mt-1">
                        Target Team: <span className="font-semibold text-white">{validationData ? validationData.team : "Unknown (Identify Team First)"}</span>
                      </p>
                    </div>
                    {rosterStatus === "success" && rosterPlayers.length > 0 && (
                      <button onClick={exportTeamData} className="flex items-center gap-2 text-xs bg-blue-600/20 text-blue-400 hover:bg-blue-600 hover:text-white px-3 py-1.5 rounded transition-colors">
                        <Download size={14} /> Export CSV
                      </button>
                    )}
                  </div>

                  {/* Split Action Buttons */}
                  <div className="flex flex-col sm:flex-row gap-4 mb-6">
                    <button
                      onClick={handleTeamRosterSearch}
                      disabled={rosterStatus === "loading" || !validationData}
                      className="flex-1 bg-neutral-800 hover:bg-neutral-700 py-2.5 rounded-lg font-medium transition-colors flex justify-center items-center gap-2 disabled:opacity-50 border border-white/5"
                    >
                      {rosterStatus === "loading" ? <span className="animate-spin h-4 w-4 border-2 border-white/20 border-t-white rounded-full" /> : <><Search size={16} /> Fetch Validated Team</>}
                    </button>

                    <div className="relative flex-1">
                      <input
                        type="file"
                        accept=".csv"
                        ref={fileInputRef}
                        onChange={handleCsvUpload}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
                        disabled={rosterStatus === "loading"}
                      />
                      <button
                        disabled={rosterStatus === "loading"}
                        className="w-full bg-blue-600/20 text-blue-400 hover:bg-blue-600 hover:text-white py-2.5 rounded-lg font-medium transition-colors flex justify-center items-center gap-2 disabled:opacity-50 border border-blue-500/30"
                      >
                        <Upload size={16} /> Upload Custom CSV
                      </button>
                    </div>
                  </div>

                  {/* Tabular Display */}
                  <div className="flex-1 bg-neutral-900/50 rounded-lg border border-white/10 overflow-hidden relative">
                    {rosterStatus === "success" && rosterPlayers.length > 0 ? (
                      <div className="max-h-[400px] overflow-y-auto custom-scrollbar">
                        <table className="w-full text-left border-collapse">
                          <thead className="sticky top-0 bg-neutral-900 border-b border-white/10 shadow-sm z-10">
                            <tr className="text-neutral-400 text-xs uppercase tracking-wider">
                              <th className="py-3 px-6 font-medium w-24">Photo</th>
                              <th className="py-3 px-6 font-medium">Player Name</th>
                              <th className="py-3 px-6 font-medium">Position / Role</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-white/5">
                            {rosterPlayers.map((p, idx) => (
                              <tr key={idx} className="hover:bg-white/5 transition-colors">
                                <td className="py-3 px-6">
                                  <div className="w-10 h-10 rounded-full bg-neutral-800 border border-white/10 overflow-hidden shadow-inner">
                                    {p.image_url ? (
                                      <img src={p.image_url} alt={p.name} className="w-full h-full object-cover" />
                                    ) : (
                                      <div className="flex items-center justify-center w-full h-full text-[10px] text-neutral-500">N/A</div>
                                    )}
                                  </div>
                                </td>
                                <td className="py-3 px-6 font-semibold text-white">{p.name}</td>
                                <td className="py-3 px-6 text-blue-400 text-sm">{p.role || "Player"}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : rosterStatus === "loading" ? (
                      <div className="absolute inset-0 flex flex-col items-center justify-center text-neutral-400 text-sm">
                        <span className="animate-spin h-8 w-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full mb-4" />
                        Processing Roster...
                      </div>
                    ) : (
                      <div className="absolute inset-0 flex flex-col items-center justify-center text-neutral-600 text-sm p-6 text-center">
                        <Search size={32} className="mb-3 opacity-20" />
                        <p>No roster data available.</p>
                        <p className="mt-1 max-w-xs text-xs">Fetch the validated team, or upload a CSV containing a single column of player names.</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* GENERATOR TAB */}
          {activeTab === "generator" && (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <h2 className="text-xl font-semibold mb-6 flex items-center gap-2"><ImageIcon className="text-blue-400" /> Figma-Level Background Generator</h2>

              {artStatus === "loading" ? (
                <div className="aspect-video w-full max-w-3xl mx-auto flex flex-col items-center justify-center bg-black/40 rounded-2xl border border-dashed border-white/10 text-neutral-400">
                  <span className="animate-spin h-8 w-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full mb-4" />
                  <p>Compositing Figma-style layers and gradients...</p>
                </div>
              ) : artworkData ? (
                <div className="border-t border-white/10 pt-8 animate-in zoom-in-95">
                  <ArtworkGallery artwork={artworkData} />
                </div>
              ) : (
                <div className="aspect-video w-full max-w-3xl mx-auto flex flex-col items-center justify-center bg-black/40 rounded-2xl border border-dashed border-white/10 text-neutral-500">
                  <ImageIcon size={32} className="mx-auto mb-3 opacity-20" />
                  <p>Generate background from the Validation tab first.</p>
                </div>
              )}
            </div>
          )}

        </div>
      </div>
    </main>
  );
}