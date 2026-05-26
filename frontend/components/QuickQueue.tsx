"use client";

import { useState, useCallback } from "react";
import { api } from "@/lib/api";
import type { StepObject } from "@/lib/types";
import clsx from "clsx";

const TYPE_BADGE: Record<string, string> = {
  focus_step: "text-indigo-400",
  background_step: "text-sky-400",
  rescue_entry_step: "text-amber-400",
};

const TYPE_LABEL: Record<string, string> = {
  focus_step: "фокус",
  background_step: "фон",
  rescue_entry_step: "срочно",
};

interface Props {
  initialSteps: StepObject[];
  token: string;
}

export function QuickQueue({ initialSteps, token }: Props) {
  const [steps, setSteps] = useState(initialSteps);
  const [completing, setCompleting] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [done, setDone] = useState<Set<string>>(new Set());

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const data = await api.steps.listQuick(token) as StepObject[];
      setSteps(data);
    } catch {
      // keep old list
    } finally {
      setRefreshing(false);
    }
  }, [token]);

  async function handleComplete(step: StepObject) {
    if (completing) return;
    setCompleting(step.id);
    try {
      const ts = new Date().toISOString();
      await api.steps.createWitness(
        step.id,
        { witness_type: "manual", witness_timestamp: ts, verification_class: "reported" },
        token
      );
      setDone((prev) => new Set(prev).add(step.id));
      // remove from list after brief animation delay
      setTimeout(() => {
        setSteps((prev) => prev.filter((s) => s.id !== step.id));
        setDone((prev) => { const n = new Set(prev); n.delete(step.id); return n; });
      }, 600);
    } catch {
      // ignore — show as not completed
    } finally {
      setCompleting(null);
    }
  }

  return (
    <div className="space-y-4">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-400">
          {steps.length === 0
            ? "Нет быстрых задач"
            : `${steps.length} задач${steps.length === 1 ? "а" : steps.length < 5 ? "и" : ""} ≤15 мин`}
        </p>
        <button
          onClick={refresh}
          disabled={refreshing}
          className="text-xs text-gray-500 hover:text-gray-300 transition-colors disabled:opacity-40"
        >
          {refreshing ? "Обновляю…" : "↻ Обновить"}
        </button>
      </div>

      {/* Steps */}
      {steps.length === 0 && (
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-8 text-center">
          <p className="text-2xl mb-2">✅</p>
          <p className="text-sm text-gray-500">Все быстрые задачи выполнены.</p>
          <p className="text-xs text-gray-600 mt-1">Создайте задачи ≤15 мин в Pipeline → Steps.</p>
        </div>
      )}

      <div className="space-y-2">
        {steps.map((step) => {
          const isDone = done.has(step.id);
          const isCompleting = completing === step.id;

          return (
            <div
              key={step.id}
              className={clsx(
                "flex items-center gap-4 rounded-xl border px-4 py-3 transition-all duration-300",
                isDone
                  ? "border-green-800 bg-green-950/40 opacity-60"
                  : "border-gray-700 bg-gray-900 hover:border-gray-600"
              )}
            >
              {/* Checkbox / done indicator */}
              <button
                onClick={() => handleComplete(step)}
                disabled={!!completing || isDone}
                className={clsx(
                  "flex-shrink-0 w-6 h-6 rounded-md border-2 flex items-center justify-center transition-all",
                  isDone
                    ? "border-green-500 bg-green-500"
                    : "border-gray-600 hover:border-indigo-500"
                )}
              >
                {isDone && <span className="text-white text-xs font-bold">✓</span>}
                {isCompleting && (
                  <span className="w-3 h-3 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
                )}
              </button>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <p
                  className={clsx(
                    "text-sm font-medium",
                    isDone ? "line-through text-gray-500" : "text-gray-100"
                  )}
                >
                  {step.title}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className={clsx("text-xs font-medium", TYPE_BADGE[step.step_type] ?? "text-gray-500")}>
                    {TYPE_LABEL[step.step_type] ?? step.step_type}
                  </span>
                  {step.estimated_minutes && (
                    <span className="text-xs text-gray-600">
                      {step.estimated_minutes} мин
                    </span>
                  )}
                </div>
              </div>

              {/* Action button */}
              {!isDone && (
                <button
                  onClick={() => handleComplete(step)}
                  disabled={!!completing}
                  className="flex-shrink-0 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-xs font-semibold px-3 py-1.5 transition-colors"
                >
                  {isCompleting ? "…" : "Готово"}
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
