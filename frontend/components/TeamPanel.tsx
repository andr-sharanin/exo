"use client";

import { useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";

interface Subscription {
  tier: string;
  status: string;
}

interface Invitation {
  id: string;
  email: string;
  status: string;
  created_at: string;
  expires_at: string | null;
}

interface Props {
  subscription: Subscription;
  initialInvitations: Invitation[];
  token: string;
}

const TEAM_FEATURES = [
  "Неограниченные цели и горизонты",
  "Неограниченные депозиты обязательств",
  "Неограниченные интеграции календаря",
  "Режим x2 — подтверждение через партнёра",
  "Приглашение участников в команду",
  "Приоритетная поддержка",
];

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  pending: { label: "Ожидает", color: "text-amber-400" },
  accepted: { label: "Принято", color: "text-green-400" },
  revoked: { label: "Отозвано", color: "text-gray-600" },
};

export function TeamPanel({ subscription, initialInvitations, token }: Props) {
  const isTeam = subscription.tier === "team";
  const [invitations, setInvitations] = useState<Invitation[]>(initialInvitations);
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isTeam) {
    return (
      <div className="space-y-6">
        <div className="rounded-xl border border-purple-800 bg-purple-950/40 px-5 py-4">
          <div className="flex items-start gap-3">
            <span className="text-2xl">👥</span>
            <div>
              <p className="text-sm font-semibold text-purple-200">Team тариф</p>
              <p className="text-xs text-purple-400 mt-1">
                Текущий тариф: <span className="font-medium text-white capitalize">{subscription.tier}</span>.
                Для доступа к командным функциям перейди на Team.
              </p>
              <Link
                href="/settings/subscription"
                className="inline-block mt-3 text-xs font-semibold text-white bg-purple-600 hover:bg-purple-500 rounded-lg px-4 py-1.5 transition-colors"
              >
                Перейти к подписке →
              </Link>
            </div>
          </div>
        </div>

        <div className="rounded-xl bg-gray-900 border border-gray-800">
          <div className="px-5 py-4 border-b border-gray-800">
            <h2 className="text-sm font-semibold text-gray-300">Что входит в Team</h2>
          </div>
          <ul className="px-5 py-4 space-y-2">
            {TEAM_FEATURES.map((f) => (
              <li key={f} className="flex items-center gap-2 text-sm text-gray-400">
                <span className="text-purple-400 flex-shrink-0">✓</span>
                {f}
              </li>
            ))}
          </ul>
        </div>
      </div>
    );
  }

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    setSending(true);
    setError(null);
    try {
      const inv = await api.team.createInvitation(email.trim(), token) as Invitation;
      setInvitations((prev) => [inv, ...prev]);
      setEmail("");
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError(err instanceof Error ? err.message : "Ошибка");
      }
    } finally {
      setSending(false);
    }
  }

  async function handleRevoke(id: string) {
    try {
      await api.team.revokeInvitation(id, token);
      setInvitations((prev) =>
        prev.map((inv) => inv.id === id ? { ...inv, status: "revoked" } : inv)
      );
    } catch {
      // ignore
    }
  }

  const memberCount = invitations.filter((i) => i.status === "accepted").length;
  const pendingCount = invitations.filter((i) => i.status === "pending").length;

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-purple-700 bg-purple-950/40 px-5 py-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">👥</span>
          <div>
            <p className="text-sm font-semibold text-purple-200">Team тариф активен</p>
            <p className="text-xs text-purple-400 mt-0.5">
              {memberCount > 0
                ? `${memberCount} участник${memberCount === 1 ? "" : memberCount < 5 ? "а" : "ов"} · ${pendingCount} ожидает`
                : "Пригласите первого участника ниже."}
            </p>
          </div>
        </div>
      </div>

      {/* Invite form */}
      <div className="rounded-xl bg-gray-900 border border-gray-800">
        <div className="px-5 py-4 border-b border-gray-800">
          <h2 className="text-sm font-semibold text-gray-300">Пригласить участника</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Ссылка-приглашение действует 7 дней.
          </p>
        </div>
        <form onSubmit={handleInvite} className="px-5 py-4 flex gap-3">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="colleague@example.com"
            className="flex-1 rounded-lg bg-gray-950 border border-gray-700 text-gray-100 text-sm px-3 py-2 focus:outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            disabled={sending || !email.trim()}
            className="rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-sm font-semibold px-4 py-2 transition-colors"
          >
            {sending ? "…" : "Пригласить"}
          </button>
        </form>
        {error && <p className="px-5 pb-3 text-xs text-red-400">{error}</p>}
      </div>

      {/* Invitations list */}
      <div className="rounded-xl bg-gray-900 border border-gray-800">
        <div className="px-5 py-4 border-b border-gray-800">
          <h2 className="text-sm font-semibold text-gray-300">Приглашения</h2>
        </div>
        {invitations.length === 0 ? (
          <p className="px-5 py-6 text-sm text-gray-600 text-center">
            Нет отправленных приглашений.
          </p>
        ) : (
          <div className="divide-y divide-gray-800">
            {invitations.map((inv) => {
              const st = STATUS_LABELS[inv.status] ?? { label: inv.status, color: "text-gray-400" };
              return (
                <div key={inv.id} className="flex items-center justify-between px-5 py-3 gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-200 truncate">{inv.email}</p>
                    <p className="text-xs text-gray-600 mt-0.5">
                      {new Date(inv.created_at).toLocaleDateString("ru-RU", {
                        day: "numeric", month: "short", year: "numeric",
                      })}
                    </p>
                  </div>
                  <span className={`text-xs font-medium flex-shrink-0 ${st.color}`}>
                    {st.label}
                  </span>
                  {inv.status === "pending" && (
                    <button
                      onClick={() => handleRevoke(inv.id)}
                      className="text-xs text-gray-600 hover:text-red-400 transition-colors flex-shrink-0"
                    >
                      Отозвать
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
