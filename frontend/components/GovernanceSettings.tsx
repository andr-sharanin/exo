"use client";

import { useState, useTransition } from "react";
import { api } from "@/lib/api";
import { UpgradeBanner } from "@/components/UpgradeBanner";
import clsx from "clsx";

interface Policy {
  id: string;
  user_id: string;
  mode: "solo" | "x2";
  partner_email: string | null;
  created_at: string;
  updated_at: string;
}

interface GovernanceRecord {
  id: string;
  subject: string;
  reason: string;
  mode_at_time: string;
  partner_email: string | null;
  status: string;
  approved_at: string | null;
  created_at: string;
}

interface Props {
  initialPolicy: Policy;
  initialRecords: GovernanceRecord[];
  token: string;
}

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  self_approved: { label: "Подтверждено", color: "text-green-400" },
  pending_partner: { label: "Ожидает партнёра", color: "text-amber-400" },
  partner_approved: { label: "Партнёр одобрил", color: "text-indigo-400" },
};

export function GovernanceSettings({ initialPolicy, initialRecords, token }: Props) {
  const [policy, setPolicy] = useState(initialPolicy);
  const [records, setRecords] = useState(initialRecords);
  const [mode, setMode] = useState<"solo" | "x2">(initialPolicy.mode);
  const [partnerEmail, setPartnerEmail] = useState(initialPolicy.partner_email ?? "");
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<Error | null>(null);
  const [isPending, startTransition] = useTransition();

  // ADR creation form
  const [showADR, setShowADR] = useState(false);
  const [adrSubject, setAdrSubject] = useState("");
  const [adrReason, setAdrReason] = useState("");
  const [adrError, setAdrError] = useState<Error | null>(null);
  const [adrPending, startADRTransition] = useTransition();

  function handleSavePolicy() {
    setSaveError(null);
    startTransition(async () => {
      try {
        const updated = await api.governance.updatePolicy(
          { mode, partner_email: mode === "x2" ? partnerEmail : null },
          token
        ) as Policy;
        setPolicy(updated);
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      } catch (e) {
        setSaveError(e instanceof Error ? e : new Error(String(e)));
      }
    });
  }

  function handleCreateADR() {
    setAdrError(null);
    startADRTransition(async () => {
      try {
        const record = await api.governance.createRecord(
          { subject: adrSubject.trim(), reason: adrReason.trim() },
          token
        ) as GovernanceRecord;
        setRecords((prev) => [record, ...prev]);
        setAdrSubject("");
        setAdrReason("");
        setShowADR(false);
      } catch (e) {
        setAdrError(e instanceof Error ? e : new Error(String(e)));
      }
    });
  }

  return (
    <div className="space-y-8">
      {/* Policy section */}
      <div className="rounded-xl bg-gray-900 border border-gray-800">
        <div className="px-5 py-4 border-b border-gray-800">
          <h2 className="text-sm font-semibold text-gray-300">Режим подтверждения</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Определяет, как фиксируются решения об откате обязательств.
          </p>
        </div>
        <div className="px-5 py-4 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            {(["solo", "x2"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={clsx(
                  "rounded-xl border p-4 text-left transition-all",
                  mode === m
                    ? "border-indigo-500 bg-indigo-900/30 ring-1 ring-indigo-500"
                    : "border-gray-700 bg-gray-800 hover:border-gray-600"
                )}
              >
                <p className="text-sm font-bold text-white">
                  {m === "solo" ? "Solo" : "x2 (партнёр)"}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  {m === "solo"
                    ? "Вы сами подтверждаете. Достаточно написать причину."
                    : "Партнёр должен одобрить по email. Защита от самосаботажа."}
                </p>
              </button>
            ))}
          </div>

          {mode === "x2" && (
            <div>
              <label className="text-xs text-gray-400 block mb-1">Email партнёра</label>
              <input
                type="email"
                value={partnerEmail}
                onChange={(e) => setPartnerEmail(e.target.value)}
                placeholder="partner@example.com"
                className="w-full rounded-lg bg-gray-950 border border-gray-700 text-gray-100 text-sm px-3 py-2 focus:outline-none focus:border-indigo-500"
              />
            </div>
          )}

          <UpgradeBanner error={saveError} onDismiss={() => setSaveError(null)} />
          {saveError && !(saveError instanceof Error && (saveError as { isPaymentRequired?: boolean }).isPaymentRequired) && (
            <p className="text-xs text-red-400">{saveError instanceof Error ? saveError.message : String(saveError)}</p>
          )}

          <button
            onClick={handleSavePolicy}
            disabled={isPending || (mode === policy.mode && partnerEmail === (policy.partner_email ?? ""))}
            className={clsx(
              "rounded-lg px-4 py-2 text-sm font-semibold transition-colors",
              saved
                ? "bg-green-700 text-green-200"
                : "bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white"
            )}
          >
            {isPending ? "Сохраняю…" : saved ? "✓ Сохранено" : "Сохранить"}
          </button>
        </div>
      </div>

      {/* Create ADR */}
      <div className="rounded-xl bg-gray-900 border border-gray-800">
        <div className="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-gray-300">Записать решение (ADR)</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Зафиксируй обоснование для любого отступления от обязательства.
            </p>
          </div>
          <button
            onClick={() => setShowADR((v) => !v)}
            className="rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-3 py-1.5 transition-colors"
          >
            {showADR ? "Свернуть" : "+ Новый ADR"}
          </button>
        </div>

        {showADR && (
          <div className="px-5 py-4 space-y-3">
            <div>
              <label className="text-xs text-gray-400 block mb-1">Решение (что меняется)</label>
              <input
                type="text"
                value={adrSubject}
                onChange={(e) => setAdrSubject(e.target.value)}
                placeholder="Например: откладываю задачу «Фитнес» на следующую неделю"
                className="w-full rounded-lg bg-gray-950 border border-gray-700 text-gray-100 text-sm px-3 py-2 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">
                Обоснование <span className="text-gray-600">(минимум 20 символов)</span>
              </label>
              <textarea
                value={adrReason}
                onChange={(e) => setAdrReason(e.target.value)}
                placeholder="Почему принято это решение? Какие обстоятельства?"
                rows={3}
                className="w-full rounded-lg bg-gray-950 border border-gray-700 text-gray-100 text-sm px-3 py-2 resize-none focus:outline-none focus:border-indigo-500"
              />
            </div>
            <UpgradeBanner error={adrError} onDismiss={() => setAdrError(null)} />
            {adrError && !(adrError instanceof Error && (adrError as { isPaymentRequired?: boolean }).isPaymentRequired) && (
              <p className="text-xs text-red-400">{adrError instanceof Error ? adrError.message : String(adrError)}</p>
            )}
            <div className="flex gap-3">
              <button
                onClick={handleCreateADR}
                disabled={adrPending || !adrSubject.trim() || adrReason.trim().length < 20}
                className="rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-sm font-semibold px-4 py-2 transition-colors"
              >
                {adrPending ? "Записываю…" : policy.mode === "x2" ? "Записать и отправить партнёру" : "Записать"}
              </button>
              <button
                onClick={() => setShowADR(false)}
                className="rounded-lg border border-gray-700 text-gray-400 hover:text-white text-sm px-4 py-2 transition-colors"
              >
                Отмена
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Records log */}
      <div className="rounded-xl bg-gray-900 border border-gray-800">
        <div className="px-5 py-4 border-b border-gray-800">
          <h2 className="text-sm font-semibold text-gray-300">История решений</h2>
        </div>
        <div className="divide-y divide-gray-800">
          {records.length === 0 && (
            <p className="px-5 py-8 text-sm text-gray-600 text-center">Нет записей. Первые ADR появятся здесь.</p>
          )}
          {records.map((rec) => {
            const st = STATUS_LABELS[rec.status] ?? { label: rec.status, color: "text-gray-400" };
            return (
              <div key={rec.id} className="px-5 py-4">
                <div className="flex items-start justify-between gap-4">
                  <p className="text-sm font-medium text-gray-200 flex-1">{rec.subject}</p>
                  <span className={clsx("text-xs font-medium flex-shrink-0", st.color)}>{st.label}</span>
                </div>
                <p className="text-xs text-gray-500 mt-1 leading-relaxed">{rec.reason}</p>
                <div className="flex items-center gap-3 mt-2">
                  <span className="text-xs text-gray-700">
                    {new Date(rec.created_at).toLocaleString("ru-RU", {
                      day: "numeric", month: "short", year: "numeric",
                      hour: "2-digit", minute: "2-digit",
                    })}
                  </span>
                  {rec.partner_email && (
                    <span className="text-xs text-gray-700">→ {rec.partner_email}</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
