"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { deleteBatch, fetchBatches, mergeBatches } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { BatchSummary } from "@/lib/types";
import { usePollingQuery } from "@/hooks/use-polling-query";
import { hasAnyActiveBatches } from "@/lib/polling";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingState } from "@/components/ui/loading-state";
import { PaginationControls } from "@/components/ui/pagination-controls";
import { SectionHeading } from "@/components/ui/section-heading";
import { StatusBadge } from "@/components/ui/status-badge";

const PAGE_SIZE = 20;

export function BatchesScreen() {
  const router = useRouter();
  const [page, setPage] = useState(0);
  const { data, error, loading, refresh } = usePollingQuery<BatchSummary[]>(
    () => fetchBatches(PAGE_SIZE + 1, page * PAGE_SIZE),
    `batches:${page}`,
    10000,
    true,
    { shouldPoll: hasAnyActiveBatches },
  );
  const [actionError, setActionError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [selectedBatchIds, setSelectedBatchIds] = useState<Set<string>>(new Set());
  const [mergeName, setMergeName] = useState("Lote unido");
  const [merging, setMerging] = useState(false);

  if (loading && !data) {
    return <LoadingState label="Cargando lotes..." />;
  }

  async function handleDelete(batch: BatchSummary) {
    const confirmed = window.confirm(`Se eliminara el lote "${batch.name}" y todos sus correos.`);
    if (!confirmed) {
      return;
    }

    setActionError(null);
    setDeletingId(batch.id);
    try {
      await deleteBatch(batch.id);
      await refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "No se pudo eliminar el lote.");
    } finally {
      setDeletingId(null);
    }
  }

  function toggleSelectedBatch(batchId: string) {
    setSelectedBatchIds((current) => {
      const next = new Set(current);
      if (next.has(batchId)) {
        next.delete(batchId);
      } else {
        next.add(batchId);
      }
      return next;
    });
  }

  async function handleMerge() {
    const batchIds = Array.from(selectedBatchIds);
    const name = mergeName.trim();
    if (batchIds.length < 2) {
      setActionError("Selecciona al menos dos lotes para unir.");
      return;
    }
    if (!name) {
      setActionError("Debes indicar un nombre para el lote unido.");
      return;
    }

    setActionError(null);
    setMerging(true);
    try {
      const result = await mergeBatches({ name, batchIds });
      setSelectedBatchIds(new Set());
      setMergeName("Lote unido");
      router.push(`/lotes/${result.batch_id}`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "No se pudo unir los lotes.");
    } finally {
      setMerging(false);
    }
  }

  const selectedCount = selectedBatchIds.size;
  const canMerge = selectedCount >= 2 && mergeName.trim().length > 0 && !merging;
  const visibleBatches = (data ?? []).slice(0, PAGE_SIZE);
  const hasNextPage = (data?.length ?? 0) > PAGE_SIZE;

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Lotes"
        title="Todos los lotes"
        description="Cada lote contiene varios correos y un job de procesamiento en segundo plano."
        actions={
          <button className="nav-link" onClick={() => void refresh()} type="button">
            Refrescar
          </button>
        }
      />

      {(error || actionError) && <ErrorState message={actionError ?? error ?? ""} />}

      {(data?.length ?? 0) >= 2 && (
        <Card
          title="Unir lotes"
          subtitle="Selecciona lotes con los checkbox y crea un lote nuevo con los correos ya evaluados."
          actions={
            <button
              className="nav-link disabled:cursor-not-allowed disabled:opacity-50"
              disabled={!canMerge}
              onClick={() => void handleMerge()}
              type="button"
            >
              {merging ? "Creando..." : "Crear lote unido"}
            </button>
          }
        >
          <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
            <label className="space-y-2">
              <span className="text-sm font-medium text-[var(--color-muted)]">
                Nombre del lote unido
              </span>
              <input
                className="w-full rounded-2xl border border-[var(--color-border)] bg-white/75 px-4 py-3 text-sm outline-none transition focus:border-[var(--color-border-strong)]"
                maxLength={255}
                onChange={(event) => setMergeName(event.target.value)}
                value={mergeName}
              />
            </label>
            <p className="text-sm text-[var(--color-muted)]">
              {selectedCount} lotes seleccionados
            </p>
          </div>
        </Card>
      )}

      {!data?.length && (
        <EmptyState
          title="No hay lotes"
          description="Sube varios `.eml` desde Subida para crear el primer lote."
        />
      )}

      <div className="grid gap-4">
        {visibleBatches.map((batch) => (
          <Card key={batch.id}>
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-3">
                  <label className="inline-flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-white/70 px-3 py-2 text-sm font-medium">
                    <input
                      checked={selectedBatchIds.has(batch.id)}
                      className="h-4 w-4 accent-[var(--color-accent)]"
                      disabled={batch.status === "queued" || batch.status === "running"}
                      onChange={() => toggleSelectedBatch(batch.id)}
                      type="checkbox"
                    />
                    Unir
                  </label>
                  <StatusBadge status={batch.status} />
                  <span className="text-sm text-[var(--color-muted)]">
                    {batch.completed_emails}/{batch.total_emails} correos completados
                  </span>
                  {batch.discarded_emails > 0 && (
                    <span className="text-sm text-[var(--color-danger)]">
                      {batch.discarded_emails} cancelados
                    </span>
                  )}
                </div>
                <div>
                  <h3 className="text-xl font-semibold">{batch.name}</h3>
                  <p className="mt-1 text-sm text-[var(--color-muted)]">
                    Creado el {formatDate(batch.created_at)}
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap gap-3">
                <Link className="nav-link" href={`/lotes/${batch.id}`}>
                  Abrir lote
                </Link>
                <button
                  className="rounded-full border border-[var(--color-danger)] bg-white px-4 py-2 text-sm font-medium text-[var(--color-danger)] transition hover:bg-[var(--color-danger-soft)] disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={deletingId === batch.id}
                  onClick={() => void handleDelete(batch)}
                  type="button"
                >
                  {deletingId === batch.id ? "Eliminando..." : "Eliminar"}
                </button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {!!data?.length && (
        <PaginationControls
          hasNext={hasNextPage}
          itemCount={visibleBatches.length}
          onPageChange={setPage}
          page={page}
          pageSize={PAGE_SIZE}
        />
      )}
    </div>
  );
}
