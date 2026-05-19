type PaginationControlsProps = {
  page: number;
  pageSize: number;
  itemCount: number;
  hasNext: boolean;
  onPageChange: (page: number) => void;
};

export function PaginationControls({
  page,
  pageSize,
  itemCount,
  hasNext,
  onPageChange,
}: PaginationControlsProps) {
  const start = page * pageSize + 1;
  const end = page * pageSize + itemCount;

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-[var(--color-border)] bg-white/70 px-4 py-3 text-sm text-[var(--color-muted)] sm:flex-row sm:items-center sm:justify-between">
      <span>
        Mostrando {start}-{end}
      </span>
      <div className="flex flex-wrap gap-2">
        <button
          className="nav-link disabled:cursor-not-allowed disabled:opacity-50"
          disabled={page === 0}
          onClick={() => onPageChange(Math.max(page - 1, 0))}
          type="button"
        >
          Anterior
        </button>
        <button
          className="nav-link disabled:cursor-not-allowed disabled:opacity-50"
          disabled={!hasNext}
          onClick={() => onPageChange(page + 1)}
          type="button"
        >
          Siguiente
        </button>
      </div>
    </div>
  );
}
