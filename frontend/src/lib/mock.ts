import type {
  Achievement, ActivityItem, Autopilot, Category, CompleteResponse, Difficulty, Experience,
  JournalEntry, NpcClient, Player, Preferences, Quest,
} from "./types";
import { ApiError } from "./errors";
import { AUTOPILOT_DISCLAIMER, XP_BY_DIFFICULTY, autopilotLabel, levelFromXp } from "./game";

export const STORE = "npc_mock_state";
const PLAYER_KEY = "npc_player_id";
const now = () => new Date().toISOString();
const uid = (p: string) => `${p}_${Math.random().toString(36).slice(2, 10)}`;
const delay = (ms = 350) => new Promise((r) => setTimeout(r, ms));
const maps = (q: string) => `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q + ", Andheri, Mumbai")}`;

interface State {
  player: Player | null; prefs: Preferences | null; baseScore: number;
  quests: Quest[]; todayId: string | null; todayDate: string | null;
  achievements: Achievement[]; journal: JournalEntry[];
}

type Tpl = Omit<Quest, "id" | "status" | "created_at" | "started_at" | "completed_at" | "xp_reward">;
const src = (type: "google_maps" | "google_events" | "google_search", title: string, url: string | null): Quest["source"] => ({ type, title, url, thumbnail_url: null, fetched_at: now() });
const loc = (name: string, address: string, km: number): Quest["location"] => ({ name, address, lat: null, lng: null, distance_km: km, maps_url: maps(name) });

const TEMPLATES: Tpl[] = [
  { title: "Browse a bookstore you've never entered", description: "Walk into Kitab Khana-style indie shelves near Lokhandwala. Pick up one book purely by its cover and read the first page.", why_selected: "You said you like learning new things and have about an hour free.", category: "explore", difficulty: "easy", duration_minutes: 45, estimated_cost_inr: 0, cost_label: "Free", location: loc("Granth Book Store", "Juhu Tara Rd, Andheri West", 1.8), source: src("google_maps", "Granth Book Store — Google Maps", maps("Granth Book Store")), reflection_prompt: "Which book did you pick, and why that one?" },
  { title: "Order a chai you can't pronounce", description: "Find a tapri near Andheri station and order the drink on the board you've never tried.", why_selected: "Food is one of your interests and this costs almost nothing.", category: "explore", difficulty: "easy", duration_minutes: 20, estimated_cost_inr: 40, cost_label: "Under ₹100", location: loc("Yari Road chai tapri", "Yari Rd, Versova", 2.4), source: src("google_maps", "Chai spots near Versova", null), reflection_prompt: "How did it taste compared to your usual?" },
  { title: "Ask a shopkeeper for their favourite local spot", description: "Pick any shop on your route. Ask the person behind the counter where they'd eat lunch around here.", why_selected: "A gentle social stretch that fits a solo style.", category: "social", difficulty: "medium", duration_minutes: 15, estimated_cost_inr: 0, cost_label: "Free", location: null, source: null, reflection_prompt: "What did they recommend? Will you go?" },
  { title: "Join a free open-mic as a listener", description: "Sit in on an open-mic at a café in Versova. You don't have to perform, just stay for three acts.", why_selected: "You picked 'Culture & local life' and evenings look free.", category: "social", difficulty: "medium", duration_minutes: 90, estimated_cost_inr: null, cost_label: "Cost unknown", location: loc("The Habitat-style café, Versova", "Versova, Andheri West", 3.1), source: src("google_events", "Open mic nights — Andheri", null), reflection_prompt: "Which act stuck with you?" },
  { title: "Sketch a street-art wall in 10 minutes", description: "Find a mural near Bandra–Andheri link road and draw it badly, quickly. Speed over skill.", why_selected: "Art & creativity is on your list; no materials beyond a pen.", category: "creativity", difficulty: "easy", duration_minutes: 30, estimated_cost_inr: 0, cost_label: "Free", location: loc("Murals near Andheri West", "Andheri West", 2.9), source: src("google_search", "Andheri street art walls", null), reflection_prompt: "What detail did you notice only because you were drawing it?" },
  { title: "Try a one-time pottery workshop", description: "Book a beginner wheel session. Make one wonky bowl you're allowed to be proud of.", why_selected: "A hands-on first time that fits your budget.", category: "creativity", difficulty: "hard", duration_minutes: 120, estimated_cost_inr: 1200, cost_label: "About ₹1,200", location: loc("Pottery studio, Four Bungalows", "Four Bungalows, Andheri West", 2.2), source: src("google_events", "Beginner pottery — Andheri", null), reflection_prompt: "What did your hands figure out before your brain did?" },
  { title: "Eat lunch somewhere with no reviews", description: "Choose the place with the hand-painted sign, not the one with 4.5 stars.", why_selected: "A low-stakes courage quest built around food.", category: "courage", difficulty: "medium", duration_minutes: 45, estimated_cost_inr: null, cost_label: "Cost unknown", location: null, source: null, reflection_prompt: "Was it a gamble that paid off?" },
  { title: "Take a different train home", description: "Ride one stop past yours or take the Metro line instead, and walk back a new way.", why_selected: "Small route changes are a soft way to break autopilot.", category: "courage", difficulty: "easy", duration_minutes: 40, estimated_cost_inr: 30, cost_label: "Under ₹100", location: loc("Andheri Metro Station", "Andheri East", 0.9), source: src("google_maps", "Andheri Metro — Google Maps", maps("Andheri Metro Station")), reflection_prompt: "What did you see that you'd never have seen otherwise?" },
  { title: "Ten minutes of sound-spotting", description: "Sit on a bench at Lokhandwala garden. Count every distinct sound you hear for ten minutes.", why_selected: "Awareness quests fit any day, even a tired one.", category: "awareness", difficulty: "easy", duration_minutes: 15, estimated_cost_inr: 0, cost_label: "Free", location: loc("Lokhandwala Garden", "Lokhandwala Complex, Andheri West", 1.5), source: src("google_maps", "Lokhandwala Garden", maps("Lokhandwala Garden")), reflection_prompt: "Which sound surprised you?" },
  { title: "Walk without your phone for 20 minutes", description: "Leave it in your bag. Just walk your block and notice three things you never noticed.", why_selected: "No location or cost needed. A quiet reset.", category: "awareness", difficulty: "medium", duration_minutes: 20, estimated_cost_inr: 0, cost_label: "Free", location: null, source: null, reflection_prompt: "Name the three things you noticed." },
];

