import type { AnalyticsResponse, Category, Difficulty } from "./types";

/** Rough average time per short-video swipe, used only for the playful "reels not scrolled" figure. */
export const SECONDS_PER_REEL = 30;
const DAY = 864e5;
const CATS: Category[] = ["explore", "social", "creativity", "courage", "awareness"];

export type TimeOfDay = "morning" | "afternoon" | "evening" | "night";
export const TIME_OF_DAY: { key: TimeOfDay; label: string; hours: string }[] = [
  { key: "morning", label: "Morning", hours: "5–12" },
  { key: "afternoon", label: "Afternoon", hours: "12–17" },
  { key: "evening", label: "Evening", hours: "17–21" },
  { key: "night", label: "Night", hours: "21–5" },
];
export const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export interface PlaceStat {
  name: string;
  address: string | null;
  distance_km: number | null;
  visits: number;
  last_visit: string;
  category: Category;
}
export interface WeekStat {
  start: Date;
  quests: number;
  minutes: number;
}

export interface Stats {
  quests: number;
  minutesOffline: number;
  reelsSkipped: number;
  newActivities: number;
  places: PlaceStat[];
  kmTravelled: number;
  farthestPlace: PlaceStat | null;
  spentInr: number;
  freeQuests: number;
  xp: number;
  categories: Record<Category, { quests: number; minutes: number }>;
  topCategory: Category | null;
  difficulty: Record<Difficulty, number>;
  weeks: WeekStat[];
  timeOfDay: Record<TimeOfDay, number>;
  weekdays: number[];
  activeDays: number;
  daysSinceFirst: number;
  recentPerWeek: number;
  previousPerWeek: number;
  followThrough: number | null;
  reflections: number;
  photos: number;
}

function timeOfDay(d: Date): TimeOfDay {
  const h = d.getHours();
  if (h >= 5 && h < 12) return "morning";
  if (h >= 12 && h < 17) return "afternoon";
  if (h >= 17 && h < 21) return "evening";
  return "night";
}

/** Monday 00:00 local of the week containing d. */
function weekStart(d: Date): Date {
  const s = new Date(d);
  s.setHours(0, 0, 0, 0);
  s.setDate(s.getDate() - ((s.getDay() + 6) % 7));
  return s;
}

/** Turn the raw per-quest facts into the numbers the analytics tab shows. Uses the device's local time. */
export function computeStats(data: AnalyticsResponse, now = new Date(), weeksShown = 8): Stats {
  const e = data.entries;
  const minutesOffline = e.reduce((a, x) => a + x.duration_minutes, 0);

  const placeMap = new Map<string, PlaceStat>();
  for (const x of [...e].sort((a, b) => a.completed_at.localeCompare(b.completed_at))) {
    if (!x.location?.name) continue;
    const p = placeMap.get(x.location.name);
    if (p) {
      p.visits += 1;
      p.last_visit = x.completed_at;
      p.category = x.category;
    } else
      placeMap.set(x.location.name, {
        name: x.location.name,
        address: x.location.address,
        distance_km: x.location.distance_km,
        visits: 1,
        last_visit: x.completed_at,
        category: x.category,
      });
  }
  const places = [...placeMap.values()].sort(
    (a, b) => b.visits - a.visits || b.last_visit.localeCompare(a.last_visit),
  );
  const withDistance = places.filter((p) => p.distance_km != null);
  const farthestPlace = withDistance.length
    ? withDistance.reduce((a, b) => (b.distance_km! > a.distance_km! ? b : a))
    : null;
  // Round trips from home, for every visit with a known distance.
  const kmTravelled = e.reduce((a, x) => a + (x.location?.distance_km ?? 0) * 2, 0);

  const categories = Object.fromEntries(
    CATS.map((c) => [c, { quests: 0, minutes: 0 }]),
  ) as Stats["categories"];
  const difficulty: Record<Difficulty, number> = { easy: 0, medium: 0, hard: 0 };
  const tod: Record<TimeOfDay, number> = { morning: 0, afternoon: 0, evening: 0, night: 0 };
  const weekdays = [0, 0, 0, 0, 0, 0, 0];
  const days = new Set<string>();
  for (const x of e) {
    categories[x.category].quests += 1;
    categories[x.category].minutes += x.duration_minutes;
    difficulty[x.difficulty] += 1;
    const d = new Date(x.completed_at);
    tod[timeOfDay(d)] += 1;
    weekdays[(d.getDay() + 6) % 7]! += 1;
    days.add(d.toDateString());
  }
  const topCategory = e.length
    ? CATS.reduce((a, b) => (categories[b].quests > categories[a].quests ? b : a))
    : null;

  const thisWeek = weekStart(now);
  const weeks: WeekStat[] = Array.from({ length: weeksShown }, (_, i) => {
    const start = new Date(thisWeek);
    start.setDate(start.getDate() - (weeksShown - 1 - i) * 7);
    return { start, quests: 0, minutes: 0 };
  });
  for (const x of e) {
    const ws = weekStart(new Date(x.completed_at)).getTime();
    const w = weeks.find((k) => k.start.getTime() === ws);
    if (w) {
      w.quests += 1;
      w.minutes += x.duration_minutes;
    }
  }

  const since = (days: number) =>
    e.filter((x) => now.getTime() - Date.parse(x.completed_at) < days * DAY).length;
  const last28 = since(28);
  const prev28 = since(56) - last28;
  const first = e.length ? Math.min(...e.map((x) => Date.parse(x.completed_at))) : null;
  const decided = e.length + data.quests_dismissed;

  return {
    quests: e.length,
    minutesOffline,
    reelsSkipped: Math.round((minutesOffline * 60) / SECONDS_PER_REEL),
    newActivities: new Set(e.map((x) => x.title.trim().toLowerCase())).size,
    places,
    kmTravelled: Math.round(kmTravelled * 10) / 10,
    farthestPlace,
    spentInr: e.reduce((a, x) => a + (x.estimated_cost_inr ?? 0), 0),
    freeQuests: e.filter((x) => x.estimated_cost_inr === 0).length,
    xp: e.reduce((a, x) => a + x.xp_earned, 0),
    categories,
    topCategory,
    difficulty,
    weeks,
    timeOfDay: tod,
    weekdays,
    activeDays: days.size,
    daysSinceFirst: first == null ? 0 : Math.max(1, Math.ceil((now.getTime() - first) / DAY)),
    recentPerWeek: Math.round((last28 / 4) * 10) / 10,
    previousPerWeek: Math.round((prev28 / 4) * 10) / 10,
    followThrough: decided ? Math.round((e.length / decided) * 100) : null,
    reflections: e.filter((x) => x.has_reflection).length,
    photos: e.filter((x) => x.has_photo).length,
  };
}

export function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60),
    m = minutes % 60;
  return h ? (m ? `${h}h ${m}m` : `${h}h`) : `${m}m`;
}
