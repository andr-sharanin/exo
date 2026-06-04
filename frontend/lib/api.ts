/**
 * Typed API client — all requests go through Next.js rewrite proxy
 * to avoid CORS and keep the backend URL server-side only.
 *
 * Base path: /api/backend  →  FastAPI /api/v1
 */

const isServer = typeof window === "undefined";
const BASE = isServer
  ? `${process.env.BACKEND_URL ?? "http://api:8000"}/api/v1`
  : "/api/backend";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number
  ) {
    super(message);
    this.name = "ApiError";
  }

  get isPaymentRequired(): boolean {
    return this.status === 402;
  }
}

async function request<T>(
  path: string,
  options: RequestInit & { token?: string } = {}
): Promise<T> {
  const { token, ...init } = options;
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(err.detail ?? "Request failed", res.status);
  }
  return res.json() as Promise<T>;
}

// ── Onboarding ────────────────────────────────────────────────────────────────
export const api = {
  onboarding: {
    start: (mode: "quick" | "deep", token: string) =>
      request("/onboarding/start", {
        method: "POST",
        body: JSON.stringify({ mode }),
        token,
      }),

    submit: (
      sessionId: string,
      answers: { question_id: string; option_id: string }[],
      token: string
    ) =>
      request("/onboarding/submit", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId, answers }),
        token,
      }),

    profile: (token: string) =>
      request("/onboarding/profile", { token }),
  },

  // ── Energy ────────────────────────────────────────────────────────────────
  energy: {
    checkin: (body: { sleep_quality: number; mood: number; energy_level: number; note?: string }, token: string) =>
      request("/energy/checkin", { method: "POST", body: JSON.stringify(body), token }),

    score: (token: string) =>
      request("/energy/score", { token }),
  },

  // ── Secretary ───────────────────────────────────────────────────────────────
  secretary: {
    generatePlan: (token: string, regenerate = false) =>
      request(`/secretary/plan${regenerate ? "?regenerate=true" : ""}`, { method: "POST", token }),

    planJobStatus: (jobId: string, token: string) =>
      request(`/secretary/plan/status/${encodeURIComponent(jobId)}`, { token }),

    todayPlan: (token: string) =>
      request("/secretary/plan/today", { token }),

    acceptPlan: (planId: string, token: string) =>
      request(`/secretary/plan/${planId}/accept`, { method: "POST", token }),
  },

  // ── Planning Goals ──────────────────────────────────────────────────────────
  goals: {
    list: (token: string, horizon?: string) =>
      request(`/planning/goals${horizon ? `?horizon=${horizon}` : ""}`, { token }),

    create: (body: { title: string; horizon: string; description?: string; parent_id?: string }, token: string) =>
      request("/planning/goals", { method: "POST", body: JSON.stringify(body), token }),

    complete: (goalId: string, token: string) =>
      request(`/planning/goals/${goalId}/complete`, { method: "POST", token }),
  },

  // ── Agents ──────────────────────────────────────────────────────────────────
  agents: {
    createSession: (body: { entity_type: string; session_mode: string }, token: string) =>
      request("/agents/sessions", { method: "POST", body: JSON.stringify(body), token }),

    sendMessage: (sessionId: string, content: string, token: string) =>
      request(`/agents/sessions/${sessionId}/message`, {
        method: "POST",
        body: JSON.stringify({ content }),
        token,
      }),

    getMessages: (sessionId: string, token: string) =>
      request(`/agents/sessions/${sessionId}/messages`, { token }),
  },

  // ── Deposits ─────────────────────────────────────────────────────────────────
  deposits: {
    list: (token: string) => request("/deposits", { token }),

    create: (body: { step_id: string; amount_cents: number; currency: string; due_date: string }, token: string) =>
      request("/deposits", { method: "POST", body: JSON.stringify(body), token }),

    release: (depositId: string, token: string) =>
      request(`/deposits/${depositId}/release`, { method: "POST", token }),

    forfeit: (depositId: string, token: string) =>
      request(`/deposits/${depositId}/forfeit`, { method: "POST", token }),
  },

  // ── Admin Config ─────────────────────────────────────────────────────────────
  config: {
    list: (token: string) => request("/admin/config", { token }),

    get: (key: string, token: string) => request(`/admin/config/${key}`, { token }),

    set: (
      key: string,
      body: { value: string; is_secret: boolean; description: string; category: string },
      token: string
    ) => request(`/admin/config/${key}`, { method: "PUT", body: JSON.stringify(body), token }),
  },

  // ── Commands / Inbox ────────────────────────────────────────────────────────
  commands: {
    list: (token: string, params?: { status_filter?: string; limit?: number; offset?: number }) => {
      const q = new URLSearchParams();
      if (params?.status_filter) q.set("status_filter", params.status_filter);
      if (params?.limit) q.set("limit", String(params.limit));
      if (params?.offset) q.set("offset", String(params.offset));
      const qs = q.toString();
      return request(`/commands${qs ? `?${qs}` : ""}`, { token });
    },

    create: (
      body: { raw_payload_ref: string; ingress_channel?: string; ingress_modality?: string; idempotency_key: string },
      token: string
    ) => request("/commands", { method: "POST", body: JSON.stringify(body), token }),

    getAnalysis: (commandId: string, token: string) =>
      request(`/commands/${commandId}/analysis`, { token }),

    confirm: (commandId: string, decision: "confirmed" | "deferred", note: string | undefined, token: string) =>
      request(`/commands/${commandId}/confirm`, {
        method: "POST",
        body: JSON.stringify({ decision, note }),
        token,
      }),
  },

  // ── Habits ──────────────────────────────────────────────────────────────────
  habits: {
    list: (token: string) =>
      request("/habits", { token }),

    create: (
      body: {
        title: string;
        frequency?: string;
        category?: string;
        estimated_minutes?: number;
        target_time?: string;
        include_in_plan?: boolean;
      },
      token: string
    ) => request("/habits", { method: "POST", body: JSON.stringify(body), token }),

    update: (
      habitId: string,
      body: { title?: string; include_in_plan?: boolean; category?: string },
      token: string
    ) => request(`/habits/${habitId}`, { method: "PUT", body: JSON.stringify(body), token }),

    delete: (habitId: string, token: string) =>
      request(`/habits/${habitId}`, { method: "DELETE", token }),

    checkin: (habitId: string, body: { note?: string; quality?: number }, token: string) =>
      request(`/habits/${habitId}/checkin`, {
        method: "POST",
        body: JSON.stringify(body),
        token,
      }),
  },

  // ── Reviews (планёрки) ──────────────────────────────────────────────────────
  reviews: {
    pending: (token: string) =>
      request("/reviews/pending", { token }),

    history: (token: string, limit = 20, offset = 0) =>
      request(`/reviews/history?limit=${limit}&offset=${offset}`, { token }),

    get: (sessionId: string, token: string) =>
      request(`/reviews/${sessionId}`, { token }),

    start: (sessionId: string, token: string) =>
      request(`/reviews/${sessionId}/start`, { method: "POST", token }),

    complete: (
      sessionId: string,
      body: {
        answers?: Record<string, string>;
        plan_confirmed?: boolean;
        plan_adjustments?: unknown[] | null;
        user_notes?: string | null;
      },
      token: string
    ) =>
      request(`/reviews/${sessionId}/complete`, {
        method: "POST",
        body: JSON.stringify(body),
        token,
      }),

    triggerDaily: (token: string) =>
      request("/reviews/daily", { method: "POST", token }),
  },

  // ── Morning Brief ────────────────────────────────────────────────────────────
  brief: {
    today: (token: string) =>
      request("/brief/today", { token }),

    regenerate: (token: string) =>
      request("/brief/regenerate", { method: "POST", token }),
  },

  // ── Admin Agents ────────────────────────────────────────────────────────────
  adminAgents: {
    list: (token: string) =>
      request("/admin/agents", { token }),

    create: (
      body: {
        name: string;
        display_name: string;
        entity_type: string;
        avatar_emoji?: string;
        description?: string;
        system_prompt?: string;
        behavior_rules?: string[];
        tone_style?: Record<string, unknown>;
        preferred_tier?: number;
      },
      token: string
    ) => request("/admin/agents", { method: "POST", body: JSON.stringify(body), token }),

    update: (
      entityType: string,
      body: {
        display_name?: string;
        avatar_emoji?: string;
        description?: string;
        system_prompt?: string;
        behavior_rules?: string[];
        tone_style?: Record<string, unknown>;
        preferred_tier?: number;
        is_enabled?: boolean;
      },
      token: string
    ) =>
      request(`/admin/agents/${entityType}`, {
        method: "PUT",
        body: JSON.stringify(body),
        token,
      }),

    disable: (entityType: string, token: string) =>
      request(`/admin/agents/${entityType}`, { method: "DELETE", token }),

    train: (entityType: string, context: string, token: string) =>
      request(`/admin/agents/${entityType}/train`, {
        method: "POST",
        body: JSON.stringify({ context }),
        token,
      }),

    addKnowledge: (entityType: string, title: string, content: string, token: string) =>
      request(`/admin/agents/${entityType}/knowledge`, {
        method: "POST",
        body: JSON.stringify({ title, content }),
        token,
      }),

    removeKnowledge: (entityType: string, idx: number, token: string) =>
      request(`/admin/agents/${entityType}/knowledge/${idx}`, {
        method: "DELETE",
        token,
      }),
  },

  // ── Admin stats ──────────────────────────────────────────────────────────────
  admin: {
    health: (token: string) => request("/admin/health", { token }),
    aiStats: (token: string) => request("/admin/ai-stats", { token }),
    audit: (token: string, limit = 50) => request(`/admin/audit?limit=${limit}`, { token }),
  },

  // ── Users (GDPR) ─────────────────────────────────────────────────────────────
  users: {
    exportData: (token: string) => request("/users/me/export", { token }),

    deleteAccount: (token: string) =>
      request("/users/me", {
        method: "DELETE",
        token,
        headers: { "X-Confirm-Delete": "DELETE MY ACCOUNT" },
      }),
  },

  // ── Telegram linking ──────────────────────────────────────────────────────
  telegram: {
    getLinkToken: (token: string) => request("/telegram/link-token", { token }),
  },

  // ── Steps + Witness ───────────────────────────────────────────────────────
  steps: {
    listAll: (token: string) =>
      request("/steps", { token }),

    listQuick: (token: string, maxMinutes = 15) =>
      request(`/steps/quick-queue?max_minutes=${maxMinutes}`, { token }),

    createWitness: (
      stepId: string,
      body: { witness_type: string; witness_timestamp: string; verification_class: string },
      token: string
    ) =>
      request(`/steps/${stepId}/witness`, {
        method: "POST",
        body: JSON.stringify(body),
        token,
      }),
  },

  // ── Governance ADR ───────────────────────────────────────────────────────
  governance: {
    getPolicy: (token: string) =>
      request("/governance/policy", { token }),

    updatePolicy: (body: { mode: "solo" | "x2"; partner_email?: string | null }, token: string) =>
      request("/governance/policy", { method: "PUT", body: JSON.stringify(body), token }),

    createRecord: (body: { subject: string; reason: string }, token: string) =>
      request("/governance/records", { method: "POST", body: JSON.stringify(body), token }),

    listRecords: (token: string, limit = 50) =>
      request(`/governance/records?limit=${limit}`, { token }),

    approveRecord: (recordId: string, approvalToken: string, token: string) =>
      request(`/governance/records/${recordId}/approve?token=${encodeURIComponent(approvalToken)}`, {
        method: "POST",
        token,
      }),
  },

  // ── Team ─────────────────────────────────────────────────────────────────
  team: {
    listInvitations: (token: string) =>
      request("/team/invitations", { token }),

    createInvitation: (email: string, token: string) =>
      request("/team/invitations", { method: "POST", body: JSON.stringify({ email }), token }),

    revokeInvitation: (id: string, token: string) =>
      request(`/team/invitations/${id}`, { method: "DELETE", token }),

    lookupInvitation: (invToken: string) =>
      request(`/team/invitations/lookup?token=${encodeURIComponent(invToken)}`),

    acceptInvitation: (invToken: string, authToken: string) =>
      request(`/team/invitations/accept?token=${encodeURIComponent(invToken)}`, {
        method: "POST",
        token: authToken,
      }),
  },

  // ── System Mode ──────────────────────────────────────────────────────────
  modes: {
    current: (token: string) =>
      request("/mode/current", { token }),

    switch: (body: { mode: string; reason?: string }, token: string) =>
      request("/mode/switch", { method: "POST", body: JSON.stringify(body), token }),
  },

  // ── Calendar ──────────────────────────────────────────────────────────────
  calendar: {
    events: (token: string, daysAhead = 7) =>
      request(`/calendar/events?days_ahead=${daysAhead}`, { token }),

    integrations: (token: string) =>
      request("/calendar/integrations", { token }),

    connectCalDAV: (
      body: { display_name: string; calendar_url: string; username: string; password: string },
      token: string
    ) => request("/calendar/integrations/caldav", { method: "POST", body: JSON.stringify(body), token }),

    connectICal: (
      body: { display_name: string; ical_url: string },
      token: string
    ) => request("/calendar/integrations/ical", { method: "POST", body: JSON.stringify(body), token }),

    startGoogleOAuth: (token: string) =>
      request("/calendar/integrations/google", { method: "POST", token }),

    startMicrosoftOAuth: (token: string) =>
      request("/calendar/integrations/microsoft", { method: "POST", token }),

    disconnect: (integrationId: string, token: string) =>
      request(`/calendar/integrations/${integrationId}`, { method: "DELETE", token }),
  },

  // ── Subscriptions / Tiers ─────────────────────────────────────────────────
  subscriptions: {
    current: (token: string) =>
      request("/subscriptions/current", { token }),

    checkout: (
      body: { plan: "pro" | "team"; success_url: string; cancel_url: string },
      token: string
    ) => request("/subscriptions/checkout", { method: "POST", body: JSON.stringify(body), token }),

    portal: (token: string, returnUrl?: string) =>
      request(
        `/subscriptions/portal${returnUrl ? `?return_url=${encodeURIComponent(returnUrl)}` : ""}`,
        { method: "POST", token }
      ),
  },
};
