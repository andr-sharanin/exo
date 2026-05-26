"use client";

import { useState, useCallback, useTransition } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useSSE } from "@/hooks/useSSE";
import { DailyPlanCard } from "@/components/DailyPlanCard";
import type { DayPlan } from "@/lib/types";

interface Props {
  initialPlan: DayPlan | null;
  token: string;
}

type GenState = "idle" | "queued" | "polling" | "done" | "error";

const POLL_INTERVAL_MS = 3_000;
const MAX_POLLS = 20; // 1 minute before giving up

export function PlanPageClient({ initialPlan, token }: Props) {
  const router = useRouter();
  const [plan, setPlan] = useState<DayPlan | null>(initialPlan);
  const [genState, setGenState] = useState<GenState>("idle");
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const [polls, setPolls] = useState(0);

  const fetchPlan = useCallback(async () => {
    try {
      const data = await api.secretary.todayPlan(token) as DayPlan;
      setPlan(data);
      setGenState("done");
      setJobId(null);
    } catch {
      // plan not ready yet — keep polling
    }
  }, [token]);

  // SSE handler — plan_ready triggers immediate refetch
  useSSE(useCallback((event) => {
    if (event.type === "plan_ready") {
      setGenState("done");
      fetchPlan();
    }
    if (event.type === "job_failed" && (event.payload as Record<string, string>).job === "generate_plan") {
      setGenState("error");
      setError("Генерация плана не удалась. Попробуй снова.");
    }
  }, [fetchPlan]));

  // Polling fallback when SSE isn't available or job is slow
  const startPolling = useCallback((jId: string) => {
    let count = 0;
    const interval = setInterval(async () => {
      count++;
      setPolls(count);

      try {
        const status = await api.secretary.planJobStatus(jId, token) as { status: string; result?: { plan_id?: string } };
        if (status.status === "complete") {
          clearInterval(interval);
          await fetchPlan();
          return;
        }
        if (status.status === "failed") {
          clearInterval(interval);
          setGenState("error");
          setError("Генерация плана завершилась с ошибкой.");
          return;
        }
      } catch {
        // ignore transient errors
      }

      if (count >= MAX_POLLS) {
        clearInterval(interval);
        setGenState("error");
        setError("Превышено время ожидания. Обнови страницу.");
      }
    }, POLL_INTERVAL_MS);
  }, [fetchPlan, token]);

  function handleGenerate(regenerate = false) {
    setError(null);
    setGenState("queued");
    startTransition(async () => {
      try {
        const res = await api.secretary.generatePlan(token, regenerate) as { job_id: string; status: string };
        setJobId(res.job_id);
        setGenState("polling");
        setPolls(0);
        startPolling(res.job_id);
      } catch (e) {
        setGenState("error");
        setError((e as Error).message);
      }
    });
  }

  const isGenerating = genState === "queued" || genState === "polling";

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Day Plan</h1>
        <div className="flex items-center gap-3">
          {isGenerating && (
            <span className="text-xs text-indigo-400 animate-pulse">
              {genState === "queued" ? "В очереди…" : `Генерирую… (${polls})`}
            </span>
          )}
          <button
            onClick={() => handleGenerate(!!plan)}
            disabled={isGenerating || isPending}
            className="text-sm rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-4 py-2 transition-colors"
          >
            {isGenerating ? (
              <span className="flex items-center gap-2">
                <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Генерирую
              </span>
            ) : plan ? "Пересобрать" : "Сгенерировать план"}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-800 bg-red-950 px-4 py-3">
          <p className="text-sm text-red-300">{error}</p>
          <button
            onClick={() => { setError(null); setGenState("idle"); }}
            className="text-xs text-red-500 mt-1 hover:text-red-400"
          >
            Закрыть
          </button>
        </div>
      )}

      {isGenerating && !plan && (
        <div className="rounded-xl border border-indigo-800 bg-indigo-950/30 p-8 text-center space-y-3">
          <div className="flex justify-center">
            <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          </div>
          <p className="text-sm text-indigo-300 font-medium">Секретарь строит твой план дня…</p>
          <p className="text-xs text-indigo-600">
            Анализирует энергию, режим и задачи. Обновится автоматически.
          </p>
        </div>
      )}

      {plan && !isGenerating ? (
        <DailyPlanCard plan={plan} token={token} showFull />
      ) : !plan && !isGenerating && (
        <div className="rounded-xl border border-dashed border-gray-700 p-12 text-center">
          <p className="text-gray-400">На сегодня нет плана.</p>
          <p className="text-sm text-gray-600 mt-2">
            Нажми «Сгенерировать план» — Секретарь составит расписание исходя из энергии и режима.
          </p>
        </div>
      )}
    </div>
  );
}