const ACH: Omit<Achievement, "unlocked" | "unlocked_at">[] = [
  { id: "first_quest", name: "Player One", description: "Complete your first side quest.", icon_key: "star" },
  { id: "three_quests", name: "Side Character No More", description: "Complete 3 quests.", icon_key: "sword" },
  { id: "five_quests", name: "Main Character Energy", description: "Complete 5 quests.", icon_key: "crown" },
  { id: "all_categories", name: "Full Spectrum", description: "Complete a quest in every category.", icon_key: "rainbow" },
  { id: "level_2", name: "Level Up", description: "Reach level 2.", icon_key: "arrow" },
  { id: "photo", name: "Field Photographer", description: "Attach a photo to a completed quest.", icon_key: "camera" },
  { id: "courage", name: "Brave Little NPC", description: "Complete a courage quest.", icon_key: "heart" },
];

const EXPERIENCES: Omit<Experience, "fetched_at">[] = [
  { id: "exp_granth", kind: "place", title: "Granth Book Store", subtitle: "Independent bookshop", tag: "bookstore", thumbnail_url: null, address: "Juhu Tara Rd, Andheri West", lat: null, lng: null, distance_km: 1.8, price_label: null, hours_label: "10 am – 9 pm", event_time_label: null, rating: 4.4, link_url: maps("Granth Book Store"), source: "google_maps", why_worth_it: "Shelves curated by humans, not algorithms." },
  { id: "exp_kitab", kind: "place", title: "Second-hand book stalls", subtitle: "Pavement bookstalls", tag: "bookstore", thumbnail_url: null, address: "Near Andheri station (W)", lat: null, lng: null, distance_km: 0.7, price_label: "From ₹50", hours_label: null, event_time_label: null, rating: null, link_url: null, source: "google_search", why_worth_it: "Dig for a ₹50 treasure and haggle a little." },
  { id: "exp_gallery", kind: "place", title: "Small contemporary gallery, Versova", subtitle: "Rotating exhibitions", tag: "gallery", thumbnail_url: null, address: "Versova, Andheri West", lat: null, lng: null, distance_km: 3.0, price_label: "Free", hours_label: "11 am – 7 pm", event_time_label: null, rating: 4.6, link_url: null, source: "google_maps", why_worth_it: "Ten minutes in a quiet white room resets the day." },
  { id: "exp_pottery", kind: "activity", title: "Beginner pottery wheel session", subtitle: "Studio workshop", tag: "workshop", thumbnail_url: null, address: "Four Bungalows, Andheri West", lat: null, lng: null, distance_km: 2.2, price_label: "₹1,200", hours_label: null, event_time_label: "Sat · 4 pm", rating: 4.8, link_url: null, source: "google_events", why_worth_it: "Getting clay on your hands is a guaranteed first." },
  { id: "exp_calligraphy", kind: "event", title: "Intro to calligraphy", subtitle: "2-hour workshop", tag: "workshop", thumbnail_url: null, address: "Lokhandwala, Andheri West", lat: null, lng: null, distance_km: 1.4, price_label: null, hours_label: null, event_time_label: "Sun · 11 am", rating: null, link_url: null, source: "google_events", why_worth_it: "Slow, focused and oddly satisfying." },
  { id: "exp_vadapav", kind: "place", title: "Vada pav stall by the market", subtitle: "Street food", tag: "food", thumbnail_url: null, address: "Andheri Market, Andheri West", lat: null, lng: null, distance_km: 0.9, price_label: "Under ₹50", hours_label: "7 am – 10 pm", event_time_label: null, rating: 4.3, link_url: null, source: "google_maps", why_worth_it: "The cheapest way to try a local legend." },
  { id: "exp_irani", kind: "place", title: "Old Irani café", subtitle: "Bun maska & chai", tag: "food", thumbnail_url: null, address: "Andheri East", lat: null, lng: null, distance_km: 2.6, price_label: null, hours_label: null, event_time_label: null, rating: 4.2, link_url: null, source: "google_search", why_worth_it: "Bentwood chairs and a slower pace." },
  { id: "exp_openmic", kind: "event", title: "Free open-mic night", subtitle: "Poetry & comedy", tag: "free events", thumbnail_url: null, address: "Versova, Andheri West", lat: null, lng: null, distance_km: 3.1, price_label: "Free", hours_label: null, event_time_label: "Fri · 8 pm", rating: null, link_url: null, source: "google_events", why_worth_it: "Strangers being brave on stage is contagious." },
  { id: "exp_mural", kind: "place", title: "Murals on the Versova lanes", subtitle: "Street art walk", tag: "street art", thumbnail_url: null, address: "Versova village", lat: null, lng: null, distance_km: 3.4, price_label: "Free", hours_label: null, event_time_label: null, rating: null, link_url: null, source: "google_search", why_worth_it: "Fishing-village walls painted loud and bright." },
];

