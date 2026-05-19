export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Sin fecha";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("es-ES", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
}

export function formatNumber(
  value: number | null | undefined,
  digits = 3,
): string {
  if (value === null || value === undefined) {
    return "Sin valor";
  }

  if (Number.isInteger(value)) {
    return String(value);
  }

  return value.toFixed(digits);
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "Sin score";
  }

  return `${(value * 100).toFixed(2)}%`;
}

export function formatSubcriterionValue(
  subcriterionKey: string,
  value: number | null | undefined,
): string {
  return formatNumber(value);
}
