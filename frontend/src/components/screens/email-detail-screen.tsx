"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { analyzeEmailSubcriterion, analyzeMissingEmailSubcriteria, deleteEmail, fetchEmail } from "@/lib/api";
import { formatDate, formatPercent, formatSubcriterionValue } from "@/lib/format";
import type { EmailDetail } from "@/lib/types";
import { usePollingQuery } from "@/hooks/use-polling-query";
import { hasActiveEmail } from "@/lib/polling";
import { Card } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { KeyValueGrid } from "@/components/ui/key-value-grid";
import { LoadingState } from "@/components/ui/loading-state";
import { SectionHeading } from "@/components/ui/section-heading";
import { StatusBadge } from "@/components/ui/status-badge";

type EmailDetailScreenProps = {
  emailId: string;
};

function familyTitle(family: string) {
  return family === "criterio1" ? "Subcriterios de cabecera" : "Subcriterios de cuerpo";
}

function formatMcdmMethod(method: string | null, isMock: boolean) {
  if (isMock) {
    return "Calculo temporal";
  }
  if (!method) {
    return "TOPSIS";
  }

  const normalized = method
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
  return normalized;
}

export function EmailDetailScreen({ emailId }: EmailDetailScreenProps) {
  const router = useRouter();
  const { data, error, loading, refresh } = usePollingQuery<EmailDetail>(
    () => fetchEmail(emailId),
    emailId,
    10000,
    true,
    { shouldPoll: hasActiveEmail },
  );
  const [actionError, setActionError] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const blockedStatus = data?.status === "error" || data?.status === "cancelled";

  useEffect(() => {
    if (!data || !blockedStatus) {
      return;
    }
    router.replace(data.batch ? `/lotes/${data.batch.id}` : "/correos");
  }, [blockedStatus, data, router]);

  if (loading && !data) {
    return <LoadingState label="Cargando detalle del correo..." />;
  }

  if (error && !data) {
    return <ErrorState message={error} />;
  }

  if (!data) {
    return <ErrorState message="No se ha podido cargar el correo." />;
  }

  const email = data;

  if (email.status === "error" || email.status === "cancelled") {
    return <LoadingState label="Redirigiendo..." />;
  }

  const headerSubcriteria = email.subcriteria.filter((item) => item.family === "criterio1");
  const bodySubcriteria = email.subcriteria.filter((item) => item.family === "criterio2");
  const missingCount = email.missing_subcriteria.length;
  const hasActiveJob = hasActiveEmail(email);

  async function handleAnalyzeSubcriterion(subcriterionKey: string) {
    setPendingAction(subcriterionKey);
    setActionError(null);
    try {
      await analyzeEmailSubcriterion(emailId, subcriterionKey);
      await refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "No se pudo lanzar el analisis.");
    } finally {
      setPendingAction(null);
    }
  }

  async function handleAnalyzeMissing() {
    setPendingAction("analyze_missing");
    setActionError(null);
    try {
      await analyzeMissingEmailSubcriteria(emailId);
      await refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "No se pudieron lanzar los subcriterios pendientes.");
    } finally {
      setPendingAction(null);
    }
  }

  async function handleDelete() {
    const confirmed = window.confirm(`Se eliminara el correo "${email.name}".`);
    if (!confirmed) {
      return;
    }

    setActionError(null);
    setDeleting(true);
    try {
      await deleteEmail(email.id);
      router.push("/correos");
      router.refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "No se pudo eliminar el correo.");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Correo"
        title={email.name}
        description={email.subject ?? "Sin asunto"}
        actions={
          <div className="flex flex-wrap gap-2">
            <button className="nav-link" onClick={() => void refresh()} type="button">
              Refrescar
            </button>
            <Link className="nav-link" href={`/correos/${emailId}/mcdm`}>
              Ver MCDM
            </Link>
            <Link className="nav-link" href="/correos">
              Volver a correos
            </Link>
            <button
              className="rounded-full border border-[var(--color-danger)] bg-white px-4 py-2 text-sm font-medium text-[var(--color-danger)] transition hover:bg-[var(--color-danger-soft)] disabled:cursor-not-allowed disabled:opacity-50"
              disabled={deleting}
              onClick={() => void handleDelete()}
              type="button"
            >
              {deleting ? "Eliminando..." : "Eliminar correo"}
            </button>
          </div>
        }
      />

      {(error || actionError) && <ErrorState message={actionError ?? error ?? ""} />}

      <Card title="Resumen general">
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-[24px] border border-[var(--color-border)] bg-[var(--color-accent-soft)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]">
              Estado
            </p>
            <div className="mt-3">
              <StatusBadge status={email.status} />
            </div>
          </div>
          <div className="rounded-[24px] border border-[var(--color-border)] bg-white/80 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]">
              MCDM score
            </p>
            <p className="mt-3 text-3xl font-semibold">{formatPercent(email.mcdm_score)}</p>
            <p className="mt-1 text-xs text-[var(--color-muted)]">
              {formatMcdmMethod(email.mcdm_method, email.mcdm_is_mock)}
            </p>
          </div>
          <div className="rounded-[24px] border border-[var(--color-border)] bg-white/80 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]">
              Lote
            </p>
            <p className="mt-3 text-base font-semibold">
              {email.batch ? email.batch.name : "Sin lote"}
            </p>
            {email.batch && (
              <Link
                className="mt-2 inline-block text-sm font-medium text-[var(--color-accent)]"
                href={`/lotes/${email.batch.id}`}
              >
                Abrir lote
              </Link>
            )}
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <p className="text-sm text-[var(--color-muted)]">
            Pendientes: {missingCount}
          </p>
          <button
            className="nav-link"
            disabled={!missingCount || pendingAction === "analyze_missing" || hasActiveJob}
            onClick={() => void handleAnalyzeMissing()}
            type="button"
          >
            {pendingAction === "analyze_missing"
              ? "Lanzando..."
              : "Analizar resto de subcriterios"}
          </button>
        </div>
      </Card>

      <div className="space-y-6">
        <Card title="Cabeceras clave">
          <KeyValueGrid
            items={[
              { label: "From", value: email.headers_summary.from ?? "Sin dato" },
              { label: "To", value: email.headers_summary.to ?? "Sin dato" },
              { label: "Date", value: email.headers_summary.date ?? "Sin dato" },
              {
                label: "Return-Path",
                value: email.headers_summary.return_path ?? "Sin dato",
              },
              {
                label: "Message-ID",
                value: email.headers_summary.message_id ?? "Sin dato",
              },
              { label: "Creado", value: formatDate(email.created_at) },
            ]}
          />
        </Card>

        <Card
          title="Analisis del correo"
          subtitle="Cada subcriterio muestra su estado y su valor numerico en la misma lista."
        >
          <div className="space-y-6">
            {[headerSubcriteria, bodySubcriteria].map((group) => {
              if (!group.length) {
                return null;
              }

              return (
                <div key={group[0].family} className="space-y-3">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-lg font-semibold tracking-[-0.02em]">
                      {familyTitle(group[0].family)}
                    </h3>
                    <span className="text-sm text-[var(--color-muted)]">
                      {group.length} subcriterios
                    </span>
                  </div>

                  {group.map((item) => (
                    <div
                      key={item.key}
                      className="flex flex-col gap-4 rounded-[24px] border border-[var(--color-border)] bg-white/70 px-4 py-4"
                    >
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div className="space-y-1">
                          <p className="font-semibold">{item.label}</p>
                          <p className="text-sm text-[var(--color-muted)]">
                            Campo del vector: <span className="font-mono">{item.vector_field}</span>
                          </p>
                          {item.updated_at && (
                            <p className="text-xs text-[var(--color-muted)]">
                              {`Actualizado: ${formatDate(item.updated_at)}`}
                            </p>
                          )}
                        </div>

                        <div className="flex flex-wrap items-center gap-3">
                          <StatusBadge status={item.status} />
                          {item.has_result ? (
                            <Link
                              className="nav-link"
                              href={`/correos/${email.id}/subcriterios/${item.key}`}
                            >
                              Ver detalle
                            </Link>
                          ) : (
                            <button
                              className="nav-link"
                              disabled={pendingAction === item.key || hasActiveJob}
                              onClick={() => void handleAnalyzeSubcriterion(item.key)}
                              type="button"
                            >
                              {pendingAction === item.key ? "Lanzando..." : "Analizar"}
                            </button>
                          )}
                        </div>
                      </div>

                      <div className="grid gap-3 md:grid-cols-2">
                        <div className="rounded-[20px] border border-[var(--color-border)] bg-[var(--color-panel)] px-4 py-3">
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]">
                            Valor numerico
                          </p>
                          <p className="mt-2 text-2xl font-semibold">
                            {formatSubcriterionValue(item.key, item.value)}
                          </p>
                        </div>
                        <div className="rounded-[20px] border border-[var(--color-border)] bg-[var(--color-panel)] px-4 py-3">
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]">
                            Medicion
                          </p>
                          <p className="mt-2 text-sm leading-6 text-[var(--color-text)]">
                            {item.measurement}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </Card>
      </div>
    </div>
  );
}
