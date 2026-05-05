import React from "react";
import { Download, Monitor, TabletSmartphone, CheckCircle2 } from "lucide-react";

// Helper function to safely build the full image URL
const assetUrl = (path) => {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `http://127.0.0.1:8000${path.startsWith('/') ? path : '/' + path}`;
};

export function ArtworkGallery({ artwork }) {
  if (!artwork) return null;

  const handleDownload = async (url, filename) => {
    try {
      const response = await fetch(assetUrl(url));
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(objectUrl);
    } catch (error) {
      console.error("Download failed:", error);
    }
  };

  return (
    <div className="space-y-6">

      {/* Clean Success Banner */}
      <div className="bg-emerald-900/10 border border-emerald-500/20 rounded-xl p-4 flex items-center gap-3">
        <CheckCircle2 size={20} className="text-emerald-400" />
        <p className="text-emerald-100 font-medium">Background Generated Successfully</p>
      </div>

      {/* Gallery Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* 16:9 Image Card */}
        <div className="bg-black/30 rounded-xl border border-white/5 overflow-hidden flex flex-col shadow-2xl">
          <div className="aspect-video bg-black relative group">
            <img
              src={assetUrl(artwork.poster)}
              alt="16:9 Background"
              className="w-full h-full object-cover"
            />
          </div>
          <div className="p-5 flex items-center justify-between bg-neutral-900/80 backdrop-blur">
            <div>
              <h4 className="font-semibold text-white flex items-center gap-2">
                <Monitor size={16} className="text-neutral-400" /> 16:9 Broadcast Format
              </h4>
              <p className="text-xs text-neutral-400 mt-1">1920x1080 • Desktop & TV Background</p>
            </div>
            <button
              onClick={() => handleDownload(artwork.poster, "background_16x9.png")}
              className="bg-neutral-800 hover:bg-blue-600 text-white p-2.5 rounded-lg transition-colors border border-white/10 hover:border-transparent flex items-center gap-2"
              title="Download 16:9 Image"
            >
              <Download size={18} />
            </button>
          </div>
        </div>

        {/* 4:3 Image Card */}
        <div className="bg-black/30 rounded-xl border border-white/5 overflow-hidden flex flex-col shadow-2xl">
          <div className="aspect-[4/3] bg-black relative group">
            <img
              src={assetUrl(artwork.thumbnail)}
              alt="4:3 Background"
              className="w-full h-full object-cover"
            />
          </div>
          <div className="p-5 flex items-center justify-between bg-neutral-900/80 backdrop-blur mt-auto">
            <div>
              <h4 className="font-semibold text-white flex items-center gap-2">
                <TabletSmartphone size={16} className="text-neutral-400" /> 4:3 Digital Format
              </h4>
              <p className="text-xs text-neutral-400 mt-1">1600x1200 • Tablet & Social Media</p>
            </div>
            <button
              onClick={() => handleDownload(artwork.thumbnail, "background_4x3.png")}
              className="bg-neutral-800 hover:bg-blue-600 text-white p-2.5 rounded-lg transition-colors border border-white/10 hover:border-transparent flex items-center gap-2"
              title="Download 4:3 Image"
            >
              <Download size={18} />
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}