import { auth } from "@/auth";
import { AccountPanel } from "@/components/AccountPanel";

export default async function AccountPage() {
  const session = await auth();
  const token = session!.accessToken;

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-white">Аккаунт</h1>
      <AccountPanel token={token} />
    </div>
  );
}
