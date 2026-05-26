import { auth } from "@/auth";
import { redirect } from "next/navigation";

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();
  const isAdmin = session?.roles.includes("admin") || session?.roles.includes("system_admin");
  if (!isAdmin) redirect("/dashboard");
  return <>{children}</>;
}
