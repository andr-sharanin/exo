import { auth } from "@/auth";
import { api } from "@/lib/api";
import Link from "next/link";

export default async function AdminDashboardPage() {
  const session = await auth();
  const token = session!.accessToken;

  const [healthResult, statsResult] = await Promise.allSettled([
    api.admin.health(token),
    api.admin.aiStats(token),
  ]);

  const health = healthResult.status === "fulfilled" ? healthResult.value as { status: string; ai_tiers: string[] } : null;
  const stats = statsResult.status === "fulfilled" ? statsResult.value as { total_requests: number; success_rate: number } : null;

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-white">Admin Panel</h1>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">System</p>
          <p className={`text-lg font-bold mt-1 ${health?.status === "healthy" ? "text-green-400" : "text-red-400"}`}>
            {health?.status ?? "—"}
          </p>
          <p className="text-xs text-gray-600 mt-1">
            Tiers: {health?.ai_tiers.join(", ") ?? "—"}
          </p>
        </div>
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">AI Requests</p>
          <p className="text-lg font-bold mt-1 text-white">{stats?.total_requests ?? "—"}</p>
          <p className="text-xs text-gray-600 mt-1">
            Success: {stats ? `${(stats.success_rate * 100).toFixed(1)}%` : "—"}
          </p>
        </div>
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Quick Links</p>
          <div className="mt-2 space-y-1">
            <Link href="/admin/agents" className="block text-sm text-indigo-400 hover:text-indigo-300">→ Agents</Link>
            <Link href="/admin/settings" className="block text-sm text-indigo-400 hover:text-indigo-300">→ Settings</Link>
            <Link href="/admin/audit" className="block text-sm text-indigo-400 hover:text-indigo-300">→ Audit Log</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
