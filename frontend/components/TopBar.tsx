import React, { KeyboardEvent } from "react";

type TopBarProps = {
  url: string;
  onUrlChange: (value: string) => void;
  onThumbnail: () => void;
  onPreview: () => void;
  onDownload: () => void;
  onCancel: () => void;
};

const TopBar: React.FC<TopBarProps> = ({
  url,
  onUrlChange,
  onThumbnail,
  onPreview,
  onDownload,
  onCancel,
}) => {
  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      onPreview();
    }
  };

  return (
    <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center">
      <label className="sr-only" htmlFor="url-input">
        Media URL
      </label>
      <input
        id="url-input"
        aria-label="Paste a video URL"
        placeholder="Paste a video URL..."
        className="flex-1 rounded-xl bg-neutral-900/70 border border-white/10 px-4 py-3 text-neutral-100 placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-sky-500/50 focus:border-sky-400"
        value={url}
        onChange={(e) => onUrlChange(e.target.value)}
        onKeyDown={handleKeyDown}
      />
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          aria-label="Fetch thumbnail"
          className="px-4 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-pink-500 text-white shadow hover:opacity-95 active:opacity-90 focus:outline-none focus:ring-2 focus:ring-pink-400/50"
          onClick={onThumbnail}
        >
          Thumbnail
        </button>
        <button
          type="button"
          aria-label="Preview video"
          className="px-4 py-2 rounded-xl bg-gradient-to-r from-sky-500 to-emerald-500 text-white shadow hover:opacity-95 active:opacity-90 focus:outline-none focus:ring-2 focus:ring-emerald-400/50"
          onClick={onPreview}
        >
          Preview
        </button>
        <button
          type="button"
          aria-label="Download video"
          className="px-4 py-2 rounded-xl bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white shadow hover:opacity-95 active:opacity-90 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/50"
          onClick={onDownload}
        >
          Download
        </button>
        <button
          type="button"
          aria-label="Cancel"
          className="px-4 py-2 rounded-xl bg-neutral-800 text-neutral-200 border border-white/10 shadow hover:bg-neutral-800/80 active:bg-neutral-800/70 focus:outline-none focus:ring-2 focus:ring-neutral-600/50"
          onClick={onCancel}
        >
          Cancel
        </button>
      </div>
    </div>
  );
};

export default TopBar;

