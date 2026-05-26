"use client";

import type { CommitmentDeposit } from "@/lib/types";
import { api } from "@/lib/api";
import { useRouter } from "next/navigation";
import clsx from "clsx";

const STATUS_CONFIG = {
  held: { color: "bg-amber-900 text-amber-300", label: "Held" },
  released: { color: "bg-green-900 text-green-300", label: "Released ✓" },
  forfeited: { color: "bg-red-900 text-red-300", label: "Forfeited" },
} as const;

export function DepositsList({ deposits, token }: { deposits: CommitmentDeposit[]; token: string }) {
  const router = useRouter();

  async function release(id: string) {
    await api.deposits.release(id, token);
    router.refresh();
  }

  async function forfeit(id: string) {
    if (!confirm("Mark this deposit as forfeited? This cannot be undone.")) return;
    await api.deposits.forfeit(id, token);
    router.refresh();
  }

  if (deposits.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-gray-700 p-12 text-center">
        <p className="text-gray-400">No commitment deposits yet.</p>
        <p className="text-sm text-gray-600 mt-1">Create a deposit when starting a high-stakes step.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-gray-900 border border-gray-800 divide-y divide-gray-800">
      {deposits.map((dep) => {
        const cfg = STATUS_CONFIG[dep.status];
        const amount = `${(dep.amount_cents / 100).toFixed(2)} ${dep.currency}`;
        return (
          <div key={dep.id} className="p-4 flex items-center justify-between gap-4">
            <div>
              <p className="text-sm text-gray-200 font-medium">{amount}</p>
              <p className="text-xs text-gray-500 mt-0.5">Due: {dep.due_date}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className={clsx("text-xs px-2 py-0.5 rounded-full font-medium", cfg.color)}>
                {cfg.label}
              </span>
              {dep.status === "held" && (
                <>
                  <button
                    onClick={() => release(dep.id)}
                    className="text-xs rounded-lg bg-green-700 hover:bg-green-600 text-white px-3 py-1"
                  >
                    Release
                  </button>
                  <button
                    onClick={() => forfeit(dep.id)}
                    className="text-xs rounded-lg bg-gray-700 hover:bg-red-800 text-gray-300 px-3 py-1"
                  >
                    Forfeit
                  </button>
                </>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
