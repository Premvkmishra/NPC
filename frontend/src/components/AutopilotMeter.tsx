import type { Autopilot } from "@/lib/types";

const FACES: Record<Autopilot["label"], string[]> = {
  "Wide awake": ["........", ".#....#.", ".#....#.", "........", "#......#", ".#....#.", "..####..", "........"],
  "Mostly exploring": ["........", ".#....#.", ".#....#.", "........", "........", ".#....#.", "..####..", "........"],
  "Needs a little adventure": ["........", ".#....#.", "........", "........", "........", "..####..", "........", "........"],
  "Deep autopilot": ["........", "##....##", "........", "........", "........", "..####..", ".#....#.", "........"],
};
const COLOR: Record<Autopilot["label"], string> = {
  "Wide awake": "bg-lime", "Mostly exploring": "bg-teal", "Needs a little adventure": "bg-butter", "Deep autopilot": "bg-orange",
};

export function AutopilotMeter({ autopilot }: { autopilot: Autopilot }) {
  const segs = 10; const filled = Math.round(autopilot.score / 10);
  const face = FACES[autopilot.label];
  return (
    <section aria-label="Autopilot meter" className="ink-border bg-card p-4 shadow-hard">
      <div className="flex items-start gap-3">
        <div className={`ink-border ${COLOR[autopilot.label]} p-1`}>
          <svg width="44" height="44" viewBox="0 0 8 8" shapeRendering="crispEdges" aria-hidden>
            {face.flatMap((r, y) => [...r].map((c, x) => c === "#" ? <rect key={`${x}${y}`} x={x} y={y} width={1} height={1} fill="currentColor" /> : null))}
          </svg>
        </div>
        <div className="relative flex-1 ink-border bg-paper px-3 py-2">
          <span className="absolute -left-[9px] top-4 h-3 w-3 rotate-45 border-b-[3px] border-l-[3px] border-ink bg-paper" aria-hidden />
          <p className="hud-label text-muted-foreground">Autopilot meter</p>
          <p className="font-pixel text-lg leading-tight">{autopilot.label}</p>
        </div>
        <p className="font-mono text-3xl font-bold leading-none">{autopilot.score}</p>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <div className="flex flex-1 gap-0.5 ink-border bg-paper-deep p-1" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={autopilot.score} aria-label="Autopilot score">
          {Array.from({ length: segs }, (_, i) => <div key={i} className={`h-5 flex-1 ${i < filled ? COLOR[autopilot.label] : "bg-card"} ${i < filled ? "border-2 border-ink" : ""}`} />)}
        </div>
        <div className="h-3 w-1.5 bg-ink" aria-hidden />
      </div>
      <p className="mt-1 flex justify-between hud-label text-muted-foreground"><span>Fresh</span><span>Higher = more repetition</span></p>
      <p className="mt-2 text-sm">{autopilot.explanation}</p>
      <p className="mt-2 text-[11px] text-muted-foreground">{autopilot.disclaimer}</p>
    </section>
  );
}
