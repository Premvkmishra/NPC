import { describe, expect, it } from "vitest";
import { autopilotLabel, levelFromXp, XP_BY_DIFFICULTY } from "@/lib/game";

describe("game rules", () => {
  it("level = floor(xp/1000)+1, xp_in_level = xp % 1000", () => {
    expect(levelFromXp(0)).toEqual({ level: 1, xp_in_level: 0, xp_for_next_level: 1000 });
    expect(levelFromXp(1050)).toEqual({ level: 2, xp_in_level: 50, xp_for_next_level: 1000 });
  });
  it("difficulty XP is 50/100/150", () => {
    expect(XP_BY_DIFFICULTY).toEqual({ easy: 50, medium: 100, hard: 150 });
  });
  it("autopilot label bands", () => {
    expect(autopilotLabel(24)).toBe("Wide awake");
    expect(autopilotLabel(25)).toBe("Mostly exploring");
    expect(autopilotLabel(74)).toBe("Needs a little adventure");
    expect(autopilotLabel(75)).toBe("Deep autopilot");
  });
});
