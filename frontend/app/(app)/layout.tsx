import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { Sidebar } from "@/components/Sidebar";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();
  if (!session) redirect("/login");

  const isAdmin = session.roles.includes("admin") || session.roles.includes("system_admin");

  return (
    <div className="flex h-screen overflow-hidden bg-gray-950">
      <Sidebar isAdmin={isAdmin} />
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}
