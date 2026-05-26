import { auth } from "@/auth";
import { api } from "@/lib/api";
import Link from "next/link";

interface AuditItem {
  id: string;
  tenant_id: string;
  user_id: string;
  object_type: string;
  object_id: string;
  action: string;
  from_status: string | null;
  to_status: string | null;
  occurred_at: string;
}

interface AuditResponse {
  items: AuditItem[];
  total: number;
  limit: number;
  offset: number;
}

function actionColor(action: string) {
  if (action === "create") return "text-green-400";
  if (action === "delete" || action === "forfeit") return "text-red-400";
  if (action === "transition") return "text-indigo-400";
  return "text-gray-400";
}

function objectTypeIcon(objectType: string) {
  const icons: Record<string, string> = {
    command: "📥",
    day_plan: "📅",
    habit_definition: "🔁",
    planning_goal: "🎯",
    energy_score: "⚡",
    system_mode: "🔄",
    commitment_deposit: "💰",
    agent_persona: "🤖",
    review_session: "📋",
  };
  return icons[objectType] ?? "📄";
}

export default async function AdminAuditPage() {
  const session = await auth();
  const token = session!.accessToken;

  let data: AuditResponse | null = null;
  try {
    data = (await api.admin.audit(token, 100)) as AuditResponse;
  } catch {
    // show error state
  }

  const items = data?.items ?? [];

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Audit Log</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {data ? `${data.total} записей` : "Загрузка..."}
          </p>
        </div>
        <Link href="/admin" className="text-sm text-gray-500 hover:text-gray-300">
          ← Admin
        </Link>
      </div>

      {items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-700 p-8 text-center">
          <p className="text-gray-500">Нет записей в аудит-логе</p>
        </div>
      ) : (
        <div className="space-y-1">
          {items.map((item) => (
            <div
              key={item.id}
              className="flex items-start gap-3 rounded-lg bg-gray-900 border border-gray-800 px-4 py-3"
            >
              <span className="text-lg mt-0.5 flex-shrink-0">
                {objectTypeIcon(item.object_type)}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-mono text-gray-400">{item.object_type}</span>
                  <span className={`text-xs font-semibold ${actionColor(item.action)}`}>
                    {item.action}
                  </span>
                  {item.from_status && item.to_status && (
                    <span className="text-xs text-gray-500">
                      {item.from_status} → {item.to_status}
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-600 mt-0.5 font-mono truncate">
                  {item.object_id}
                </p>
              </div>
              <time className="text-xs text-gray-600 flex-shrink-0 mt-0.5">
                {new Date(item.occurred_at).toLocaleString("ru-RU", {
                  day: "numeric",
                  month: "short",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </time>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
