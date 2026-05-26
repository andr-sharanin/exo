/**
 * SSE auth proxy: /api/sse → backend /api/v1/events/stream
 *
 * EventSource (browser) cannot set custom headers, so it can't pass a Bearer
 * token. This Next.js route reads the session cookie (server-side), extracts
 * the Keycloak access token, and forwards the SSE stream to the backend with
 * the Authorization header attached.
 */
import { auth } from "@/auth";

export const dynamic = "force-dynamic";
// Disable Next.js response body buffering so SSE frames pass through immediately.
export const runtime = "nodejs";

export async function GET() {
  const session = await auth();
  if (!session?.accessToken) {
    return new Response("Unauthorized", { status: 401 });
  }

  const backendUrl = `${process.env.BACKEND_URL}/api/v1/events/stream`;

  const upstream = await fetch(backendUrl, {
    headers: {
      Authorization: `Bearer ${session.accessToken}`,
      Accept: "text/event-stream",
      "Cache-Control": "no-cache",
    },
    // @ts-expect-error — Node.js fetch supports duplex streaming
    duplex: "half",
  });

  if (!upstream.ok) {
    return new Response("Backend SSE unavailable", { status: 502 });
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      // Disable Vercel / Next.js response buffering
      "X-Accel-Buffering": "no",
    },
  });
}
