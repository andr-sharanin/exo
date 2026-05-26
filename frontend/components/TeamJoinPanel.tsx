"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

interface InvitationInfo {
  email: string;
  status: string;
  expires_at: string | null;
}

interface Props {
  inviteToken: string;
  authToken: string;
}

export function TeamJoinPanel({ inviteToken, authToken }: Props) {
  const router = useRouter();
  const [info, setInfo] = useState<InvitationInfo | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [accepting, setAccepting] = useState(false);
  const [accepted, setAccepted] = useState(false);
  const [acceptError, setAcceptError] = useState<string | null>(null);

  useEffect(() => {
    if (!inviteToken) {
      setLoadError("Токен приглашения не указан.");
      return;
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    api.team.lookupInvitation(inviteToken).then((data: any) => {
      setInfo(data);
    }).catch((err: unknown) => {
      if (err instanceof ApiError) {
        setLoadError(err.message);
      } else {
        setLoadError("Не удалось загрузить приглашение.");
      }
    });
  }, [inviteToken]);

  async function handleAccept() {
    setAccepting(true);
    setAcceptError(null);
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await api.team.acceptInvitation(inviteToken, authToken) as any;
      setAccepted(true);
      setTimeout(() => router.push("/dashboard"), 2000);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setAcceptError(err.message);
      } else {
        setAcceptError("Не удалось принять приглашение.");
      }
    } finally {
      setAccepting(false);
    }
  }

  if (!inviteToken) {
    return (
      <div className="rounded-xl bg-gray-900 border border-gray-800 px-5 py-6 text-center">
        <p className="text-sm text-red-400">Ссылка приглашения недействительна.</p>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="rounded-xl bg-gray-900 border border-red-800 px-5 py-6">
        <p className="text-sm text-red-400">{loadError}</p>
      </div>
    );
  }

  if (!info) {
    return (
      <div className="rounded-xl bg-gray-900 border border-gray-800 px-5 py-6 text-center">
        <p className="text-sm text-gray-500">Загрузка…</p>
      </div>
    );
  }

  if (info.status !== "pending") {
    return (
      <div className="rounded-xl bg-gray-900 border border-gray-800 px-5 py-6 text-center">
        <p className="text-sm text-amber-400">
          Это приглашение уже {info.status === "accepted" ? "принято" : "отозвано"}.
        </p>
      </div>
    );
  }

  if (accepted) {
    return (
      <div className="rounded-xl border border-green-800 bg-green-950/30 px-5 py-6 text-center">
        <p className="text-green-400 font-semibold">Приглашение принято!</p>
        <p className="text-sm text-gray-400 mt-1">Перенаправление на дашборд…</p>
      </div>
    );
  }

  const expiresAt = info.expires_at
    ? new Date(info.expires_at).toLocaleDateString("ru-RU", {
        day: "numeric", month: "long", year: "numeric",
      })
    : null;

  return (
    <div className="rounded-xl bg-gray-900 border border-gray-800">
      <div className="px-5 py-5 border-b border-gray-800 flex items-center gap-3">
        <span className="text-2xl">👥</span>
        <div>
          <p className="text-sm font-semibold text-gray-200">Приглашение в команду ExoCortex</p>
          <p className="text-xs text-gray-500 mt-0.5">
            Для: <span className="text-gray-300">{info.email}</span>
          </p>
        </div>
      </div>

      <div className="px-5 py-4 space-y-3">
        {expiresAt && (
          <p className="text-xs text-gray-500">Действительно до: {expiresAt}</p>
        )}

        {acceptError && (
          <p className="text-xs text-red-400">{acceptError}</p>
        )}

        <button
          onClick={handleAccept}
          disabled={accepting}
          className="w-full rounded-lg bg-purple-600 hover:bg-purple-500 disabled:opacity-40
                     text-white text-sm font-semibold px-4 py-2.5 transition-colors"
        >
          {accepting ? "Принятие…" : "Принять приглашение"}
        </button>
      </div>
    </div>
  );
}
