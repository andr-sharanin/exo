"use client";

import { useState, useTransition } from "react";
import type { DayPlan, PlanItem } from "@/lib/types";
import { api } from "@/lib/api";
import Link from "next/link";
import clsx from "clsx";
import { useRouter } from "next/navigation";

const ENERGY_PILL = {
  low: "bg-green-900 text-green-300",
  medium: "bg-amber-900 text-amber-300",
  high: "bg-red-900 text-red-300",
};

const TYPE_ICON = {
  focus_step: "⚡",
  background_step: "📌",
  rescue_entry_step: "🚨",
};

function PlanItemRow({ item }: { item: PlanItem }) {
  return (
    <div className="flex items-center gap-3 py-3 border-b border-gray-800 last:border-0">
      <span className="text-xs text-gray-600 w-5 text-right tabular-nums">{item.order}</span>
      <span className="text-base">{TYPE_ICON[item.step_type]}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-200 truncate">{item.title}</p>
        {item.estimated_minutes && (
          <p className="text-xs text-gray-600">{item.estimated_minutes} min</p>
        )}
      </div>
      <span className={clsx("text-xs px-2 py-0.5 rounded-full font-medium", ENERGY_PILL[item.energy_cost])}>
        {item.energy_cost}
      </span>
      <Link href="/focus" className="text-xs text-indigo-500 hover:text-indigo-400 flex-shrink-0">
        ▶
      </Link>
    </div>
  );
}

export function DailyPlanCard({
  plan,
  token,
  showFull = false,
}: {
  plan: DayPlan;
  token: string;
  showFull?: boolean;
}) {
  const router = useRouter();
  const [accepting, setAccepting] = useState(false);
  const displayItems = showFull ? plan.items : plan.items.slice(0, 4);

  async function accept() {
    setAccepting(true);
    try {
      await api.secretary.acceptPlan(plan.id, token);
      router.refresh();
    } finally {
      setAccepting(false);
    }
  }

  return (
    <div className="rounded-xl bg-gray-900 border border-gray-800">
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-800">
        <div>
          <h2 className="text-sm font-semibold text-gray-200">Day Plan</h2>
          <p className="text-xs text-gray-600">
            {plan.total_estimated_minutes} min total · {plan.items.length} steps
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={clsx(
              "text-xs px-2 py-0.5 rounded-full font-medium",
              plan.status === "draft" ? "bg-gray-800 text-gray-400" : "bg-green-900 text-green-300"
            )}
          >
            {plan.status}
          </span>
          {plan.status === "draft" && (
            <button
              onClick={accept}
              disabled={accepting}
              className="text-xs rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-3 py-1 transition-colors"
            >
              {accepting ? "…" : "Accept"}
            </button>
          )}
        </div>
      </div>

      <div className="px-5">
        {plan.items.length === 0 ? (
          <p className="py-4 text-sm text-gray-600 text-center">No steps in plan</p>
        ) : (
          displayItems.map((item) => <PlanItemRow key={item.step_id} item={item} />)
        )}
        {!showFull && plan.items.length > 4 && (
          <Link
            href="/plan"
            className="block py-3 text-center text-sm text-indigo-500 hover:text-indigo-400"
          >
            +{plan.items.length - 4} more steps →
          </Link>
        )}
      </div>
    </div>
  );
}
