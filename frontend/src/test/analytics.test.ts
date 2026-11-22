import { describe, expect, it } from "vitest";
import { computeStats, formatDuration } from "@/lib/analytics";
import type { AnalyticsEntry, AnalyticsResponse, Autopilot } from "@/lib/types";

const ap: Autopilot = {
  score: 50,
  label: "Needs a little adventure",
  explanation: "",
  disclaimer: "",
};
const now = new Date(2026, 10, 22, 12); // Sun 22 Nov 2026, local
const at = (daysAgo: number, hour: number) => {
  const d = new Date(now);
  d.setDate(d.getDate() - daysAgo);
  d.setHours(hour, 0, 0, 0);
  return d.toISOString();
};
const entry = (p: Partial<AnalyticsEntry>): AnalyticsEntry => ({
  quest_id: Math.random().toString(36),
  title: "Quest",
  category: "explore",
  difficulty: "easy",
  duration_minutes: 30,
  estimated_cost_inr: 0,
  xp_earned: 50,
  completed_at: at(0, 9),
  location: null,
  has_reflection: false,
  has_photo: false,
  ...p,
});
const loc = (name: string, km: number) => ({
  name,
  address: null,
  lat: null,
  lng: null,
  distance_km: km,
  maps_url: null,
});
const data = (entries: AnalyticsEntry[], dismissed = 0): AnalyticsResponse => ({
  player: {
    id: "p",
    display_name: "T",
    city: "X",
    level: 1,
    total_xp: 0,
    xp_in_level: 0,
    xp_for_next_level: 1000,
    quests_completed: entries.length,
    achievements_unlocked: 0,
    created_at: at(60, 9),
  },
  entries,
  quests_dismissed: dismissed,
  quests_open: 0,
  autopilot_start: ap,
  autopilot_now: ap,
});

describe("computeStats", () => {
  it("handles an empty history", () => {
    const s = computeStats(data([]), now);
    expect(s.quests).toBe(0);
    expect(s.topCategory).toBeNull();
    expect(s.followThrough).toBeNull();
    expect(s.weeks).toHaveLength(8);
  });

  it("aggregates time, places, money and habits", () => {
    const s = computeStats(
      data(
        [
          entry({
            title: "Bookshop",
            duration_minutes: 45,
            location: loc("Granth", 2),
            has_reflection: true,
            completed_at: at(0, 9),
          }),
          entry({
            title: "bookshop ",
            duration_minutes: 45,
            location: loc("Granth", 2),
            completed_at: at(3, 19),
          }),
          entry({
            title: "Hike",
            category: "courage",
            difficulty: "hard",
            duration_minutes: 180,
            estimated_cost_inr: 120,
            location: loc("Kanheri", 15),
            has_photo: true,
            completed_at: at(10, 7),
          }),
          entry({
            title: "Chat",
            category: "social",
            estimated_cost_inr: null,
            completed_at: at(40, 14),
          }),
        ],
        1,
      ),
      now,
    );

    expect(s.minutesOffline).toBe(300);
    expect(s.reelsSkipped).toBe(600);
    expect(s.newActivities).toBe(3); // repeated title (case/space-insensitive) counts once
    expect(s.places.map((p) => [p.name, p.visits])).toEqual([
      ["Granth", 2],
      ["Kanheri", 1],
    ]);
    expect(s.farthestPlace?.name).toBe("Kanheri");
    expect(s.kmTravelled).toBe(38); // (2 + 2 + 15) * 2
    expect(s.spentInr).toBe(120);
    expect(s.freeQuests).toBe(2);
    expect(s.topCategory).toBe("explore");
    expect(s.difficulty).toEqual({ easy: 3, medium: 0, hard: 1 });
    expect(s.timeOfDay).toEqual({ morning: 2, afternoon: 1, evening: 1, night: 0 });
    expect(s.followThrough).toBe(80);
    expect(s.reflections).toBe(1);
    expect(s.photos).toBe(1);
    expect(s.recentPerWeek).toBe(0.8); // 3 in the last 28 days
    expect(s.previousPerWeek).toBe(0.3); // 1 in the 28 before
    expect(s.weeks.at(-1)!.quests).toBe(2); // today (Sun) and Thu fall in this Mon–Sun week
    expect(s.weeks.at(-2)!.quests).toBe(1); // 10 days ago
  });

  it("formats durations", () => {
    expect(formatDuration(45)).toBe("45m");
    expect(formatDuration(120)).toBe("2h");
    expect(formatDuration(135)).toBe("2h 15m");
  });
});
