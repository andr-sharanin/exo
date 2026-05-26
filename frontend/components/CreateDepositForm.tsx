"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { UpgradeBanner } from "@/components/UpgradeBanner";
import { useRouter } from "next/navigation";

interface Step {
  id: string;
  title: string;
  estimated_minutes: number | null;
  status: string;
}

interface Props {
  steps: Step[];
  token: string;
}

const CURRENCIES = ["USD", "EUR", "RUB", "GBP"];

function todayPlus(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().split("T")[0];
}

export function CreateDepositForm({ steps, token }: Props) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [stepId, setStepId] = useState(steps[0]?.id ?? "");
  const [amount, setAmount] = useState("10");
  const [currency, setCurrency] = useState("USD");
  const [dueDate, setDueDate] = useState(todayPlus(7));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        disabled={steps.length === 0}
        className="rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-sm font-semibold px-4 py-2 transition-colors"
      >
        + Новый депозит
      </button>
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const amountCents = Math.round(parseFloat(amount) * 100);
      if (isNaN(amountCents) || amountCents <= 0) {
        setError(new Error("Введите корректную сумму"));
        return;
      }
      await api.deposits.create(
        { step_id: stepId, amount_cents: amountCents, currency, due_date: dueDate },
        token
      );
      setOpen(false);
      setAmount("10");
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl bg-gray-900 border border-gray-800 p-5 space-y-4"
    >
      <p className="text-sm font-semibold text-gray-200">Новый депозит обязательства</p>

      <div>
        <label className="text-xs text-gray-400 block mb-1">Задача</label>
        {steps.length === 0 ? (
          <p className="text-xs text-gray-600">Нет активных задач. Создай задачи сначала.</p>
        ) : (
          <select
            value={stepId}
            onChange={(e) => setStepId(e.target.value)}
            className="w-full rounded-lg bg-gray-950 border border-gray-700 text-gray-100 text-sm px-3 py-2 focus:outline-none focus:border-indigo-500"
          >
            {steps.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title}
                {s.estimated_minutes ? ` (${s.estimated_minutes} мин)` : ""}
              </option>
            ))}
          </select>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-gray-400 block mb-1">Сумма</label>
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="w-full rounded-lg bg-gray-950 border border-gray-700 text-gray-100 text-sm px-3 py-2 focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Валюта</label>
          <select
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            className="w-full rounded-lg bg-gray-950 border border-gray-700 text-gray-100 text-sm px-3 py-2 focus:outline-none focus:border-indigo-500"
          >
            {CURRENCIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="text-xs text-gray-400 block mb-1">Дедлайн</label>
        <input
          type="date"
          value={dueDate}
          min={todayPlus(0)}
          onChange={(e) => setDueDate(e.target.value)}
          className="w-full rounded-lg bg-gray-950 border border-gray-700 text-gray-100 text-sm px-3 py-2 focus:outline-none focus:border-indigo-500"
        />
      </div>

      <UpgradeBanner error={error} onDismiss={() => setError(null)} />
      {error && !(error instanceof ApiError && error.isPaymentRequired) && (
        <p className="text-xs text-red-400">{error instanceof Error ? error.message : String(error)}</p>
      )}

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={saving || steps.length === 0 || !amount || !dueDate}
          className="rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-sm font-semibold px-4 py-2 transition-colors"
        >
          {saving ? "Создаю…" : "Создать депозит"}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="rounded-lg border border-gray-700 text-gray-400 hover:text-white text-sm px-4 py-2 transition-colors"
        >
          Отмена
        </button>
      </div>
    </form>
  );
}
