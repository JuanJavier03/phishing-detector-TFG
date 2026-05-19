type StatusBadgeProps = {
  status: string;
};

const statusStyles: Record<string, string> = {
  queued:
    "bg-[var(--color-warning-soft)] text-[var(--color-warning)] border-[var(--color-warning)]/20",
  running:
    "bg-[var(--color-accent-soft)] text-[var(--color-accent)] border-[var(--color-accent)]/20",
  partial:
    "bg-[var(--color-warning-soft)] text-[var(--color-warning)] border-[var(--color-warning)]/20",
  pending:
    "bg-slate-100 text-slate-700 border-slate-300",
  completed:
    "bg-[var(--color-success-soft)] text-[var(--color-success)] border-[var(--color-success)]/20",
  cancelled:
    "bg-[var(--color-warning-soft)] text-[var(--color-warning)] border-[var(--color-warning)]/20",
  error:
    "bg-[var(--color-danger-soft)] text-[var(--color-danger)] border-[var(--color-danger)]/20",
  failed:
    "bg-[var(--color-danger-soft)] text-[var(--color-danger)] border-[var(--color-danger)]/20",
  not_analyzed:
    "bg-slate-100 text-slate-700 border-slate-300",
  available:
    "bg-slate-100 text-slate-700 border-slate-300",
};

const statusLabels: Record<string, string> = {
  queued: "En cola",
  running: "En progreso",
  partial: "A medias",
  pending: "Pendiente",
  completed: "Completado",
  cancelled: "Cancelado",
  error: "Error",
  failed: "Fallido",
  not_analyzed: "Sin analizar",
  available: "Sin analizar",
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const className =
    statusStyles[status] ?? "bg-slate-100 text-slate-700 border-slate-300";
  const label = statusLabels[status] ?? status;

  return (
    <span
      className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${className}`}
    >
      {label}
    </span>
  );
}
