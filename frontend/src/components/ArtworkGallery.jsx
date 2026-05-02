import React from "react";
import { ImageIcon } from "lucide-react";

import { assetUrl } from "../services/processTeam";

export function ArtworkGallery({ artwork }) {
  const images = artwork ? [artwork.thumbnail, artwork.poster, ...(artwork.variants || [])].filter(Boolean) : [];

  return (
    <section className="instrument-card result-card">
      <div className="result-heading">
        <div>
          <p className="eyebrow">Artwork</p>
          <h2 className="panel-title">Generated gallery</h2>
        </div>
        <ImageIcon className="text-clay" />
      </div>
      {images.length === 0 ? (
        <p className="empty-state">Artwork generation did not return images yet. Retry will trigger the PIL fallback.</p>
      ) : (
        <>
        <div className="transparency-panel">
          <p><strong>Provider:</strong> {artwork.provider}</p>
          <p><strong>Model:</strong> {artwork.model || "local composer"}</p>
          {artwork.prompt ? <p><strong>Prompt:</strong> {artwork.prompt}</p> : null}
        </div>
        <div className="artwork-grid">
          {images.map((image, index) => (
            <a href={assetUrl(image)} target="_blank" rel="noreferrer" className={index === 1 ? "artwork-tile poster" : "artwork-tile"} key={image}>
              <img src={assetUrl(image)} alt={`Artwork variant ${index + 1}`} />
            </a>
          ))}
        </div>
        </>
      )}
    </section>
  );
}
