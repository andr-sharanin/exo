"use client";

import Link from "next/link";
import { ApiError } from "@/lib/api";

interface Props {
  error: unknown;
  onDismiss?: () => void;
}

/**
 * Shown when an API call returns 402. Displays the error message and a link
 * to the subscription settings page so the user can upgrade.
 */
export function UpgradeBanner({ error, onDismiss }: Props) {
  if (!(error instanceof ApiError && error.isPaymentRequired)) return null;

  return (
    <div className="rounded-xl border border-amber-700 bg-amber-950/60 px-4 py-3 flex items-start gap-3">
      <span className="text-amber-400 text-lg flex-shrink-0">💎</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-amber-200 font-medium">Требуется Pro подписка</p>
        <p className="text-xs text-amber-400 mt-0.5 leading-relaxed">{error.message}</p>
        <Link
          href="/settings/subscription"
          className="inline-block mt-2 text-xs font-semibold text-white bg-amber-600 hover:bg-amber-500 rounded-lg px-3 py-1 transition-colors"
        >
          Перейти к подписке →
        </Link>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="text-amber-600 hover:text-amber-400 text-xs flex-shrink-0"
        >
          ✕
        </button>
      )}
    </div>
  );
}
