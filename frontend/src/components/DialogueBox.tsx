import { useEffect, useState } from "react";

export function DialogueBox({ text, speaker = "NPC", typewriter = false, className = "" }: { text: string; speaker?: string; typewriter?: boolean; className?: string }) {
  const [n, setN] = useState(typewriter ? 0 : text.length);
  useEffect(() => {
    if (!typewriter || window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setN(text.length); return; }
    setN(0);
    const t = setInterval(() => setN((v) => { if (v >= text.length) { clearInterval(t); return v; } return v + 1; }), 28);
    return () => clearInterval(t);
  }, [text, typewriter]);
  return (
    <div className={`relative ink-border bg-card p-3 pt-4 shadow-hard ${className}`}>
      <span className="absolute -top-3 left-3 bg-ink px-2 py-0.5 hud-label text-paper">{speaker}</span>
      <p className="text-sm leading-relaxed" aria-label={text}>
        <span aria-hidden>{text.slice(0, n)}</span>
        <span aria-hidden className="ml-0.5 inline-block h-3 w-2 translate-y-0.5 bg-ink animate-blink" />
      </p>
    </div>
  );
}
