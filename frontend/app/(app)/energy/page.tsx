"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { api } from "@/lib/api";

const LABELS = {
  sleep_quality: "Sleep quality",
  mood: "Mood",
  energy_level: "Energy level",
} as const;

type Field = keyof typeof LABELS;

export default function EnergyCheckinPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const [values, setValues] = useState<Record<Field, number>>({
    sleep_quality: 3,
    mood: 3,
    energy_level: 3,
  });
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!session?.accessToken) return;
    setLoading(true);
    setError(null);
    try {
      await api.energy.checkin({ ...values, note: note || undefined }, session.accessToken);
      router.push("/dashboard");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 max-w-md mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Morning Check-in</h1>
        <p className="text-sm text-gray-400 mt-1">Rate yourself 1–5 to calibrate today&apos;s plan</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {(Object.keys(LABELS) as Field[]).map((field) => (
          <div key={field}>
            <div className="flex justify-between mb-2">
              <label className="text-sm font-medium text-gray-300">{LABELS[field]}</label>
              <span className="text-sm font-bold text-indigo-400">{values[field]}</span>
            </div>
            <input
              type="range" min={1} max={5} value={values[field]}
              onChange={(e) => setValues((v) => ({ ...v, [field]: Number(e.target.value) }))}
              className="w-full accent-indigo-500"
            />
            <div className="flex justify-between text-xs text-gray-600 mt-1">
              <span>1 — Terrible</span><span>5 — Excellent</span>
            </div>
          </div>
        ))}

        <div>
          <label className="text-sm font-medium text-gray-300">Note (optional)</label>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            placeholder="Anything to add..."
            className="mt-1 w-full rounded-lg bg-gray-900 border border-gray-700 text-gray-100 text-sm px-3 py-2 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <button
          type="submit" disabled={loading}
          className="w-full rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold py-3 transition-colors"
        >
          {loading ? "Submitting..." : "Submit check-in"}
        </button>
      </form>
    </div>
  );
}
