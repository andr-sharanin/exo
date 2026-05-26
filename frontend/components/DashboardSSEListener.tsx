"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { useSSE } from "@/hooks/useSSE";

/**
 * Invisible component — mounts in dashboard layout, refreshes server data
 * when backend publishes relevant SSE events.
 *
 * brief_ready     → morning brief appeared, re-fetch
 * task_analyzed   → inbox item got kernel_status, re-fetch
 * plan_ready      → plan was generated, re-fetch
 */
export function DashboardSSEListener() {
  const router = useRouter();

  useSSE(useCallback((event) => {
    const refreshEvents = new Set(["brief_ready", "task_analyzed", "plan_ready", "review_ready"]);
    if (refreshEvents.has(event.type)) {
      router.refresh();
    }
  }, [router]));

  return null;
}
