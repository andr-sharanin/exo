"use client";

import { useState } from "react";
import { api } from "@/lib/api";

function TelegramLinkSection({ token }: { token: string }) {
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleGenerate() {
    setLoading(true);
    try {
      const res = await api.telegram.getLinkToken(token) as { token: string };
      setLinkToken(res.token);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl bg-gray-900 border border-gray-800 p-5 space-y-3">
      <div>
        <p className="text-sm font-semibold text-white">Telegram Bot</p>
        <p className="text-xs text-gray-500 mt-0.5">
          Связать аккаунт для управления через Telegram
        </p>
      </div>
      {!linkToken ? (
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="text-sm text-indigo-400 hover:text-indigo-300 disabled:opacity-50"
        >
          {loading ? "Генерация..." : "→ Получить токен для привязки"}
        </button>
      ) : (
        <div className="space-y-2">
          <p className="text-xs text-gray-400">
            Открой бота и отправь команду (токен действителен 10 минут):
          </p>
          <code className="block bg-gray-800 rounded-lg px-3 py-2 text-sm text-green-400 select-all break-all">
            /link {linkToken}
          </code>
          <button
            onClick={() => setLinkToken(null)}
            className="text-xs text-gray-600 hover:text-gray-400"
          >
            Сгенерировать новый
          </button>
        </div>
      )}
    </div>
  );
}

export function AccountPanel({ token }: { token: string }) {
  const [exporting, setExporting] = useState(false);
  const [exportDone, setExportDone] = useState(false);
  const [deletePhase, setDeletePhase] = useState<"idle" | "confirm" | "deleting" | "done">("idle");
  const [error, setError] = useState<string | null>(null);

  async function handleExport() {
    setExporting(true);
    setError(null);
    try {
      const data = await api.users.exportData(token);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `exocortex-export-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setExportDone(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Ошибка экспорта");
    } finally {
      setExporting(false);
    }
  }

  async function handleDelete() {
    setDeletePhase("deleting");
    setError(null);
    try {
      await api.users.deleteAccount(token);
      setDeletePhase("done");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Ошибка удаления");
      setDeletePhase("confirm");
    }
  }

  return (
    <div className="space-y-4">
      {/* Telegram */}
      <TelegramLinkSection token={token} />

      {/* Export */}
      <div className="rounded-xl bg-gray-900 border border-gray-800 p-5 space-y-3">
        <div>
          <p className="text-sm font-semibold text-white">Экспорт данных</p>
          <p className="text-xs text-gray-500 mt-0.5">
            Скачай все свои данные в формате JSON (GDPR Art. 20)
          </p>
        </div>
        <button
          onClick={handleExport}
          disabled={exporting}
          className="text-sm font-medium text-indigo-400 hover:text-indigo-300 disabled:opacity-50"
        >
          {exporting ? "Экспорт..." : exportDone ? "✓ Скачано" : "→ Скачать мои данные"}
        </button>
      </div>

      {/* Delete */}
      <div className="rounded-xl bg-gray-900 border border-red-900/40 p-5 space-y-3">
        <div>
          <p className="text-sm font-semibold text-red-400">Удаление аккаунта</p>
          <p className="text-xs text-gray-500 mt-0.5">
            Деактивирует привычки и цели. Физическое удаление через 30 дней (GDPR Art. 17).
          </p>
        </div>

        {deletePhase === "idle" && (
          <button
            onClick={() => setDeletePhase("confirm")}
            className="text-sm text-red-500 hover:text-red-400"
          >
            → Удалить аккаунт
          </button>
        )}

        {deletePhase === "confirm" && (
          <div className="space-y-3">
            <p className="text-sm text-amber-400 font-medium">
              Это действие необратимо. Продолжить?
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleDelete}
                className="text-sm font-semibold text-white bg-red-700 hover:bg-red-600 px-4 py-2 rounded-lg"
              >
                Да, удалить аккаунт
              </button>
              <button
                onClick={() => setDeletePhase("idle")}
                className="text-sm text-gray-400 hover:text-gray-300"
              >
                Отмена
              </button>
            </div>
          </div>
        )}

        {deletePhase === "deleting" && (
          <p className="text-sm text-gray-400">Удаление...</p>
        )}

        {deletePhase === "done" && (
          <p className="text-sm text-green-400">
            Аккаунт деактивирован. Данные будут удалены через 30 дней.
          </p>
        )}
      </div>

      {error && (
        <p className="text-sm text-red-400 bg-red-950/40 border border-red-800/40 rounded-lg px-4 py-3">
          {error}
        </p>
      )}
    </div>
  );
}
