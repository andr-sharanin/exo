"use client";

import { useState } from "react";
import type { PlanningGoal, Horizon } from "@/lib/types";
import { api, ApiError } from "@/lib/api";
import { UpgradeBanner } from "@/components/UpgradeBanner";
import { useRouter } from "next/navigation";
import clsx from "clsx";

const HORIZON_LABELS: Record<Horizon, string> = {
  vision: "🌟 Vision (5yr)",
  annual: "📅 Annual",
  quarterly: "📊 Quarterly",
  monthly: "🗓 Monthly",
  weekly: "📌 Weekly",
  daily: "⚡ Daily",
};

export function GoalsList({
  horizon,
  goals,
  token,
}: {
  horizon: Horizon;
  goals: PlanningGoal[];
  token: string;
}) {
  const router = useRouter();
  const [newTitle, setNewTitle] = useState("");
  const [adding, setAdding] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [createError, setCreateError] = useState<Error | null>(null);

  async function addGoal() {
    if (!newTitle.trim()) return;
    setAdding(true);
    setCreateError(null);
    try {
      await api.goals.create({ title: newTitle.trim(), horizon }, token);
      setNewTitle("");
      setShowForm(false);
      router.refresh();
    } catch (e) {
      setCreateError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      setAdding(false);
    }
  }

  async function completeGoal(id: string) {
    await api.goals.complete(id, token);
    router.refresh();
  }

  return (
    <div className="rounded-xl bg-gray-900 border border-gray-800">
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-800">
        <h2 className="text-sm font-semibold text-gray-300">{HORIZON_LABELS[horizon]}</h2>
        <button
          onClick={() => setShowForm((f) => !f)}
          className="text-xs text-indigo-400 hover:text-indigo-300"
        >
          + Add
        </button>
      </div>

      <div className="px-5">
        {goals.length === 0 && !showForm && (
          <p className="py-4 text-xs text-gray-600 text-center">No goals at this level</p>
        )}
        {goals.map((g) => (
          <div key={g.id} className="flex items-center gap-3 py-3 border-b border-gray-800 last:border-0">
            <span
              className={clsx(
                "w-2 h-2 rounded-full flex-shrink-0",
                g.status === "completed" ? "bg-green-500" : "bg-indigo-500"
              )}
            />
            <p
              className={clsx(
                "flex-1 text-sm",
                g.status === "completed" ? "line-through text-gray-600" : "text-gray-200"
              )}
            >
              {g.title}
            </p>
            {g.status === "active" && (
              <button
                onClick={() => completeGoal(g.id)}
                className="text-xs text-gray-600 hover:text-green-400 transition-colors"
              >
                ✓
              </button>
            )}
          </div>
        ))}

        {createError && (
          <div className="py-2">
            <UpgradeBanner error={createError} onDismiss={() => setCreateError(null)} />
            {!(createError instanceof ApiError && createError.isPaymentRequired) && (
              <p className="text-xs text-red-400 py-1">{createError instanceof Error ? createError.message : String(createError)}</p>
            )}
          </div>
        )}

        {showForm && (
          <div className="py-3 flex gap-2">
            <input
              autoFocus
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addGoal()}
              placeholder="Goal title…"
              className="flex-1 rounded-lg bg-gray-950 border border-gray-700 text-gray-100 text-sm px-3 py-1.5 focus:outline-none focus:border-indigo-500"
            />
            <button
              onClick={addGoal}
              disabled={adding}
              className="rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm px-4 py-1.5"
            >
              {adding ? "…" : "Add"}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="text-gray-600 hover:text-gray-400 text-sm px-2"
            >
              ✕
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
