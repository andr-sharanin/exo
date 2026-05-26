"use client";

import { useState, useOptimistic, useTransition } from "react";
import clsx from "clsx";
import { api } from "@/lib/api";
import type { Habit } from "@/lib/types";

const CATEGORY_COLOR: Record<string, string> = {
  health:       "bg-green-900/50 text-green-400",
  learning:     "bg-blue-900/50 text-blue-400",
  mindfulness:  "bg-purple-900/50 text-purple-400",
  productivity: "bg-amber-900/50 text-amber-400",
  social:       "bg-pink-900/50 text-pink-400",
  custom:       "bg-gray-800 text-gray-400",
};

const FREQ_LABEL: Record<string, string> = {
  daily:    "каждый день",
  weekdays: "пн–пт",
  weekly:   "еженедельно",
  custom:   "выборочно",
};

// ── Streak badge ──────────────────────────────────────────────────────────────
function StreakBadge({ streak }: { streak: number }) {
  if (streak === 0) return <span className="text-xs text-gray-600">0 дней</span>;
  return (
    <span className={clsx(
      "text-xs font-semibold",
      streak >= 7  ? "text-orange-400" :
      streak >= 3  ? "text-amber-400" :
                     "text-gray-400"
    )}>
      {streak >= 7 ? "🔥" : streak >= 3 ? "⚡" : "◉"} {streak}
    </span>
  );
}

