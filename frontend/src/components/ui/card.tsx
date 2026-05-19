import type { ReactNode } from "react";

type CardProps = {
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
};

export function Card({ title, subtitle, actions, children }: CardProps) {
  return (
    <section className="rounded-[30px] border border-[var(--color-border)] bg-[var(--color-panel)] p-5 shadow-[0_24px_60px_rgba(16,34,49,0.09)] backdrop-blur-md sm:p-6">
      {(title || subtitle || actions) && (
        <header className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-1">
            {title && <h2 className="text-lg font-semibold tracking-[-0.02em]">{title}</h2>}
            {subtitle && (
              <p className="text-sm text-[var(--color-muted)]">{subtitle}</p>
            )}
          </div>
          {actions && <div>{actions}</div>}
        </header>
      )}
      {children}
    </section>
  );
}
