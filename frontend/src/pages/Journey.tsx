import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { CATEGORIES, CATEGORY_META, PixelIcon } from "@/components/PixelIcon";
import { EmptyState, ErrorState, LoadingState } from "@/components/States";

function Stat({ label, value }: { label: string; value: number }) {
  return <div className="ink-border bg-card p-3"><p className="hud-label text-muted-foreground">{label}</p><p className="font-mono text-3xl font-bold">{value}</p></div>;
}

export function Journey() {
  const j = useQuery({ queryKey: ["journey"], queryFn: () => api.journey() });
  const r = useQuery({ queryKey: ["recap"], queryFn: () => api.weeklyRecap() });
  if (j.isPending) return <LoadingState label="Opening your passport" />;
  if (j.isError) return <ErrorState error={j.error} onRetry={() => j.refetch()} />;
  const { player, achievements, journal, category_counts } = j.data;
  const maxCount = Math.max(1, ...Object.values(category_counts));

  return (
    <>
      <h1 className="text-3xl">My journey</h1>
      <section className="grid grid-cols-2 gap-3">
        <Stat label="Level" value={player.level} /><Stat label="Total XP" value={player.total_xp} />
        <Stat label="Quests" value={player.quests_completed} /><Stat label="Badges" value={player.achievements_unlocked} />
      </section>

      <section className="space-y-2 ink-border bg-card p-4 shadow-hard">
        <h2 className="text-lg">Quest types</h2>
        {CATEGORIES.map((c) => (
          <div key={c} className="flex items-center gap-2">
            <span className="flex w-28 items-center gap-1.5 hud-label"><PixelIcon name={c} size={14} />{CATEGORY_META[c].label}</span>
            <div className="flex flex-1 gap-0.5">{Array.from({ length: maxCount }, (_, i) => <div key={i} className={`h-4 flex-1 border-2 border-ink ${i < category_counts[c] ? CATEGORY_META[c].bg : "bg-paper"}`} />)}</div>
            <span className="w-6 text-right font-mono text-xs">{category_counts[c]}</span>
          </div>
        ))}
      </section>

      <section className="space-y-2">
        <h2 className="text-xl">Weekly recap</h2>
        {r.isPending ? <LoadingState /> : r.isError ? <ErrorState error={r.error} onRetry={() => r.refetch()} /> : (
          <div className="ink-border bg-butter p-4 shadow-hard">
            <p className="hud-label">{new Date(r.data.week_start).toLocaleDateString()} – {new Date(r.data.week_end).toLocaleDateString()}</p>
            <p className="mt-2 font-pixel text-lg leading-snug">{r.data.summary}</p>
            <div className="mt-3 grid grid-cols-3 gap-2 text-center font-mono">
              <div className="ink-border bg-card p-1"><p className="text-xl font-bold">{r.data.stats.quests_completed}</p><p className="text-[10px] uppercase">quests</p></div>
              <div className="ink-border bg-card p-1"><p className="text-xl font-bold">{r.data.stats.new_places}</p><p className="text-[10px] uppercase">new places</p></div>
              <div className="ink-border bg-card p-1"><p className="text-xl font-bold">{r.data.stats.xp_earned}</p><p className="text-[10px] uppercase">xp</p></div>
            </div>
          </div>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-xl">Passport</h2>
        {journal.length === 0 ? <EmptyState text="No stamps yet. Every page starts blank." /> : (
          <div className="ink-border bg-card ruled-bg shadow-hard">
            {journal.map((e, i) => (
              <article key={e.quest_id} className="flex gap-3 border-b-2 border-dashed border-ink p-4 last:border-b-0">
                <div className={`flex h-16 w-16 shrink-0 flex-col items-center justify-center rounded-full border-[3px] border-double border-ink ${CATEGORY_META[e.category].bg} ${i % 2 ? "rotate-6" : "-rotate-6"}`}>
                  <PixelIcon name={e.category} size={18} /><span className="font-mono text-[10px] font-bold">+{e.xp_earned}</span>
                </div>
                <div className="min-w-0 flex-1 space-y-1">
                  <h3 className="text-base leading-tight">{e.title}</h3>
                  <p className="font-mono text-[11px]">{new Date(e.completed_at).toLocaleDateString()}{e.location_name ? ` · ${e.location_name}` : ""}</p>
                  {e.reflection && <p className="text-sm italic">“{e.reflection}”</p>}
                  {e.photo_url && <img src={e.photo_url} alt={`Photo from ${e.title}`} className="mt-1 max-h-40 w-full rotate-1 border-[3px] border-ink object-cover" />}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-xl">Achievements</h2>
        <div className="grid grid-cols-2 gap-3">
          {achievements.map((a) => (
            <div key={a.id} className={`p-3 ${a.unlocked ? "ink-border bg-butter shadow-hard-sm" : "border-[3px] border-dashed border-ink bg-transparent opacity-70"}`}>
              <PixelIcon name={a.unlocked ? a.icon_key : "lock"} size={24} />
              <p className="mt-1 font-pixel leading-tight">{a.unlocked ? a.name : "???"}</p>
              <p className="text-xs">{a.description}</p>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
