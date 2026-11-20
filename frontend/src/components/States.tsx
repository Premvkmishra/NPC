import { ApiError } from "@/lib/errors";
import { Btn } from "./Btn";
import { DialogueBox } from "./DialogueBox";

export function LoadingState({ label = "Loading the map…" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center gap-3 py-10" role="status">
      <div className="flex gap-1">{[0, 1, 2].map((i) => <div key={i} className="h-3 w-3 bg-ink animate-blink" style={{ animationDelay: `${i * 0.2}s` }} />)}</div>
      <p className="hud-label">{label}</p>
    </div>
  );
}
export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const msg = error instanceof ApiError || error instanceof Error ? error.message : "Something glitched.";
  return (
    <div className="space-y-3 py-4" role="alert">
      <DialogueBox speaker="Uh oh" text={`The map didn't load. ${msg} Try again?`} />
      {onRetry && <Btn variant="butter" onClick={onRetry}>Try again</Btn>}
    </div>
  );
}
export function EmptyState({ text }: { text: string }) {
  return <div className="ink-border border-dashed bg-card/60 p-4 text-center text-sm">{text}</div>;
}
