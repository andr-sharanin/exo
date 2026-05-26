"use client";

import { useState, useTransition } from "react";
import { api } from "@/lib/api";
import clsx from "clsx";

interface Limits {
  max_active_goals: number | null;
  max_held_deposits: number | null;
  allow_x2_governance: boolean;
  max_calendar_integrations: number | null;
}

interface SubscriptionData {
  tier: string;
  status: string;
  current_period_end: string | null;
  trial_end: string | null;
  limits: Limits;
}

interface Props {
  initialData: SubscriptionData;
  token: string;
}

const TIER_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  free: { label: "Free", color: "text-gray-300", bg: "bg-gray-800" },
  pro: { label: "Pro", color: "text-indigo-300", bg: "bg-indigo-900/40" },
  team: { label: "Team", color: "text-purple-300", bg: "bg-purple-900/40" },
};

function LimitRow({ label, value }: { label: string; value: string | boolean }) {
  const isAllowed = value === true || (typeof value === "string" && value !== "0");
  const display =
    typeof value === "boolean"
      ? value ? "✓ Включено" : "✗ Недоступно"
      : value;

  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
      <span className="text-sm text-gray-400">{label}</span>
      <span
        className={clsx(
          "text-sm font-medium",
          typeof value === "boolean"
            ? value ? "text-green-400" : "text-gray-600"
            : "text-gray-200"
        )}
      >
        {display}
      </span>
    </div>
  );
}

export function SubscriptionPanel({ initialData, token }: Props) {
  const [data] = useState<SubscriptionData>(initialData);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const tierInfo = TIER_LABELS[data.tier] ?? TIER_LABELS.free;
  const isFree = data.tier === "free";

  function handleUpgrade(plan: "pro" | "team") {
    setError(null);
    startTransition(async () => {
      try {
        const origin = window.location.origin;
        const res = await api.subscriptions.checkout(
          {
            plan,
            success_url: `${origin}/settings/subscription?success=1`,
            cancel_url: `${origin}/settings/subscription?canceled=1`,
          },
          token
        ) as { checkout_url: string };
        window.location.href = res.checkout_url;
      } catch (e) {
        setError((e as Error).message);
      }
    });
  }

  function handlePortal() {
    setError(null);
    startTransition(async () => {
      try {
        const res = await api.subscriptions.portal(
          token,
          `${window.location.origin}/settings/subscription`
        ) as { portal_url: string };
        window.location.href = res.portal_url;
      } catch (e) {
        setError((e as Error).message);
      }
    });
  }

  return (
    <div className="space-y-6">
      {/* Current plan card */}
      <div className={clsx("rounded-xl border border-gray-700 p-5", tierInfo.bg)}>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Текущий тариф</p>
            <p className={clsx("text-3xl font-bold", tierInfo.color)}>{tierInfo.label}</p>
            {data.status !== "free" && (
              <p className="text-xs text-gray-500 mt-1 capitalize">{data.status}</p>
            )}
          </div>
          {!isFree && data.current_period_end && (
            <div className="text-right">
              <p className="text-xs text-gray-500">Активен до</p>
              <p className="text-sm text-gray-300">
                {new Date(data.current_period_end).toLocaleDateString("ru-RU", {
                  day: "numeric",
                  month: "long",
                  year: "numeric",
                })}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Limits */}
      <div className="rounded-xl border border-gray-800 bg-gray-900">
        <div className="px-5 py-3 border-b border-gray-800">
          <h2 className="text-sm font-semibold text-gray-300">Лимиты тарифа</h2>
        </div>
        <div className="px-5 py-2">
          <LimitRow
            label="Активных целей"
            value={data.limits.max_active_goals === null ? "Без ограничений" : String(data.limits.max_active_goals)}
          />
          <LimitRow
            label="Депозитов"
            value={data.limits.max_held_deposits === null ? "Без ограничений" : String(data.limits.max_held_deposits)}
          />
          <LimitRow
            label="Режим x2 (партнёр)"
            value={data.limits.allow_x2_governance}
          />
          <LimitRow
            label="Календарей"
            value={data.limits.max_calendar_integrations === null ? "Без ограничений" : String(data.limits.max_calendar_integrations)}
          />
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-xl border border-red-800 bg-red-950 px-4 py-3">
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      {/* Actions */}
      {isFree ? (
        <div className="space-y-3">
          <p className="text-sm text-gray-400">
            Upgrade для снятия всех ограничений: безлимитные цели, депозиты, режим x2, любое количество календарей.
          </p>
          <div className="flex gap-3">
            <button
              onClick={() => handleUpgrade("pro")}
              disabled={isPending}
              className="flex-1 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-semibold px-4 py-3 transition-colors"
            >
              {isPending ? "Перенаправляю…" : "Upgrade → Pro"}
            </button>
            <button
              onClick={() => handleUpgrade("team")}
              disabled={isPending}
              className="flex-1 rounded-xl bg-purple-700 hover:bg-purple-600 disabled:opacity-50 text-white text-sm font-semibold px-4 py-3 transition-colors"
            >
              {isPending ? "Перенаправляю…" : "Upgrade → Team"}
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={handlePortal}
          disabled={isPending}
          className="w-full rounded-xl border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white text-sm font-semibold px-4 py-3 transition-colors disabled:opacity-50"
        >
          {isPending ? "Открываю портал…" : "Управление подпиской →"}
        </button>
      )}
    </div>
  );
}
