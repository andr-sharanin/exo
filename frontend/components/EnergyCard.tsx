import type { EnergyScore } from "@/lib/types";
import Link from "next/link";
import clsx from "clsx";

const STATE_CONFIG = {
  sufficient: { color: "text-green-400", bg: "bg-green-950 border-green-800", label: "Sufficient" },
  constrained: { color: "text-amber-400", bg: "bg-amber-950 border-amber-800", label: "Constrained" },
  critical: { color: "text-red-400", bg: "bg-red-950 border-red-800", label: "Critical" },
} as const;

export function EnergyCard({ energy }: { energy: EnergyScore }) {
  const cfg = STATE_CONFIG[energy.state] ?? STATE_CONFIG.sufficient;

  return (
    <div className={clsx("rounded-xl border p-4", cfg.bg)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="text-2xl">🔋</div>
          <div>
            <p className="text-sm text-gray-400">Energy State</p>
            <p className={clsx("text-lg font-bold", cfg.color)}>{cfg.label}</p>
          </div>
        </div>
        <div className="text-right">
          <p className={clsx("text-3xl font-bold tabular-nums", cfg.color)}>
            {energy.score}
          </p>
          <p className="text-xs text-gray-500">/ 100</p>
        </div>
      </div>
      {energy.suggested_mode && (
        <p className="text-xs text-gray-500 mt-2">
          Suggested mode: <span className="text-gray-300 font-medium">{energy.suggested_mode}</span>
        </p>
      )}
      <Link href="/energy" className="text-xs text-gray-600 hover:text-indigo-400 mt-1 block">
        → Update check-in
      </Link>
    </div>
  );
}
