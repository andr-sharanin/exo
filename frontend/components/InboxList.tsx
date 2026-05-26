"use client";

import { useState, useCallback } from "react";
import clsx from "clsx";
import { api } from "@/lib/api";
import type { Command, TaskAnalysis } from "@/lib/types";
import { useSSE } from "@/hooks/useSSE";

// ── Score ring ────────────────────────────────────────────────────────────────
function AlignmentScore({ score }: { score: number }) {
  const color =
    score >= 70 ? "text-green-400" :
    score >= 40 ? "text-amber-400" :
                  "text-red-400";
  return (
    <span className={clsx("text-lg font-bold tabular-nums", color)}>
      {score}
    </span>
  );
}

// ── Recommendation pill ───────────────────────────────────────────────────────
const REC_STYLE: Record<string, string> = {
  proceed:  "bg-green-900/50 text-green-400",
  neutral:  "bg-gray-800 text-gray-400",
  defer:    "bg-amber-900/50 text-amber-400",
  decline:  "bg-red-900/50 text-red-400",
};
const REC_LABEL: Record<string, string> = {
  proceed: "Выполнять",
  neutral: "На ваше усмотрение",
  defer:   "Отложить",
  decline: "Отклонить",
};

// ── Analysis panel ────────────────────────────────────────────────────────────
function AnalysisPanel({
  analysis,
  commandId,
  token,
  onDecision,
}: {
  analysis: TaskAnalysis;
  commandId: string;
  token: string;
  onDecision: (id: string, decision: "confirmed" | "deferred") => void;
}) {
  const [deciding, setDeciding] = useState(false);
  const [note, setNote] = useState("");
  const [showNote, setShowNote] = useState(false);

  async function decide(decision: "confirmed" | "deferred") {
    setDeciding(true);
    try {
      await api.commands.confirm(commandId, decision, note || undefined, token);
      onDecision(commandId, decision);
    } finally {
      setDeciding(false);
    }
  }

  if (!analysis.available) {
    return (
      <div className="mt-3 pt-3 border-t border-gray-800">
        <p className="text-xs text-gray-600">Анализ выполняется...</p>
      </div>
    );
  }

  return (
    <div className="mt-3 pt-3 border-t border-gray-800 space-y-3">
      {/* Score + recommendation */}
      <div className="flex items-center gap-3">
        <div className="text-center">
          <AlignmentScore score={analysis.alignment_score ?? 50} />
          <p className="text-xs text-gray-600">совпадение</p>
        </div>
        <div className="flex-1">
          {analysis.recommendation && (
            <span className={clsx(
              "text-xs px-2 py-0.5 rounded-full font-medium",
              REC_STYLE[analysis.recommendation] ?? REC_STYLE.neutral
            )}>
              {REC_LABEL[analysis.recommendation] ?? analysis.recommendation}
            </span>
          )}
          {analysis.reasoning && (
            <p className="text-xs text-gray-500 mt-1 leading-relaxed">{analysis.reasoning}</p>
          )}
        </div>
      </div>

      {/* Conflicts / synergies */}
      {(analysis.conflicts?.length ?? 0) > 0 && (
        <div className="space-y-1">
          {analysis.conflicts!.map((c, i) => (
            <div key={i} className="flex items-start gap-1.5 text-xs text-amber-500/80">
              <span className="flex-shrink-0 mt-0.5">⚠</span>
              <span>{c}</span>
            </div>
          ))}
        </div>
      )}
      {(analysis.synergies?.length ?? 0) > 0 && (
        <div className="space-y-1">
          {analysis.synergies!.map((s, i) => (
            <div key={i} className="flex items-start gap-1.5 text-xs text-green-500/80">
              <span className="flex-shrink-0 mt-0.5">✓</span>
              <span>{s}</span>
            </div>
          ))}
        </div>
      )}

      {/* Note toggle */}
      {showNote && (
        <input
          autoFocus
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Комментарий (опционально)..."
          className="w-full rounded-lg bg-gray-800 border border-gray-700 text-xs text-gray-300 px-3 py-2 focus:outline-none focus:border-indigo-500"
        />
      )}

      {/* Decision buttons */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => decide("confirmed")}
          disabled={deciding}
          className="flex-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold py-2 transition-colors"
        >
          {deciding ? "…" : "✓ Подтвердить"}
        </button>
        <button
          onClick={() => decide("deferred")}
          disabled={deciding}
          className="flex-1 rounded-lg bg-gray-800 hover:bg-gray-700 disabled:opacity-50 text-gray-400 text-xs py-2 transition-colors"
        >
          Отложить
        </button>
        <button
          onClick={() => setShowNote((v) => !v)}
          className="rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-600 text-xs px-2 py-2 transition-colors"
          title="Добавить комментарий"
        >
          ✎
        </button>
      </div>
    </div>
  );
}

