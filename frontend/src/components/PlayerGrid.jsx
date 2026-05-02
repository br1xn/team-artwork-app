import React from "react";
import { UserRound } from "lucide-react";

import { assetUrl } from "../services/processTeam";

export function PlayerGrid({ players }) {
  return (
    <section className="instrument-card result-card">
      <div className="result-heading">
        <div>
          <p className="eyebrow">Players</p>
          <h2 className="panel-title">Processed headshots</h2>
        </div>
        <span className="count-pill">{players.length}</span>
      </div>
      {players.length === 0 ? (
        <p className="empty-state">No players were found. Fallback roster data will appear after retry.</p>
      ) : (
        <div className="players-grid">
          {players.map((player) => (
            <article className="player-tile" key={`${player.name}-${player.role || "role"}`}>
              {player.processed_image_path ? (
                <img src={assetUrl(player.processed_image_path)} alt={player.name} />
              ) : (
                <div className="headshot-placeholder"><UserRound size={28} /></div>
              )}
              <div>
                <h3>{player.name}</h3>
                <p>{player.role || "Role pending"}{player.source ? ` / ${player.source}` : ""}</p>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
