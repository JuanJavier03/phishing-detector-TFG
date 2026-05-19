"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import {
  analyzeMissingBatchSubcriteria,
  deleteBatch,
  downloadBatchMcdmExport,
  fetchBatch,
  fetchBatchCharts,
  recalculateBatchMcdm,
  retryCancelledBatch,
  retryEmail,
} from "@/lib/api";
import { formatDate, formatPercent } from "@/lib/format";
import type { BatchChartsOverview, BatchDetail } from "@/lib/types";
import { usePollingQuery } from "@/hooks/use-polling-query";
import { hasActiveBatch } from "@/lib/polling";
import { Card } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingState } from "@/components/ui/loading-state";
import { PaginationControls } from "@/components/ui/pagination-controls";
import { ScoreChartCard } from "@/components/ui/score-chart-card";
import { SectionHeading } from "@/components/ui/section-heading";
import { StatusBadge } from "@/components/ui/status-badge";

type BatchDetailScreenProps = {
  batchId: string;
};

type BatchDetailView = "emails" | "charts";

const PAGE_SIZE = 20;

function familyTitle(family: string) {
  return family === "criterio1" ? "Subcriterios de cabecera" : "Subcriterios de cuerpo";
}

export function BatchDetailScreen({ batchId }: BatchDetailScreenProps) {
  const router = useRouter();
  const [activeView, setActiveView] = useState<BatchDetailView>("emails");
  const [emailsPage, setEmailsPage] = useState(0);
  const { data, error, loading, refresh } = usePollingQuery<BatchDetail>(
    () => fetchBatch(batchId, PAGE_SIZE + 1, emailsPage * PAGE_SIZE),
    `${batchId}:emails:${emailsPage}`,
    10000,
    true,
    { shouldPoll: hasActiveBatch },
  );
  const chartsQuery = usePollingQuery<BatchChartsOverview>(
    () => fetchBatchCharts(batchId),
    `batch-charts-${batchId}`,
    4000,
    activeView === "charts",
    {
      shouldPoll: () => hasActiveBatch(data),
      pollKey: hasActiveBatch(data) ? "active" : "idle",
    },
  );
  const [actionError, setActionError] = useState<string | null>(null);
  const [pendingAnalyzeMissing, setPendingAnalyzeMissing] = useState(false);
  const [recalculatingMcdm, setRecalculatingMcdm] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [retryingCancelledBatch, setRetryingCancelledBatch] = useState(false);
  const [retryingEmailId, setRetryingEmailId] = useState<string | null>(null);

  if (loading && !data) {
    return <LoadingState label="Cargando detalle del lote..." />;
  }

  if (error && !data) {
    return <ErrorState message={error} />;
  }

  if (!data) {
    return <ErrorState message="No se ha podido cargar el lote." />;
  }

  const batch = data;
  const missingCount = batch.missing_subcriteria.length;
  const hasActiveJob = hasActiveBatch(batch);
  const headerCharts = (chartsQuery.data?.items ?? []).filter(
    (item) => item.subcriterion.family === "criterio1",
  );
  const bodyCharts = (chartsQuery.data?.items ?? []).filter(
    (item) => item.subcriterion.family === "criterio2",
  );
  const visibleEmails = batch.emails.slice(0, PAGE_SIZE);
  const hasNextEmailsPage = batch.emails.length > PAGE_SIZE;

  async function handleRefreshView() {
    await refresh();
    if (activeView === "charts") {
      await chartsQuery.refresh();
    }
  }

  async function handleAnalyzeMissing() {
    setPendingAnalyzeMissing(true);
    setActionError(null);
    try {
      await analyzeMissingBatchSubcriteria(batchId);
      await handleRefreshView();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "No se pudieron lanzar los subcriterios pendientes.");
    } finally {
      setPendingAnalyzeMissing(false);
    }
  }

  async function handleDelete() {
    const confirmed = window.confirm(`Se eliminara el lote "${batch.name}" y todos sus correos.`);
    if (!confirmed) {
      return;
    }

    setActionError(null);
    setDeleting(true);
    try {
      await deleteBatch(batch.id);
      router.push("/lotes");
      router.refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "No se pudo eliminar el lote.");
    } finally {
      setDeleting(false);
    }
  }

  async function handleExport() {
    setActionError(null);
    setExporting(true);
    try {
      await downloadBatchMcdmExport(batchId);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "No se pudo exportar el Excel.");
    } finally {
      setExporting(false);
    }
  }

  async function handleRecalculateMcdm() {
    setActionError(null);
    setRecalculatingMcdm(true);
    try {
      await recalculateBatchMcdm(batchId);
      await handleRefreshView();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "No se pudo recalcular el MCDM.");
    } finally {
      setRecalculatingMcdm(false);
    }
  }

  async function handleRetryCancelledBatch() {
    setActionError(null);
    setRetryingCancelledBatch(true);
    try {
      await retryCancelledBatch(batchId);
      await handleRefreshView();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "No se pudieron reintentar los correos cancelados.");
    } finally {
      setRetryingCancelledBatch(false);
    }
  }

  async function handleRetryEmail(emailId: string) {
    setActionError(null);
    setRetryingEmailId(emailId);
    try {
      await retryEmail(emailId);
      await handleRefreshView();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "No se pudo reintentar el correo.");
    } finally {
      setRetryingEmailId(null);
    }
  }

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Lote"
        title={batch.name}
        description={`Creado el ${formatDate(batch.created_at)}`}
        actions={
          <div className="flex flex-wrap gap-2">
            <button className="nav-link" onClick={() => void handleRefreshView()} type="button">
              Refrescar
            </button>
            <button
              className="nav-link"
              disabled={recalculatingMcdm || hasActiveJob}
              onClick={() => void handleRecalculateMcdm()}
              type="button"
            >
              {recalculatingMcdm ? "Recalculando..." : "Recalcular MCDM global"}
            </button>
            <button
              className="nav-link"
              disabled={exporting || hasActiveJob}
              onClick={() => void handleExport()}
              type="button"
            >
              {exporting ? "Exportando..." : "Exportar Excel MCDM"}
            </button>
            <Link className="nav-link" href="/lotes">
              Volver a lotes
            </Link>
            <button
              className="rounded-full border border-[var(--color-danger)] bg-white px-4 py-2 text-sm font-medium text-[var(--color-danger)] transition hover:bg-[var(--color-danger-soft)] disabled:cursor-not-allowed disabled:opacity-50"
              disabled={deleting}
              onClick={() => void handleDelete()}
              type="button"
            >
              {deleting ? "Eliminando..." : "Eliminar lote"}
            </button>
          </div>
        }
      />

      {(error || actionError) && <ErrorState message={actionError ?? error ?? ""} />}

      <Card>
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-accent)]">
              Vista activa
            </p>
            <h3 className="text-2xl font-semibold tracking-[-0.03em]">
              {activeView === "emails" ? "Correos del lote" : "Graficas del lote"}
            </h3>
            <p className="max-w-2xl text-sm leading-6 text-[var(--color-muted)]">
              {activeView === "emails"
                ? "Consulta el estado general del lote y revisa cada correo individual."
                : "Visualiza todas las graficas del lote usando valores reales y labels semanticas, separadas entre cabecera y cuerpo."}
            </p>
          </div>

          <div className="inline-flex w-full rounded-[24px] border border-[var(--color-border)] bg-white/70 p-1 shadow-[0_18px_32px_rgba(16,34,49,0.08)] sm:w-auto">
            <button
              className={`flex-1 rounded-[18px] px-4 py-3 text-sm font-semibold transition sm:flex-none ${
                activeView === "emails"
                  ? "bg-[var(--color-text)] text-white shadow-[0_16px_30px_rgba(16,34,49,0.18)]"
                  : "text-[var(--color-muted)] hover:bg-white hover:text-[var(--color-text)]"
              }`}
              onClick={() => setActiveView("emails")}
              type="button"
            >
              Vista de correos
            </button>
            <button
              className={`flex-1 rounded-[18px] px-4 py-3 text-sm font-semibold transition sm:flex-none ${
                activeView === "charts"
                  ? "bg-[var(--color-text)] text-white shadow-[0_16px_30px_rgba(16,34,49,0.18)]"
                  : "text-[var(--color-muted)] hover:bg-white hover:text-[var(--color-text)]"
              }`}
              onClick={() => setActiveView("charts")}
              type="button"
            >
              Vista de graficas
            </button>
          </div>
        </div>
      </Card>

      {activeView === "emails" ? (
        <div className="space-y-6">
          <Card title="Resumen del lote">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-[24px] border border-[var(--color-border)] bg-[var(--color-accent-soft)] p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]">
                  Estado
                </p>
                <div className="mt-3">
                  <StatusBadge status={batch.status} />
                </div>
              </div>
              <div className="rounded-[24px] border border-[var(--color-border)] bg-white/80 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]">
                  Total correos
                </p>
                <p className="mt-3 text-3xl font-semibold">{batch.total_emails}</p>
                <p className="mt-1 text-xs text-[var(--color-muted)]">
                  Procesables: {batch.processable_emails}
                </p>
              </div>
              <div className="rounded-[24px] border border-[var(--color-border)] bg-white/80 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]">
                  Completados
                </p>
                <p className="mt-3 text-3xl font-semibold">
                  {batch.completed_emails}
                </p>
                <p className="mt-1 text-xs text-[var(--color-danger)]">
                  Cancelados: {batch.discarded_emails}
                </p>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <p className="text-sm text-[var(--color-muted)]">
                Subcriterios pendientes en el lote: {missingCount}
              </p>
              <button
                className="nav-link"
                disabled={!missingCount || pendingAnalyzeMissing || hasActiveJob}
                onClick={() => void handleAnalyzeMissing()}
                type="button"
              >
                {pendingAnalyzeMissing
                  ? "Lanzando..."
                  : "Analizar resto de subcriterios"}
              </button>
              <button
                className="nav-link"
                disabled={!batch.discarded_emails || retryingCancelledBatch || hasActiveJob}
                onClick={() => void handleRetryCancelledBatch()}
                type="button"
              >
                {retryingCancelledBatch
                  ? "Reintentando cancelados..."
                  : "Reintentar cancelados"}
              </button>
            </div>
          </Card>

          <Card title="Correos del lote">
            <div className="space-y-3">
              {visibleEmails.map((email) => (
                <div
                  key={email.id}
                  className="flex flex-col gap-3 rounded-2xl border border-[var(--color-border)] bg-white/70 px-4 py-4 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div>
                    <p className="font-semibold">{email.name}</p>
                    <p className="text-sm text-[var(--color-muted)]">
                      {email.subject ?? "Sin asunto"}
                    </p>
                    <p className="text-sm text-[var(--color-muted)]">
                      MCDM: {formatPercent(email.mcdm_score)}
                    </p>
                    {email.processing_error?.message && (
                      <p className="text-sm text-[var(--color-danger)]">
                        {email.processing_error.message}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center gap-3">
                    <StatusBadge status={email.status} />
                    {email.status === "cancelled" || email.status === "error" ? (
                      <button
                        className="nav-link"
                        disabled={retryingEmailId === email.id || hasActiveJob}
                        onClick={() => void handleRetryEmail(email.id)}
                        type="button"
                      >
                        {retryingEmailId === email.id ? "Reintentando..." : "Reintentar"}
                      </button>
                    ) : (
                      <Link className="nav-link" href={`/correos/${email.id}`}>
                        Abrir correo
                      </Link>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {!!batch.emails.length && (
            <PaginationControls
              hasNext={hasNextEmailsPage}
              itemCount={visibleEmails.length}
              onPageChange={setEmailsPage}
              page={emailsPage}
              pageSize={PAGE_SIZE}
            />
          )}
        </div>
      ) : (
        <div className="space-y-6">
          {chartsQuery.loading && !chartsQuery.data && (
            <LoadingState label="Cargando graficas del lote..." />
          )}

          {chartsQuery.error && !chartsQuery.data && (
            <ErrorState message={chartsQuery.error} />
          )}

          {!chartsQuery.loading &&
            !chartsQuery.error &&
            !headerCharts.length &&
            !bodyCharts.length && (
              <ErrorState message="Este lote no tiene subcriterios con datos disponibles para representar." />
            )}

          {[headerCharts, bodyCharts].map((group) => {
            if (!group.length || (chartsQuery.loading && !chartsQuery.data)) {
              return null;
            }

            return (
              <Card
                key={group[0].subcriterion.family}
                title={familyTitle(group[0].subcriterion.family)}
                subtitle={`${group.length} visualizaciones en esta seccion.`}
              >
                <div className="grid gap-5 lg:grid-cols-2">
                  {group.map((item) => (
                    <ScoreChartCard
                      href={`/lotes/${batchId}/subcriterios/${item.subcriterion.key}`}
                      item={item}
                      key={item.subcriterion.key}
                    />
                  ))}
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
