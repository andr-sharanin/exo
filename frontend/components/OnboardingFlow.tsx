"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import clsx from "clsx";
import { api } from "@/lib/api";
import type { OnboardingQuestion, OnboardingMode, OnboardingStartResponse } from "@/lib/types";

type Phase = "mode_select" | "questions" | "processing" | "complete";

const MODE_INFO = {
  quick: {
    label: "Быстрый",
    duration: "~10 минут",
    count: "7 вопросов",
    description: "Базовый поведенческий профиль. Подходит для старта.",
    icon: "⚡",
  },
  deep: {
    label: "Глубокий",
    duration: "~45 минут",
    count: "12 вопросов",
    description: "Полный профиль со всеми 9 измерениями. Точнее рекомендации.",
    icon: "🔬",
  },
};

const OPTION_LABELS = ["A", "B", "C", "D"];

export function OnboardingFlow({ token }: { token: string }) {
  const router = useRouter();

  const [phase, setPhase] = useState<Phase>("mode_select");
  const [sessionId, setSessionId] = useState("");
  const [questions, setQuestions] = useState<OnboardingQuestion[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Phase: mode select ────────────────────────────────────────────────────
  async function handleModeSelect(mode: OnboardingMode) {
    setLoading(true);
    setError(null);
    try {
      const data = (await api.onboarding.start(mode, token)) as OnboardingStartResponse;
      setSessionId(data.session_id);
      setQuestions(data.questions);
      setCurrentIndex(0);
      setAnswers({});
      setPhase("questions");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось начать онбординг");
    } finally {
      setLoading(false);
    }
  }

  // ── Phase: question navigation ────────────────────────────────────────────
  function handleAnswer(questionId: string, optionId: string) {
    const next = { ...answers, [questionId]: optionId };
    setAnswers(next);

    // Auto-advance to next question after brief delay
    if (currentIndex < questions.length - 1) {
      setTimeout(() => setCurrentIndex((i) => i + 1), 300);
    }
  }

  function handleBack() {
    if (currentIndex > 0) setCurrentIndex((i) => i - 1);
  }

  // ── Phase: submit ─────────────────────────────────────────────────────────
  async function handleSubmit() {
    setPhase("processing");
    setError(null);
    try {
      const answerList = Object.entries(answers).map(([question_id, option_id]) => ({
        question_id,
        option_id,
      }));
      await api.onboarding.submit(sessionId, answerList, token);
      setPhase("complete");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка при отправке ответов");
      setPhase("questions");
    }
  }

  const currentQ = questions[currentIndex];
  const allAnswered = questions.length > 0 && questions.every((q) => answers[q.question_id]);
  const progress = questions.length > 0 ? ((currentIndex + 1) / questions.length) * 100 : 0;

  // ── Render: mode select ───────────────────────────────────────────────────
  if (phase === "mode_select") {
    return (
      <div className="space-y-8">
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold text-white">Настройка ExoCortex</h1>
          <p className="text-gray-400">
            Пройди интервью — система научится работать именно под тебя
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {(["quick", "deep"] as OnboardingMode[]).map((mode) => {
            const info = MODE_INFO[mode];
            return (
              <button
                key={mode}
                onClick={() => handleModeSelect(mode)}
                disabled={loading}
                className={clsx(
                  "group relative rounded-2xl border p-6 text-left transition-all",
                  "bg-gray-900 border-gray-800 hover:border-indigo-500 hover:bg-gray-800/80",
                  "disabled:opacity-50 disabled:cursor-not-allowed"
                )}
              >
                <div className="text-3xl mb-3">{info.icon}</div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-base font-semibold text-white">{info.label}</span>
                  <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded-full">
                    {info.count}
                  </span>
                </div>
                <p className="text-xs text-indigo-400 font-medium mb-2">{info.duration}</p>
                <p className="text-sm text-gray-400">{info.description}</p>
              </button>
            );
          })}
        </div>

        {error && (
          <p className="text-sm text-red-400 text-center">{error}</p>
        )}

        <p className="text-center text-xs text-gray-600">
          Можно пройти повторно в любое время через настройки
        </p>
      </div>
    );
  }

  // ── Render: processing ────────────────────────────────────────────────────
  if (phase === "processing") {
    return (
      <div className="text-center space-y-6 py-12">
        <div className="text-5xl animate-pulse">🧠</div>
        <div>
          <h2 className="text-xl font-semibold text-white">Формируется твой профиль...</h2>
          <p className="text-sm text-gray-500 mt-2">
            AI анализирует ответы и строит поведенческое ядро
          </p>
        </div>
      </div>
    );
  }

  // ── Render: complete ──────────────────────────────────────────────────────
  if (phase === "complete") {
    return (
      <div className="text-center space-y-6 py-8">
        <div className="text-6xl">✅</div>
        <div className="space-y-2">
          <h2 className="text-2xl font-bold text-white">Профиль создан</h2>
          <p className="text-gray-400">
            Поведенческое ядро сформировано. Теперь каждая задача будет анализироваться
            через твой профиль перед выполнением.
          </p>
        </div>

        <div className="rounded-xl bg-gray-900 border border-gray-800 p-5 text-left space-y-2">
          <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">
            Что дальше
          </p>
          {[
            "Определи цели (vision → year → quarter → week)",
            "Пройди утреннюю планёрку для первого плана дня",
            "Добавь первые привычки",
          ].map((item, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className="text-indigo-400 mt-0.5">→</span>
              <p className="text-sm text-gray-300">{item}</p>
            </div>
          ))}
        </div>

        <button
          onClick={() => router.push("/dashboard")}
          className="w-full rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-3 transition-colors"
        >
          Открыть Dashboard
        </button>
      </div>
    );
  }

  // ── Render: questions ─────────────────────────────────────────────────────
  if (!currentQ) return null;

  return (
    <div className="space-y-6">
      {/* Progress */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>
            Вопрос {currentIndex + 1} из {questions.length}
          </span>
          <button
            onClick={() => setPhase("mode_select")}
            className="hover:text-gray-300 transition-colors"
          >
            Изменить режим
          </button>
        </div>
        <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-indigo-500 rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Scenario */}
      <div className="rounded-2xl bg-gray-900 border border-gray-800 p-6">
        <p className="text-base text-gray-200 leading-relaxed">
          {currentQ.scenario}
        </p>
      </div>

      {/* Options */}
      <div className="space-y-3">
        {currentQ.options.map((opt, i) => {
          const selected = answers[currentQ.question_id] === opt.option_id;
          return (
            <button
              key={opt.option_id}
              onClick={() => handleAnswer(currentQ.question_id, opt.option_id)}
              className={clsx(
                "w-full flex items-start gap-4 rounded-xl border px-4 py-3.5 text-left transition-all",
                selected
                  ? "border-indigo-500 bg-indigo-950/50 text-white"
                  : "border-gray-800 bg-gray-900 text-gray-300 hover:border-gray-600 hover:bg-gray-800/80"
              )}
            >
              <span
                className={clsx(
                  "flex-shrink-0 w-6 h-6 rounded-md flex items-center justify-center text-xs font-bold mt-0.5",
                  selected ? "bg-indigo-600 text-white" : "bg-gray-800 text-gray-500"
                )}
              >
                {OPTION_LABELS[i]}
              </span>
              <span className="text-sm leading-relaxed">{opt.text}</span>
            </button>
          );
        })}
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between pt-2">
        <button
          onClick={handleBack}
          disabled={currentIndex === 0}
          className="text-sm text-gray-500 hover:text-gray-300 disabled:opacity-0 transition-colors"
        >
          ← Назад
        </button>

        {currentIndex < questions.length - 1 ? (
          <button
            onClick={() => setCurrentIndex((i) => i + 1)}
            disabled={!answers[currentQ.question_id]}
            className={clsx(
              "text-sm px-5 py-2 rounded-lg transition-colors",
              answers[currentQ.question_id]
                ? "bg-gray-800 hover:bg-gray-700 text-gray-200"
                : "text-gray-600 cursor-not-allowed"
            )}
          >
            Далее →
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={!allAnswered}
            className={clsx(
              "text-sm px-6 py-2 rounded-lg font-semibold transition-colors",
              allAnswered
                ? "bg-indigo-600 hover:bg-indigo-500 text-white"
                : "bg-gray-800 text-gray-600 cursor-not-allowed"
            )}
          >
            Завершить
          </button>
        )}
      </div>

      {error && (
        <p className="text-sm text-red-400 text-center">{error}</p>
      )}
    </div>
  );
}
