import type { ReactNode } from "react";

type SectionHeadingProps = {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
};

export function SectionHeading({
  eyebrow,
  title,
  description,
  actions,
}: SectionHeadingProps) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="space-y-1">
        {eyebrow && (
          <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--color-accent)]">
            {eyebrow}
          </p>
        )}
        <h2 className="max-w-4xl text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">
          {title}
        </h2>
        {description && (
          <p className="max-w-3xl text-sm leading-6 text-[var(--color-muted)]">
            {description}
          </p>
        )}
      </div>
      {actions && <div>{actions}</div>}
    </div>
  );
}
