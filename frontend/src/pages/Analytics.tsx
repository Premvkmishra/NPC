import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Link } from "@tanstack/react-router";
import {
  SECONDS_PER_REEL,
  computeRewardStats,
  computeStats,
  formatDuration,
  type Stats,
} from "@/lib/analytics";
import type { Autopilot } from "@/lib/types";
import { CATEGORIES, CATEGORY_META, PixelIcon } from "@/components/PixelIcon";
import { DialogueBox } from "@/components/DialogueBox";
import { SamplePlayerButton } from "@/components/SamplePlayer";
import { ErrorState, LoadingState } from "@/components/States";

const n = (v: number) => v.toLocaleString("en-IN");

function Card({
  title,
  children,
  className = "bg-card",
}: {
  title: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`space-y-3 ink-border p-4 shadow-hard ${className}`}>
      <h2 className="text-lg leading-none">{title}</h2>
      {children}
    </section>
  );
}

function Tile({
  icon,
  label,
  value,
  note,
}: {
  icon: string;
  label: string;
  value: string;
  note?: string | undefined;
}) {
  return (
    <div className="ink-border bg-card p-3">
      <p className="flex items-center gap-1.5 hud-label text-muted-foreground">
        <PixelIcon name={icon} size={12} />
        {label}
      </p>
      <p className="mt-1 font-mono text-2xl font-bold leading-none">{value}</p>
      {note && <p className="mt-1 text-xs">{note}</p>}
    </div>
  );
}

/** Columns that share one hue; the value is in the tooltip and accessible label. */
function Columns({
  items,
  height = 96,
}: {
  items: { label: string; value: number; tip: string; highlight?: boolean }[];
  height?: number;
}) {
  const max = Math.max(1, ...items.map((i) => i.value));
  const twoLine = items.some((i) => i.label.includes("\n"));
  return (
    <div className="space-y-1">
      {/* Bars share one baseline; labels live in their own row so wrapping can't shift a bar. */}
      <div className="flex items-end gap-1.5 border-b-2 border-ink" style={{ height: height + 16 }}>
        {items.map((i, idx) => (
          <div
            key={idx}
            className="flex flex-1 flex-col items-center justify-end gap-0.5"
            title={i.tip}
            aria-label={i.tip}
            role="img"
          >
            <span className="font-mono text-[10px] leading-none">{i.value}</span>
            <div
              className={`w-full border-2 border-b-0 border-ink ${i.highlight ? "bg-lime" : "bg-butter"}`}
              style={{ height: i.value ? Math.max(6, (i.value / max) * height) : 0 }}
            />
          </div>
        ))}
      </div>
      <div className={`flex gap-1.5 ${twoLine ? "h-6" : "h-3"}`} aria-hidden>
        {items.map((i, idx) => (
          <span
            key={idx}
            className="flex-1 whitespace-pre-line text-center hud-label text-[9px] leading-tight text-muted-foreground"
          >
            {i.label}
          </span>
        ))}
      </div>
    </div>
  );
}

function AutopilotShift({ start, now }: { start: Autopilot; now: Autopilot }) {
  const drop = start.score - now.score;
  const Row = ({ label, a }: { label: string; a: Autopilot }) => (
    <div className="space-y-1">
      <div className="flex justify-between hud-label">
        <span>
          {label} · {a.label}
        </span>
        <span className="font-mono">{a.score}</span>
      </div>
      <div className="h-4 border-2 border-ink bg-paper">
        <div className="h-full bg-ink" style={{ width: `${a.score}%` }} />
      </div>
    </div>
  );
  return (
    <Card title="Autopilot, then vs now">
      <Row label="When you joined" a={start} />
      <Row label="Today" a={now} />
      <p className="text-sm">
        {drop > 0
          ? `Down ${drop} points. Lower means fewer days on repeat.`
          : drop < 0
            ? `Up ${-drop} points. One small quest nudges it back down.`
            : "Holding steady. One small quest nudges it down."}
      </p>
      <p className="text-[11px] text-muted-foreground">{now.disclaimer}</p>
    </Card>
  );
}

