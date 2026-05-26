import { auth } from "@/auth";
import { api } from "@/lib/api";
import type { AgentPersona } from "@/lib/types";
import { AgentsManager } from "@/components/AgentsManager";

export default async function AdminAgentsPage() {
  const session = await auth();
  const token = session!.accessToken;

  let personas: AgentPersona[] = [];
  try {
    personas = (await api.adminAgents.list(token)) as AgentPersona[];
  } catch {
    // show empty state
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Agent Personas</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Управление AI-агентами: промпты, обучение, база знаний
        </p>
      </div>

      <AgentsManager initialPersonas={personas} token={token} />
    </div>
  );
}
