type Point = {
  label: string;
  count: number;
};

type SimpleBarChartProps = {
  data: Point[];
};

export function SimpleBarChart({ data }: SimpleBarChartProps) {
  if (!data.length) {
    return (
      <div className="rounded-2xl border border-dashed border-[var(--color-border)] px-4 py-8 text-sm text-[var(--color-muted)]">
        Sin datos para representar.
      </div>
    );
  }

  const maxValue = Math.max(...data.map((item) => item.count), 1);

  return (
    <div className="space-y-3">
      {data.map((item) => (
        <div key={item.label} className="space-y-1">
          <div className="flex items-center justify-between gap-3 text-sm">
            <span className="font-medium">{item.label}</span>
            <span className="font-mono text-[var(--color-muted)]">
              {item.count}
            </span>
          </div>
          <div className="h-3 rounded-full bg-[var(--color-panel-strong)]">
            <div
              className="h-3 rounded-full bg-[var(--color-accent)]"
              style={{
                width: `${Math.max((item.count / maxValue) * 100, 6)}%`,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