function CategoryMix({ s }: { s: Stats }) {
  const total = Math.max(1, s.quests);
  const used = CATEGORIES.filter((c) => s.categories[c].quests > 0);
  return (
    <Card title="Quest mix">
      <div
        className="flex h-6 gap-0.5 border-2 border-ink bg-ink"
        role="img"
        aria-label={used
          .map((c) => `${CATEGORY_META[c].label} ${s.categories[c].quests}`)
          .join(", ")}
      >
        {used.map((c) => (
          <div
            key={c}
            className={CATEGORY_META[c].bg}
            style={{ width: `${(s.categories[c].quests / total) * 100}%` }}
            title={`${CATEGORY_META[c].label}: ${s.categories[c].quests} quests · ${formatDuration(s.categories[c].minutes)}`}
          />
        ))}
      </div>
      <ul className="space-y-1.5">
        {CATEGORIES.map((c) => (
          <li key={c} className="flex items-center gap-2 text-sm">
            <span
              className={`flex h-6 w-6 items-center justify-center border-2 border-ink ${CATEGORY_META[c].bg}`}
            >
              <PixelIcon name={c} size={12} />
            </span>
            <span className="flex-1">{CATEGORY_META[c].label}</span>
            <span className="font-mono text-xs">
              {s.categories[c].quests} · {formatDuration(s.categories[c].minutes)}
            </span>
          </li>
        ))}
      </ul>
      {s.topCategory && (
        <p className="text-sm">
          Your go-to: <b>{CATEGORY_META[s.topCategory].label}</b>.
        </p>
      )}
    </Card>
  );
}

