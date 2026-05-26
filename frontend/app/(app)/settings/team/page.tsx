import { auth } from "@/auth";
import { api } from "@/lib/api";
import { TeamPanel } from "@/components/TeamPanel";

export const metadata = { title: "Команда — ExoCortex" };

export default async function TeamPage() {
  const session = await auth();
  const token = session!.accessToken;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data = await api.subscriptions.current(token) as any;

  // Load invitations only for team tier (free/pro will get a 402 that we catch)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let invitations: any[] = [];
  if (data?.tier === "team") {
    try {
      invitations = await api.team.listInvitations(token) as typeof invitations;
    } catch {
      // non-critical — show empty list
    }
  }

  return (
    <div className="p-6 max-w-xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Команда</h1>
        <p className="text-sm text-gray-400 mt-1">
          Управление Team тарифом и участниками воркспейса.
        </p>
      </div>

      <TeamPanel subscription={data} initialInvitations={invitations} token={token} />
    </div>
  );
}
