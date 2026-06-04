import { auth } from "@/auth";
import { api } from "@/lib/api";
import type { ConfigEntry } from "@/lib/types";
import { AdminSettingsForm } from "@/components/AdminSettingsForm";

export default async function AdminSettingsPage() {
  const session = await auth();
  const token = session!.accessToken;

  let entries: ConfigEntry[] = [];
  try {
    entries = await api.config.list(token) as ConfigEntry[];
  } catch {
    entries = [];
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">System Settings</h1>
        <p className="text-sm text-gray-400 mt-1">
          Configure API keys and integration settings. Secrets are encrypted and never shown in full.
        </p>
      </div>
      <AdminSettingsForm entries={entries} token={token} />
    </div>
  );
}
