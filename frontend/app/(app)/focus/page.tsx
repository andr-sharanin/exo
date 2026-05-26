import { auth } from "@/auth";
import { api } from "@/lib/api";
import type { DayPlan } from "@/lib/types";
import { FocusScreen } from "@/components/FocusScreen";

export default async function FocusPage() {
  const session = await auth();
  const token = session!.accessToken;

  let plan: DayPlan | null = null;
  try {
    plan = await api.secretary.todayPlan(token) as DayPlan;
  } catch {
    // No plan yet
  }

  // Pass all items; FocusScreen handles step selection
  const items = plan?.items ?? [];

  return <FocusScreen items={items} planId={plan?.id ?? null} token={token} />;
}
