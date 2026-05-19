"use client";

import Link from "next/link";
import { hierarchy, pack } from "d3-hierarchy";
import { formatNumber } from "@/lib/format";
import type {
  BatchScoreAnalyticsItem,
  BatchScoreBin,
  BatchScoreSegment,
  BatchScoreStats,
} from "@/lib/types";

const BAND_BACKGROUNDS = [
  "var(--chart-risk-0)",
  "var(--chart-risk-1)",
  "var(--chart-risk-2)",
  "var(--chart-risk-3)",
  "var(--chart-risk-4)",
];

const BAND_STROKES = [
  "var(--chart-risk-0-strong)",
  "var(--chart-risk-1-strong)",
  "var(--chart-risk-2-strong)",
  "var(--chart-risk-3-strong)",
  "var(--chart-risk-4-strong)",
];

const CHART_SURFACE_CLASS =
  "h-full min-h-0 overflow-hidden rounded-[24px] border border-[var(--color-border)] bg-white/78 p-4";

const BUBBLE_WEIGHT_EXPONENT = 1.6;
const BUBBLE_MIN_WEIGHT_RATIO = 0.1;
const BUBBLE_MIN_LABEL_FONT_SIZE = 10;
const BUBBLE_MAX_LABEL_FONT_SIZE = 17;

type ChartRendererProps = {
  item: BatchScoreAnalyticsItem;
  href?: string;
};

type PackedBubbleNode = Partial<BatchScoreSegment> & {
  children?: PackedBubbleNode[];
  colorIndex?: number;
  weight?: number;
};

function bandColorByIndex(index: number) {
  return BAND_BACKGROUNDS[Math.max(0, Math.min(index, BAND_BACKGROUNDS.length - 1))];
}

function strokeColorByIndex(index: number) {
  return BAND_STROKES[Math.max(0, Math.min(index, BAND_STROKES.length - 1))];
}

function chartEmptyState(message: string) {
  return (
    <div className="flex h-full items-center justify-center rounded-[24px] border border-dashed border-[var(--color-border)] bg-white/70 px-6 text-center text-sm leading-6 text-[var(--color-muted)]">
      {message}
    </div>
  );
}

function normalizeMax(values: number[]) {
  return Math.max(...values, 1);
}

function buildPackedBubbles(points: BatchScoreSegment[]) {
  const width = 320;
  const height = 190;
  const weightedPoints = points.map((point) => ({
    ...point,
    weight: point.count ** BUBBLE_WEIGHT_EXPONENT,
  }));
  const minWeight = normalizeMax(weightedPoints.map((point) => point.weight)) * BUBBLE_MIN_WEIGHT_RATIO;
  const root = hierarchy<PackedBubbleNode>({
    children: weightedPoints.map((point, index) => ({
      ...point,
      colorIndex: index,
      weight: Math.max(point.weight, minWeight),
    })),
  })
    .sum((node) => node.weight ?? 0)
    .sort((left, right) => (right.value ?? 0) - (left.value ?? 0));

  const packedRoot = pack<PackedBubbleNode>()
    .size([width, height])
    .padding(8)(root);

  return packedRoot.leaves().map((leaf) => ({
    label: leaf.data.label ?? "",
    value: leaf.data.value ?? 0,
    count: leaf.data.count ?? 0,
    ratio: leaf.data.ratio ?? 0,
    colorIndex: leaf.data.colorIndex ?? 0,
    x: leaf.x,
    y: leaf.y,
    r: leaf.r,
  }));
}

function bubbleLabelFontSize(label: string, radius: number) {
  const readableSize = Math.max(
    BUBBLE_MIN_LABEL_FONT_SIZE,
    Math.min(BUBBLE_MAX_LABEL_FONT_SIZE, radius * 0.54),
  );
  const maxTextWidth = radius * 1.48;
  const estimatedTextWidth = label.length * readableSize * 0.58;

  if (estimatedTextWidth <= maxTextWidth) {
    return readableSize;
  }

  return Math.max(8, Math.min(readableSize, maxTextWidth / (label.length * 0.58)));
}

function polarToCartesian(cx: number, cy: number, radius: number, angle: number) {
  const radians = ((angle - 90) * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(radians),
    y: cy + radius * Math.sin(radians),
  };
}

