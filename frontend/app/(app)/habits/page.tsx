import { auth } from "@/auth";
import { api } from "@/lib/api";
import type { Habit } from "@/lib/types";
import { HabitsList } from "@/components/HabitsList";

export default async function HabitsPage() {
  const session = await auth();
  const token = session!.accessToken;

  let habits: Habit[] = [];
  try {
    habits = (await api.habits.list(token)) as Habit[];
  } catch {
    // show empty state
  }

  const streak7plus = habits.filter((h) => h.streak >= 7).length;
  const doneToday = habits.filter((h) => h.checked_today).length;

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Привычки</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Маленькие действия, большие результаты
          </p>
        </div>
        {habits.length > 0 && (
          <div className="text-right">
            <p className="text-2xl font-bold text-white">{doneToday}/{habits.length}</p>
            <p className="text-xs text-gray-500">выполнено сегодня</p>
          </div>
        )}
      </div>

      {/* Stats row */}
      {habits.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-xl bg-gray-900 border border-gray-800 p-4 text-center">
            <p className="text-xl font-bold text-white">{habits.length}</p>
            <p className="text-xs text-gray-500 mt-0.5">Всего привычек</p>
          </div>
          <div className="rounded-xl bg-gray-900 border border-gray-800 p-4 text-center">
            <p className="text-xl font-bold text-orange-400">{streak7plus}</p>
            <p className="text-xs text-gray-500 mt-0.5">Серий 7+ дней</p>
          </div>
          <div className="rounded-xl bg-gray-900 border border-gray-800 p-4 text-center">
            <p className="text-xl font-bold text-green-400">
              {habits.length > 0
                ? Math.round((doneToday / habits.length) * 100)
                : 0}%
            </p>
            <p className="text-xs text-gray-500 mt-0.5">Сегодня</p>
          </div>
        </div>
      )}

      {/* Habits list with interactions */}
      <HabitsList initialHabits={habits} token={token} />

      {/* Tip */}
      {habits.length > 0 && (
        <p className="text-xs text-center text-gray-700">
          Привычки с включённым планом попадут в ежедневный план дня автоматически
        </p>
      )}
    </div>
  );
}
