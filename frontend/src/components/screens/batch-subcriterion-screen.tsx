"use client";

import Link from "next/link";
import { fetchBatchSubcriterion } from "@/lib/api";
import type { BatchSubcriterionAnalytics } from "@/lib/types";
import { usePollingQuery } from "@/hooks/use-polling-query";
import { Card } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingState } from "@/components/ui/loading-state";
import { SectionHeading } from "@/components/ui/section-heading";
import { SimpleBarChart } from "@/components/ui/simple-bar-chart";

type BatchSubcriterionScreenProps = {
  batchId: string;
  subcriterionKey: string;
};

export function BatchSubcriterionScreen({
  batchId,
  subcriterionKey,
}: BatchSubcriterionScreenProps) {
  const { data, error, loading, refresh } = usePollingQuery<BatchSubcriterionAnalytics>(
    () => fetchBatchSubcriterion(batchId, subcriterionKey),
    `${batchId}:${subcriterionKey}`,
    60000,
    true,
    { shouldPoll: () => false },
  );

  if (loading && !data) {
    return <LoadingState label="Cargando analitica del lote..." />;
  }

  if (error && !data) {
    return <ErrorState message={error} />;
  }

  if (!data) {
    return <ErrorState message="No se ha podido cargar la analitica." />;
  }

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Analitica"
        title={data.subcriterion.label}
        description={`Lote: ${data.batch_name}`}
        actions={
          <div className="flex flex-wrap gap-2">
            <button className="nav-link" onClick={() => void refresh()} type="button">
              Refrescar
            </button>
            <Link className="nav-link" href={`/lotes/${batchId}`}>
              Volver al lote
            </Link>
          </div>
        }
      />

      {error && <ErrorState message={error} />}

      <div className="grid gap-6">
        {data.series.map((serie) => (
          <Card
            key={serie.metric_key}
            title={serie.metric_label}
            subtitle={`${serie.emails_with_value}/${serie.emails_total} correos con valor`}
          >
            <div className="mb-4 grid gap-3 md:grid-cols-3">
              <div className="rounded-2xl border border-[var(--color-border)] bg-white/80 px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]">
                  Campo del vector
                </p>
                <p className="mt-2 font-mono text-sm">{serie.metric_key}</p>
              </div>
              <div className="rounded-2xl border border-[var(--color-border)] bg-white/80 px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]">
                  Con valor
                </p>
                <p className="mt-2 text-2xl font-semibold">
                  {serie.emails_with_value}
                </p>
              </div>
              <div className="rounded-2xl border border-[var(--color-border)] bg-white/80 px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]">
                  Sin valor
                </p>
                <p className="mt-2 text-2xl font-semibold">
                  {serie.emails_without_value}
                </p>
              </div>
            </div>
            <SimpleBarChart data={serie.distribution} />
          </Card>
        ))}
      </div>
    </div>
  );
}