function describeDonutArc(
  cx: number,
  cy: number,
  radius: number,
  startAngle: number,
  endAngle: number,
) {
  const start = polarToCartesian(cx, cy, radius, endAngle);
  const end = polarToCartesian(cx, cy, radius, startAngle);
  const largeArcFlag = endAngle - startAngle > 180 ? 1 : 0;
  return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArcFlag} 0 ${end.x} ${end.y}`;
}

function describePieSlice(
  cx: number,
  cy: number,
  radius: number,
  startAngle: number,
  endAngle: number,
) {
  if (endAngle - startAngle >= 360) {
    return `M ${cx} ${cy} m -${radius} 0 a ${radius} ${radius} 0 1 0 ${radius * 2} 0 a ${radius} ${radius} 0 1 0 -${radius * 2} 0`;
  }

  const start = polarToCartesian(cx, cy, radius, startAngle);
  const end = polarToCartesian(cx, cy, radius, endAngle);
  const largeArcFlag = endAngle - startAngle > 180 ? 1 : 0;
  return `M ${cx} ${cy} L ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${end.x} ${end.y} Z`;
}

function HistogramChart({ bins }: { bins: BatchScoreBin[] }) {
  if (!bins.length || bins.every((item) => item.count === 0)) {
    return chartEmptyState("No hay datos disponibles para representar.");
  }

  const maxCount = normalizeMax(bins.map((item) => item.count));
  const histogramColumns = `repeat(${bins.length}, minmax(0, 1fr))`;
  return (
    <div className={CHART_SURFACE_CLASS}>
      <div className="grid h-full min-h-0 grid-rows-[1fr_auto]">
        <div
          className="grid h-full min-h-0 items-end gap-2"
          style={{ gridTemplateColumns: histogramColumns }}
        >
          {bins.map((item, index) => (
            <div key={`${item.label}-bar`} className="flex h-full min-h-0 items-end">
              <div
                className="relative flex h-full w-full items-end overflow-hidden rounded-[18px]"
                style={{ backgroundColor: "var(--color-panel-strong)" }}
              >
                <div
                  className="w-full rounded-[18px] shadow-[0_12px_24px_rgba(16,34,49,0.08)]"
                  style={{
                    height: `${Math.max((item.count / maxCount) * 100, 6)}%`,
                    background: `linear-gradient(180deg, ${strokeColorByIndex(index)}, ${bandColorByIndex(index)})`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>

        <div
          className="mt-3 grid gap-2"
          style={{ gridTemplateColumns: histogramColumns }}
        >
        {bins.map((item) => (
          <div key={`${item.label}-label`} className="space-y-1 text-center">
            <div className="space-y-1 text-center">
              <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--color-muted)]">
                {item.label}
              </p>
              <p className="text-xs font-medium text-[var(--color-text)]">{item.count}</p>
            </div>
          </div>
        ))}
        </div>
      </div>
    </div>
  );
}

function BandBarChart({ bins }: { bins: BatchScoreBin[] }) {
  if (!bins.length || bins.every((item) => item.count === 0)) {
    return chartEmptyState("No hay datos disponibles para representar.");
  }

  const maxCount = normalizeMax(bins.map((item) => item.count));
  return (
    <div className={CHART_SURFACE_CLASS}>
      <div className="flex h-full flex-col gap-3">
      {bins.map((item, index) => (
        <div key={item.label} className="space-y-2">
          <div className="flex items-center justify-between gap-3 text-[11px] font-semibold uppercase tracking-[0.1em] text-[var(--color-muted)]">
            <span>{item.label}</span>
            <span className="font-mono">{item.count}</span>
          </div>
          <div
            className="h-4 rounded-full"
            style={{ backgroundColor: "var(--color-panel-strong)" }}
          >
            <div
              className="h-4 rounded-full border"
              style={{
                width: `${Math.max((item.count / maxCount) * 100, 6)}%`,
                borderColor: strokeColorByIndex(index),
                backgroundColor: strokeColorByIndex(index),
                backgroundImage:
                  "linear-gradient(90deg, rgba(255,255,255,0.42), rgba(255,255,255,0.08) 42%, rgba(255,255,255,0))",
              }}
            />
          </div>
        </div>
      ))}
      </div>
    </div>
  );
}

function PyramidChart({ bins }: { bins: BatchScoreBin[] }) {
  if (!bins.length || bins.every((item) => item.count === 0)) {
    return chartEmptyState("No hay datos disponibles para representar.");
  }

  const maxCount = normalizeMax(bins.map((item) => item.count));
  const orderedBins = [...bins].sort((left, right) => right.count - left.count);

  return (
    <div className={CHART_SURFACE_CLASS}>
      <div className="flex h-full flex-col justify-center gap-3">
        {orderedBins.map((item, index) => {
          const width = Math.max((item.count / maxCount) * 92, 18);
          return (
            <div key={item.label} className="grid grid-cols-[62px_minmax(0,1fr)_42px] items-center gap-2">
              <span className="text-right text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-muted)]">
                {item.label}
              </span>
              <div className="flex justify-center">
                <div
                  className="h-7 rounded-full border shadow-[0_10px_18px_rgba(16,34,49,0.08)]"
                  style={{
                    width: `${width}%`,
                    borderColor: strokeColorByIndex(index),
                    background: `linear-gradient(90deg, ${bandColorByIndex(index)}, ${strokeColorByIndex(index)})`,
                  }}
                />
              </div>
              <span className="font-mono text-xs font-semibold text-[var(--color-text)]">{item.count}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function BoxPlotChart({
  bins,
  stats,
}: {
  bins: BatchScoreBin[];
  stats: BatchScoreStats | null;
}) {
  if (!bins.length || bins.every((item) => item.count === 0)) {
    return chartEmptyState("No hay datos disponibles para representar.");
  }

  const maxCount = normalizeMax(bins.map((item) => item.count));
  const min = stats?.min ?? bins[0]?.start ?? 0;
  const max = stats?.max ?? bins[bins.length - 1]?.end ?? 1;
  const range = Math.max(max - min, 1);
  const position = (value: number) => `${Math.max(0, Math.min(100, ((value - min) / range) * 100))}%`;
  const q1 = stats?.q1 ?? min + range * 0.25;
  const median = stats?.median ?? min + range * 0.5;
  const q3 = stats?.q3 ?? min + range * 0.75;

  return (
    <div className={CHART_SURFACE_CLASS}>
      <div className="grid h-full grid-rows-[92px_minmax(0,1fr)] gap-5">
        <div className="rounded-[22px] border border-[var(--color-border)] bg-white/82 p-4">
          <div className="relative mt-7 h-6 rounded-full bg-[var(--color-panel-strong)]">
            <div
              className="absolute top-1/2 h-1 -translate-y-1/2 rounded-full bg-[var(--color-border-strong)]"
              style={{ left: position(min), right: `calc(100% - ${position(max)})` }}
            />
            <div
              className="absolute top-1/2 h-10 -translate-y-1/2 rounded-[14px] border-2 bg-[var(--chart-risk-2)]"
              style={{
                left: position(q1),
                width: `calc(${position(q3)} - ${position(q1)})`,
                borderColor: "var(--chart-risk-2-strong)",
              }}
            />
            {[min, median, max].map((value, index) => (
              <span
                key={`${value}-${index}`}
                className="absolute top-1/2 h-12 w-1 -translate-y-1/2 rounded-full bg-[var(--color-text)]"
                style={{ left: position(value) }}
              />
            ))}
          </div>
          <div className="mt-7 flex justify-between text-[11px] font-semibold text-[var(--color-muted)]">
            <span>min {formatNumber(min, 0)}</span>
            <span>mediana {formatNumber(median, 0)}</span>
            <span>max {formatNumber(max, 0)}</span>
          </div>
        </div>

        <div className="grid min-h-0 grid-cols-5 items-end gap-2">
          {bins.map((item, index) => (
            <div key={item.label} className="flex h-full min-h-0 flex-col justify-end gap-2">
              <div className="flex min-h-0 flex-1 items-end rounded-[14px] bg-white/62 p-1">
                <div
                  className="w-full rounded-[12px]"
                  style={{
                    height: `${Math.max((item.count / maxCount) * 100, 8)}%`,
                    backgroundColor: strokeColorByIndex(index),
                  }}
                />
              </div>
              <span className="text-center text-[10px] font-semibold text-[var(--color-muted)]">{item.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function DonutChart({
  segments,
  stats,
}: {
  segments: BatchScoreSegment[];
  stats: BatchScoreStats | null;
}) {
  if (!segments.length || segments.every((item) => item.count === 0)) {
    return chartEmptyState("No hay datos disponibles para representar.");
  }

  const donutSegments = segments.map((item, index) => {
    const startAngle =
      segments.slice(0, index).reduce((sum, current) => sum + current.ratio, 0) * 360;
    const angleSpan = item.ratio * 360;
    return {
      ...item,
      startAngle,
      path: describeDonutArc(110, 110, 68, startAngle, startAngle + angleSpan),
    };
  });

  return (
    <div className={CHART_SURFACE_CLASS}>
      <div className="grid h-full grid-cols-[minmax(0,1fr)_100px] gap-3">
      <div className="flex items-center justify-center rounded-[22px] bg-[linear-gradient(180deg,rgba(255,255,255,0.9),rgba(233,238,243,0.7))]">
        <svg aria-hidden="true" className="h-full w-full" viewBox="0 0 160 160">
          <circle
            cx="80"
            cy="80"
            r="42"
            fill="none"
            stroke="rgba(16,34,49,0.08)"
            strokeWidth="16"
          />
          {donutSegments.map((item, index) => (
            <path
              key={`${item.label}-${item.startAngle}`}
              d={describeDonutArc(80, 80, 42, item.startAngle, item.startAngle + item.ratio * 360)}
              fill="none"
              stroke={strokeColorByIndex(index)}
              strokeLinecap="butt"
              strokeWidth="16"
            />
          ))}
          <circle cx="80" cy="80" r="26" fill="white" />
          <text
            x="80"
            y="74"
            fill="var(--color-muted)"
            fontSize="8"
            fontWeight="700"
            letterSpacing="1.2"
            textAnchor="middle"
          >
            MEDIA
          </text>
          <text
            x="80"
            y="93"
            fill="var(--color-text)"
            fontSize="12"
            fontWeight="700"
            textAnchor="middle"
          >
            {formatNumber(stats?.mean ?? null, 2)}
          </text>
        </svg>
      </div>

      <div className="space-y-2">
        {segments.slice(0, 4).map((item, index) => (
          <div
            key={`${item.label}-${item.value}`}
            className="rounded-[16px] border border-[var(--color-border)] bg-white/86 px-2.5 py-2"
          >
            <div className="flex items-center gap-2">
              <span
                className="h-3 w-3 rounded-full"
                style={{ backgroundColor: strokeColorByIndex(index) }}
              />
              <span className="text-[11px] font-semibold text-[var(--color-text)]">{item.label}</span>
            </div>
            <p className="mt-1 text-[11px] text-[var(--color-muted)]">{item.count} correos</p>
          </div>
        ))}
      </div>
      </div>
    </div>
  );
}

function PieChart({ segments }: { segments: BatchScoreSegment[] }) {
  if (!segments.length || segments.every((item) => item.count === 0)) {
    return chartEmptyState("No hay datos disponibles para representar.");
  }

  const pieSegments = segments.map((item, index) => {
    const startAngle =
      segments.slice(0, index).reduce((sum, current) => sum + current.ratio, 0) * 360;
    const angleSpan = item.ratio * 360;
    return {
      ...item,
      startAngle,
      angleSpan,
    };
  });

  return (
    <div className={CHART_SURFACE_CLASS}>
      <div className="grid h-full grid-cols-[minmax(0,1fr)_132px] gap-4">
        <div className="flex items-center justify-center rounded-[22px] bg-[radial-gradient(circle_at_30%_20%,rgba(255,255,255,0.96),rgba(240,244,248,0.84)_58%,rgba(228,234,240,0.92)_100%)]">
          <svg aria-hidden="true" className="h-full w-full" viewBox="0 0 160 160">
            <defs>
              <filter id="pie-shadow" x="-30%" y="-30%" width="160%" height="160%">
                <feDropShadow dx="0" dy="8" stdDeviation="10" floodColor="rgba(16,34,49,0.14)" />
              </filter>
              <radialGradient id="pie-gloss" cx="32%" cy="26%" r="62%">
                <stop offset="0%" stopColor="rgba(255,255,255,0.52)" />
                <stop offset="55%" stopColor="rgba(255,255,255,0.10)" />
                <stop offset="100%" stopColor="rgba(255,255,255,0)" />
              </radialGradient>
            </defs>

            <circle
              cx="80"
              cy="80"
              r="54"
              fill="rgba(255,255,255,0.82)"
              stroke="rgba(16,34,49,0.06)"
              strokeWidth="1.5"
            />

            <g filter="url(#pie-shadow)">
            {pieSegments.map((item, index) => (
              <path
                key={`${item.label}-${item.startAngle}`}
                d={describePieSlice(80, 80, 52, item.startAngle, item.startAngle + item.angleSpan)}
                fill={strokeColorByIndex(index)}
                stroke="rgba(255,255,255,0.95)"
                strokeWidth="1"
                strokeLinejoin="round"
              />
            ))}
            </g>

            <circle cx="80" cy="80" r="52" fill="url(#pie-gloss)" />
          </svg>
        </div>

        <div className="space-y-2">
          {segments.slice(0, 4).map((item, index) => (
            <div
              key={`${item.label}-${item.value}`}
              className="rounded-[16px] border border-[var(--color-border)] bg-white/86 px-3 py-2.5"
            >
              <div className="flex items-start gap-2">
                <span
                  className="mt-0.5 h-3 w-3 shrink-0 rounded-full"
                  style={{ backgroundColor: strokeColorByIndex(index) }}
                />
                <span className="min-w-0 text-[11px] font-semibold leading-5 text-[var(--color-text)]">
                  {item.label}
                </span>
              </div>
              <p className="mt-1 text-[11px] text-[var(--color-muted)]">{item.count} correos</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function BubbleLaneChart({
  points,
}: {
  points: BatchScoreSegment[];
}) {
  if (!points.length || points.every((item) => item.count === 0)) {
    return chartEmptyState("No hay datos disponibles para representar.");
  }

  const packed = buildPackedBubbles(points);

  return (
    <div className={CHART_SURFACE_CLASS}>
      <div className="flex h-full items-center">
      <svg aria-hidden="true" className="h-full w-full" viewBox="0 0 360 220">
        {packed.map((item) => {
          const label = item.label;
          const fontSize = bubbleLabelFontSize(label, item.r);
          return (
            <g key={`${item.label}-${item.value}`}>
              <circle
                cx={item.x + 20}
                cy={item.y + 16}
                fill={bandColorByIndex(item.colorIndex)}
                r={item.r}
                stroke={strokeColorByIndex(item.colorIndex)}
                strokeWidth="3"
              />
              <text
                x={item.x + 20}
                y={item.y + 16}
                alignmentBaseline="central"
                fill="var(--color-text)"
                fontSize={fontSize}
                fontWeight="700"
                textAnchor="middle"
                dominantBaseline="central"
              >
                {label}
              </text>
            </g>
          );
        })}
      </svg>
      </div>
    </div>
  );
}

function StackedBarChart({ segments }: { segments: BatchScoreSegment[] }) {
  if (!segments.length || segments.every((item) => item.count === 0)) {
    return chartEmptyState("No hay datos disponibles para representar.");
  }

  return (
    <div className={CHART_SURFACE_CLASS}>
      <div className="flex h-full flex-col">
      <div
        className="flex h-8 overflow-hidden rounded-full border border-[var(--color-border)]"
        style={{ backgroundColor: "var(--color-panel-strong)" }}
      >
        {segments.map((item, index) => (
          <div
            key={`${item.label}-${item.value}`}
            style={{
              width: `${Math.max(item.ratio * 100, 6)}%`,
              backgroundColor: strokeColorByIndex(index),
            }}
          />
        ))}
      </div>

      <div className="mt-4 grid flex-1 grid-cols-1 gap-2">
        {segments.map((item, index) => (
          <div
            key={`${item.label}-${item.count}`}
            className="flex items-center justify-between rounded-[16px] border border-[var(--color-border)] bg-white/86 px-3 py-2 text-xs"
          >
            <div className="flex items-center gap-2">
              <span
                className="h-3 w-3 rounded-full"
                style={{ backgroundColor: strokeColorByIndex(index) }}
              />
              <span className="font-semibold text-[var(--color-text)]">{item.label}</span>
            </div>
            <span className="font-mono text-[var(--color-muted)]">{item.count}</span>
          </div>
        ))}
      </div>
      </div>
    </div>
  );
}

function allocateWaffleCells(segments: BatchScoreSegment[], cellCount: number) {
  const provisional = segments.map((segment) => {
    const exact = segment.ratio * cellCount;
    const floorValue = Math.floor(exact);
    return {
      segment,
      floorValue,
      remainder: exact - floorValue,
    };
  });

  let assigned = provisional.reduce((sum, item) => sum + item.floorValue, 0);
  const ordered = [...provisional].sort((a, b) => b.remainder - a.remainder);
  let index = 0;
  while (assigned < cellCount && ordered.length > 0) {
    ordered[index % ordered.length].floorValue += 1;
    assigned += 1;
    index += 1;
  }

  const cells: Array<BatchScoreSegment & { colorIndex: number }> = [];
  provisional.forEach((item, colorIndex) => {
    for (let count = 0; count < item.floorValue; count += 1) {
      cells.push({ ...item.segment, colorIndex });
    }
  });
  return cells.slice(0, cellCount);
}

function WaffleChart({ segments }: { segments: BatchScoreSegment[] }) {
  if (!segments.length || segments.every((item) => item.count === 0)) {
    return chartEmptyState("No hay datos disponibles para representar.");
  }

  const cells = allocateWaffleCells(segments, 28);
  return (
    <div className={CHART_SURFACE_CLASS}>
      <div className="grid h-full grid-cols-[156px_minmax(0,1fr)] gap-4">
      <div className="grid h-full w-[156px] grid-cols-4 gap-2 rounded-[20px] bg-white/76 p-3">
        {cells.map((segment, index) => (
          <div
            key={`${segment.label}-${index}`}
            className="aspect-square rounded-[10px] border border-white/80"
            style={{ backgroundColor: strokeColorByIndex(segment.colorIndex) }}
          />
        ))}
      </div>
      <div className="space-y-3">
        {segments.slice(0, 4).map((item, index) => (
          <div
            key={`${item.label}-${item.value}`}
            className="rounded-[18px] border border-[var(--color-border)] bg-white/86 px-3 py-2"
          >
            <div className="flex items-center gap-2">
              <span
                className="h-3 w-3 rounded-full"
                style={{ backgroundColor: strokeColorByIndex(index) }}
              />
              <span className="text-xs font-semibold text-[var(--color-text)]">{item.label}</span>
            </div>
            <p className="mt-1 text-xs text-[var(--color-muted)]">{item.count} correos</p>
          </div>
        ))}
      </div>
      </div>
    </div>
  );
}

function renderChart(item: BatchScoreAnalyticsItem) {
  switch (item.chart_type) {
    case "histogram":
      return <HistogramChart bins={item.bins} />;
    case "donut":
      return <DonutChart segments={item.segments} stats={item.value_stats} />;
    case "pie":
      return <PieChart segments={item.segments} />;
    case "bubble_lane":
      return <BubbleLaneChart points={item.points} />;
    case "pyramid":
      return <PyramidChart bins={item.bins} />;
    case "stacked_bar":
      return <StackedBarChart segments={item.segments} />;
    case "box_plot":
      return <BoxPlotChart bins={item.bins} stats={item.value_stats} />;
    case "waffle":
      return <WaffleChart segments={item.segments} />;
    case "band_bars":
      return <BandBarChart bins={item.bins} />;
    default:
      return <HistogramChart bins={item.bins} />;
  }
}

export function ScoreChartCard({ href, item }: ChartRendererProps) {
  const card = (
    <article className="grid h-[470px] grid-rows-[58px_minmax(0,1fr)] gap-4 overflow-hidden rounded-[30px] border border-[var(--color-border)] bg-white/72 p-4 shadow-[0_18px_40px_rgba(16,34,49,0.08)]">
      <div className="flex h-[58px] items-start justify-between gap-3">
        <p className="max-w-[80%] text-base font-semibold leading-6 tracking-[-0.02em]">
          {item.subcriterion.label}
        </p>
        <span className="rounded-full border border-[var(--color-border)] bg-white/90 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--color-muted)]">
          {item.emails_with_value}/{item.emails_total}
        </span>
      </div>

      <div className="min-h-0">{renderChart(item)}</div>
    </article>
  );

  if (!href) {
    return card;
  }

  return (
    <Link
      className="block rounded-[30px] transition hover:-translate-y-0.5 hover:shadow-[0_18px_40px_rgba(16,34,49,0.12)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-2"
      href={href}
    >
      {card}
    </Link>
  );
}
