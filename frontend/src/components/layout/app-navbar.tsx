"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "Subida" },
  { href: "/correos", label: "Correos" },
  { href: "/lotes", label: "Lotes" },
];

export function AppNavbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 w-full border-b border-[var(--color-border)] bg-[color:var(--color-header)]/78 backdrop-blur-xl">
      <div className="mx-auto flex w-full max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <Link
          className="flex items-center gap-3 text-left"
          href="/"
        >
          <span aria-hidden="true" className="brand-mark" />
          <div className="space-y-1">
            <p className="text-[0.68rem] font-semibold uppercase tracking-[0.34em] text-[var(--color-muted)]">
              Plataforma
            </p>
            <p className="text-sm font-semibold tracking-[0.18em] text-[var(--color-text)] sm:text-base">
              PHISHING DETECTOR
            </p>
          </div>
        </Link>

        <nav className="ml-auto flex flex-wrap items-center gap-2">
          {navItems.map((item) => {
            const isActive =
              pathname === item.href || pathname.startsWith(`${item.href}/`);

            return (
              <Link
                key={item.href}
                className={`topbar-link ${isActive ? "topbar-link-active" : ""}`}
                href={item.href}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
