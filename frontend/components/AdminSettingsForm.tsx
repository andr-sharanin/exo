"use client";

import { useState, useTransition } from "react";
import type { ConfigEntry, ConfigCategory } from "@/lib/types";
import { api } from "@/lib/api";
import clsx from "clsx";

const CATEGORY_LABELS: Record<ConfigCategory | string, string> = {
  ai_keys: "🤖 AI API Keys",
  agent_prompts: "💬 Agent Prompts",
  stripe: "💳 Stripe Payments",
  integrations: "🔗 Integrations",
  email: "📧 Email / SMTP",
  misc: "⚙️ Other",
};

const CATEGORY_ORDER: string[] = ["ai_keys", "stripe", "integrations", "email", "agent_prompts", "misc"];

interface RowProps {
  entry: ConfigEntry;
  token: string;
  onSaved: (key: string, description: string) => void;
}

function ConfigRow({ entry, token, onSaved }: RowProps) {
  const [value, setValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    if (!value.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await api.config.set(
        entry.key,
        { value, is_secret: entry.is_secret, description: entry.description, category: entry.category },
        token
      );
      setValue("");
      setSaved(true);
      onSaved(entry.key, entry.description);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="py-4 border-b border-gray-800 last:border-0">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-200 font-mono">{entry.key}</p>
          <p className="text-xs text-gray-500 mt-0.5">{entry.description}</p>
          {entry.value && (
            <p className="text-xs text-gray-600 mt-1">
              Current: <span className="font-mono">{entry.value}</span>
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <input
            type={entry.is_secret ? "password" : "text"}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={entry.is_secret ? "Enter new value…" : "Value…"}
            className="w-56 rounded-lg bg-gray-950 border border-gray-700 text-gray-100 text-sm px-3 py-1.5 focus:outline-none focus:border-indigo-500 font-mono"
            onKeyDown={(e) => e.key === "Enter" && handleSave()}
          />
          <button
            onClick={handleSave}
            disabled={saving || !value.trim()}
            className={clsx(
              "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
              saved
                ? "bg-green-700 text-green-200"
                : "bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white"
            )}
          >
            {saving ? "…" : saved ? "✓ Saved" : "Save"}
          </button>
        </div>
      </div>
      {error && <p className="text-xs text-red-400 mt-2">{error}</p>}
    </div>
  );
}

export function AdminSettingsForm({ entries, token }: { entries: ConfigEntry[]; token: string }) {
  const [savedKeys, setSavedKeys] = useState<Set<string>>(new Set());

  // Group by category
  const byCategory = CATEGORY_ORDER.reduce<Record<string, ConfigEntry[]>>((acc, cat) => {
    acc[cat] = entries.filter((e) => e.category === cat);
    return acc;
  }, {});

  // Add any unknown categories
  entries.forEach((e) => {
    if (!CATEGORY_ORDER.includes(e.category)) {
      byCategory[e.category] = [...(byCategory[e.category] ?? []), e];
    }
  });

  // If no entries in DB yet, show the known keys from a static list
  const hasEntries = entries.length > 0;

  return (
    <div className="space-y-6">
      {!hasEntries && (
        <div className="rounded-xl border border-amber-800 bg-amber-950 p-4">
          <p className="text-sm text-amber-300 font-medium">No settings configured yet.</p>
          <p className="text-xs text-amber-600 mt-1">
            The system starts with env var fallbacks. Enter values below to override.
          </p>
        </div>
      )}

      {savedKeys.size > 0 && (
        <div className="rounded-xl border border-green-800 bg-green-950 p-3">
          <p className="text-sm text-green-300">
            ✓ {savedKeys.size} key{savedKeys.size > 1 ? "s" : ""} saved. Changes take effect immediately.
          </p>
        </div>
      )}

      {CATEGORY_ORDER.map((cat) => {
        const catEntries = byCategory[cat] ?? [];
        if (catEntries.length === 0) return null;
        return (
          <div key={cat} className="rounded-xl bg-gray-900 border border-gray-800">
            <div className="px-5 py-3 border-b border-gray-800">
              <h2 className="text-sm font-semibold text-gray-300">
                {CATEGORY_LABELS[cat] ?? cat}
              </h2>
            </div>
            <div className="px-5">
              {catEntries.map((entry) => (
                <ConfigRow
                  key={entry.key}
                  entry={entry}
                  token={token}
                  onSaved={(key) => setSavedKeys((s) => new Set(s).add(key))}
                />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
