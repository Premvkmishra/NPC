import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CompleteResponse, Quest } from "@/lib/types";
import { CATEGORY_META, PixelIcon } from "@/components/PixelIcon";
import { QuestMeta } from "@/components/QuestCard";
import { DialogueBox } from "@/components/DialogueBox";
import { Btn } from "@/components/Btn";
import { StampModal } from "@/components/StampModal";
import { ErrorState, LoadingState } from "@/components/States";

const SRC = { google_maps: "Google Maps", google_events: "Google Events", google_search: "Google Search" } as const;

async function compress(file: File): Promise<string> {
  const url = URL.createObjectURL(file);
  const img = await new Promise<HTMLImageElement>((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = url; });
  let max = 1600; let q = 0.82; let out = "";
  for (let k = 0; k < 6; k++) {
    const scale = Math.min(1, max / Math.max(img.width, img.height));
    const c = document.createElement("canvas"); c.width = Math.round(img.width * scale); c.height = Math.round(img.height * scale);
    c.getContext("2d")!.drawImage(img, 0, 0, c.width, c.height);
    out = c.toDataURL("image/jpeg", q);
    if (out.length * 0.75 < 1.5e6) break;
    max *= 0.75; q -= 0.08;
  }
  URL.revokeObjectURL(url);
  return out;
}

function CompleteForm({ quest, onDone }: { quest: Quest; onDone: (r: CompleteResponse) => void }) {
  const qc = useQueryClient();
  const [reflection, setReflection] = useState("");
  const [photo, setPhoto] = useState<string | null>(null);
  const [photoErr, setPhotoErr] = useState("");
  const m = useMutation({
    mutationFn: () => api.completeQuest(quest.id, { reflection, photo_data_url: photo }),
    onSuccess: (r) => { qc.setQueryData(["quest", quest.id], { quest: r.quest }); qc.invalidateQueries({ queryKey: ["home"] }); qc.invalidateQueries({ queryKey: ["journey"] }); qc.invalidateQueries({ queryKey: ["recap"] }); qc.invalidateQueries({ queryKey: ["quests"] }); onDone(r); },
  });
  return (
    <form className="space-y-3 ink-border bg-card p-4 shadow-hard" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
      <label className="block space-y-1">
        <span className="font-pixel text-lg">{quest.reflection_prompt}</span>
        <textarea required maxLength={500} rows={4} value={reflection} onChange={(e) => setReflection(e.target.value)} className="w-full ink-border bg-paper p-2 text-sm" />
        <span className="block text-right font-mono text-[11px]">{reflection.length}/500</span>
      </label>
      <label className="block space-y-1">
        <span className="hud-label">Photo (optional)</span>
        <input type="file" accept="image/*" className="block w-full text-sm file:mr-3 file:min-h-11 file:ink-border file:bg-butter file:px-3 file:font-pixel"
          onChange={async (e) => { const f = e.target.files?.[0]; setPhotoErr(""); if (!f) return setPhoto(null); try { setPhoto(await compress(f)); } catch { setPhotoErr("That image wouldn't load. Try another?"); } }} />
        <span className="block text-xs text-muted-foreground">Photos are optional evidence, not proof.</span>
      </label>
      {photoErr && <p className="text-xs">{photoErr}</p>}
      {photo && <div className="relative"><img src={photo} alt="Your quest photo preview" className="max-h-48 w-full ink-border object-cover" /><button type="button" onClick={() => setPhoto(null)} className="absolute right-2 top-2 ink-border bg-card px-2 hud-label">Remove</button></div>}
      {m.isError && <ErrorState error={m.error} />}
      <Btn type="submit" className="w-full" disabled={m.isPending || !reflection.trim()}>{m.isPending ? "Stamping…" : "Complete quest"}</Btn>
    </form>
  );
}

export function QuestDetails({ id }: { id: string }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["quest", id], queryFn: () => api.getQuest(id) });
  const [result, setResult] = useState<CompleteResponse | null>(null);
  const start = useMutation({ mutationFn: () => api.startQuest(id), onSuccess: (r) => { qc.setQueryData(["quest", id], r); qc.invalidateQueries({ queryKey: ["home"] }); } });

  if (q.isPending) return <LoadingState label="Unrolling the scroll" />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const quest = q.data.quest;
  const c = CATEGORY_META[quest.category];

  return (
    <>
      {result && <StampModal result={result} onClose={() => setResult(null)} />}
      <article className="ink-border bg-card shadow-hard">
        <div className={`flex items-center justify-between border-b-[3px] border-ink ${c.bg} px-4 py-2`}>
          <span className="flex items-center gap-2 hud-label"><PixelIcon name={quest.category} size={18} />{c.label}</span>
          <span className="hud-label">{quest.difficulty}</span>
        </div>
        <div className="space-y-3 p-4">
          <h1 className="text-3xl leading-tight">{quest.title}</h1>
          <QuestMeta quest={quest} />
          <p>{quest.description}</p>
        </div>
      </article>
      <DialogueBox speaker="Why NPC picked this" text={quest.why_selected} typewriter />
      {quest.location && (
        <section className="flex items-start gap-3 ink-border bg-card p-3">
          <PixelIcon name="pin" size={24} />
          <div className="flex-1 text-sm">
            <p className="font-semibold">{quest.location.name}</p>
            {quest.location.address && <p>{quest.location.address}</p>}
            {quest.location.distance_km != null && <p className="font-mono text-xs">{quest.location.distance_km} km away</p>}
            {quest.location.maps_url && <a className="text-sm underline" href={quest.location.maps_url} target="_blank" rel="noreferrer">Open in Maps ↗</a>}
          </div>
        </section>
      )}
      {quest.source && (
        <p className="text-xs"><span className="rotate-[-2deg] inline-block border-2 border-dashed border-ink px-1.5 hud-label">via {SRC[quest.source.type]}</span>{" "}
          {quest.source.url ? <a href={quest.source.url} target="_blank" rel="noreferrer" className="underline">{quest.source.title}</a> : quest.source.title}</p>
      )}
      {quest.status === "suggested" && <>
        <Btn className="w-full text-lg" disabled={start.isPending} onClick={() => start.mutate()}>{start.isPending ? "Starting…" : "Start quest"}</Btn>
        {start.isError && <ErrorState error={start.error} />}
      </>}
      {quest.status === "active" && <CompleteForm quest={quest} onDone={setResult} />}
      {quest.status === "completed" && (
        <div className="relative ink-border bg-card p-6 text-center">
          <span className="inline-block rotate-[-8deg] border-[5px] border-double border-ink px-4 py-2 font-pixel text-2xl">COMPLETED</span>
          {quest.completed_at && <p className="mt-3 font-mono text-xs">{new Date(quest.completed_at).toLocaleDateString()}</p>}
        </div>
      )}
      {quest.status === "dismissed" && <DialogueBox speaker="Resting" text="You skipped this one. No penalty. It'll be here if you change your mind." />}
    </>
  );
}