// ── Single habit card ─────────────────────────────────────────────────────────
function HabitCard({
  habit,
  token,
  onCheckin,
  onDelete,
}: {
  habit: Habit;
  token: string;
  onCheckin: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const [checking, setChecking] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  async function handleCheckin() {
    if (habit.checked_today || checking) return;
    setChecking(true);
    try {
      await api.habits.checkin(habit.id, {}, token);
      onCheckin(habit.id);
    } finally {
      setChecking(false);
    }
  }

  async function handleDelete() {
    if (!confirmDelete) { setConfirmDelete(true); return; }
    await api.habits.delete(habit.id, token);
    onDelete(habit.id);
  }

  return (
    <div
      className={clsx(
        "rounded-xl border px-4 py-3 transition-colors",
        habit.checked_today
          ? "bg-gray-900/50 border-gray-800/50"
          : "bg-gray-900 border-gray-800 hover:border-gray-700"
      )}
    >
      <div className="flex items-center gap-3">
        {/* Check button */}
        <button
          onClick={handleCheckin}
          disabled={habit.checked_today || checking}
          className={clsx(
            "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-all",
            habit.checked_today
              ? "bg-green-700 text-white cursor-default"
              : "border-2 border-gray-700 text-transparent hover:border-indigo-500 hover:text-indigo-500"
          )}
          title={habit.checked_today ? "Выполнено сегодня" : "Отметить выполненным"}
        >
          {habit.checked_today ? "✓" : checking ? "…" : "✓"}
        </button>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={clsx(
                "text-sm font-medium",
                habit.checked_today ? "text-gray-500 line-through" : "text-gray-200"
              )}
            >
              {habit.title}
            </span>
            {habit.category && (
              <span
                className={clsx(
                  "text-xs px-1.5 py-0.5 rounded-md font-medium",
                  CATEGORY_COLOR[habit.category] ?? CATEGORY_COLOR.custom
                )}
              >
                {habit.category}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-0.5">
            <span className="text-xs text-gray-600">{FREQ_LABEL[habit.frequency] ?? habit.frequency}</span>
            {habit.target_time && (
              <span className="text-xs text-gray-600">⏰ {habit.target_time}</span>
            )}
            {habit.estimated_minutes && (
              <span className="text-xs text-gray-600">{habit.estimated_minutes} мин</span>
            )}
          </div>
        </div>

        {/* Streak */}
        <StreakBadge streak={habit.streak} />

        {/* Delete */}
        <button
          onClick={handleDelete}
          onBlur={() => setConfirmDelete(false)}
          className={clsx(
            "text-xs px-2 py-1 rounded transition-colors ml-1",
            confirmDelete
              ? "bg-red-900/50 text-red-400 hover:bg-red-900"
              : "text-gray-700 hover:text-gray-500"
          )}
        >
          {confirmDelete ? "Удалить?" : "✕"}
        </button>
      </div>
    </div>
  );
}

// ── Add habit form ────────────────────────────────────────────────────────────
function AddHabitForm({
  token,
  onAdd,
  onCancel,
}: {
  token: string;
  onAdd: (habit: Habit) => void;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("");
  const [frequency, setFrequency] = useState("daily");
  const [minutes, setMinutes] = useState(10);
  const [time, setTime] = useState("");
  const [inPlan, setInPlan] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setLoading(true);
    setError("");
    try {
      const habit = await api.habits.create(
        {
          title: title.trim(),
          frequency,
          category: category || undefined,
          estimated_minutes: minutes,
          target_time: time || undefined,
          include_in_plan: inPlan,
        },
        token
      ) as Habit;
      onAdd(habit);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl bg-gray-900 border border-indigo-800/50 p-4 space-y-3"
    >
      <p className="text-xs text-indigo-400 font-medium uppercase tracking-wide">
        Новая привычка
      </p>

      <input
        autoFocus
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Что нужно делать каждый день?"
        className="w-full rounded-lg bg-gray-800 border border-gray-700 text-sm text-gray-200 px-3 py-2 focus:outline-none focus:border-indigo-500"
        required
      />

      <div className="grid grid-cols-2 gap-2">
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="rounded-lg bg-gray-800 border border-gray-700 text-sm text-gray-400 px-3 py-2 focus:outline-none focus:border-indigo-500"
        >
          <option value="">Категория</option>
          {["health", "learning", "mindfulness", "productivity", "social", "custom"].map(
            (c) => <option key={c} value={c}>{c}</option>
          )}
        </select>

        <select
          value={frequency}
          onChange={(e) => setFrequency(e.target.value)}
          className="rounded-lg bg-gray-800 border border-gray-700 text-sm text-gray-400 px-3 py-2 focus:outline-none focus:border-indigo-500"
        >
          <option value="daily">Каждый день</option>
          <option value="weekdays">Пн–Пт</option>
          <option value="weekly">Еженедельно</option>
        </select>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="flex items-center gap-2">
          <input
            type="number"
            value={minutes}
            onChange={(e) => setMinutes(Number(e.target.value))}
            min={1}
            max={480}
            className="w-full rounded-lg bg-gray-800 border border-gray-700 text-sm text-gray-400 px-3 py-2 focus:outline-none focus:border-indigo-500"
            placeholder="Минут"
          />
        </div>
        <input
          type="time"
          value={time}
          onChange={(e) => setTime(e.target.value)}
          className="rounded-lg bg-gray-800 border border-gray-700 text-sm text-gray-400 px-3 py-2 focus:outline-none focus:border-indigo-500"
        />
      </div>

      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={inPlan}
          onChange={(e) => setInPlan(e.target.checked)}
          className="rounded"
        />
        <span className="text-xs text-gray-400">Включать в план дня</span>
      </label>

      {error && <p className="text-xs text-red-400">{error}</p>}

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={loading || !title.trim()}
          className="flex-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium py-2 transition-colors"
        >
          {loading ? "…" : "Добавить"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 text-sm px-4 py-2 transition-colors"
        >
          Отмена
        </button>
      </div>
    </form>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export function HabitsList({
  initialHabits,
  token,
}: {
  initialHabits: Habit[];
  token: string;
}) {
  const [habits, setHabits] = useState(initialHabits);
  const [showAdd, setShowAdd] = useState(false);

  function handleCheckin(id: string) {
    setHabits((prev) =>
      prev.map((h) =>
        h.id === id ? { ...h, checked_today: true, streak: h.streak + 1 } : h
      )
    );
  }

  function handleDelete(id: string) {
    setHabits((prev) => prev.filter((h) => h.id !== id));
  }

  function handleAdd(habit: Habit) {
    setHabits((prev) => [...prev, habit]);
    setShowAdd(false);
  }

  const done = habits.filter((h) => h.checked_today).length;
  const total = habits.length;

  return (
    <div className="space-y-4">
      {/* Progress summary */}
      {total > 0 && (
        <div className="flex items-center gap-3">
          <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500 rounded-full transition-all duration-500"
              style={{ width: `${total > 0 ? (done / total) * 100 : 0}%` }}
            />
          </div>
          <span className="text-xs text-gray-500 flex-shrink-0">
            {done}/{total} сегодня
          </span>
        </div>
      )}

      {/* Habits list */}
      {habits.length === 0 && !showAdd ? (
        <div className="rounded-xl border border-dashed border-gray-700 p-8 text-center">
          <p className="text-gray-500 text-sm">Нет привычек</p>
          <p className="text-xs text-gray-600 mt-1">Добавь первую привычку для отслеживания</p>
        </div>
      ) : (
        <div className="space-y-2">
          {habits.map((h) => (
            <HabitCard
              key={h.id}
              habit={h}
              token={token}
              onCheckin={handleCheckin}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      {/* Add form or button */}
      {showAdd ? (
        <AddHabitForm
          token={token}
          onAdd={handleAdd}
          onCancel={() => setShowAdd(false)}
        />
      ) : (
        <button
          onClick={() => setShowAdd(true)}
          className="w-full rounded-xl border border-dashed border-gray-700 hover:border-indigo-600 text-gray-600 hover:text-indigo-400 text-sm py-3 transition-colors"
        >
          + Добавить привычку
        </button>
      )}
    </div>
  );
}
