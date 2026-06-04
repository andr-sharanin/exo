import { auth } from "@/auth";
import { api } from "@/lib/api";
import type { AgentSession, EntityType } from "@/lib/types";
import { ChatWindow } from "@/components/ChatWindow";
import { notFound } from "next/navigation";

const VALID_TYPES: EntityType[] = [
  "core_advisor", "tutor", "reflective_support", "coach", "consultant",
];

const LABELS: Record<EntityType, string> = {
  core_advisor: "Core Advisor",
  tutor: "Tutor",
  reflective_support: "Reflective Support",
  coach: "Coach",
  consultant: "Consultant",
};

export default async function ChatPage({
  params,
}: {
  params: Promise<{ entityType: string }>;
}) {
  const { entityType } = await params;
  if (!VALID_TYPES.includes(entityType as EntityType)) notFound();

  const session = await auth();
  const token = session!.accessToken;

  let agentSession: AgentSession | null = null;
  try {
    agentSession = await api.agents.createSession(
      { entity_type: entityType, session_mode: "advisory" },
      token
    ) as AgentSession;
  } catch {
    notFound();
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-gray-800">
        <h1 className="text-lg font-semibold text-white">
          {LABELS[entityType as EntityType]}
        </h1>
        <p className="text-xs text-gray-500">Advisory session</p>
      </div>
      <ChatWindow session={agentSession!} token={token} />
    </div>
  );
}
