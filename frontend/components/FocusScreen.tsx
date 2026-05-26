"use client";

import { useState, useEffect, useRef } from "react";
import type { PlanItem } from "@/lib/types";
import { api } from "@/lib/api";
import Link from "next/link";

interface Props {
  items: PlanItem[];
  planId: string | null;
  token: string;
}

const ENERGY_COLORS = {
  low: "#22c55e",
  medium: "#f59e0b",
  high: "#ef4444",
} as const;

function LifeWormCircle({
  totalSeconds,
  elapsedSeconds,
  energyCost,
}: {
  totalSeconds: number;
  elapsedSeconds: number;
  energyCost: "low" | "medium" | "high";
}) {
  const R = 110;
  const CX = 140;
  const CY = 140;
  const circumference = 2 * Math.PI * R;
  const remaining = Math.max(0, totalSeconds - elapsedSeconds);
  const fraction = remaining / totalSeconds;
  const consumed = 1 - fraction;
  const color = ENERGY_COLORS[energyCost];

  // Worm head: leading edge of remaining arc
  const angle = (fraction * 360 - 90) * (Math.PI / 180);
  const headX = CX + R * Math.cos(angle);
  const headY = CY + R * Math.sin(angle);

  const pct = Math.round(fraction * 100);

  return (
    <svg width={280} height={280} className="drop-shadow-2xl">
      {/* Track */}
      <circle cx={CX} cy={CY} r={R} fill="none" stroke="#1f2937" strokeWidth={20} />

      {/* Consumed (eaten) arc — dark red */}
      <circle
        cx={CX} cy={CY} r={R} fill="none"
        stroke="#7f1d1d" strokeWidth={12}
        strokeDasharray={`${circumference * consumed} ${circumference * fraction}`}
        strokeDashoffset={0}
        strokeLinecap="butt"
        transform={`rotate(-90 ${CX} ${CY})`}
        style={{ transition: "stroke-dasharray 1s linear" }}
      />

      {/* Remaining time arc */}
      <circle
        cx={CX} cy={CY} r={R} fill="none"
        stroke={color} strokeWidth={18}
        strokeDasharray={`${circumference * fraction} ${circumference * consumed}`}
        strokeDashoffset={0}
        strokeLinecap="round"
        transform={`rotate(-90 ${CX} ${CY})`}
        style={{ transition: "stroke-dasharray 1s linear" }}
      />

      {/* Worm head */}
      <circle cx={headX} cy={headY} r={14} fill={color} />
      <circle cx={headX - 4} cy={headY - 3} r={3} fill="#111827" />
      <circle cx={headX + 4} cy={headY - 3} r={3} fill="#111827" />

      {/* Center: % remaining */}
      <text x={CX} y={CY - 14} textAnchor="middle" fill="white" fontSize={34} fontWeight="bold">
        {pct}%
      </text>
      <text x={CX} y={CY + 12} textAnchor="middle" fill="#9ca3af" fontSize={12}>
        осталось
      </text>
      {consumed > 0 && (
        <text x={CX} y={CY + 30} textAnchor="middle" fill="#7f1d1d" fontSize={11}>
          -{Math.round(consumed * 100)}% съедено
        </text>
      )}
    </svg>
  );
}

// ── Phase: pre-start briefing ────────────────────────────────────────────────

