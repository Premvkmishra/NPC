import { useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { Link } from "@tanstack/react-router";
import type { CompleteResponse } from "@/lib/types";
import { Btn } from "./Btn";
import { PixelIcon } from "./PixelIcon";
import { AutopilotMeter } from "./AutopilotMeter";

const CONF = ["bg-lime", "bg-orange", "bg-butter", "bg-rose", "bg-teal"];

function Confetti() {
  const bits = useMemo(() => Array.from({ length: 36 }, (_, i) => ({ left: (i * 37) % 100, delay: (i % 9) * 0.12, c: CONF[i % 5], s: 6 + (i % 3) * 4 })), []);
  return <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">{bits.map((b, i) => (
    <span key={i} className={`absolute top-0 animate-confetti border border-ink ${b.c}`} style={{ left: `${b.left}%`, width: b.s, height: b.s, animationDelay: `${b.delay}s` }} />
  ))}</div>;
}

export function StampModal({ result, onClose }: { result: CompleteResponse; onClose: () => void }) {
  const steps = ["stamp", ...(result.leveled_up ? ["level"] : []), ...(result.achievements_unlocked.length ? ["ach"] : []), "end"];
  const [i, setI] = useState(0);
  const step = steps[i];
  const next = () => setI((v) => Math.min(v + 1, steps.length - 1));
  return createPortal(
    <div role="dialog" aria-modal="true" aria-label="Quest completed" className="fixed inset-0 z-50 flex items-center justify-center bg-ink p-4">
      <Confetti />
      <div className="relative w-full max-w-[400px] space-y-5 text-center">
        {step === "stamp" && <>
          <div className="mx-auto inline-block animate-stamp border-[6px] border-double border-lime px-6 py-4 font-pixel text-4xl leading-none text-lime">QUEST<br />COMPLETED</div>
          <p className="font-mono text-5xl font-bold text-butter">+{result.xp_awarded} XP</p>
          <p className="font-pixel text-xl text-paper">{result.message}</p>
        </>}
        {step === "level" && <>
          <p className="animate-level font-pixel text-6xl text-butter">LEVEL UP!</p>
          <div className="mx-auto w-32 ink-border bg-butter py-4 shadow-[6px_6px_0_var(--lime)]"><p className="hud-label">Level</p><p className="font-mono text-6xl font-bold">{result.new_level}</p></div>
        </>}
        {step === "ach" && <>
          <p className="font-pixel text-3xl text-paper">Achievement{result.achievements_unlocked.length > 1 ? "s" : ""} unlocked</p>
          <div className="space-y-3">{result.achievements_unlocked.map((a, k) => (
            <div key={a.id} className="flex animate-pop items-center gap-3 ink-border bg-butter p-3 text-left shadow-[4px_4px_0_var(--lime)]" style={{ animationDelay: `${k * 150}ms` }}>
              <div className="ink-border bg-card p-2"><PixelIcon name={a.icon_key} size={28} /></div>
              <div><p className="font-pixel text-lg leading-tight">{a.name}</p><p className="text-xs">{a.description}</p></div>
            </div>
          ))}</div>
        </>}
        {step === "end" && <>
          <AutopilotMeter autopilot={result.autopilot} />
          <Link to="/journey" className="block min-h-11 ink-border border-paper bg-lime px-4 py-3 font-pixel uppercase tracking-wider">See it in your Journey</Link>
          <button onClick={onClose} className="min-h-11 text-sm text-paper underline">Back to quest</button>
        </>}
        {step !== "end" && <Btn onClick={next} className="w-full">Continue</Btn>}
      </div>
    </div>,
    document.body,
  );
}
