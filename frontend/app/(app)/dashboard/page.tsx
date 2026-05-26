import { auth } from "@/auth";
import { api } from "@/lib/api";
import type { Command, DayPlan, EnergyScore, MorningBrief, ReviewSessionSummary } from "@/lib/types";
import { DailyPlanCard } from "@/components/DailyPlanCard";
import { EnergyCard } from "@/components/EnergyCard";
import { DashboardSSEListener } from "@/components/DashboardSSEListener";
import Link from "next/link";

export default async function DashboardPage() {
  const session = await auth();
  const token = session!.accessToken;

  const [energyResult, planResult, reviewsResult, profileResult, commandsResult, briefResult] =
    await Promise.allSettled([
      api.energy.score(token) as Promise<EnergyScore>,
      api.secretary.todayPlan(token) as Promise<DayPlan>,
      api.reviews.pending(token) as Promise<ReviewSessionSummary[]>,
      api.onboarding.profile(token),
      api.commands.list(token, { limit: 50 }) as Promise<Command[]>,
      api.brief.today(token) as Promise<MorningBrief | { status: string }>,
    ]);

  const energy = energyResult.status === "fulfilled" ? energyResult.value : null;
  const plan = planResult.status === "fulfilled" ? planResult.value : null;
  const pendingReviews = reviewsResult.status === "fulfilled" ? reviewsResult.value : [];
  const dailyReview = pendingReviews.find((r) => r.review_type === "daily");
  const hasProfile = profileResult.status === "fulfilled";
  const allCommands = commandsResult.status === "fulfilled" ? commandsResult.value : [];
  const pendingConfirmations = allCommands.filter(
    (c) => c.kernel_status === "pending_confirmation"
  ).length;

  // Brief is available only when it's a full object (not a 202 stub)
  const briefRaw = briefResult.status === "fulfilled" ? briefResult.value : null;
  const brief = briefRaw && "greeting" in briefRaw ? (briefRaw as MorningBrief) : null;

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <DashboardSSEListener />
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Today</h1>
        <span className="text-sm text-gray-400">
          {new Date().toLocaleDateString("ru-RU", {
            weekday: "long", month: "long", day: "numeric",
          })}
        </span>
      </div>

      {/* Morning Brief */}
      {brief && (
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-5 space-y-3">
          <p className="text-sm font-semibold text-white">{brief.greeting}</p>
          <ul className="space-y-1.5">
            {brief.bullets.map((b, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                <span className="flex-shrink-0">{b.emoji}</span>
                <span>{b.text}</span>
              </li>
            ))}
          </ul>
          {brief.focus_recommendation && (
            <p className="text-xs text-indigo-400 border-t border-gray-800 pt-3">
              🎯 {brief.focus_recommendation}
            </p>
          )}
          {brief.energy_tip && (
            <p className="text-xs text-amber-400/80">{brief.energy_tip}</p>
          )}
        </div>
      )}

      {/* Onboarding banner — shown until profile is created */}
      {!hasProfile && (
        <Link
          href="/onboarding"
          className="flex items-center gap-4 rounded-xl bg-amber-950/40 border border-amber-700/40 hover:border-amber-500/60 px-5 py-4 transition-colors"
        >
          <span className="text-2xl">🧭</span>
          <div className="flex-1">
            <p className="text-sm font-semibold text-amber-200">Настрой ExoCortex под себя</p>
            <p className="text-xs text-amber-400/70 mt-0.5">
              Пройди интервью — система научится работать именно под тебя
            </p>
          </div>
          <span className="text-amber-400 text-lg">→</span>
        </Link>
      )}

      {/* Morning review banner */}
      {dailyReview && (
        <Link
          href="/review"
          className="flex items-center gap-4 rounded-xl bg-indigo-950/60 border border-indigo-700/50 hover:border-indigo-500/70 px-5 py-4 transition-colors"
        >
          <span className="text-2xl">☀️</span>
          <div className="flex-1">
            <p className="text-sm font-semibold text-indigo-200">Утренняя планёрка ожидает</p>
            <p className="text-xs text-indigo-400/70 mt-0.5">
              AI подготовил план дня — подтверди и начни
            </p>
          </div>
          <span className="text-indigo-400 text-lg">→</span>
        </Link>
      )}

      {/* Energy Status */}
      {energy ? (
        <EnergyCard energy={energy} />
      ) : (
        <Link
          href="/energy"
          className="block rounded-xl border border-dashed border-gray-700 p-6 text-center hover:border-indigo-500 transition-colors"
        >
          <p className="text-gray-400">No energy check-in today</p>
          <p className="text-indigo-400 text-sm mt-1 font-medium">→ Do morning check-in</p>
        </Link>
      )}

      {/* Daily Plan */}
      {plan ? (
        <DailyPlanCard plan={plan} token={token} />
      ) : (
        <div className="rounded-xl border border-dashed border-gray-700 p-6 text-center">
          <p className="text-gray-400">No plan for today yet</p>
          <Link
            href="/plan"
            className="mt-3 inline-block text-sm font-medium text-indigo-400 hover:text-indigo-300"
          >
            → Generate day plan
          </Link>
        </div>
      )}

      {/* Pending confirmations banner */}
      {pendingConfirmations > 0 && (
        <Link
          href="/inbox"
          className="flex items-center gap-4 rounded-xl bg-gray-900 border border-amber-800/40 hover:border-amber-600/60 px-5 py-4 transition-colors"
        >
          <span className="text-2xl">📥</span>
          <div className="flex-1">
            <p className="text-sm font-semibold text-gray-200">
              {pendingConfirmations} задач ждут подтверждения
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              AI проанализировал — нужно твоё решение
            </p>
          </div>
          <span className="text-sm bg-amber-600 text-white px-2 py-0.5 rounded-full font-medium">
            {pendingConfirmations}
          </span>
        </Link>
      )}

      {/* Quick actions */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { href: "/inbox", label: "Inbox", icon: "📥" },
          { href: "/review", label: "Планёрка", icon: "📅" },
          { href: "/habits", label: "Привычки", icon: "🔁" },
          { href: "/chat/core_advisor", label: "Advisor", icon: "🧠" },
        ].map(({ href, label, icon }) => (
          <Link
            key={href}
            href={href}
            className="flex flex-col items-center gap-2 rounded-xl bg-gray-900 hover:bg-gray-800 border border-gray-800 p-4 transition-colors"
          >
            <span className="text-2xl">{icon}</span>
            <span className="text-sm text-gray-300">{label}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
