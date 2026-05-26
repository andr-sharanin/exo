import { auth } from "@/auth";
import { api } from "@/lib/api";
import { CalendarSettings } from "@/components/CalendarSettings";

interface CalendarIntegration {
  id: string;
  provider: string;
  display_name: string;
  sync_direction: string;
  is_active: boolean;
  last_synced_at: string | null;
  last_error: string | null;
  created_at: string;
}

export default async function CalendarSettingsPage() {
  const session = await auth();
  const token = session!.accessToken;

  let integrations: CalendarIntegration[] = [];
  try {
    integrations = (await api.calendar.integrations(token)) as CalendarIntegration[];
  } catch {
    // show empty state
  }

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Календари</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          CalDAV, Google Calendar — синхронизация событий с планом
        </p>
      </div>

      <CalendarSettings initialIntegrations={integrations} token={token} />
    </div>
  );
}
