import React from "react";

export type QueueItem = {
  id: string;
  url: string;
  status: "queued" | "running" | "done" | "error";
  title?: string;
  filepath?: string;
  error?: string;
  progress?: {
    progress_pct?: number;
    downloaded_bytes?: number;
    total_bytes?: number;
    speed?: number;
    eta?: number;
  };
};

type QueuePaneProps = {
  queueText: string;
  onQueueTextChange: (value: string) => void;
  onAdd: () => void;
  onStart: () => void;
  onClear: () => void;
  queue: QueueItem[];
};

const QueuePane: React.FC<QueuePaneProps> = ({
  queueText,
  onQueueTextChange,
  onAdd,
  onStart,
  onClear,
  queue,
}) => {
  const apiBase: string = (import.meta.env.VITE_API_URL as string) || "/";
  const joinApiUrl = (path: string) => {
    try {
      return new URL(path.replace(/^\//, ""), apiBase).toString();
    } catch {
      return (apiBase.endsWith("/") ? apiBase : apiBase + "/") + path.replace(/^\//, "");
    }
  };

  const handleSaveToPC = async (item: QueueItem) => {
    try {
      const url = joinApiUrl(`/api/jobs/${item.id}/file`);
      const suggestedName = (item.filepath?.split(/[/\\\\]/).pop() || item.title || "download.mp4") as string;

      // Prefer File System Access API when available
      // @ts-ignore
      if (window.showSaveFilePicker) {
        // @ts-ignore
        const fileHandle = await window.showSaveFilePicker({
          suggestedName,
          types: [
            {
              description: "Media file",
              accept: { "application/octet-stream": [".mp4", ".mkv", ".webm", ".mp3", ".m4a"] },
            },
          ],
        });
        const writable = await fileHandle.createWritable();
        const resp = await fetch(url);
        if (!resp.ok || !resp.body) throw new Error(`Download failed (${resp.status})`);
        // Stream to disk
        await resp.body.pipeTo(writable);
        return;
      }

      // Fallback: open in a new tab; browser will prompt or auto-save based on settings
      const a = document.createElement("a");
      a.href = url;
      a.rel = "noopener noreferrer";
      a.target = "_blank";
      a.download = suggestedName;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      // No centralized error UI here; the queue poller remains unaffected
      // Could integrate with a toast system if added later
      console.error(err);
    }
  };
  const renderProgress = (item: QueueItem) => {
    const pct = Math.max(0, Math.min(100, Math.floor(item.progress?.progress_pct ?? 0)));
    const label = `${pct}%`;
    return (
      <div className="mt-2">
        <div
          className="w-full h-2 bg-neutral-800 rounded-full overflow-hidden border border-white/10"
          aria-label={`Progress ${label}`}
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={pct}
        >
          <div className="h-full bg-gradient-to-r from-sky-500 to-emerald-500" style={{ width: `${pct}%` }} />
        </div>
        <div className="mt-1 flex justify-between text-[11px] text-neutral-400">
          <span>{label}</span>
          <span>
            {item.progress?.downloaded_bytes ? Math.round((item.progress.downloaded_bytes / (1024 * 1024)) * 10) / 10 : 0}
            MB
            {item.progress?.total_bytes ? ` / ${Math.round((item.progress.total_bytes / (1024 * 1024)) * 10) / 10}MB` : ""}
          </span>
        </div>
      </div>
    );
  };

  return (
    <section className="rounded-2xl bg-neutral-900/60 border border-white/10 shadow-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide text-neutral-300">Download Queue</h2>
        <div className="flex gap-2">
          <button
            type="button"
            aria-label="Add URLs to queue"
            className="px-3 py-1.5 rounded-lg bg-sky-600 text-white text-sm shadow hover:opacity-95 active:opacity-90 focus:outline-none focus:ring-2 focus:ring-sky-400/50"
            onClick={onAdd}
          >
            Add to Queue
          </button>
          <button
            type="button"
            aria-label="Start queue"
            className="px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-sm shadow hover:opacity-95 active:opacity-90 focus:outline-none focus:ring-2 focus:ring-emerald-400/50"
            onClick={onStart}
          >
            Start Queue
          </button>
          <button
            type="button"
            aria-label="Clear textarea"
            className="px-3 py-1.5 rounded-lg bg-neutral-800 text-neutral-200 border border-white/10 text-sm shadow hover:bg-neutral-800/80 active:bg-neutral-800/70 focus:outline-none focus:ring-2 focus:ring-neutral-600/50"
            onClick={onClear}
          >
            Clear
          </button>
        </div>
      </div>

      <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label htmlFor="queue-textarea" className="sr-only">
            Paste multiple URLs, one per line
          </label>
          <textarea
            id="queue-textarea"
            aria-label="Paste multiple URLs, one per line"
            placeholder="Paste multiple URLs, one per line…"
            className="w-full h-40 rounded-xl bg-neutral-950/60 border border-white/10 px-4 py-3 text-neutral-100 placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-sky-500/50 focus:border-sky-400 resize-y"
            value={queueText}
            onChange={(e) => onQueueTextChange(e.target.value)}
          />
        </div>

        <div>
          <h3 className="text-xs font-semibold tracking-wide text-neutral-400 mb-2">Statuses</h3>
          <ul className="space-y-2 max-h-40 overflow-auto pr-1">
            {queue.length === 0 && (
              <li className="text-neutral-500 text-sm">No items yet</li>
            )}
            {queue.map((item) => (
              <li
                key={item.id}
                className="rounded-lg border border-white/10 bg-neutral-950/50 p-3"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="text-xs px-2 py-0.5 rounded-full border border-white/10">
                    {item.status}
                  </span>
                  {item.title && (
                    <span className="truncate text-xs text-neutral-400" title={item.title}>
                      {item.title}
                    </span>
                  )}
                </div>
                <div className="mt-1 text-xs text-neutral-400 truncate" title={item.url}>
                  {item.url}
                </div>
                {item.filepath && (
                  <div className="mt-1 text-xs text-emerald-300 truncate" title={item.filepath}>
                    {item.filepath}
                  </div>
                )}
                {item.status === "running" && renderProgress(item)}
                {item.status === "done" && (
                  <div className="mt-2 flex justify-end gap-2">
                    <a
                      href={joinApiUrl(`/api/jobs/${item.id}/file`)}
                      className="inline-flex items-center px-3 py-1.5 rounded-lg bg-neutral-800 text-neutral-200 border border-white/10 text-sm shadow hover:bg-neutral-800/80 focus:outline-none focus:ring-2 focus:ring-neutral-600/50"
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label="Download using browser"
                    >
                      Browser Download
                    </a>
                    <button
                      type="button"
                      className="inline-flex items-center px-3 py-1.5 rounded-lg bg-gradient-to-r from-amber-500 to-pink-500 text-white text-sm shadow hover:opacity-95 focus:outline-none focus:ring-2 focus:ring-pink-400/50"
                      onClick={() => handleSaveToPC(item)}
                      aria-label="Save to a chosen location on your computer"
                    >
                      Save As…
                    </button>
                  </div>
                )}
                {item.error && (
                  <div className="mt-1 text-xs text-red-300 break-words">{item.error}</div>
                )}
              </li>
            ))}
          </ul>
          <p className="mt-3 text-[11px] text-neutral-500">
            Files are saved to your configured downloads path on the server.
          </p>
        </div>
      </div>
      {/* TODO: quality selector (1080p/720p/audio) */}
    </section>
  );
};

export default QueuePane;

