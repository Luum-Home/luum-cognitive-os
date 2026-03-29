"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navigation = [
  { name: "Dashboard", href: "/" },
  { name: "Rules", href: "/rules" },
  { name: "Skills", href: "/skills" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-56 flex-col border-r border-[var(--color-border)] bg-[var(--color-bg-sidebar)]">
      <div className="flex h-14 items-center border-b border-[var(--color-border)] px-4">
        <span className="text-sm font-bold tracking-tight">COS Dashboard</span>
      </div>
      <nav className="flex-1 px-2 py-4">
        <ul className="space-y-1">
          {navigation.map((item) => {
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`block rounded-md px-3 py-2 text-sm transition-colors ${
                    isActive
                      ? "bg-[var(--color-accent)]/10 text-[var(--color-accent)]"
                      : "text-[var(--color-text-muted)] hover:bg-[var(--color-bg-card)] hover:text-[var(--color-text)]"
                  }`}
                >
                  {item.name}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="border-t border-[var(--color-border)] px-4 py-3 text-xs text-[var(--color-text-muted)]">
        v0.1.0
      </div>
    </aside>
  );
}
