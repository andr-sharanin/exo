import { auth } from "@/auth";
import { api } from "@/lib/api";
import type { ReviewSessionSummary, ReviewSessionDetail } from "@/lib/types";
import { ReviewSessionCard } from "@/components/ReviewSessionCard";
import Link from "next/link";

const NEXT_SCHEDULE = [
  { label: "Утренняя планёрка", time: "07:00 ежедневно", icon: "☀️" },
  { label: "Еженедельная планёрка", time: "Пятница, 18:00", icon: "📅" },
  { label: "Ежемесячная планёрка", time: "Последний день месяца, 09:00", icon: "🗓️" },
];

export default async function ReviewPage() {
  const session = await auth();
  const token = session!.accessToken;

  // Load pending sessions
  let pending: ReviewSessionSummary[] = [];
  try {
    pending = (await api.reviews.pending(token)) as ReviewSessionSummary[];
  } catch {
    // not critical — show empty state
  }

  // Load history (last 10 completed)
  let history: ReviewSessionSummary[] = [];
  try {
    history = (await api.reviews.history(token, 10)) as ReviewSessionSummary[];
  } catch {
    // not critical
  }

  // Pick the most important session to show (daily > weekly > monthly)
  const priority = ["daily", "weekly", "monthly"];
  const sorted = [...pending].sort(
    (a, b) => priority.indexOf(a.review_type) - priority.indexOf(b.review_type)
  );
  const active = sorted[0] ?? null;

  let activeDetail: ReviewSessionDetail | null = null;
  if (active) {
    try {
      activeDetail = (await api.reviews.get(active.id, token)) as ReviewSessionDetail;
    } catch {
      activeDetail = null;
    }
  }

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Планёрки</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Думай один раз — утром. Потом просто выполняй.
          </p>
        </div>
        {pending.length > 1 && (
          <span className="text-xs bg-amber-900 text-amber-300 px-2.5 py-1 rounded-full font-medium">
            {pending.length} ожидают
          </span>
        )}
      </div>

      {/* Active session */}
      {activeDetail ? (
        <ReviewSessionCard session={activeDetail} token={token} />
      ) : (
        <NoActiveSessions token={token} />
      )}

      {/* Other pending sessions */}
      {sorted.length > 1 && (
        <div className="space-y-3">
          <p className="text-xs text-gray-600 uppercase tracking-wide font-medium">
            Ещё {sorted.length - 1} планёрки ожидают
          </p>
          {sorted.slice(1).map((s) => (
            <Link
              key={s.id}
              href={`/review/${s.id}`}
              className="flex items-center gap-3 rounded-xl bg-gray-900 border border-gray-800 hover:border-gray-700 px-4 py-3 transition-colors"
            >
              <span className="text-lg">
                {s.review_type === "daily" ? "☀️" : s.review_type === "weekly" ? "📅" : "🗓️"}
              </span>
              <div className="flex-1">
                <p className="text-sm text-gray-200">
                  {s.review_type === "daily"
                    ? "Утренняя планёрка"
                    : s.review_type === "weekly"
                    ? "Еженедельная планёрка"
                    : "Ежемесячная планёрка"}
                </p>
                <p className="text-xs text-gray-500">
                  {new Date(s.created_at).toLocaleDateString("ru-RU")}
                </p>
              </div>
              <span className="text-xs text-indigo-400">→</span>
            </Link>
          ))}
        </div>
      )}

      {/* History */}
      {history.length > 0 && (
        <div className="rounded-xl bg-gray-900 border border-gray-800">
          <div className="px-5 py-3 border-b border-gray-800">
            <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">
              История планёрок
            </p>
          </div>
          <div className="divide-y divide-gray-800">
            {history.map((s) => (
              <Link
                key={s.id}
                href={`/review/${s.id}`}
                className="flex items-center gap-3 px-5 py-3 hover:bg-gray-800/50 transition-colors"
              >
                <span className="text-base">
                  {s.review_type === "daily" ? "☀️" : s.review_type === "weekly" ? "📅" : "🗓️"}
                </span>
                <div className="flex-1">
                  <p className="text-sm text-gray-300">
                    {s.review_type === "daily"
                      ? "Утренняя"
                      : s.review_type === "weekly"
                      ? "Еженедельная"
                      : "Ежемесячная"}
                  </p>
                  <p className="text-xs text-gray-600">
                    {new Date(s.created_at).toLocaleDateString("ru-RU", {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                    })}
                  </p>
                </div>
                <span className="text-xs text-green-500">✓</span>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Schedule reference */}
      <div className="rounded-xl bg-gray-900 border border-gray-800 divide-y divide-gray-800">
        <div className="px-5 py-3">
          <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">
            Расписание планёрок
          </p>
        </div>
        {NEXT_SCHEDULE.map(({ label, time, icon }) => (
          <div key={label} className="flex items-center gap-3 px-5 py-3">
            <span className="text-base">{icon}</span>
            <div>
              <p className="text-sm text-gray-300">{label}</p>
              <p className="text-xs text-gray-600">{time}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Empty state ────────────────────────────────────────────────────────────────
function NoActiveSessions({ token }: { token: string }) {
  return (
    <div className="rounded-xl border border-dashed border-gray-700 p-8 text-center space-y-3">
      <p className="text-3xl">✅</p>
      <p className="text-gray-300 font-medium">Нет активных планёрок</p>
      <p className="text-sm text-gray-600">
        Следующая утренняя планёрка появится в 07:00
      </p>
      <form
        action={async () => {
          "use server";
          const s = await (await import("@/auth")).auth();
          await api.reviews.triggerDaily(s!.accessToken);
        }}
      >
        <button
          type="submit"
          className="mt-2 text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
        >
          → Создать вручную
        </button>
      </form>
    </div>
  );
}