function freshState(): State {
  return { player: null, prefs: null, baseScore: 50, quests: [], todayId: null, todayDate: null,
    achievements: ACH.map((a) => ({ ...a, unlocked: false, unlocked_at: null })), journal: [] };
}
function load(): State {
  try { const raw = localStorage.getItem(STORE); if (raw) return JSON.parse(raw) as State; } catch { /* ignore */ }
  return freshState();
}
function save(s: State) { localStorage.setItem(STORE, JSON.stringify(s)); }

function requirePlayer(s: State): Player {
  const id = localStorage.getItem(PLAYER_KEY);
  if (!id || !s.player || s.player.id !== id) throw new ApiError("player_required", "No player found. Start a new save file.", 401);
  return s.player;
}

function initialScore(p: Preferences): number {
  const nf = { daily: 5, weekly: 25, monthly: 50, rarely: 75 }[p.novelty_frequency];
  const lf = { this_week: 0, this_month: 10, this_year: 20, cant_remember: 25 }[p.last_first_time];
  return Math.max(0, Math.min(100, Math.round(nf * 0.8 + lf - (p.comfort_level - 3) * 3)));
}
function autopilot(s: State): Autopilot {
  const recent = s.journal.filter((j) => Date.now() - Date.parse(j.completed_at) < 14 * 864e5).length;
  const score = Math.max(0, Math.min(100, s.baseScore - recent * 8));
  const label = autopilotLabel(score);
  const explanation = {
    "Wide awake": "You've been trying lots of new things lately. Keep the curiosity rolling.",
    "Mostly exploring": "Plenty of fresh moments in your week, with a comfy routine underneath.",
    "Needs a little adventure": "Higher means more repetition. A small first-time could tip the scale.",
    "Deep autopilot": "Higher means more repetition. Your days look familiar right now, and that's okay. One tiny quest is enough.",
  }[label];
  return { score, label, explanation, disclaimer: AUTOPILOT_DISCLAIMER };
}

