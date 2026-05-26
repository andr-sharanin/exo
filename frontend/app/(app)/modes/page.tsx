import { auth } from "@/auth";
import { api } from "@/lib/api";
import { ModeSwitcher } from "@/components/ModeSwitcher";

export const metadata = { title: "Режим системы" };

export default async function ModesPage() {
  const session = await auth();
  const token = session!.accessToken;

  let currentMode: string | null = null;
  try {
    const data = await api.modes.current(token) as { mode: string };
    currentMode = data.mode;
  } catch {
    // 404 = no mode set yet, start with null
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Режим системы</h1>
        <p className="text-sm text-gray-400 mt-1">
          Режим определяет поведение плана, приоритеты агентов и нагрузку на день.
        </p>
      </div>
      <ModeSwitcher initialMode={currentMode} token={token} />
    </div>
  );
}
