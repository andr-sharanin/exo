import { auth } from "@/auth";
import { TeamJoinPanel } from "@/components/TeamJoinPanel";

export const metadata = { title: "Принять приглашение — ExoCortex" };

export default async function TeamJoinPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const { token } = await searchParams;
  const session = await auth();
  const authToken = session!.accessToken;

  return (
    <div className="p-6 max-w-md mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Приглашение в команду</h1>
        <p className="text-sm text-gray-400 mt-1">
          Примите приглашение, чтобы присоединиться к рабочему пространству.
        </p>
      </div>
      <TeamJoinPanel inviteToken={token ?? ""} authToken={authToken} />
    </div>
  );
}