function PreStartCard({
  item,
  onStart,
  onSelectOther,
}: {
  item: PlanItem;
  onStart: () => void;
  onSelectOther: () => void;
}) {
  const energyLabel = { low: "🟢 Низкая", medium: "🟡 Средняя", high: "🔴 Высокая" }[item.energy_cost];

  return (
    <div className="flex flex-col items-center gap-6 max-w-sm w-full text-center">
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-widest text-gray-500">
          {item.step_type.replace(/_/g, " ")}
        </p>
        <h2 className="text-2xl font-bold text-white leading-snug">{item.title}</h2>
      </div>

      <div className="grid grid-cols-2 gap-3 w-full">
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-4">
          <p className="text-xs text-gray-500">Время</p>
          <p className="text-xl font-bold text-white mt-1">
            {item.estimated_minutes ?? 25} мин
          </p>
        </div>
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-4">
          <p className="text-xs text-gray-500">Энергозатраты</p>
          <p className="text-sm font-semibold text-white mt-1">{energyLabel}</p>
        </div>
      </div>

      <div className="flex flex-col gap-3 w-full">
        <button
          onClick={onStart}
          className="w-full rounded-xl py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-lg transition-colors"
        >
          ▶ Начать фокус
        </button>
        <button
          onClick={onSelectOther}
          className="text-sm text-gray-500 hover:text-gray-300"
        >
          Выбрать другую задачу
        </button>
      </div>

      <Link
        href="/chat/core_advisor"
        className="text-xs text-gray-600 hover:text-indigo-400 transition-colors"
      >
        🧠 Обсудить с Core Advisor перед стартом
      </Link>
    </div>
  );
}

// ── Phase: step selector ─────────────────────────────────────────────────────