function makeQuest(t: Tpl): Quest {
  return { ...t, id: uid("q"), status: "suggested", xp_reward: XP_BY_DIFFICULTY[t.difficulty as Difficulty], created_at: now(), started_at: null, completed_at: null };
}
function pickTemplate(s: State, category?: Category | null): Tpl {
  const used = new Set(s.quests.filter((q) => q.status !== "dismissed").map((q) => q.title));
  let pool = TEMPLATES.filter((t) => (!category || t.category === category));
  const fresh = pool.filter((t) => !used.has(t.title));
  if (fresh.length) pool = fresh;
  if (!pool.length) throw new ApiError("no_suitable_quest", "No quest fits right now. Try another category?", 404);
  return pool[Math.floor(Math.random() * pool.length)]!;
}
const today = () => new Date().toDateString();

function ensureToday(s: State): Quest | null {
  const cur = s.quests.find((q) => q.id === s.todayId);
  if (s.todayDate === today() && cur) return cur.status === "dismissed" ? null : cur;
  const q = makeQuest(pickTemplate(s));
  s.quests.unshift(q); s.todayId = q.id; s.todayDate = today();
  return q;
}
function findQuest(s: State, id: string): Quest {
  const q = s.quests.find((x) => x.id === id);
  if (!q) throw new ApiError("not_found", "That quest scroll seems to have blown away.", 404);
  return q;
}
function seedBoard(s: State) {
  const cats: Category[] = ["explore", "social", "creativity", "courage", "awareness"];
  for (const c of cats) {
    if (!s.quests.some((q) => q.category === c && q.status === "suggested")) {
      const t = TEMPLATES.find((x) => x.category === c && !s.quests.some((q) => q.title === x.title));
      if (t) s.quests.push(makeQuest(t));
    }
  }
}

const SAMPLE_REFLECTIONS = [
  "Didn't miss my phone once.", "Talked to a stranger and it was fine. Better than fine.", "Noticed a detail I'd walked past for years.",
  "Terrible drawing, great time.", "Worth it. Would go again.", "", "Got a recommendation I'm actually going to follow.",
];
// [days ago, local hour, template index]. Denser recently, so the trend climbs.
const SAMPLE_SCHEDULE: [number, number, number][] = [
  [55, 18, 0], [51, 7, 8], [47, 19, 2], [44, 17, 4], [40, 10, 1], [37, 19, 9], [34, 18, 3], [31, 8, 7],
  [29, 16, 6], [26, 20, 5], [23, 11, 0], [21, 7, 8], [19, 18, 7], [16, 6, 5], [14, 17, 4], [12, 9, 3],
  [10, 19, 9], [8, 13, 1], [6, 18, 6], [4, 7, 8], [2, 19, 2], [1, 12, 0],
];

