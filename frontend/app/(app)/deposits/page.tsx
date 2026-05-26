import { auth } from "@/auth";
import { api } from "@/lib/api";
import type { CommitmentDeposit } from "@/lib/types";
import { DepositsList } from "@/components/DepositsList";
import { CreateDepositForm } from "@/components/CreateDepositForm";

export default async function DepositsPage() {
  const session = await auth();
  const token = session!.accessToken;

  const [deposits, steps] = await Promise.all([
    api.deposits.list(token) as Promise<CommitmentDeposit[]>,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    api.steps.listAll(token).catch(() => []) as Promise<any[]>,
  ]);

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Commitment Deposits</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Поставь деньги на кон — и выполни.
          </p>
        </div>
      </div>

      <CreateDepositForm steps={steps} token={token} />

      <DepositsList deposits={deposits} token={token} />
    </div>
  );
}