function Places({ s }: { s: Stats }) {
  if (!s.places.length) return null;
  return (
    <Card title={`Places you've been (${s.places.length})`}>
      <ol className="divide-y-2 divide-dashed divide-ink">
        {s.places.slice(0, 8).map((p) => (
          <li key={p.name} className="flex items-center gap-3 py-2">
            <span
              className={`flex h-8 w-8 shrink-0 items-center justify-center border-2 border-ink ${CATEGORY_META[p.category].bg}`}
            >
              <PixelIcon name="pin" size={14} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate font-semibold leading-tight">{p.name}</p>
              <p className="truncate font-mono text-[11px]">
                {[p.address, p.distance_km != null ? `${p.distance_km} km` : null]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            </div>
            <span className="shrink-0 font-mono text-xs">{p.visits}×</span>
          </li>
        ))}
      </ol>
      {s.places.length > 8 && (
        <p className="text-xs">+{s.places.length - 8} more in your passport.</p>
      )}
    </Card>
  );
}

/** Vouchers redeemed with XP. Shares the Rewards page's query, so a redemption there shows up here. */
function RewardsEarned() {
  const q = useQuery({ queryKey: ["rewards"], queryFn: () => api.listRewards() });
  if (q.isPending) return <LoadingState label="Counting your rewards" />;
  if (q.isError) return null; // Rewards are a bonus; don't block the rest of the stats.
  const r = computeRewardStats(q.data);
  return (
    <Card title="Rewards earned" className="bg-orange">
      <div className="grid grid-cols-3 gap-2 text-center">
        {[
          { label: "Vouchers", value: n(r.redeemed) },
          { label: "Saved", value: `₹${n(r.savedInr)}` },
          { label: "XP spent", value: n(r.xpSpent) },
        ].map((t) => (
          <div key={t.label} className="border-2 border-ink bg-card p-2">
            <p className="font-mono text-xl font-bold leading-none">{t.value}</p>
            <p className="hud-label text-[9px]">{t.label}</p>
          </div>
        ))}
      </div>
      {r.recent.length > 0 && (
        <ul className="divide-y-2 divide-dashed divide-ink border-2 border-ink bg-card px-3">
          {r.recent.map((x) => (
            <li key={x.id} className="flex items-center justify-between gap-2 py-2 text-sm">
              <span className="min-w-0 truncate">
                <b>{x.brand}</b> · {new Date(x.redeemed_at).toLocaleDateString(undefined, { day: "numeric", month: "short" })}
              </span>
              <span className="shrink-0 font-mono text-xs">₹{x.discount_inr} off</span>
            </li>
          ))}
        </ul>
      )}
      <p className="text-sm">
        <b>{n(r.balance)} XP</b> to spend.{" "}
        {r.affordable > 0
          ? `Enough for ${r.affordable} reward${r.affordable > 1 ? "s" : ""} right now.`
          : r.next
            ? `${n(r.next.cost_xp - r.balance)} XP more unlocks ${r.next.brand}.`
            : ""}
      </p>
      <Link to="/rewards" className="block min-h-11 ink-border btn-press bg-card px-4 py-2 text-center font-pixel uppercase tracking-wider">
        {r.redeemed ? "Browse rewards" : "Redeem your first reward"}
      </Link>
    </Card>
  );
}

export function Analytics() {
  const q = useQuery({ queryKey: ["analytics"], queryFn: () => api.analytics() });
  if (q.isPending) return <LoadingState label="Crunching your adventures" />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const s = computeStats(q.data);

  if (!s.quests) {
    return (
      <>
        <h1 className="text-3xl">My stats</h1>
        <DialogueBox text="No quests completed yet, so there's nothing to chart. Finish one and this page starts filling in." />
        <div className="space-y-2 ink-border border-dashed bg-card/60 p-4">
          <p className="text-sm">
            Want to see what it looks like with two months of adventures? This replaces your current
            save on this device.
          </p>
          <SamplePlayerButton label="Load a sample player" variant="butter" />
        </div>
      </>
    );
  }

  const trend = s.recentPerWeek - s.previousPerWeek;

  return (
    <>
      <div>
        <h1 className="text-3xl">My stats</h1>
        <p className="text-sm">
          {q.data.player.display_name} · {s.daysSinceFirst} days since your first quest
        </p>
      </div>

      <section className="ink-border bg-lime p-4 shadow-hard">
        <p className="hud-label">Time reclaimed from the scroll</p>
        <p className="mt-1 font-pixel text-5xl leading-none">{formatDuration(s.minutesOffline)}</p>
        <p className="mt-2 text-sm">
          Out in the world instead of on your phone. That's about <b>{n(s.reelsSkipped)} reels</b>{" "}
          you didn't scroll.
        </p>
        <p className="mt-2 text-[11px]">
          Estimated from quest durations, at ~{SECONDS_PER_REEL}s a reel.
        </p>
      </section>

      <section className="grid grid-cols-2 gap-3">
        <Tile
          icon="star"
          label="New activities"
          value={n(s.newActivities)}
          note={`${s.quests} quests done`}
        />
        <Tile
          icon="pin"
          label="Places visited"
          value={n(s.places.length)}
          note={s.farthestPlace ? `Farthest: ${s.farthestPlace.distance_km} km` : undefined}
        />
        <Tile
          icon="map"
          label="Km explored"
          value={n(s.kmTravelled)}
          note="Round trips to quest spots"
        />
        <Tile
          icon="heart"
          label="Spent"
          value={`₹${n(s.spentInr)}`}
          note={`${s.freeQuests} quests were free`}
        />
        <Tile
          icon="clock"
          label="Active days"
          value={n(s.activeDays)}
          note={`${s.recentPerWeek}/week lately`}
        />
        <Tile
          icon="crown"
          label="XP earned"
          value={n(s.xp)}
          note={`Level ${q.data.player.level}`}
        />
      </section>

      <AutopilotShift start={q.data.autopilot_start} now={q.data.autopilot_now} />

      <Card title="Quests per week">
        <Columns
          items={s.weeks.map((w, i) => ({
            label:
              i === s.weeks.length - 1
                ? "This\nweek"
                : `${w.start.getDate()}\n${w.start.toLocaleDateString(undefined, { month: "short" }).slice(0, 3)}`,
            value: w.quests,
            highlight: i === s.weeks.length - 1,
            tip: `Week of ${w.start.toLocaleDateString()}: ${w.quests} quests, ${formatDuration(w.minutes)} offline`,
          }))}
        />
        <p className="text-sm">
          {trend > 0
            ? `Up from ${s.previousPerWeek} to ${s.recentPerWeek} quests a week over the last month.`
            : trend < 0
              ? `${s.recentPerWeek} a week lately, down from ${s.previousPerWeek}. Quiet weeks count too.`
              : `A steady ${s.recentPerWeek} quests a week.`}
        </p>
      </Card>

      <RewardsEarned />
      <CategoryMix s={s} />
      <Places s={s} />

      <Card title="How you play" className="bg-butter">
        <div className="grid grid-cols-3 gap-2 text-center">
          {(["easy", "medium", "hard"] as const).map((d) => (
            <div key={d} className="border-2 border-ink bg-card p-2">
              <p className="font-mono text-xl font-bold leading-none">{s.difficulty[d]}</p>
              <p className="hud-label text-[9px]">{d}</p>
            </div>
          ))}
        </div>
        <ul className="space-y-1 text-sm">
          {s.followThrough != null && (
            <li>
              Follow-through: <b>{s.followThrough}%</b> of quests you decided on were completed, not
              skipped.
            </li>
          )}
          <li>
            Reflections written: <b>{s.reflections}</b> of {s.quests}
          </li>
          <li>
            Photos added: <b>{s.photos}</b>
          </li>
          {q.data.quests_open > 0 && (
            <li>
              Open quests waiting: <b>{q.data.quests_open}</b>
            </li>
          )}
        </ul>
      </Card>
    </>
  );
}
