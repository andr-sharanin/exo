import { auth } from "@/auth";
import { api } from "@/lib/api";
import { SubscriptionPanel } from "@/components/SubscriptionPanel";

export const metadata = { title: "Subscription — ExoCortex" };

export default async function SubscriptionPage({
  searchParams,
}: {
  searchParams: Promise<{ success?: string; canceled?: string }>;
}) {
  const session = await auth();
  const token = session!.accessToken;
  const params = await searchParams;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data = await api.subscriptions.current(token) as any;

  return (
    <div className="p-6 max-w-xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Подписка</h1>
        <p className="text-sm text-gray-400 mt-1">
          Управляй тарифным планом и лимитами аккаунта.
        </p>
      </div>

      {params.success && (
        <div className="rounded-xl border border-green-800 bg-green-950 px-4 py-3">
          <p className="text-sm text-green-300 font-medium">
            ✓ Подписка успешно оформлена. Новые лимиты уже активны.
          </p>
        </div>
      )}

      {params.canceled && (
        <div className="rounded-xl border border-amber-800 bg-amber-950 px-4 py-3">
          <p className="text-sm text-amber-300">
            Оплата отменена — тариф не изменён.
          </p>
        </div>
      )}

      <SubscriptionPanel initialData={data} token={token} />
    </div>
  );
}
