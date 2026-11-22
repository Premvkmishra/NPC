import { ApiError } from "@/lib/errors";
import { Btn } from "./Btn";
import { DialogueBox } from "./DialogueBox";
import { useRestart } from "./ResetProfile";

export function LoadingState({ label = "Loading the map…" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center gap-3 py-10" role="status">
      <div className="flex gap-1">{[0, 1, 2].map((i) => <div key={i} className="h-3 w-3 bg-ink animate-blink" style={{ animationDelay: `${i * 0.2}s` }} />)}</div>
      <p className="hud-label">{label}</p>
    </div>
  );
}
export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const restart = useRestart();
  const msg = error instanceof ApiError || error instanceof Error ? error.message : "Something glitched.";

  // The saved player no longer exists on the server (e.g. the database was reset): retrying won't help.
  if (error instanceof ApiError && error.code === "player_required") {
    return (
      <div className="space-y-3 py-4" role="alert">
        <DialogueBox speaker="Uh oh" text="We couldn't find your save file. Start a new one to keep playing." />
        <Btn variant="butter" onClick={restart}>Start a new save file</Btn>
      </div>
    );
  }

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
