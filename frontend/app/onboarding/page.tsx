import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { api } from "@/lib/api";
import { OnboardingFlow } from "@/components/OnboardingFlow";

export default async function OnboardingPage() {
  const session = await auth();
  if (!session) redirect("/login");

  const token = session.accessToken;

  // If already calibrated → go to dashboard
  try {
    await api.onboarding.profile(token);
    redirect("/dashboard");
  } catch {
    // 404 = not done yet, continue showing onboarding
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-start justify-center py-12 px-4">
      <div className="w-full max-w-lg">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🧠</span>
            <span className="text-sm font-semibold text-gray-400">ExoCortex</span>
          </div>
          <a
            href="/dashboard"
            className="text-xs text-gray-600 hover:text-gray-400 transition-colors"
          >
            Пропустить →
          </a>
        </div>

        <OnboardingFlow token={token} />
      </div>
    </div>
  );
}