function StepSelector({
  items,
  onSelect,
}: {
  items: PlanItem[];
  onSelect: (item: PlanItem) => void;
}) {
  const energyIcon = { low: "🟢", medium: "🟡", high: "🔴" };
  return (
    <div className="w-full max-w-md space-y-3">
      <h2 className="text-xl font-bold text-white text-center mb-4">Выбери задачу</h2>
      {items.map((item) => (
        <button
          key={item.step_id}
          onClick={() => onSelect(item)}
          className="w-full rounded-xl bg-gray-900 hover:bg-gray-800 border border-gray-800 p-4 text-left transition-colors"
        >
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm font-medium text-white leading-snug">{item.title}</span>
            <span className="text-xs flex-shrink-0">
              {energyIcon[item.energy_cost]} {item.estimated_minutes ?? "—"}м
            </span>
          </div>
        </button>
      ))}
      <Link
        href="/plan"
        className="block text-center text-sm text-gray-600 hover:text-gray-400 pt-2"
      >
        → Открыть план дня
      </Link>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

type Phase = "select" | "brief" | "focus" | "done";

export function FocusScreen({ items, planId, token }: Props) {
  const [phase, setPhase] = useState<Phase>(items.length === 1 ? "brief" : items.length > 1 ? "brief" : "select");
  const [activeItem, setActiveItem] = useState<PlanItem | null>(items[0] ?? null);
  const [elapsed, setElapsed] = useState(0);
  const [running, setRunning] = useState(false);
  const [isolated, setIsolated] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const totalSeconds = (activeItem?.estimated_minutes ?? 25) * 60;

  useEffect(() => {
    if (running && phase === "focus") {
      intervalRef.current = setInterval(() => {
        setElapsed((e) => {
          if (e + 1 >= totalSeconds) {
            setRunning(false);
            setPhase("done");
            // Record completion in backend
            if (activeItem) {
              const stepId = activeItem.step_id;
              const ts = new Date().toISOString();
              if (stepId.startsWith("habit:")) {
                const habitId = stepId.replace("habit:", "");
                api.habits.checkin(habitId, {}, token).catch(() => {});
              } else {
                api.steps.createWitness(
                  stepId,
                  { witness_type: "manual", witness_timestamp: ts, verification_class: "reported" },
                  token
                ).catch(() => {});
              }
            }
            return totalSeconds;
          }
          return e + 1;
        });
      }, 1000);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [running, phase, totalSeconds]);

  const minutes = Math.floor((totalSeconds - elapsed) / 60);
  const seconds = (totalSeconds - elapsed) % 60;

  function handleSelectItem(item: PlanItem) {
    setActiveItem(item);
    setElapsed(0);
    setRunning(false);
    setPhase("brief");
  }

  function handleStart() {
    setElapsed(0);
    setRunning(true);
    setPhase("focus");
  }

  const nextItem = activeItem
    ? items.find((it) => it.order === activeItem.order + 1) ?? null
    : null;

  const wrapper = isolated
    ? "fixed inset-0 z-50 bg-gray-950 flex flex-col items-center justify-center"
    : "flex flex-col items-center justify-center min-h-full gap-8 p-6 bg-gray-950";

  return (
    <div className={wrapper}>
      {/* Isolation toggle */}
      {phase === "focus" && (
        <button
          onClick={() => setIsolated((v) => !v)}
          title={isolated ? "Выйти из режима изоляции" : "Режим изоляции"}
          className="fixed top-4 right-4 z-50 text-xs text-gray-600 hover:text-gray-400"
        >
          {isolated ? "✕ выйти" : "⛶ изоляция"}
        </button>
      )}

      {phase === "select" && (
        items.length === 0 ? (
          <div className="flex flex-col items-center gap-6 text-center">
            <p className="text-gray-400 text-lg">Нет задач в плане на сегодня</p>
            <Link href="/plan" className="text-indigo-400 hover:text-indigo-300">
              → Перейти к плану дня
            </Link>
          </div>
        ) : (
          <StepSelector items={items} onSelect={handleSelectItem} />
        )
      )}

      {phase === "brief" && activeItem && (
        <PreStartCard
          item={activeItem}
          onStart={handleStart}
          onSelectOther={() => setPhase("select")}
        />
      )}

      {phase === "focus" && activeItem && (
        <>
          <div className="text-center max-w-md">
            <span className="text-xs uppercase tracking-widest text-gray-500">
              {activeItem.step_type.replace(/_/g, " ")}
            </span>
            <h2 className="text-xl font-bold text-white mt-2 leading-snug">{activeItem.title}</h2>
          </div>

          <LifeWormCircle
            totalSeconds={totalSeconds}
            elapsedSeconds={elapsed}
            energyCost={activeItem.energy_cost}
          />

          <div className="text-4xl font-mono font-bold text-white tabular-nums">
            {String(minutes).padStart(2, "0")}:{String(seconds).padStart(2, "0")}
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => setRunning((r) => !r)}
              className={`rounded-xl px-8 py-3 font-bold text-lg transition-colors ${
                running
                  ? "bg-gray-700 text-gray-300 hover:bg-gray-600"
                  : "bg-indigo-600 text-white hover:bg-indigo-500"
              }`}
            >
              {running ? "⏸ Пауза" : elapsed > 0 ? "▶ Продолжить" : "▶ Старт"}
            </button>
            {elapsed > 0 && (
              <button
                onClick={() => { setElapsed(0); setRunning(false); }}
                className="rounded-xl px-4 py-3 bg-gray-800 text-gray-400 hover:bg-gray-700"
              >
                ↺
              </button>
            )}
          </div>

          {!isolated && (
            <Link
              href="/chat/core_advisor"
              className="text-sm text-gray-600 hover:text-indigo-400 transition-colors"
            >
              🧠 Нужна помощь? Core Advisor
            </Link>
          )}
        </>
      )}

      {phase === "done" && activeItem && (
        <div className="flex flex-col items-center gap-6 text-center">
          <span className="text-6xl">✅</span>
          <div>
            <p className="text-xl font-bold text-white">Задача завершена!</p>
            <p className="text-sm text-gray-400 mt-1">{activeItem.title}</p>
          </div>

          {nextItem ? (
            <div className="space-y-3 w-full max-w-xs">
              <p className="text-xs text-gray-500 uppercase tracking-wide">Следующая</p>
              <button
                onClick={() => handleSelectItem(nextItem)}
                className="w-full rounded-xl bg-gray-900 border border-gray-700 hover:border-indigo-500 p-4 text-left transition-colors"
              >
                <p className="text-sm font-medium text-white">{nextItem.title}</p>
                <p className="text-xs text-gray-500 mt-0.5">{nextItem.estimated_minutes ?? 25} мин</p>
              </button>
            </div>
          ) : null}

          <div className="flex gap-3">
            <button
              onClick={() => { setElapsed(0); setRunning(false); setPhase("brief"); }}
              className="rounded-xl px-5 py-2.5 bg-gray-800 text-gray-300 hover:bg-gray-700 text-sm font-medium"
            >
              Ещё раз
            </button>
            <Link
              href="/dashboard"
              className="rounded-xl px-5 py-2.5 bg-green-600 hover:bg-green-500 text-white text-sm font-semibold"
            >
              → Дашборд
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