// ── Command card ──────────────────────────────────────────────────────────────
function CommandCard({
  cmd,
  token,
  onDecision,
}: {
  cmd: Command;
  token: string;
  onDecision: (id: string, decision: "confirmed" | "deferred") => void;
}) {
  const [analysis, setAnalysis] = useState<TaskAnalysis | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [expanded, setExpanded] = useState(
    cmd.kernel_status === "pending_confirmation"
  );

  async function loadAnalysis() {
    if (analysis || loadingAnalysis) return;
    setLoadingAnalysis(true);
    try {
      const data = await api.commands.getAnalysis(cmd.id, token) as TaskAnalysis;
      setAnalysis(data);
    } finally {
      setLoadingAnalysis(false);
    }
  }

  function handleExpand() {
    setExpanded((v) => !v);
    if (!expanded) loadAnalysis();
  }

  const needsConfirmation = cmd.kernel_status === "pending_confirmation";
  const isAnalyzing = cmd.kernel_status === "pending_analysis";
  const text = cmd.raw_input ?? cmd.raw_payload_ref;

  return (
    <div
      className={clsx(
        "rounded-xl border transition-colors",
        needsConfirmation
          ? "bg-amber-950/20 border-amber-800/50"
          : "bg-gray-900 border-gray-800"
      )}
    >
      <button
        onClick={handleExpand}
        className="w-full flex items-start gap-3 px-4 py-3 text-left"
      >
        {/* Status dot */}
        <span
          className={clsx(
            "flex-shrink-0 w-2 h-2 rounded-full mt-1.5",
            needsConfirmation ? "bg-amber-400" :
            isAnalyzing      ? "bg-blue-400 animate-pulse" :
            cmd.kernel_status === "confirmed" ? "bg-green-500" :
            cmd.kernel_status === "deferred"  ? "bg-gray-600" :
                                                "bg-gray-700"
          )}
        />

        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-200 leading-relaxed line-clamp-2">{text}</p>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-gray-600">
              {new Date(cmd.created_at).toLocaleTimeString("ru-RU", {
                hour: "2-digit", minute: "2-digit",
              })}
            </span>
            {needsConfirmation && (
              <span className="text-xs text-amber-500 font-medium">
                Ждёт подтверждения
              </span>
            )}
            {isAnalyzing && (
              <span className="text-xs text-blue-400">Анализируется...</span>
            )}
          </div>
        </div>

        <span className="text-gray-600 text-xs flex-shrink-0 mt-0.5">
          {expanded ? "▲" : "▼"}
        </span>
      </button>

      {expanded && (
        <div className="px-4 pb-4">
          {loadingAnalysis && (
            <p className="text-xs text-gray-600 animate-pulse">Загружаю анализ...</p>
          )}
          {analysis && (
            <AnalysisPanel
              analysis={analysis}
              commandId={cmd.id}
              token={token}
              onDecision={onDecision}
            />
          )}
          {!analysis && !loadingAnalysis && !needsConfirmation && (
            <button
              onClick={loadAnalysis}
              className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              Показать анализ →
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ── New task input ────────────────────────────────────────────────────────────
function NewTaskInput({ token, onAdded }: { token: string; onAdded: (cmd: Command) => void }) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setLoading(true);
    setError("");
    try {
      const key = `web-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      const cmd = await api.commands.create(
        {
          raw_payload_ref: text.trim(),
          ingress_channel: "web",
          ingress_modality: "text",
          idempotency_key: key,
        },
        token
      ) as Command;
      onAdded(cmd);
      setText("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <div className="flex gap-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Что нужно сделать? Введи задачу или мысль..."
          className="flex-1 rounded-xl bg-gray-900 border border-gray-700 text-sm text-gray-200 px-4 py-3 focus:outline-none focus:border-indigo-500 transition-colors"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !text.trim()}
          className="rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium px-5 py-3 transition-colors flex-shrink-0"
        >
          {loading ? "…" : "→"}
        </button>
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
      <p className="text-xs text-gray-700">
        AI проанализирует задачу через твои ядра и попросит подтверждения при низком совпадении
      </p>
    </form>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export function InboxList({
  initialCommands,
  token,
}: {
  initialCommands: Command[];
  token: string;
}) {
  const [commands, setCommands] = useState(initialCommands);

  // Real-time: update kernel_status when analysis completes
  useSSE(useCallback((event) => {
    if (event.type === "task_analyzed") {
      const p = event.payload as { command_id: string; kernel_status: string };
      setCommands((prev) =>
        prev.map((c) =>
          c.id === p.command_id ? { ...c, kernel_status: p.kernel_status as import("@/lib/types").KernelStatus } : c
        )
      );
    }
  }, []));

  function handleAdded(cmd: Command) {
    setCommands((prev) => [cmd, ...prev]);
  }

  function handleDecision(id: string, decision: "confirmed" | "deferred") {
    setCommands((prev) =>
      prev.map((c) =>
        c.id === id
          ? { ...c, kernel_status: decision, status: decision === "deferred" ? "dismissed" : c.status }
          : c
      )
    );
  }

  const pendingConfirmation = commands.filter(
    (c) => c.kernel_status === "pending_confirmation"
  );
  const others = commands.filter(
    (c) => c.kernel_status !== "pending_confirmation"
  );

  return (
    <div className="space-y-6">
      {/* New task */}
      <NewTaskInput token={token} onAdded={handleAdded} />

      {/* Pending confirmation section */}
      {pendingConfirmation.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-amber-400 uppercase tracking-wide font-medium flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 inline-block" />
            Ждут подтверждения · {pendingConfirmation.length}
          </p>
          {pendingConfirmation.map((cmd) => (
            <CommandCard
              key={cmd.id}
              cmd={cmd}
              token={token}
              onDecision={handleDecision}
            />
          ))}
        </div>
      )}

      {/* Other commands */}
      {others.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-gray-600 uppercase tracking-wide font-medium">
            Последние задачи
          </p>
          {others.map((cmd) => (
            <CommandCard
              key={cmd.id}
              cmd={cmd}
              token={token}
              onDecision={handleDecision}
            />
          ))}
        </div>
      )}

      {commands.length === 0 && (
        <div className="rounded-xl border border-dashed border-gray-700 p-8 text-center">
          <p className="text-gray-500 text-sm">Inbox пуст</p>
          <p className="text-xs text-gray-600 mt-1">Введи задачу выше — AI её проанализирует</p>
        </div>
      )}
    </div>
  );
}
