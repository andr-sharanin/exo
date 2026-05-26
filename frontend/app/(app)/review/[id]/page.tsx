import { auth } from "@/auth";
import { api } from "@/lib/api";
import type { ReviewSessionDetail } from "@/lib/types";
import { ReviewSessionCard } from "@/components/ReviewSessionCard";
import Link from "next/link";
import { notFound } from "next/navigation";

export default async function ReviewDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const session = await auth();
  const token = session!.accessToken;

  let detail: ReviewSessionDetail | null = null;
  try {
    detail = (await api.reviews.get(id, token)) as ReviewSessionDetail;
  } catch {
    notFound();
  }

  if (!detail) notFound();

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-4">
      <Link
        href="/review"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-300 transition-colors"
      >
        ← Все планёрки
      </Link>
      <ReviewSessionCard session={detail} token={token} />
    </div>
  );
}
