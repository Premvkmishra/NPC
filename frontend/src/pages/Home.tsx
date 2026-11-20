import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { api } from "@/lib/api";
import type { Player } from "@/lib/types";
import { AutopilotMeter } from "@/components/AutopilotMeter";
import { XpBar } from "@/components/XpBar";
import { QuestCard } from "@/components/QuestCard";
import { Btn } from "@/components/Btn";
import { EmptyState, ErrorState, LoadingState } from "@/components/States";

const LINES = ["A quiet day is not a failed day.", "Tiny counts. Tiny is the whole point.", "No streaks here. Just stories.", "Curiosity doesn't expire.", "You can always come back tomorrow."];

export function PlayerCard({ player }: { player: Player }) {
  return (
    <section className="ink-border bg-card p-4 shadow-hard">
      <div className="flex items-end justify-between">
        <div><p className="hud-label text-muted-foreground">Player</p><h2 className="text-2xl leading-none">{player.display_name}</h2></div>
        <div className="ink-border bg-ink px-3 py-1 text-right text-paper"><p className="hud-label">Level</p><p className="font-mono text-2xl font-bold leading-none">{player.level}</p></div>
      </div>
      <div className="mt-3"><XpBar value={player.xp_in_level} max={player.xp_for_next_level} /></div>
      <p className="mt-1 text-right font-mono text-xs">{player.xp_in_level} / {player.xp_for_next_level} XP</p>
    </section>
  );
}

export function Home() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const q = useQuery({ queryKey: ["home"], queryFn: () => api.home() });
  const line = useMemo(() => LINES[new Date().getDate() % LINES.length], []);
  const regen = useMutation({ mutationFn: () => api.generateQuest({ replace_today: true }), onSuccess: () => qc.invalidateQueries({ queryKey: ["home"] }) });
  const skip = useMutation({ mutationFn: (id: string) => api.dismissQuest(id), onSuccess: () => qc.invalidateQueries({ queryKey: ["home"] }) });

  if (q.isPending) return <LoadingState />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const { player, autopilot, todays_quest, recent_activity } = q.data;

  return (
    <>
      <PlayerCard player={player} />
      <AutopilotMeter autopilot={autopilot} />
      <section className="space-y-3">
        <h2 className="text-xl">Today's side quest</h2>
        {todays_quest ? (
          <QuestCard quest={todays_quest} featured>
            <Btn className="w-full" onClick={() => navigate({ to: "/quest/$id", params: { id: todays_quest.id } })}>
              {todays_quest.status === "active" ? "Continue quest" : todays_quest.status === "completed" ? "View quest" : "Start quest"}
            </Btn>
          </QuestCard>
        ) : <EmptyState text="Resting today. Roll a new challenge whenever you feel like it." />}
        <div className="grid grid-cols-2 gap-3">
          <Link to="/explore" className="flex min-h-11 items-center justify-center ink-border btn-press bg-butter px-2 font-pixel uppercase">Explore quests</Link>
          <Btn variant="orange" disabled={regen.isPending} onClick={() => regen.mutate()}>{regen.isPending ? "Rolling…" : "New challenge"}</Btn>
        </div>
        {regen.isError && <ErrorState error={regen.error} />}
        {todays_quest?.status === "suggested" && (
          <button className="min-h-11 w-full text-sm underline" disabled={skip.isPending} onClick={() => skip.mutate(todays_quest.id)}>Skip for today, no penalty</button>
        )}
      </section>
      <section className="space-y-2">
        <h2 className="text-xl">Recent activity</h2>
        {recent_activity.length === 0 ? <EmptyState text="Nothing yet. Your first stamp is waiting." /> : recent_activity.map((a) => (
          <Link key={a.quest_id} to="/quest/$id" params={{ id: a.quest_id }} className="flex items-center justify-between ink-border bg-card px-3 py-2 shadow-hard-sm">
            <span className="text-sm font-semibold">{a.title}</span><span className="font-mono text-xs font-bold">+{a.xp_earned}</span>
          </Link>
        ))}
      </section>
      <p className="text-center font-pixel text-base">“{line}”</p>
    </>
  );
}
