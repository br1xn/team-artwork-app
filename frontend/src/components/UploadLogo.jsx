import React from "react";
import { ImageUp, X } from "lucide-react";

export function UploadLogo({ logoFile, onChange }) {
  const previewUrl = logoFile ? URL.createObjectURL(logoFile) : "";

  return (
    <div className="instrument-card upload-zone">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="eyebrow">Logo Input</p>
          <h2 className="panel-title">Upload a team mark</h2>
        </div>
        {logoFile ? (
          <button className="icon-button" type="button" onClick={() => onChange(null)} aria-label="Remove logo">
            <X size={18} />
          </button>
        ) : (
          <ImageUp className="text-clay" size={28} />
        )}
      </div>

      <label className="drop-target" htmlFor="logo-upload">
        {logoFile ? (
          <img src={previewUrl} alt="Logo preview" className="logo-preview" />
        ) : (
          <span>PNG, JPG, WEBP, or SVG</span>
        )}
        <input
          id="logo-upload"
          type="file"
          accept="image/*"
          onChange={(event) => onChange(event.target.files?.[0] || null)}
        />
      </label>
      <p className="microcopy">Small or low-resolution logos are upscaled before validation.</p>
    </div>
  );
}
