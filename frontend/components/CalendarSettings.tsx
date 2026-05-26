"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { UpgradeBanner } from "@/components/UpgradeBanner";

interface CalendarIntegration {
  id: string;
  provider: string;
  display_name: string;
  sync_direction: string;
  is_active: boolean;
  last_synced_at: string | null;
  last_error: string | null;
  created_at: string;
}

const PROVIDER_ICONS: Record<string, string> = {
  caldav: "📅",
  google: "🔵",
  microsoft: "🟦",
  ical: "📆",
};

function IntegrationCard({
  integ,
  onDisconnect,
}: {
  integ: CalendarIntegration;
  onDisconnect: (id: string) => void;
}) {
  const [disconnecting, setDisconnecting] = useState(false);

  return (
    <div className="flex items-center gap-3 rounded-xl bg-gray-900 border border-gray-800 px-4 py-3">
      <span className="text-xl">{PROVIDER_ICONS[integ.provider] ?? "📅"}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white">{integ.display_name}</p>
        <p className="text-xs text-gray-500">
          {integ.provider}
          {integ.last_synced_at
            ? ` · синх. ${new Date(integ.last_synced_at).toLocaleString("ru-RU", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}`
            : " · ещё не синхронизировано"}
        </p>
        {integ.last_error && (
          <p className="text-xs text-red-400 mt-0.5 truncate">{integ.last_error}</p>
        )}
      </div>
      <button
        onClick={async () => {
          setDisconnecting(true);
          onDisconnect(integ.id);
        }}
        disabled={disconnecting}
        className="text-xs text-gray-500 hover:text-red-400 disabled:opacity-40"
      >
        Отключить
      </button>
    </div>
  );
}

function ICalForm({ token, onAdded }: { token: string; onAdded: (i: CalendarIntegration) => void }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ display_name: "iCal Feed", ical_url: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const result = await api.calendar.connectICal(form, token) as CalendarIntegration;
      onAdded(result);
      setOpen(false);
      setForm({ display_name: "iCal Feed", ical_url: "" });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Ошибка подключения");
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="text-sm text-indigo-400 hover:text-indigo-300">
        + Подключить iCal (URL)
      </button>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-xl bg-gray-900 border border-gray-800 p-4 space-y-3">
      <p className="text-sm font-medium text-white">Подключить iCal фид</p>
      <input
        type="text"
        placeholder="Название"
        value={form.display_name}
        onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
      />
      <input
        type="url"
        placeholder="https://example.com/calendar.ics"
        value={form.ical_url}
        onChange={(e) => setForm((f) => ({ ...f, ical_url: e.target.value }))}
        required
        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
      />
      {error && <p className="text-xs text-red-400">{error}</p>}
      <div className="flex gap-3">
        <button
          type="submit"
          disabled={saving || !form.ical_url}
          className="text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 px-4 py-2 rounded-lg"
        >
          {saving ? "Подключение..." : "Подключить"}
        </button>
        <button type="button" onClick={() => setOpen(false)} className="text-sm text-gray-500 hover:text-gray-300">
          Отмена
        </button>
      </div>
    </form>
  );
}

function CalDAVForm({ token, onAdded }: { token: string; onAdded: (i: CalendarIntegration) => void }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ display_name: "", calendar_url: "", username: "", password: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const result = await api.calendar.connectCalDAV(form, token) as CalendarIntegration;
      onAdded(result);
      setOpen(false);
      setForm({ display_name: "", calendar_url: "", username: "", password: "" });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Ошибка подключения");
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="text-sm text-indigo-400 hover:text-indigo-300"
      >
        + Подключить CalDAV
      </button>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-xl bg-gray-900 border border-gray-800 p-4 space-y-3">
      <p className="text-sm font-medium text-white">Подключить CalDAV</p>
      {(["display_name", "calendar_url", "username", "password"] as const).map((field) => (
        <input
          key={field}
          type={field === "password" ? "password" : "text"}
          placeholder={{ display_name: "Название", calendar_url: "URL календаря", username: "Логин", password: "Пароль" }[field]}
          value={form[field]}
          onChange={(e) => setForm((f) => ({ ...f, [field]: e.target.value }))}
          required={field !== "display_name"}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
        />
      ))}
      {error && <p className="text-xs text-red-400">{error}</p>}
      <div className="flex gap-3">
        <button
          type="submit"
          disabled={saving}
          className="text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 px-4 py-2 rounded-lg"
        >
          {saving ? "Подключение..." : "Подключить"}
        </button>
        <button type="button" onClick={() => setOpen(false)} className="text-sm text-gray-500 hover:text-gray-300">
          Отмена
        </button>
      </div>
    </form>
  );
}

export function CalendarSettings({
  initialIntegrations,
  token,
}: {
  initialIntegrations: CalendarIntegration[];
  token: string;
}) {
  const [integrations, setIntegrations] = useState(initialIntegrations);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [msLoading, setMsLoading] = useState(false);
  const [connectError, setConnectError] = useState<Error | null>(null);

  function handleAdded(integ: CalendarIntegration) {
    setIntegrations((prev) => [...prev, integ]);
  }

  async function handleDisconnect(id: string) {
    try {
      await api.calendar.disconnect(id, token);
      setIntegrations((prev) => prev.filter((i) => i.id !== id));
    } catch {
      // ignore
    }
  }

  async function handleGoogleConnect() {
    setGoogleLoading(true);
    setConnectError(null);
    try {
      const res = await api.calendar.startGoogleOAuth(token) as { auth_url: string };
      window.location.href = res.auth_url;
    } catch (e) {
      setConnectError(e instanceof Error ? e : new Error(String(e)));
      setGoogleLoading(false);
    }
  }

  async function handleMicrosoftConnect() {
    setMsLoading(true);
    setConnectError(null);
    try {
      const res = await api.calendar.startMicrosoftOAuth(token) as { auth_url: string };
      window.location.href = res.auth_url;
    } catch (e) {
      setConnectError(e instanceof Error ? e : new Error(String(e)));
      setMsLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      {integrations.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-700 p-6 text-center">
          <p className="text-gray-500 text-sm">Нет подключённых календарей</p>
        </div>
      ) : (
        <div className="space-y-2">
          {integrations.map((integ) => (
            <IntegrationCard key={integ.id} integ={integ} onDisconnect={handleDisconnect} />
          ))}
        </div>
      )}

      {connectError && (
        <div>
          <UpgradeBanner error={connectError} onDismiss={() => setConnectError(null)} />
          {!(connectError instanceof ApiError && connectError.isPaymentRequired) && (
            <p className="text-xs text-red-400">{connectError instanceof Error ? connectError.message : String(connectError)}</p>
          )}
        </div>
      )}

      <div className="flex flex-col gap-3">
        <ICalForm token={token} onAdded={handleAdded} />
        <CalDAVForm token={token} onAdded={handleAdded} />
        <button
          onClick={handleGoogleConnect}
          disabled={googleLoading}
          className="text-sm text-indigo-400 hover:text-indigo-300 disabled:opacity-50 text-left"
        >
          {googleLoading ? "Перенаправление..." : "+ Подключить Google Calendar"}
        </button>
        <button
          onClick={handleMicrosoftConnect}
          disabled={msLoading}
          className="text-sm text-indigo-400 hover:text-indigo-300 disabled:opacity-50 text-left"
        >
          {msLoading ? "Перенаправление..." : "+ Подключить Microsoft Calendar"}
        </button>
      </div>
    </div>
  );
}
