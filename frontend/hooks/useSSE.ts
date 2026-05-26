"use client";

import { useEffect, useRef, useCallback } from "react";

export type SSEEvent = {
  type: string;
  payload: Record<string, unknown>;
};

type Handler = (event: SSEEvent) => void;

const BASE_DELAY_MS = 1_000;
const MAX_DELAY_MS = 30_000;

/**
 * Connect to /api/sse (our Next.js auth proxy → backend SSE stream).
 * Reconnects automatically with exponential back-off on disconnect.
 *
 * Usage:
 *   useSSE((event) => {
 *     if (event.type === "plan_ready") refetchPlan();
 *   });
 */
export function useSSE(onEvent: Handler): void {
  const handlerRef = useRef<Handler>(onEvent);
  const esRef = useRef<EventSource | null>(null);
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const delayRef = useRef<number>(BASE_DELAY_MS);

  // Keep handler ref fresh without restarting the connection
  useEffect(() => {
    handlerRef.current = onEvent;
  }, [onEvent]);

  const connect = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
    }

    const es = new EventSource("/api/sse");
    esRef.current = es;

    es.onmessage = (raw) => {
      try {
        const parsed: SSEEvent = JSON.parse(raw.data);
        // Ignore the "connected" handshake and keepalive comments
        if (parsed.type !== "connected") {
          handlerRef.current(parsed);
        }
      } catch {
        // Malformed frame — ignore
      }
    };

    es.onopen = () => {
      delayRef.current = BASE_DELAY_MS; // reset back-off on successful connect
    };

    es.onerror = () => {
      es.close();
      esRef.current = null;
      // Exponential back-off, cap at MAX_DELAY_MS
      retryRef.current = setTimeout(() => {
        delayRef.current = Math.min(delayRef.current * 2, MAX_DELAY_MS);
        connect();
      }, delayRef.current);
    };
  }, []);

  useEffect(() => {
    connect();

    return () => {
      esRef.current?.close();
      if (retryRef.current) clearTimeout(retryRef.current);
    };
  }, [connect]);
}
