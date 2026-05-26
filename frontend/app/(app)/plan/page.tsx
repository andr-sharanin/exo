import { auth } from "@/auth";
import { api } from "@/lib/api";
import type { DayPlan } from "@/lib/types";
import { PlanPageClient } from "@/components/PlanPageClient";

export const metadata = { title: "Day Plan" };

export default async function PlanPage() {
  const session = await auth();
  const token = session!.accessToken;

  let plan: DayPlan | null = null;
  try {
    plan = await api.secretary.todayPlan(token) as DayPlan;
  } catch {
    // 404 — no plan yet
  }

  return <PlanPageClient initialPlan={plan} token={token} />;
}
