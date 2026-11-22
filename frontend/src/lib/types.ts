export type Category = "explore" | "social" | "creativity" | "courage" | "awareness";
export type Difficulty = "easy" | "medium" | "hard";
export type QuestStatus = "suggested" | "active" | "completed" | "dismissed";
export type Interest = "food" | "art" | "people" | "learning" | "outdoors" | "culture";

export interface Player {
  id: string; display_name: string; city: string; level: number; total_xp: number;
  xp_in_level: number; xp_for_next_level: number; quests_completed: number;
  achievements_unlocked: number; created_at: string;
}
export interface Preferences {
  display_name: string; interests: Interest[];
  novelty_frequency: "rarely" | "monthly" | "weekly" | "daily";
  social_style: "solo" | "friends" | "either"; comfort_level: number;
  city: string; lat: number | null; lng: number | null;
  free_time_minutes: number; max_distance_km: number; budget_inr: number;
  accessibility_notes: string | null;
  last_first_time: "this_week" | "this_month" | "this_year" | "cant_remember";
}
export type AutopilotLabel = "Wide awake" | "Mostly exploring" | "Needs a little adventure" | "Deep autopilot";
export interface Autopilot { score: number; label: AutopilotLabel; explanation: string; disclaimer: string }
export type SourceType = "google_maps" | "google_events" | "google_search";
export interface QuestSource { type: SourceType; title: string; url: string | null; thumbnail_url: string | null; fetched_at: string }
export interface QuestLocation { name: string; address: string | null; lat: number | null; lng: number | null; distance_km: number | null; maps_url: string | null }
export interface Quest {
  id: string; title: string; description: string; why_selected: string;
  category: Category; difficulty: Difficulty; duration_minutes: number;
  estimated_cost_inr: number | null; cost_label: string; xp_reward: number;
  status: QuestStatus; location: QuestLocation | null; source: QuestSource | null;
  reflection_prompt: string; created_at: string; started_at: string | null; completed_at: string | null;
}
export interface Experience {
  id: string; kind: "place" | "event" | "activity"; title: string; subtitle: string | null; tag: string;
  thumbnail_url: string | null; address: string | null; lat: number | null; lng: number | null;
  distance_km: number | null; price_label: string | null; hours_label: string | null;
  event_time_label: string | null; rating: number | null; link_url: string | null;
  source: SourceType; why_worth_it: string; fetched_at: string;
}
export interface ActivityItem { quest_id: string; title: string; xp_earned: number; completed_at: string }
export interface Achievement { id: string; name: string; description: string; icon_key: string; unlocked: boolean; unlocked_at: string | null }
export interface JournalEntry { quest_id: string; title: string; category: Category; completed_at: string; xp_earned: number; reflection: string | null; photo_url: string | null; location_name: string | null }

export interface Health { status: "ok"; mock_mode: boolean; serpapi_live: boolean; llm_live: boolean }
export interface PlayerMe { player: Player; preferences: Preferences; autopilot: Autopilot }
export interface HomeResponse { player: Player; autopilot: Autopilot; todays_quest: Quest | null; recent_activity: ActivityItem[] }
export interface CompleteResponse {
  quest: Quest; xp_awarded: number; player: Player; leveled_up: boolean; new_level: number | null;
  achievements_unlocked: Achievement[]; autopilot: Autopilot; message: string;
}
export interface JourneyResponse { player: Player; achievements: Achievement[]; journal: JournalEntry[]; category_counts: Record<Category, number> }
export interface WeeklyRecap {
  week_start: string; week_end: string; summary: string;
  stats: { quests_completed: number; new_places: number; categories_tried: Category[]; xp_earned: number };
  generated_by: "llm" | "template";
}
export type ErrorCode = "validation_error" | "not_found" | "player_required" | "upstream_error" | "no_suitable_quest";

export interface Reward {
  id: string;
  title: string;
  description: string;
  brand: string;
  category: string;
  discount_amount_inr: number;
  cost_xp: number;
  location: string | null;
  terms: string | null;
  icon_key: string;
  is_active: boolean;
}

export interface RewardRedemption {
  id: string;
  reward_id: string;
  reward_title: string;
  brand: string;
  voucher_code: string;
  cost_xp: number;
  redeemed_at: string;
  expires_at: string;
  status: string;
}

export interface RewardsListResponse {
  rewards: Reward[];
  redemptions: RewardRedemption[];
  player_xp: number;
}

export interface RedeemRewardResponse {
  success: boolean;
  redemption: RewardRedemption;
  player: Player;
  reward: Reward;
  code: string;
  message: string;
}

export interface NpcClient {
  health(): Promise<Health>;
  createPlayer(p: Preferences): Promise<{ player: Player; autopilot: Autopilot }>;
  getMe(): Promise<PlayerMe>;
  updateMe(p: Partial<Preferences>): Promise<PlayerMe>;
  home(): Promise<HomeResponse>;
  generateQuest(body: { category?: Category | null; replace_today?: boolean }): Promise<{ quest: Quest }>;
  listQuests(q: { category?: Category; status?: QuestStatus; limit?: number }): Promise<{ quests: Quest[] }>;
  getQuest(id: string): Promise<{ quest: Quest }>;
  startQuest(id: string): Promise<{ quest: Quest }>;
  dismissQuest(id: string): Promise<{ quest: Quest }>;
  completeQuest(id: string, body: { reflection: string; photo_data_url?: string | null }): Promise<CompleteResponse>;
  listExperiences(q: { tag?: string; q?: string; limit?: number }): Promise<{ experiences: Experience[]; cached: boolean }>;
  getExperience(id: string): Promise<{ experience: Experience }>;
  questFromExperience(id: string): Promise<{ quest: Quest }>;
  journey(): Promise<JourneyResponse>;
  weeklyRecap(): Promise<WeeklyRecap>;
  listRewards(): Promise<RewardsListResponse>;
  redeemReward(rewardId: string): Promise<RedeemRewardResponse>;
  myRedemptions(): Promise<{ redemptions: RewardRedemption[] }>;
}
