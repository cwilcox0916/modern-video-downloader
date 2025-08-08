import React, { useCallback, useEffect, useMemo, useState } from "react";
import TopBar from "../components/TopBar";
import PreviewPane from "../components/PreviewPane";
import QueuePane, { QueueItem } from "../components/QueuePane";

const apiBase: string = (import.meta.env.VITE_API_URL as string) || "/";

const joinApiUrl = (path: string) => {
  try {
    return new URL(path.replace(/^\//, ""), apiBase).toString();
  } catch {
    return (apiBase.endsWith("/") ? apiBase : apiBase + "/") + path.replace(/^\//, "");
  }
};

const App: React.FC = () => {
  const [url, setUrl] = useState<string>("");
  const [thumbnailUrl, setThumbnailUrl] = useState<string>("");
  const [streamUrl, setStreamUrl] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [queueText, setQueueText] = useState<string>("");
  const [queue, setQueue] = useState<QueueItem[]>([]);

  const resetPreview = useCallback(() => {
    setThumbnailUrl("");
    setStreamUrl("");
    setError("");
  }, []);

  const handleThumbnail = useCallback(async () => {
    setError("");
    setThumbnailUrl("");
    try {
      const res = await fetch(joinApiUrl("/api/thumbnail"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j?.detail || `Error ${res.status}`);
      }
      const data = await res.json();
      setThumbnailUrl(data.thumbnail || "");
      if (!data.thumbnail) throw new Error("No thumbnail returned");
    } catch (e: any) {
      setError(e?.message || "Failed to fetch thumbnail");
    }
  }, [url]);

  const handlePreview = useCallback(async () => {
    setError("");
    setStreamUrl("");
    try {
      const res = await fetch(joinApiUrl("/api/preview"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j?.detail || `Error ${res.status}`);
      }
      const data = await res.json();
      setStreamUrl(data.stream_url || "");
      if (!data.stream_url) throw new Error("No stream URL returned");
    } catch (e: any) {
      setError(e?.message || "Failed to fetch preview");
    }
  }, [url]);

  const handleDownload = useCallback(async () => {
    setError("");
    try {
      const res = await fetch(joinApiUrl("/api/download"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j?.detail || `Error ${res.status}`);
      }
      // no-op; queue poller will reflect state
    } catch (e: any) {
      setError(e?.message || "Failed to enqueue download");
    }
  }, [url]);

  const handleCancel = useCallback(() => {
    setUrl("");
    resetPreview();
    // v1: Cancel is UI-only; does not affect backend
  }, [resetPreview]);

  const parsedQueueLines = useMemo(() => {
    return queueText
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.length > 0);
  }, [queueText]);

  const handleAddToQueue = useCallback(async () => {
    if (parsedQueueLines.length === 0) return;
    setError("");
    try {
      const res = await fetch(joinApiUrl("/api/queue/add"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ urls: parsedQueueLines }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j?.detail || `Error ${res.status}`);
      }
    } catch (e: any) {
      setError(e?.message || "Failed to add to queue");
    }
  }, [parsedQueueLines]);

  const handleStartQueue = useCallback(async () => {
    // v1: Start behaves same as Add (runner is always on)
    await handleAddToQueue();
  }, [handleAddToQueue]);

  const handleClearQueueText = useCallback(() => {
    setQueueText("");
  }, []);

  // Poll queue statuses
  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const res = await fetch(joinApiUrl("/api/queue"));
        if (!res.ok) return;
        const data = await res.json();
        if (alive && data?.queue) setQueue(data.queue);
      } catch {
        // ignore
      }
    };
    tick();
    const id = setInterval(tick, 2000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="min-h-full bg-gradient-to-br from-neutral-950 via-neutral-900 to-neutral-950 text-neutral-100">
      <div className="mx-auto max-w-6xl p-4 md:p-8">
        <header className="mb-6">
          <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-fuchsia-400 via-sky-400 to-emerald-400">
            Modern Video Downloader
          </h1>
          <p className="text-neutral-400 mt-1">Local-only. Your links never leave your machine.</p>
        </header>

        <div className="backdrop-blur bg-white/5 border border-white/10 rounded-2xl shadow-xl p-4 md:p-6">
          <TopBar
            url={url}
            onUrlChange={setUrl}
            onThumbnail={handleThumbnail}
            onPreview={handlePreview}
            onDownload={handleDownload}
            onCancel={handleCancel}
          />

          {error && (
            <div
              role="alert"
              className="mt-3 text-sm text-red-300 bg-red-900/30 border border-red-700/40 rounded-lg px-3 py-2"
            >
              {error}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 mt-6">
            <PreviewPane thumbnailUrl={thumbnailUrl} streamUrl={streamUrl} />
          </div>

          <div className="mt-6">
            <QueuePane
              queueText={queueText}
              onQueueTextChange={setQueueText}
              onAdd={handleAddToQueue}
              onStart={handleStartQueue}
              onClear={handleClearQueueText}
              queue={queue}
            />
          </div>

          <footer className="mt-4 text-xs text-neutral-400">
            Local-only. Your links never leave your machine.
          </footer>
        </div>
      </div>
    </div>
  );
};

export default App;

