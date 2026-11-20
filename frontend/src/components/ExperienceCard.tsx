import type { Experience } from "@/lib/types";
import { Btn } from "./Btn";
import { PixelIcon } from "./PixelIcon";

const SOURCE: Record<Experience["source"], string> = { google_maps: "Google Maps", google_events: "Google Events", google_search: "Google Search" };

export function ExperienceCard({ exp, onQuest, busy }: { exp: Experience; onQuest: () => void; busy: boolean }) {
  return (
    <article className="animate-pop ink-border bg-card shadow-hard">
      <div className="flex gap-3 p-3">
        {exp.thumbnail_url ? (
          <img src={exp.thumbnail_url} alt="" className="h-20 w-20 shrink-0 ink-border object-cover" />
        ) : (
          <div className="flex h-20 w-20 shrink-0 items-center justify-center ink-border bg-paper-deep paper-bg"><PixelIcon name="pin" size={32} /></div>
        )}
        <div className="min-w-0 flex-1 space-y-1">
          <span className="inline-block rotate-[-2deg] ink-border bg-butter px-1.5 hud-label">{exp.tag}</span>
          <h3 className="text-base leading-tight">{exp.title}</h3>
          <div className="flex flex-wrap gap-x-3 font-mono text-[11px]">
            {exp.distance_km != null && <span>{exp.distance_km} km</span>}
            {exp.price_label && <span>{exp.price_label}</span>}
            {exp.hours_label && <span>{exp.hours_label}</span>}
            {exp.event_time_label && <span>{exp.event_time_label}</span>}
          </div>
        </div>
      </div>
      <p className="border-t-2 border-dashed border-ink px-3 py-2 text-sm"><span className="hud-label">Why it's worth it · </span>{exp.why_worth_it}</p>
      <div className="flex items-center justify-between gap-2 border-t-[3px] border-ink bg-paper-deep p-3">
        <div className="flex flex-col">
          <span className="rotate-[-3deg] self-start border-2 border-dashed border-ink px-1.5 hud-label">via {SOURCE[exp.source]}</span>
          {exp.link_url && <a href={exp.link_url} target="_blank" rel="noreferrer" className="mt-1 text-xs underline">open source ↗</a>}
        </div>
        <Btn onClick={onQuest} disabled={busy} className="text-sm">{busy ? "Writing…" : "Turn into quest"}</Btn>
      </div>
    </article>
  );
}
