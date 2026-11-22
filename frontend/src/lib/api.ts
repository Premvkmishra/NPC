import type { Autopilot, NpcClient, Player } from "./types";
import { ApiError } from "./errors";
import { mockClient } from "./mock";

export const PLAYER_KEY = "npc_player_id";
export const API_BASE: string = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
export const USE_MOCK: boolean = (import.meta.env.VITE_USE_MOCK ?? "true") !== "false";

export { ApiError };
export function getPlayerId(): string | null {
  return typeof window === "undefined" ? null : window.localStorage.getItem(PLAYER_KEY);
}
export function setPlayerId(id: string) { window.localStorage.setItem(PLAYER_KEY, id); }

async function req<T>(method: string, path: string, opts: { body?: unknown; auth?: boolean } = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (opts.auth !== false) {
    const id = getPlayerId();
    if (id) headers["X-Player-Id"] = id;
  }
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/v1${path}`, opts.body === undefined ? { method, headers } : { method, headers, body: JSON.stringify(opts.body) });
  } catch {
    throw new ApiError("network_error", "Couldn't reach the NPC server.");
  }
  const json = await res.json().catch(() => null);
  if (!res.ok) {
    const e = json?.error;
    throw new ApiError(e?.code ?? "upstream_error", e?.message ?? `Request failed (${res.status})`, res.status);
  }
  return json as T;
}
function qs(o: Record<string, string | number | undefined | null>) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(o)) if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : "";
}

export const httpClient: NpcClient = {
  health: () => req("GET", "/health", { auth: false }),
  createPlayer: async (p) => {
    const res = await req<{ player: Player; autopilot: Autopilot }>("POST", "/players", { body: p, auth: false });
    if (res?.player?.id) {
      setPlayerId(res.player.id);
    }
    return res;
  },
  createSamplePlayer: async () => {
    const res = await req<{ player: Player; autopilot: Autopilot }>("POST", "/players/sample", { auth: false });
    if (res?.player?.id) setPlayerId(res.player.id);
    return res;
  },
  getMe: () => req("GET", "/players/me"),
  updateMe: (p) => req("PATCH", "/players/me", { body: p }),
  home: () => req("GET", "/home"),
  generateQuest: (b) => req("POST", "/quests/generate", { body: b }),
  listQuests: (q) => req("GET", `/quests${qs({ category: q.category, status: q.status, limit: q.limit ?? 20 })}`),
  getQuest: (id) => req("GET", `/quests/${encodeURIComponent(id)}`),
  startQuest: (id) => req("POST", `/quests/${encodeURIComponent(id)}/start`),
  dismissQuest: (id) => req("POST", `/quests/${encodeURIComponent(id)}/dismiss`),
  completeQuest: (id, b) => req("POST", `/quests/${encodeURIComponent(id)}/complete`, { body: b }),
  listExperiences: (q) => req("GET", `/explore/experiences${qs({ tag: q.tag, q: q.q, limit: q.limit ?? 10 })}`),
  getExperience: (id) => req("GET", `/explore/experiences/${encodeURIComponent(id)}`),
  questFromExperience: (id) => req("POST", `/explore/experiences/${encodeURIComponent(id)}/quest`),
  journey: () => req("GET", "/journey"),
  weeklyRecap: () => req("GET", "/journey/weekly-recap"),
  analytics: () => req("GET", "/analytics"),
};

export const api: NpcClient = USE_MOCK ? mockClient : httpClient;
