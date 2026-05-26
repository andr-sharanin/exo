"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut } from "next-auth/react";
import clsx from "clsx";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: "🏠" },
  { href: "/review", label: "Планёрки", icon: "📅" },
  { href: "/inbox", label: "Inbox", icon: "📥" },
  { href: "/focus", label: "Focus", icon: "⚡" },
  { href: "/quick", label: "Быстрые", icon: "🏃" },
  { href: "/plan", label: "Day Plan", icon: "📋" },
  { href: "/habits", label: "Habits", icon: "🔁" },
  { href: "/energy", label: "Check-in", icon: "🔋" },
  { href: "/goals", label: "Goals", icon: "🏔️" },
  { href: "/chat/core_advisor", label: "Advisor", icon: "🧠" },
  { href: "/deposits", label: "Deposits", icon: "💰" },
  { href: "/settings/calendar", label: "Календари", icon: "🗓️" },
  { href: "/settings/governance", label: "Governance", icon: "📜" },
  { href: "/settings/subscription", label: "Подписка", icon: "💎" },
  { href: "/settings/team", label: "Команда", icon: "👥" },
  { href: "/modes", label: "Режим", icon: "🎯" },
];

const ADMIN_NAV = [
  { href: "/admin", label: "Admin", icon: "⚙️" },
  { href: "/admin/agents", label: "Agents", icon: "🤖" },
  { href: "/admin/settings", label: "Settings", icon: "🔑" },
];

export function Sidebar({ isAdmin }: { isAdmin: boolean }) {
  const pathname = usePathname();

  return (
    <aside className="w-56 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col">
      <div className="p-4 border-b border-gray-800">
        <span className="text-lg font-bold text-white">🧠 ExoCortex</span>
      </div>

      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {NAV.map(({ href, label, icon }) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
              pathname === href || pathname.startsWith(href + "/")
                ? "bg-indigo-600 text-white"
                : "text-gray-400 hover:text-white hover:bg-gray-800"
            )}
          >
            <span>{icon}</span>
            <span>{label}</span>
          </Link>
        ))}

        {isAdmin && (
          <>
            <div className="pt-3 pb-1">
              <p className="text-xs text-gray-600 uppercase tracking-wide px-3">Admin</p>
            </div>
            {ADMIN_NAV.map(({ href, label, icon }) => (
              <Link
                key={href}
                href={href}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                  pathname === href
                    ? "bg-indigo-600 text-white"
                    : "text-gray-400 hover:text-white hover:bg-gray-800"
                )}
              >
                <span>{icon}</span>
                <span>{label}</span>
              </Link>
            ))}
          </>
        )}
      </nav>

      <div className="p-3 border-t border-gray-800 space-y-1">
        <Link
          href="/account"
          className={clsx(
            "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
            pathname === "/account"
              ? "bg-indigo-600 text-white"
              : "text-gray-400 hover:text-white hover:bg-gray-800"
          )}
        >
          <span>👤</span>
          <span>Аккаунт</span>
        </Link>
        <button
          onClick={() => signOut({ callbackUrl: "/login" })}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
        >
          <span>🚪</span>
          <span>Sign out</span>
        </button>
      </div>
    </aside>
  );
}
