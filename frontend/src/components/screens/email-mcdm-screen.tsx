"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { fetchEmail } from "@/lib/api";
import { formatPercent } from "@/lib/format";
import type { EmailDetail } from "@/lib/types";
import { usePollingQuery } from "@/hooks/use-polling-query";
import { hasActiveEmail } from "@/lib/polling";
import { Card } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingState } from "@/components/ui/loading-state";
import { SectionHeading } from "@/components/ui/section-heading";

type EmailMcdmScreenProps = {
  emailId: string;
};

function formatUnitInterval(value: number | null): string {
  if (value === null) {
    return "Sin valor";
  }
  return value.toFixed(3);
}

function formatMcdmMethod(method: string | null, isMock: boolean) {
  if (isMock) {
    return "Calculo temporal";
  }
  if (!method) {
    return "TOPSIS";
  }

  return method
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function EmailMcdmScreen({ emailId }: EmailMcdmScreenProps) {
  const router = useRouter();
  const { data, error, loading, refresh } = usePollingQuery<EmailDetail>(
    () => fetchEmail(emailId),
    `${emailId}:mcdm`,
    10000,
    true,
    { shouldPoll: hasActiveEmail },
  );
  const blockedStatus = data?.status === "error" || data?.status === "cancelled";
  useEffect(() => {
    if (!data || !blockedStatus) {
      return;
    }
    router.replace(data.batch ? `/lotes/${data.batch.id}` : "/correos");
  }, [blockedStatus, data, router]);

  if (loading && !data) {
    return <LoadingState label="Cargando pantalla MCDM..." />;
  }

  if (error && !data) {
    return <ErrorState message={error} />;
  }

  if (!data) {
    return <ErrorState message="No se ha podido cargar el correo." />;
  }

  if (data.status === "error" || data.status === "cancelled") {
    return <LoadingState label="Redirigiendo..." />;
  }

  const items = data.subcriteria.map((item) => ({
    key: item.key,
    label: item.label,
    score: item.has_result ? item.mcdm_score : null,
    weight: item.mcdm_weight,
  }));

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="MCDM"
        title={data.name}
        description="Puntuacion por subcriterio derivada de la transformacion MCDM del vector."
        actions={
          <div className="flex flex-wrap gap-2">
            <button className="nav-link" onClick={() => void refresh()} type="button">
              Refrescar
            </button>
            <Link className="nav-link" href={`/correos/${emailId}`}>
              Volver al correo
            </Link>
          </div>
        }
      />

      {error && <ErrorState message={error} />}

      <Card title="Score global">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm text-[var(--color-muted)]">
              {formatMcdmMethod(data.mcdm_method, data.mcdm_is_mock)}
            </p>
            <p className="mt-2 text-4xl font-semibold">
              {formatPercent(data.mcdm_score)}
            </p>
          </div>
          <p className="text-sm text-[var(--color-muted)]">
            Vector v{data.vector.version ?? "-"}
          </p>
        </div>
      </Card>

      <Card title="Subcriterios">
        <div className="space-y-3">
          {items.map((item) => (
            <div
              key={item.key}
              className="rounded-[22px] border border-[var(--color-border)] bg-white/70 px-4 py-4"
            >
              <div className="flex items-center justify-between gap-4">
                <p className="text-sm font-semibold leading-6">{item.label}</p>
                <div className="text-right">
                  <p className="text-xs font-semibold uppercase text-[var(--color-muted)]">
                    Peso {formatPercent(item.weight)}
                  </p>
                  <p className="text-2xl font-semibold">
                    {formatUnitInterval(item.score)}
                  </p>
                </div>
              </div>
              <div
                aria-hidden="true"
                className="mt-3 h-2 rounded-full bg-[var(--color-border)]"
              >
                <div
                  className="h-full rounded-full bg-[var(--color-accent)] transition-[width]"
                  style={{ width: `${((item.score ?? 0) * 100).toFixed(2)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
