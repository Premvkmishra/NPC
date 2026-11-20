import type { Quest } from "@/lib/types";
import { CATEGORY_META, PixelIcon } from "./PixelIcon";

export function QuestMeta({ quest }: { quest: Quest }) {
  return (
    <div className="flex flex-wrap gap-2 font-mono text-xs">
      <span className="ink-border bg-paper px-2 py-0.5">{quest.duration_minutes} min</span>
      <span className="ink-border bg-paper px-2 py-0.5">{quest.cost_label}</span>
      <span className="ink-border bg-butter px-2 py-0.5 font-bold">+{quest.xp_reward} XP</span>
    </div>
  );
}

export function QuestCard({ quest, featured = false, children }: { quest: Quest; featured?: boolean; children?: React.ReactNode }) {
  const c = CATEGORY_META[quest.category];
  return (
    <article className="relative animate-pop ink-border bg-card shadow-hard">
      <div className={`flex items-center justify-between border-b-[3px] border-ink ${c.bg} px-3 py-2`}>
        <span className="flex items-center gap-2 hud-label"><PixelIcon name={quest.category} size={16} />{c.label}</span>
        <span className="hud-label">{quest.difficulty}</span>
      </div>
      {featured && <span className="absolute right-20 -top-3 rotate-[-4deg] ink-border bg-rose px-2 py-0.5 hud-label">Today</span>}
      <div className="space-y-3 p-4">
        <h3 className={featured ? "text-2xl leading-tight" : "text-lg leading-tight"}>{quest.title}</h3>
        {featured && <p className="text-sm">{quest.description}</p>}
        <QuestMeta quest={quest} />
        {quest.status === "active" && <span className="inline-block rotate-[-2deg] ink-border bg-teal px-2 py-0.5 hud-label">In progress</span>}
      </div>
      {children && <div className="perforated bg-paper-deep p-3">{children}</div>}
    </article>
  );
}
