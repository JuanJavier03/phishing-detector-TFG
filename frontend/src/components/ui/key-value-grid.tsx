type Item = {
  label: string;
  value: string;
};

type KeyValueGridProps = {
  items: Item[];
};

export function KeyValueGrid({ items }: KeyValueGridProps) {
  return (
    <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {items.map((item) => (
        <div
          key={item.label}
          className="rounded-2xl border border-[var(--color-border)] bg-white/70 px-4 py-3"
        >
          <dt className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]">
            {item.label}
          </dt>
          <dd className="mt-2 break-all text-sm font-medium">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}
