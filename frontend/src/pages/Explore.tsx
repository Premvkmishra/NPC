import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { api } from "@/lib/api";
import type { Category } from "@/lib/types";
import { CATEGORIES, CATEGORY_META, PixelIcon } from "@/components/PixelIcon";
import { QuestCard } from "@/components/QuestCard";
import { ExperienceCard } from "@/components/ExperienceCard";
import { Btn } from "@/components/Btn";
import { EmptyState, ErrorState, LoadingState } from "@/components/States";

const TAGS = ["bookstore", "gallery", "workshop", "food", "free events", "street art"];

export function Explore() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [cat, setCat] = useState<Category | undefined>();
  const [tag, setTag] = useState<string | undefined>();
  const [text, setText] = useState("");
  const [search, setSearch] = useState("");
  const quests = useQuery({ queryKey: ["quests", cat ?? "all"], queryFn: () => api.listQuests(cat ? { category: cat } : {}) });
  const exps = useQuery({ queryKey: ["experiences", tag ?? "", search], queryFn: () => api.listExperiences({ ...(tag ? { tag } : {}), ...(search ? { q: search } : {}) }) });
  const roll = useMutation({ mutationFn: () => api.generateQuest({ category: cat ?? null }), onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["quests"] }); navigate({ to: "/quest/$id", params: { id: r.quest.id } }); } });
  const toQuest = useMutation({ mutationFn: (id: string) => api.questFromExperience(id), onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["quests"] }); navigate({ to: "/quest/$id", params: { id: r.quest.id } }); } });

  const chip = (on: boolean, bg: string) => `min-h-11 shrink-0 ink-border px-3 hud-label flex items-center gap-1.5 ${on ? `${bg} translate-y-0.5` : "bg-card shadow-hard-sm"}`;

  return (
    <>
      <section className="space-y-3">
        <h1 className="text-3xl">Quest board</h1>
        <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-2">
          <button className={chip(!cat, "bg-ink text-paper")} aria-pressed={!cat} onClick={() => setCat(undefined)}>All</button>
          {CATEGORIES.map((c) => (
            <button key={c} aria-pressed={cat === c} className={chip(cat === c, CATEGORY_META[c].bg)} onClick={() => setCat(c)}>
              <PixelIcon name={c} size={14} />{CATEGORY_META[c].label}
            </button>
          ))}
        </div>
        <Btn variant="butter" className="w-full" disabled={roll.isPending} onClick={() => roll.mutate()}>{roll.isPending ? "Rolling…" : "Roll a new one"}</Btn>
        {roll.isError && <ErrorState error={roll.error} />}
        {quests.isPending ? <LoadingState label="Pinning scrolls" /> : quests.isError ? <ErrorState error={quests.error} onRetry={() => quests.refetch()} /> :
          quests.data.quests.length === 0 ? <EmptyState text="The board is empty here. Roll a new one?" /> :
          <div className="space-y-4">{quests.data.quests.map((q, i) => (
            <Link key={q.id} to="/quest/$id" params={{ id: q.id }} className={`block ${i % 2 ? "rotate-[0.6deg]" : "rotate-[-0.6deg]"}`}><QuestCard quest={q} /></Link>
          ))}</div>}
      </section>

      <section className="space-y-3 border-t-[3px] border-dashed border-ink pt-5">
        <h2 className="text-2xl">Discovered near you</h2>
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); setSearch(text.trim()); }}>
          <input aria-label="Search places" value={text} onChange={(e) => setText(e.target.value)} placeholder="Search chai, pottery…" className="min-h-11 flex-1 ink-border bg-card px-3 font-mono text-sm" />
          <Btn variant="ink" type="submit">Go</Btn>
        </form>
        <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-2">
          {TAGS.map((t) => <button key={t} aria-pressed={tag === t} className={chip(tag === t, "bg-teal")} onClick={() => setTag(tag === t ? undefined : t)}>{t}</button>)}
        </div>
        {exps.isPending ? <LoadingState label="Scouting the neighbourhood" /> : exps.isError ? <ErrorState error={exps.error} onRetry={() => exps.refetch()} /> :
          exps.data.experiences.length === 0 ? <EmptyState text="Nothing found nearby for that. Try another tag?" /> :
          <div className="space-y-4">{exps.data.experiences.map((e) => (
            <ExperienceCard key={e.id} exp={e} busy={toQuest.isPending && toQuest.variables === e.id} onQuest={() => toQuest.mutate(e.id)} />
          ))}</div>}
        {toQuest.isError && <ErrorState error={toQuest.error} />}
      </section>
    </>
  );
}
