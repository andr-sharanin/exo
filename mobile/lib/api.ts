import Constants from "expo-constants";
import type {
  Command,
  DayPlan,
  EnergyCheckinRequest,
  EnergyScore,
  Habit,
} from "./types";

const BASE_URL: string =
  (Constants.expoConfig?.extra?.apiUrl as string | undefined) ?? "http://10.0.2.2:8000/api/v1";

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init?.headers as Record<string, string> | undefined),
    },
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${path}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  energy: {
    checkin: (data: EnergyCheckinRequest, token: string): Promise<EnergyScore> =>
      request("/energy/checkin", token, { method: "POST", body: JSON.stringify(data) }),

    getScore: (token: string): Promise<EnergyScore> =>
      request("/energy/score", token),
  },

  secretary: {
    getTodayPlan: (token: string): Promise<DayPlan> =>
      request("/secretary/plan/today", token),

    generatePlan: (token: string): Promise<{ job_id: string; status: string }> =>
      request("/secretary/plan", token, { method: "POST" }),
  },

  commands: {
    create: (
      data: { raw_payload_ref: string; ingress_channel?: string; ingress_modality?: string; idempotency_key: string },
      token: string
    ): Promise<Command> =>
      request("/commands", token, { method: "POST", body: JSON.stringify(data) }),

    list: (token: string, limit = 20): Promise<Command[]> =>
      request(`/commands?limit=${limit}`, token),

    confirm: (
      commandId: string,
      decision: "confirmed" | "deferred",
      note: string | undefined,
      token: string
    ): Promise<{ command_id: string; kernel_status: string }> =>
      request(`/commands/${commandId}/confirm`, token, {
        method: "POST",
        body: JSON.stringify({ decision, note }),
      }),
  },

  habits: {
    list: (token: string): Promise<Habit[]> =>
      request("/habits", token),

    checkin: (habitId: string, token: string, note?: string): Promise<{ streak: number; already_done: boolean }> =>
      request(`/habits/${habitId}/checkin`, token, {
        method: "POST",
        body: JSON.stringify({ note }),
      }),
  },

  push: {
    subscribe: (
      data: { endpoint: string; token: string },
      userToken: string,
    ): Promise<void> =>
      request("/push/subscribe", userToken, { method: "POST", body: JSON.stringify(data) }),
  },
} as const;
