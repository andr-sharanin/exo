"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import clsx from "clsx";
import { api } from "@/lib/api";
import type { ReviewSessionDetail, AIPlanItem, ReviewQuestion } from "@/lib/types";

const TYPE_LABELS: Record<string, string> = {
  daily: "Утренняя планёрка",
  weekly: "Еженедельная планёрка",
  monthly: "Ежемесячная планёрка",
};

const TYPE_ICON: Record<string, string> = {
  daily: "☀️",
  weekly: "📅",
  monthly: "🗓️",
};

// ── Plan item row ──────────────────────────────────────────────────────────────
function PlanItemRow({ item, index }: { item: AIPlanItem; index: number }) {
  return (
    <div className="flex items-start gap-3 py-3 border-b border-gray-800 last:border-0">
      <span className="w-5 text-xs text-gray-600 text-right tabular-nums mt-0.5">{index + 1}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-200">{item.title}</p>
        {item.reason && (
          <p className="text-xs text-gray-500 mt-0.5">{item.reason}</p>
        )}
      </div>
      {item.estimated_minutes > 0 && (
        <span className="text-xs text-gray-500 flex-shrink-0 mt-0.5">
          {item.estimated_minutes} мин
        </span>
      )}
    </div>
  );
}

// ── Question input ─────────────────────────────────────────────────────────────
function QuestionInput({
  question,
  value,
  onChange,
}: {
  question: ReviewQuestion;
  value: string;
  onChange: (val: string) => void;
}) {
  if (question.answer_type === "confirm_plan") return null; // handled by confirm button
  if (question.answer_type === "scale_1_5") {
    return (
      <div className="space-y-2">
        <p className="text-sm text-gray-300">{question.text}</p>
        <div className="flex gap-2">
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => onChange(String(n))}
              className={clsx(
                "w-9 h-9 rounded-lg text-sm font-medium transition-colors",
                value === String(n)
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-800 text-gray-400 hover:bg-gray-700"
              )}
            >
              {n}
            </button>
          ))}
        </div>
      </div>
    );
  }
  return (
    <div className="space-y-2">
      <p className="text-sm text-gray-300">{question.text}</p>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={3}
        className="w-full rounded-lg bg-gray-800 border border-gray-700 text-sm text-gray-200 px-3 py-2 focus:outline-none focus:border-indigo-500 resize-none"
        placeholder="Ваш ответ..."
      />
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────
export function ReviewSessionCard({
  session: initial,
  token,
}: {
  session: ReviewSessionDetail;
  token: string;
}) {
  const router = useRouter();
  const [session, setSession] = useState(initial);
  const [answers, setAnswers] = useState<Record<string, string>>(initial.answers ?? {});
  const [userNotes, setUserNotes] = useState(initial.user_notes ?? "");
  const [loading, setLoading] = useState(false);
  const [phase, setPhase] = useState<"agenda" | "questions" | "done">(
    initial.status === "completed" ? "done" : "agenda"
  );

  const isDaily = session.review_type === "daily";
  const questions = (session.questions ?? []).filter((q) => q.answer_type !== "confirm_plan");
  const planItems = session.ai_plan_suggestion ?? [];

  async function handleStart() {
    if (session.status !== "pending") { setPhase("questions"); return; }
    setLoading(true);
    try {
      const updated = await api.reviews.start(session.id, token) as ReviewSessionDetail;
      setSession({ ...session, ...updated });
      setPhase("questions");
    } finally {
      setLoading(false);
    }
  }

  async function handleComplete(planConfirmed: boolean) {
    setLoading(true);
    try {
      await api.reviews.complete(
        session.id,
        {
          answers,
          plan_confirmed: planConfirmed,
          user_notes: userNotes || null,
        },
        token
      );
      setPhase("done");
      router.refresh();
    } finally {
      setLoading(false);
    }
  }

  // ── Completed ───────────────────────────────────────────────────────────────
  if (phase === "done") {
    return (
      <div className="rounded-xl bg-gray-900 border border-gray-800 p-6 space-y-3">
        <div className="flex items-center gap-3">
          <span className="text-2xl">✅</span>
          <div>
            <h2 className="text-base font-semibold text-white">
              {TYPE_LABELS[session.review_type]} завершена
            </h2>
            <p className="text-xs text-gray-500">
              {session.review_type === "daily" && session.plan_confirmed
                ? "План дня подтверждён. Выполняй без сомнений."
                : "Ответы записаны."}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-gray-900 border border-gray-800 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-gray-800 bg-gray-900/80">
        <span className="text-xl">{TYPE_ICON[session.review_type]}</span>
        <div className="flex-1">
          <h2 className="text-sm font-semibold text-white">{TYPE_LABELS[session.review_type]}</h2>
          <p className="text-xs text-gray-500">
            {new Date(session.created_at).toLocaleDateString("ru-RU", {
              weekday: "long", day: "numeric", month: "long",
            })}
          </p>
        </div>
        <span
          className={clsx(
            "text-xs px-2 py-0.5 rounded-full font-medium",
            session.status === "in_progress"
              ? "bg-amber-900 text-amber-300"
              : "bg-gray-800 text-gray-400"
          )}
        >
          {session.status === "in_progress" ? "В процессе" : "Ожидает"}
        </span>
      </div>

      {/* Phase: Agenda */}
      {phase === "agenda" && (
        <div className="p-5 space-y-4">
          {/* AI Agenda */}
          {session.ai_agenda ? (
            <div className="rounded-lg bg-indigo-950/40 border border-indigo-800/40 px-4 py-3">
              <p className="text-xs text-indigo-400 font-medium mb-1.5">AI брифинг</p>
              <p className="text-sm text-gray-200 leading-relaxed whitespace-pre-wrap">
                {session.ai_agenda}
              </p>
            </div>
          ) : (
            <div className="rounded-lg bg-gray-800/50 px-4 py-3">
              <p className="text-sm text-gray-500">Брифинг готовится...</p>
            </div>
          )}

          {/* AI Plan (daily only) */}
          {isDaily && planItems.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-2">
                Предложенный план дня
              </p>
              <div className="rounded-lg bg-gray-800/50 border border-gray-800 px-4">
                {planItems.map((item, i) => (
                  <PlanItemRow key={i} item={item} index={i} />
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-1">
            <button
              onClick={handleStart}
              disabled={loading}
              className="flex-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium py-2.5 transition-colors"
            >
              {loading ? "…" : isDaily ? "Начать планёрку" : "Начать обзор"}
            </button>
            <button
              onClick={() => handleComplete(false)}
              disabled={loading}
              className="rounded-lg bg-gray-800 hover:bg-gray-700 disabled:opacity-50 text-gray-400 text-sm px-4 py-2.5 transition-colors"
            >
              Пропустить
            </button>
          </div>
        </div>
      )}

      {/* Phase: Questions */}
      {phase === "questions" && (
        <div className="p-5 space-y-5">
          {/* Plan reminder (daily) */}
          {isDaily && planItems.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-2">
                Предложенный план
              </p>
              <div className="rounded-lg bg-gray-800/50 border border-gray-800 px-4 mb-4">
                {planItems.map((item, i) => (
                  <PlanItemRow key={i} item={item} index={i} />
                ))}
              </div>
            </div>
          )}

          {/* Questions */}
          {questions.length > 0 && (
            <div className="space-y-4">
              {questions.map((q) => (
                <QuestionInput
                  key={q.id}
                  question={q}
                  value={answers[q.id] ?? ""}
                  onChange={(val) => setAnswers((prev) => ({ ...prev, [q.id]: val }))}
                />
              ))}
            </div>
          )}

          {/* Notes */}
          <div className="space-y-2">
            <p className="text-xs text-gray-500 font-medium">Заметки (опционально)</p>
            <textarea
              value={userNotes}
              onChange={(e) => setUserNotes(e.target.value)}
              rows={2}
              className="w-full rounded-lg bg-gray-800 border border-gray-700 text-sm text-gray-200 px-3 py-2 focus:outline-none focus:border-indigo-500 resize-none"
              placeholder="Что-то важное, о чём стоит помнить сегодня..."
            />
          </div>

          {/* Confirm / Skip */}
          {isDaily ? (
            <div className="space-y-2 pt-1">
              <button
                onClick={() => handleComplete(true)}
                disabled={loading}
                className="w-full rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-semibold py-3 transition-colors"
              >
                {loading ? "…" : "Подтвердить план и начать день"}
              </button>
              <p className="text-xs text-center text-gray-600">
                По принципу Парабеллума: подумал один раз — теперь просто выполняй
              </p>
            </div>
          ) : (
            <button
              onClick={() => handleComplete(false)}
              disabled={loading}
              className="w-full rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium py-2.5 transition-colors"
            >
              {loading ? "…" : "Завершить обзор"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