/** A demo save with ~2 months of history so the analytics tab has something to show. */
function sampleState(): State {
  const s = freshState();
  const prefs: Preferences = {
    display_name: "Riya (sample)", interests: ["food", "art", "outdoors", "culture"], novelty_frequency: "rarely",
    social_style: "either", comfort_level: 2, city: "Andheri, Mumbai", lat: null, lng: null,
    free_time_minutes: 90, max_distance_km: 10, budget_inr: 1500, accessibility_notes: null, last_first_time: "this_year",
  };
  const player: Player = { id: uid("p"), display_name: prefs.display_name, city: prefs.city, ...levelFromXp(0), total_xp: 0,
    quests_completed: 0, achievements_unlocked: 0, created_at: new Date(Date.now() - 58 * 864e5).toISOString() };
  s.player = player; s.prefs = prefs; s.baseScore = initialScore(prefs);
  SAMPLE_SCHEDULE.forEach(([daysAgo, hour, t], i) => {
    const d = new Date(Date.now() - daysAgo * 864e5); d.setHours(hour, (i * 7) % 60, 0, 0);
    const at = d.toISOString();
    const q: Quest = { ...makeQuest(TEMPLATES[t]!), status: "completed", created_at: at, started_at: at, completed_at: at };
    s.quests.push(q);
    s.journal.unshift({ quest_id: q.id, title: q.title, category: q.category, completed_at: at, xp_earned: q.xp_reward,
      reflection: SAMPLE_REFLECTIONS[i % SAMPLE_REFLECTIONS.length] || null, photo_url: null, location_name: q.location?.name ?? null });
    player.total_xp += q.xp_reward; player.quests_completed += 1;
  });
  [2, 6, 9].forEach((t) => s.quests.push({ ...makeQuest(TEMPLATES[t]!), status: "dismissed" }));
  Object.assign(player, levelFromXp(player.total_xp));
  const cats = new Set(s.journal.map((j) => j.category));
  const earned: Record<string, boolean> = { first_quest: true, three_quests: true, five_quests: true, all_categories: cats.size >= 5,
    level_2: player.level >= 2, photo: false, courage: cats.has("courage") };
  for (const a of s.achievements) if (earned[a.id]) { a.unlocked = true; a.unlocked_at = s.journal[0]!.completed_at; }
  player.achievements_unlocked = s.achievements.filter((a) => a.unlocked).length;
  seedBoard(s);
  return s;
}

