import React from "react";

type PreviewPaneProps = {
  thumbnailUrl?: string;
  streamUrl?: string;
};

const Card: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => {
  return (
    <section
      aria-label={title}
      className="rounded-2xl bg-neutral-900/60 border border-white/10 shadow-lg overflow-hidden"
      tabIndex={0}
    >
      <div className="px-4 py-3 border-b border-white/10">
        <h2 className="text-sm font-semibold tracking-wide text-neutral-300">{title}</h2>
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
};

const PreviewPane: React.FC<PreviewPaneProps> = ({ thumbnailUrl, streamUrl }) => {
  return (
    <>
      <Card title="Thumbnail">
        {thumbnailUrl ? (
          <img
            src={thumbnailUrl}
            alt="Video thumbnail"
            className="w-full h-64 object-contain bg-neutral-950/50 rounded-xl"
            loading="eager"
            crossOrigin="anonymous"
          />
        ) : (
          <div className="w-full h-64 rounded-xl bg-neutral-950/60 border border-white/5 grid place-items-center text-neutral-500">
            No thumbnail yet
          </div>
        )}
      </Card>

      <Card title="Video Preview">
        {streamUrl ? (
          <video
            src={streamUrl}
            controls
            preload="metadata"
            className="w-full rounded-xl border border-white/10 bg-black"
            crossOrigin="anonymous"
          />
        ) : (
          <div className="w-full h-64 rounded-xl bg-neutral-950/60 border border-white/5 grid place-items-center text-neutral-500">
            No preview yet
          </div>
        )}
      </Card>
    </>
  );
};

export default PreviewPane;

