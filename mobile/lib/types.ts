export type EnergyState = "sufficient" | "constrained" | "critical";
export type Horizon = "vision" | "annual" | "quarterly" | "monthly" | "weekly" | "daily";

export interface EnergyScore {
  id: string;
  score: number;          // 0-100
  state: EnergyState;     // sufficient | constrained | critical
  is_override: boolean;
  valid_until: string;
  created_at: string;
}

export interface PlanItem {
  order: number;
  step_id: string;
  title: string;
  estimated_minutes: number | null;
  score: number;
  step_type: string;
  energy_cost: "low" | "medium" | "high";
}

export interface DayPlan {
  id: string;
  plan_date: string;
  status: "draft" | "accepted" | "completed";
  items: PlanItem[];
  total_estimated_minutes: number;
  energy_state_at_generation: string | null;
  system_mode_at_generation: string | null;
}

export interface Habit {
  id: string;
  title: string;
  description: string | null;
  frequency: string;
  target_time: string | null;
  estimated_minutes: number;
  category: string | null;
  include_in_plan: boolean;
  streak: number;
  checked_today: boolean;
  created_at: string;
}

export interface Command {
  id: string;
  status: string;
  kernel_status: string | null;
  ingress_channel: string;
  raw_input: string | null;
  submitted_at: string;
}

export interface EnergyCheckinRequest {
  sleep_quality: number;   // 1-5
  mood: number;            // 1-5
  energy_level: number;    // 1-5
  note?: string;
}
