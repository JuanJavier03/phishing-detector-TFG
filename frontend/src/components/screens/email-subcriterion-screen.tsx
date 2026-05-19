"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { analyzeEmailSubcriterion, fetchEmail, fetchEmailSubcriterion } from "@/lib/api";
import { formatPercent, formatSubcriterionValue } from "@/lib/format";
import type { EmailDetail, EmailSubcriterionDetail } from "@/lib/types";
import { usePollingQuery } from "@/hooks/use-polling-query";
import { hasActiveEmail } from "@/lib/polling";
import { Card } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { JsonViewer } from "@/components/ui/json-viewer";
import { LoadingState } from "@/components/ui/loading-state";
import { SectionHeading } from "@/components/ui/section-heading";
import { StatusBadge } from "@/components/ui/status-badge";

type EmailSubcriterionScreenProps = {
  emailId: string;
  subcriterionKey: string;
};

export function EmailSubcriterionScreen({
  emailId,
  subcriterionKey,
}: EmailSubcriterionScreenProps) {
  const router = useRouter();
  const emailQuery = usePollingQuery<EmailDetail>(
    () => fetchEmail(emailId),
    emailId,
    10000,
    true,
    { shouldPoll: hasActiveEmail },
  );
  const subcriterionQuery = usePollingQuery<EmailSubcriterionDetail>(
    () => fetchEmailSubcriterion(emailId, subcriterionKey),
    `${emailId}:${subcriterionKey}`,
    10000,
    true,
    {
      shouldPoll: () => hasActiveEmail(emailQuery.data),
      pollKey: hasActiveEmail(emailQuery.data) ? "active" : "idle",
    },
  );
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const email = emailQuery.data;
  const blockedStatus = email?.status === "error" || email?.status === "cancelled";

  useEffect(() => {
    if (!email || !blockedStatus) {
      return;
    }
    router.replace(email.batch ? `/lotes/${email.batch.id}` : "/correos");
  }, [blockedStatus, email, router]);

  async function handleAnalyze() {
    setSubmitting(true);
    setActionError(null);
    try {
      await analyzeEmailSubcriterion(emailId, subcriterionKey);
      await Promise.all([subcriterionQuery.refresh(), emailQuery.refresh()]);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "No se pudo lanzar.");
    } finally {
      setSubmitting(false);
    }
  }

  if (
    (emailQuery.loading && !emailQuery.data) ||
    (subcriterionQuery.loading && !subcriterionQuery.data)
  ) {
    return <LoadingState label="Cargando subcriterio..." />;
  }

  if (emailQuery.error && !emailQuery.data) {
    return <ErrorState message={emailQuery.error} />;
  }

  if (subcriterionQuery.error && !subcriterionQuery.data) {
    return <ErrorState message={subcriterionQuery.error} />;
  }

  const subcriterion = subcriterionQuery.data;

  if (!email || !subcriterion) {
    return <ErrorState message="No se ha podido cargar el subcriterio." />;
  }

  if (email.status === "error" || email.status === "cancelled") {
    return <LoadingState label="Redirigiendo..." />;
  }

  const hasActiveJob = hasActiveEmail(email);
  const actionJobStatus =
    email.job?.status === "queued" || email.job?.status === "running"
      ? email.job.status
      : null;

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Subcriterio"
        title={subcriterion.subcriterion.label}
        description={`Correo: ${email.name}`}
        actions={
          <div className="flex flex-wrap gap-2">
            <button
              className="nav-link"
              onClick={() => void subcriterionQuery.refresh()}
              type="button"
            >
              Refrescar
            </button>
            <Link className="nav-link" href={`/correos/${emailId}`}>
              Volver al correo
            </Link>
          </div>
        }
      />

      {(emailQuery.error || subcriterionQuery.error || actionError) && (
        <ErrorState
          message={actionError ?? emailQuery.error ?? subcriterionQuery.error ?? ""}
        />
      )}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(360px,1.05fr)]">
        <div className="space-y-6">
          <Card title="Estado del subcriterio">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-[24px] border border-[var(--color-border)] bg-white/80 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]">
                  Estado
                </p>
                <div className="mt-3">
                  <StatusBadge status={subcriterion.status} />
                </div>
              </div>
              <div className="rounded-[24px] border border-[var(--color-border)] bg-white/80 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]">
                  Valor
                </p>
                <p className="mt-3 text-3xl font-semibold">
                  {formatSubcriterionValue(subcriterion.subcriterion.key, subcriterion.value)}
                </p>
              </div>
              <div className="rounded-[24px] border border-[var(--color-border)] bg-[var(--color-accent-soft)] p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]">
                  MCDM del correo
                </p>
                <p className="mt-3 text-3xl font-semibold">
                  {formatPercent(email.mcdm_score)}
                </p>
              </div>
            </div>
          </Card>

          <Card title="Accion">
            <div className="flex flex-wrap items-center gap-3">
              <button
                className="rounded-full bg-[var(--color-accent)] px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={submitting || hasActiveJob}
                onClick={() => void handleAnalyze()}
                type="button"
              >
                {submitting
                  ? "Lanzando..."
                  : subcriterion.status === "completed"
                    ? "Reanalizar"
                    : "Analizar"}
              </button>
              {actionJobStatus && <StatusBadge status={actionJobStatus} />}
            </div>
          </Card>
        </div>

        <Card
          title="JSON del subcriterio"
          subtitle="Se guarda completo para la vista visual"
        >
          <JsonViewer value={subcriterion.result ?? {}} />
        </Card>
      </div>
    </div>
  );
}
