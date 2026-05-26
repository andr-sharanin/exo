import { auth } from "@/auth";
import { api } from "@/lib/api";
import type { StepObject } from "@/lib/types";
import { QuickQueue } from "@/components/QuickQueue";

export const metadata = { title: "Быстрые задачи" };

export default async function QuickPage() {
  const session = await auth();
  const token = session!.accessToken;

  let steps: StepObject[] = [];
  try {
    steps = await api.steps.listQuick(token) as StepObject[];
  } catch {
    // show empty
  }

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">⚡ Быстрые задачи</h1>
        <p className="text-sm text-gray-400 mt-1">
          Задачи ≤15 минут в статусе «готов». Нажми «Готово» — зафиксирует результат и уберёт из списка.
        </p>
      </div>
      <QuickQueue initialSteps={steps} token={token} />
    </div>
  );
}
