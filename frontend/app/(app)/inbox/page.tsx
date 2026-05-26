import { auth } from "@/auth";
import { api } from "@/lib/api";
import type { Command } from "@/lib/types";
import { InboxList } from "@/components/InboxList";

export default async function InboxPage() {
  const session = await auth();
  const token = session!.accessToken;

  let commands: Command[] = [];
  try {
    // Load recent commands (pending + confirmed, last 30)
    commands = (await api.commands.list(token, { limit: 30 })) as Command[];
  } catch {
    // show empty state
  }

  const pendingCount = commands.filter(
    (c) => c.kernel_status === "pending_confirmation"
  ).length;

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            Inbox
            {pendingCount > 0 && (
              <span className="text-sm bg-amber-600 text-white px-2 py-0.5 rounded-full font-normal">
                {pendingCount}
              </span>
            )}
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Каждая задача проходит через твои ядра перед выполнением
          </p>
        </div>
      </div>

      <InboxList initialCommands={commands} token={token} />
    </div>
  );
}
