"use client";

import Link from "next/link";
import { useState } from "react";
import { deleteEmail, fetchEmails, retryEmail } from "@/lib/api";
import { formatDate, formatPercent } from "@/lib/format";
import type { EmailSummary } from "@/lib/types";
import { usePollingQuery } from "@/hooks/use-polling-query";
import { hasAnyActiveEmails } from "@/lib/polling";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingState } from "@/components/ui/loading-state";
import { PaginationControls } from "@/components/ui/pagination-controls";
import { SectionHeading } from "@/components/ui/section-heading";
import { StatusBadge } from "@/components/ui/status-badge";

const PAGE_SIZE = 20;

export function EmailsScreen() {
  const [page, setPage] = useState(0);
  const { data, error, loading, refresh } = usePollingQuery<EmailSummary[]>(
    () => fetchEmails(PAGE_SIZE + 1, page * PAGE_SIZE),
    `emails:${page}`,
    10000,
    true,
    { shouldPoll: hasAnyActiveEmails },
  );
  const [actionError, setActionError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const visibleEmails = (data ?? []).slice(0, PAGE_SIZE);
  const hasNextPage = (data?.length ?? 0) > PAGE_SIZE;

  if (loading && !data) {
    return <LoadingState label="Cargando correos..." />;
  }

  async function handleDelete(email: EmailSummary) {
    const confirmed = window.confirm(`Se eliminara el correo "${email.name}".`);
    if (!confirmed) {
      return;
    }

    setActionError(null);
    setDeletingId(email.id);
    try {
      await deleteEmail(email.id);
      await refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "No se pudo eliminar el correo.");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleRetry(email: EmailSummary) {
    setActionError(null);
    setRetryingId(email.id);
    try {
      await retryEmail(email.id);
      await refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "No se pudo reintentar el correo.");
    } finally {
      setRetryingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Correos"
        title="Todos los correos"
        description="Vista global de correos individuales y correos pertenecientes a lotes. El estado se refresca automaticamente."
        actions={
          <button className="nav-link" onClick={() => void refresh()} type="button">
            Refrescar
          </button>
        }
      />

      {(error || actionError) && <ErrorState message={actionError ?? error ?? ""} />}

      {!data?.length && (
        <EmptyState
          title="No hay correos"
          description="Sube un `.eml` o un lote desde Subida para empezar."
        />
      )}

      <div className="grid gap-4">
        {visibleEmails.map((email) => (
          <Card key={email.id}>
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-3">
                  <StatusBadge status={email.status} />
                  {email.batch && (
                    <Link
                      className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-accent)]"
                      href={`/lotes/${email.batch.id}`}
                    >
                      {email.batch.name}
                    </Link>
                  )}
                </div>
                <div>
                  <h3 className="text-xl font-semibold">{email.name}</h3>
                  <p className="mt-1 text-sm text-[var(--color-muted)]">
                    {email.subject ?? "Sin asunto"}
                  </p>
                </div>
                <div className="flex flex-wrap gap-4 text-sm text-[var(--color-muted)]">
                  <span>Creado: {formatDate(email.created_at)}</span>
                  <span>MCDM: {formatPercent(email.mcdm_score)}</span>
                  <span>{email.selected_subcriteria.length} subcriterios</span>
                </div>
                {email.processing_error?.message && (
                  <p className="text-sm text-[var(--color-danger)]">
                    {email.processing_error.message}
                  </p>
                )}
              </div>
              <div className="flex flex-wrap gap-3">
                {email.status === "cancelled" || email.status === "error" ? (
                  <button
                    className="nav-link"
                    disabled={retryingId === email.id}
                    onClick={() => void handleRetry(email)}
                    type="button"
                  >
                    {retryingId === email.id ? "Reintentando..." : "Reintentar"}
                  </button>
                ) : (
                  <Link className="nav-link" href={`/correos/${email.id}`}>
                    Abrir correo
                  </Link>
                )}
                <button
                  className="rounded-full border border-[var(--color-danger)] bg-white px-4 py-2 text-sm font-medium text-[var(--color-danger)] transition hover:bg-[var(--color-danger-soft)] disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={deletingId === email.id}
                  onClick={() => void handleDelete(email)}
                  type="button"
                >
                  {deletingId === email.id ? "Eliminando..." : "Eliminar"}
                </button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {!!data?.length && (
        <PaginationControls
          hasNext={hasNextPage}
          itemCount={visibleEmails.length}
          onPageChange={setPage}
          page={page}
          pageSize={PAGE_SIZE}
        />
      )}
    </div>
  );
}
