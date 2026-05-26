"use client";

import { useState, useTransition } from "react";
import { api } from "@/lib/api";
import clsx from "clsx";

interface ModeInfo {
  key: string;
  label: string;
  emoji: string;
  description: string;
  hint: string;
}

const MODES: ModeInfo[] = [
  {
    key: "achiever",
    label: "Достигатор",
    emoji: "🚀",
    description: "Максимальная производительность",
    hint: "Жёсткие таймеры, плотный план, фокус на результат",
  },
  {
    key: "harmony",
    label: "Гармония",
    emoji: "⚖️",
    description: "Баланс работа / жизнь",
    hint: "Умеренная нагрузка, время на отдых и общение",
  },
  {
    key: "recovery",
    label: "Восстановление",
    emoji: "🌿",
    description: "Мягкий режим",
    hint: "1–3 ключевых задачи, отдых приоритет",
  },
  {
    key: "learning",
    label: "Обучение",
    emoji: "📚",
    description: "Длинные сессии фокуса",
    hint: "Агент-тьютор активен, блоки по 90 мин",
  },
  {
    key: "clarity",
    label: "Прояснение",
    emoji: "🔍",
    description: "Приоритизация и анализ",
    hint: "Только фаза Reason — разобраться, что важно",
  },
  {
    key: "crisis",
    label: "Кризис",
    emoji: "🆘",
    description: "Триаж — только критическое",
    hint: "Минимальный список, автоматический defer остального",
  },
  {
    key: "creative",
    label: "Творческий",
    emoji: "🎨",
    description: "Неструктурированные блоки",
    hint: "Длинные open-ended сессии без жёстких дедлайнов",
  },
];

interface Props {
  initialMode: string | null;
  token: string;
}

export function ModeSwitcher({ initialMode, token }: Props) {
  const [currentMode, setCurrentMode] = useState(initialMode);
  const [selected, setSelected] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function handleSelect(key: string) {
    if (key === currentMode) return;
    setSelected(key === selected ? null : key);
    setReason("");
    setError(null);
  }

  function handleSwitch() {
    if (!selected || !token) return;
    setError(null);
    startTransition(async () => {
      try {
        await api.modes.switch({ mode: selected, reason: reason.trim() || undefined }, token);
        setCurrentMode(selected);
        setSelected(null);
        setReason("");
      } catch (e) {
        setError((e as Error).message);
      }
    });
  }

  const currentInfo = MODES.find((m) => m.key === currentMode);

  return (
    <div className="space-y-6">
      {/* Current mode banner */}
      {currentInfo && (
        <div className="rounded-xl bg-indigo-950 border border-indigo-700 px-5 py-4 flex items-center gap-4">
          <span className="text-3xl">{currentInfo.emoji}</span>
          <div>
            <p className="text-xs text-indigo-400 uppercase tracking-wide font-semibold">Активный режим</p>
            <p className="text-lg font-bold text-white mt-0.5">{currentInfo.label}</p>
            <p className="text-sm text-indigo-300 mt-0.5">{currentInfo.hint}</p>
          </div>
        </div>
      )}

      {!currentInfo && (
        <div className="rounded-xl bg-gray-900 border border-gray-700 px-5 py-4">
          <p className="text-sm text-gray-400">Режим не выбран. Выберите один из вариантов ниже.</p>
        </div>
      )}

      {/* Mode grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {MODES.map((mode) => {
          const isActive = mode.key === currentMode;
          const isSelected = mode.key === selected;

          return (
            <button
              key={mode.key}
              onClick={() => handleSelect(mode.key)}
              disabled={isActive}
              className={clsx(
                "text-left rounded-xl border p-4 transition-all",
                isActive
                  ? "border-indigo-600 bg-indigo-950 cursor-default opacity-80"
                  : isSelected
                  ? "border-indigo-500 bg-indigo-900/40 ring-1 ring-indigo-500"
                  : "border-gray-700 bg-gray-900 hover:border-gray-600 hover:bg-gray-800"
              )}
            >
              <div className="flex items-center gap-3 mb-2">
                <span className="text-2xl">{mode.emoji}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-white truncate">{mode.label}</p>
                  {isActive && (
                    <span className="text-xs text-indigo-400 font-medium">● Активен</span>
                  )}
                </div>
              </div>
              <p className="text-xs font-medium text-gray-300 mb-1">{mode.description}</p>
              <p className="text-xs text-gray-500 leading-relaxed">{mode.hint}</p>
            </button>
          );
        })}
      </div>

      {/* Confirm panel */}
      {selected && (
        <div className="rounded-xl border border-indigo-700 bg-indigo-950/60 p-5 space-y-3">
          <p className="text-sm font-medium text-indigo-200">
            Переключить на{" "}
            <span className="font-bold text-white">
              {MODES.find((m) => m.key === selected)?.label}
            </span>
            ?
          </p>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Причина переключения (необязательно)…"
            rows={2}
            className="w-full rounded-lg bg-gray-950 border border-gray-700 text-gray-100 text-sm px-3 py-2 resize-none focus:outline-none focus:border-indigo-500"
          />
          {error && <p className="text-xs text-red-400">{error}</p>}
          <div className="flex gap-3">
            <button
              onClick={handleSwitch}
              disabled={isPending}
              className="flex-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-semibold py-2 transition-colors"
            >
              {isPending ? "Переключаю…" : "Подтвердить"}
            </button>
            <button
              onClick={() => setSelected(null)}
              className="rounded-lg border border-gray-700 text-gray-400 hover:text-white hover:border-gray-600 text-sm px-4 py-2 transition-colors"
            >
              Отмена
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
