import type { Autopilot, AutopilotLabel, Difficulty } from "./types";
export const XP_PER_LEVEL = 1000;
export const XP_BY_DIFFICULTY: Record<Difficulty, number> = { easy: 50, medium: 100, hard: 150 };
export function levelFromXp(total: number) {
  return { level: Math.floor(total / XP_PER_LEVEL) + 1, xp_in_level: total % XP_PER_LEVEL, xp_for_next_level: XP_PER_LEVEL };
}
export function autopilotLabel(score: number): AutopilotLabel {
  if (score < 25) return "Wide awake";
  if (score < 50) return "Mostly exploring";
  if (score < 75) return "Needs a little adventure";
  return "Deep autopilot";
}
export const AUTOPILOT_DISCLAIMER: Autopilot["disclaimer"] = "A playful reflection of your reported habits. Not a psychological score.";
