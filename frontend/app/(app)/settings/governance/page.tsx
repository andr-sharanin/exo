import { auth } from "@/auth";
import { api } from "@/lib/api";
import { GovernanceSettings } from "@/components/GovernanceSettings";

export const metadata = { title: "Governance — ADR" };

export default async function GovernancePage() {
  const session = await auth();
  const token = session!.accessToken;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [policy, records] = await Promise.all([
    api.governance.getPolicy(token),
    api.governance.listRecords(token),
  ]) as [any, any[]];

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Governance</h1>
        <p className="text-sm text-gray-400 mt-1">
          Режим подтверждения решений об откате обязательств. Solo — самоконтроль. x2 — партнёрский контроль.
        </p>
      </div>
      <GovernanceSettings initialPolicy={policy} initialRecords={records} token={token} />
    </div>
  );
}