export const mockClient: NpcClient = {
  async createSamplePlayer() {
    await delay(700);
    const s = sampleState(); save(s); localStorage.setItem(PLAYER_KEY, s.player!.id);
    return { player: s.player!, autopilot: autopilot(s) };
  },
  async analytics() {
    await delay(); const s = load(); const player = requirePlayer(s);
    const byId = new Map(s.journal.map((j) => [j.quest_id, j]));
    const entries = s.quests.filter((q) => q.status === "completed" && byId.has(q.id)).map((q) => {
      const j = byId.get(q.id)!;
      return { quest_id: q.id, title: q.title, category: q.category, difficulty: q.difficulty, duration_minutes: q.duration_minutes,
        estimated_cost_inr: q.estimated_cost_inr, xp_earned: j.xp_earned, completed_at: j.completed_at, location: q.location,
        has_reflection: !!j.reflection?.trim(), has_photo: !!j.photo_url };
    }).sort((a, b) => b.completed_at.localeCompare(a.completed_at));
    const base = { ...autopilot(s), score: s.baseScore, label: autopilotLabel(s.baseScore) };
    return { player, entries, quests_dismissed: s.quests.filter((q) => q.status === "dismissed").length,
      quests_open: s.quests.filter((q) => q.status === "suggested" || q.status === "active").length,
      autopilot_start: base, autopilot_now: autopilot(s) };
  },
  async health() { await delay(100); return { status: "ok", mock_mode: true, serpapi_live: false, llm_live: false }; },
  async createPlayer(p) {
    await delay(900);
    if (!p.display_name.trim() || !p.interests.length) throw new ApiError("validation_error", "Add a name and at least one interest.", 422);
    const s = freshState();
    const player: Player = { id: uid("p"), display_name: p.display_name.trim(), city: p.city, ...levelFromXp(0), total_xp: 0, quests_completed: 0, achievements_unlocked: 0, created_at: now() };
    s.player = player; s.prefs = p; s.baseScore = initialScore(p);
    seedBoard(s); save(s); localStorage.setItem(PLAYER_KEY, player.id);
    return { player, autopilot: autopilot(s) };
  },
  async getMe() { await delay(); const s = load(); const player = requirePlayer(s); return { player, preferences: s.prefs!, autopilot: autopilot(s) }; },
  async updateMe(p) { await delay(); const s = load(); const player = requirePlayer(s); s.prefs = { ...s.prefs!, ...p }; save(s); return { player, preferences: s.prefs, autopilot: autopilot(s) }; },
  async home() {
    await delay(); const s = load(); const player = requirePlayer(s);
    const todays_quest = ensureToday(s); save(s);
    const recent_activity: ActivityItem[] = s.journal.slice(0, 2).map((j) => ({ quest_id: j.quest_id, title: j.title, xp_earned: j.xp_earned, completed_at: j.completed_at }));
    return { player, autopilot: autopilot(s), todays_quest, recent_activity };
  },
  async generateQuest({ category, replace_today }) {
    await delay(700); const s = load(); requirePlayer(s);
    if (replace_today) {
      const cur = s.quests.find((q) => q.id === s.todayId);
      if (cur && cur.status === "suggested") cur.status = "dismissed";
    }
    const q = makeQuest(pickTemplate(s, category));
    s.quests.unshift(q);
    if (replace_today) { s.todayId = q.id; s.todayDate = today(); }
    save(s); return { quest: q };
  },
  async listQuests({ category, status, limit = 20 }) {
    await delay(); const s = load(); requirePlayer(s); seedBoard(s); save(s);
    const quests = s.quests.filter((q) => (!category || q.category === category) && (status ? q.status === status : q.status === "suggested" || q.status === "active")).slice(0, limit);
    return { quests };
  },
  async getQuest(id) { await delay(); const s = load(); requirePlayer(s); return { quest: findQuest(s, id) }; },
  async startQuest(id) { await delay(); const s = load(); requirePlayer(s); const q = findQuest(s, id); if (q.status === "suggested") { q.status = "active"; q.started_at = now(); } save(s); return { quest: q }; },
  async dismissQuest(id) { await delay(); const s = load(); requirePlayer(s); const q = findQuest(s, id); if (q.status !== "completed") q.status = "dismissed"; save(s); return { quest: q }; },
  async completeQuest(id, body): Promise<CompleteResponse> {
    await delay(800); const s = load(); const player = requirePlayer(s); const q = findQuest(s, id);
    if (body.reflection.length > 500) throw new ApiError("validation_error", "Keep your reflection under 500 characters.", 422);
    if (q.status === "completed") throw new ApiError("validation_error", "This quest is already in your journal.", 422);
    q.status = "completed"; q.completed_at = now(); q.started_at ??= q.completed_at;
    const before = player.level;
    player.total_xp += q.xp_reward;
    Object.assign(player, levelFromXp(player.total_xp));
    player.quests_completed += 1;
    s.journal.unshift({ quest_id: q.id, title: q.title, category: q.category, completed_at: q.completed_at, xp_earned: q.xp_reward, reflection: body.reflection || null, photo_url: body.photo_data_url ?? null, location_name: q.location?.name ?? null });
    const cats = new Set(s.journal.map((j) => j.category));
    const checks: Record<string, boolean> = {
      first_quest: player.quests_completed >= 1, three_quests: player.quests_completed >= 3, five_quests: player.quests_completed >= 5,
      all_categories: cats.size >= 5, level_2: player.level >= 2, photo: !!body.photo_data_url, courage: cats.has("courage"),
    };
    const unlocked: Achievement[] = [];
    for (const a of s.achievements) if (!a.unlocked && checks[a.id]) { a.unlocked = true; a.unlocked_at = now(); unlocked.push(a); }
    player.achievements_unlocked = s.achievements.filter((a) => a.unlocked).length;
    save(s);
    const leveled_up = player.level > before;
    return { quest: q, xp_awarded: q.xp_reward, player, leveled_up, new_level: leveled_up ? player.level : null, achievements_unlocked: unlocked, autopilot: autopilot(s), message: "You broke your routine today." };
  },
  async listExperiences({ tag, q, limit = 10 }) {
    await delay(600);
    const needle = (q ?? "").toLowerCase();
    const experiences = EXPERIENCES.filter((e) => (!tag || e.tag === tag) && (!needle || `${e.title} ${e.subtitle ?? ""} ${e.tag}`.toLowerCase().includes(needle)))
      .slice(0, limit).map((e) => ({ ...e, fetched_at: now() }));
    return { experiences, cached: true };
  },
  async getExperience(id) {
    await delay(); const e = EXPERIENCES.find((x) => x.id === id);
    if (!e) throw new ApiError("not_found", "That place fell off the map.", 404);
    return { experience: { ...e, fetched_at: now() } };
  },
  async questFromExperience(id) {
    await delay(700); const s = load(); requirePlayer(s);
    const e = EXPERIENCES.find((x) => x.id === id);
    if (!e) throw new ApiError("not_found", "That place fell off the map.", 404);
    const category: Category = e.tag === "food" || e.tag === "bookstore" ? "explore" : e.tag === "free events" ? "social" : e.tag === "street art" ? "awareness" : "creativity";
    const difficulty: Difficulty = e.kind === "activity" ? "hard" : e.kind === "event" ? "medium" : "easy";
    const q = makeQuest({
      title: `Visit ${e.title}`, description: `${e.subtitle ?? "A local find"}. ${e.why_worth_it} Go once, stay at least 20 minutes.`,
      why_selected: `It's ${e.distance_km ?? "?"} km away and matches the '${e.tag}' vibe you were browsing.`,
      category, difficulty, duration_minutes: e.kind === "activity" ? 120 : 45,
      estimated_cost_inr: null, cost_label: e.price_label ?? "Cost unknown",
      location: { name: e.title, address: e.address, lat: e.lat, lng: e.lng, distance_km: e.distance_km, maps_url: e.link_url ?? maps(e.title) },
      source: { type: e.source, title: e.title, url: e.link_url, thumbnail_url: e.thumbnail_url, fetched_at: now() },
      reflection_prompt: "What was the first thing you noticed when you walked in?",
    });
    s.quests.unshift(q); save(s); return { quest: q };
  },
  async journey() {
    await delay(); const s = load(); const player = requirePlayer(s);
    const category_counts: Record<Category, number> = { explore: 0, social: 0, creativity: 0, courage: 0, awareness: 0 };
    for (const j of s.journal) category_counts[j.category] += 1;
    return { player, achievements: s.achievements, journal: s.journal, category_counts };
  },
  async weeklyRecap() {
    await delay(); const s = load(); requirePlayer(s);
    const end = new Date(); const start = new Date(Date.now() - 6 * 864e5);
    const week = s.journal.filter((j) => Date.parse(j.completed_at) >= start.getTime() - 864e5);
    const cats = [...new Set(week.map((j) => j.category))];
    const xp = week.reduce((a, j) => a + j.xp_earned, 0);
    const summary = week.length
      ? `This week you stepped off the usual path ${week.length} time${week.length > 1 ? "s" : ""} and earned ${xp} XP. Nice.`
      : "A quiet week so far. Quiet weeks count too. One tiny quest whenever you're ready.";
    return { week_start: start.toISOString(), week_end: end.toISOString(), summary,
      stats: { quests_completed: week.length, new_places: week.filter((j) => j.location_name).length, categories_tried: cats, xp_earned: xp }, generated_by: "template" };
  },
};
