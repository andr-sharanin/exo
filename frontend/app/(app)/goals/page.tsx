import { auth } from "@/auth";
import { api } from "@/lib/api";
import type { PlanningGoal, Horizon } from "@/lib/types";
import { GoalsList } from "@/components/GoalsList";

const HORIZONS: Horizon[] = ["vision", "annual", "quarterly", "monthly", "weekly", "daily"];

export default async function GoalsPage() {
  const session = await auth();
  const token = session!.accessToken;
  let goals: PlanningGoal[] = [];
  try {
    goals = await api.goals.list(token) as PlanningGoal[];
  } catch {
    goals = [];
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Planning Goals</h1>
      </div>

      <div className="space-y-6">
        {HORIZONS.map((horizon) => {
          const items = goals.filter((g) => g.horizon === horizon);
          return (
            <GoalsList key={horizon} horizon={horizon} goals={items} token={token} />
          );
        })}
      </div>
    </div>
  );
}
