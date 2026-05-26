// ── Energy ────────────────────────────────────────────────────────────────────
export type EnergyState = "sufficient" | "constrained" | "critical";

export interface EnergyScore {
  id: string;
  score: number;
  state: EnergyState;
  is_override: boolean;
  valid_until: string;
  suggested_mode: string | null;
  created_at: string;
}

// ── System Mode ───────────────────────────────────────────────────────────────
export interface SystemMode {
  id: string;
  mode: string;
  activated_at: string;
}

// ── Day Plan ──────────────────────────────────────────────────────────────────
export interface PlanItem {
  order: number;
  step_id: string;
  title: string;
  step_type: "focus_step" | "background_step" | "rescue_entry_step";
  energy_cost: "low" | "medium" | "high";
  estimated_minutes: number | null;
  score: number;
}

export interface DayPlan {
  id: string;
  plan_date: string;
  status: "draft" | "accepted" | "completed";
  items: PlanItem[];
  energy_state_at_generation: string | null;
  system_mode_at_generation: string | null;
  total_estimated_minutes: number;
  generated_at: string;
  accepted_at: string | null;
}

// ── Planning Goals ────────────────────────────────────────────────────────────
export type Horizon = "vision" | "annual" | "quarterly" | "monthly" | "weekly" | "daily";

export interface PlanningGoal {
  id: string;
  horizon: Horizon;
  title: string;
  description: string | null;
  status: "active" | "completed" | "abandoned";
  parent_id: string | null;
  target_date: string | null;
  completed_at: string | null;
}

// ── Agent ─────────────────────────────────────────────────────────────────────
export type EntityType =
  | "core_advisor"
  | "tutor"
  | "reflective_support"
  | "coach"
  | "consultant";

export interface AgentSession {
  id: string;
  entity_type: EntityType;
  session_mode: string;
  status: string;
}

export interface AgentMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  message_order: number;
  model_used: string | null;
}

// ── Deposits ──────────────────────────────────────────────────────────────────
export interface CommitmentDeposit {
  id: string;
  step_id: string;
  amount_cents: number;
  currency: string;
  status: "held" | "released" | "forfeited";
  due_date: string;
  stripe_setup_intent_id: string | null;
  released_at: string | null;
  forfeited_at: string | null;
}

// ── Commands / Inbox ─────────────────────────────────────────────────────────
export type KernelStatus =
  | "pending_analysis"
  | "pending_confirmation"
  | "confirmed"
  | "deferred"
  | null;

export interface Command {
  id: string;
  status: string;
  kernel_status: KernelStatus;
  ingress_channel: string;
  ingress_modality: string;
  raw_payload_ref: string;
  raw_input: string | null;
  submitted_at: string;
  idempotency_key: string;
  created_at: string;
}

export interface TaskAnalysis {
  available: boolean;
  alignment_score?: number;
  recommendation?: "proceed" | "defer" | "decline" | "neutral";
  reasoning?: string;
  conflicts?: string[];
  synergies?: string[];
  confirm_required?: boolean;
  suggested_timing?: string | null;
  user_decision?: string | null;
}

// ── Onboarding ────────────────────────────────────────────────────────────────
export type OnboardingMode = "quick" | "deep";

export interface OnboardingOption {
  option_id: string;
  text: string;
}

export interface OnboardingQuestion {
  question_id: string;
  scenario: string;
  options: OnboardingOption[];
}

export interface OnboardingStartResponse {
  session_id: string;
  mode: OnboardingMode;
  questions: OnboardingQuestion[];
  total_questions: number;
}

export interface KernelProfile {
  id: string;
  calibration_version: number;
  calibrated_at: string;
  profile_data: Record<string, string>;
  computed_defaults: Record<string, string | number>;
}

// ── Reviews (планёрки) ────────────────────────────────────────────────────────
export type ReviewType = "daily" | "weekly" | "monthly";
export type ReviewStatus = "pending" | "in_progress" | "completed" | "skipped";

export interface ReviewQuestion {
  id: string;
  text: string;
  answer_type: "text" | "scale_1_5" | "choice" | "confirm_plan";
  options?: string[];
  required?: boolean;
}

export interface AIPlanItem {
  step_id: string | null;
  title: string;
  estimated_minutes: number;
  reason: string;
}

export interface ReviewSessionSummary {
  id: string;
  review_type: ReviewType;
  status: ReviewStatus;
  created_at: string;
  has_ai_agenda: boolean;
  plan_confirmed: boolean;
}

export interface ReviewSessionDetail extends ReviewSessionSummary {
  ai_agenda: string | null;
  ai_plan_suggestion: AIPlanItem[] | null;
  questions: ReviewQuestion[] | null;
  answers: Record<string, string> | null;
  user_notes: string | null;
  plan_adjustments: AIPlanItem[] | null;
  goals_updated: boolean;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
}

// ── Habits ────────────────────────────────────────────────────────────────────
export type HabitFrequency = "daily" | "weekdays" | "weekly" | "custom";
export type HabitCategory =
  | "health"
  | "learning"
  | "mindfulness"
  | "productivity"
  | "social"
  | "custom";

export interface Habit {
  id: string;
  title: string;
  description: string | null;
  frequency: HabitFrequency;
  target_time: string | null;
  estimated_minutes: number;
  category: string | null;
  include_in_plan: boolean;
  streak: number;
  checked_today: boolean;
  created_at: string;
}

// ── Morning Brief ─────────────────────────────────────────────────────────────
export interface BriefBullet {
  emoji: string;
  text: string;
}

export interface MorningBrief {
  greeting: string;
  bullets: BriefBullet[];
  focus_recommendation: string;
  energy_tip: string;
  date: string;
  generated_at: string;
}

// ── Agent Personas (Admin) ────────────────────────────────────────────────────
export interface KnowledgeDoc {
  title: string;
  content: string;
  added_at: string;
}

export interface ToneStyle {
  language?: string;
  response_length?: string;
  uses_emojis?: boolean;
  format?: string;
}

export interface AgentPersona {
  id: string;
  entity_type: string;
  display_name: string;
  avatar_emoji: string;
  description: string | null;
  system_prompt: string | null;
  training_context_length: number;
  knowledge_base_count: number;
  knowledge_base: KnowledgeDoc[];
  behavior_rules: string[];
  tone_style: ToneStyle;
  preferred_tier: number;
  preferred_model: string | null;
  is_enabled: boolean;
  is_default: boolean;
  total_conversations: number;
  last_trained_at: string | null;
  created_at: string;
}

// ── Step Object ───────────────────────────────────────────────────────────────
export interface StepObject {
  id: string;
  status: string;
  decision_id: string;
  step_type: "focus_step" | "background_step" | "rescue_entry_step";
  execution_readiness: "ready" | "blocked" | "needs_clarification";
  title: string;
  definition_of_done_ref: string | null;
  step_order: number;
  estimated_minutes: number | null;
  created_at: string;
}

// ── Admin Config ──────────────────────────────────────────────────────────────
export interface ConfigEntry {
  key: string;
  value: string;
  is_secret: boolean;
  description: string;
  category: string;
  updated_at: string;
}

export type ConfigCategory =
  | "ai_keys"
  | "agent_prompts"
  | "integrations"
  | "stripe"
  | "email"
  | "misc";
