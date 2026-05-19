"use client";

import type { SubcriterionDefinition, UploadResponse } from "@/lib/types";
import { ErrorState } from "@/components/ui/error-state";
import { Spinner } from "@/components/ui/spinner";

export type UploadMode = "single" | "batch";
export type ModalStep = "details" | "subcriteria" | "progress";

type UploadFlowModalProps = {
  uploadMode: UploadMode;
  modalStep: ModalStep;
  files: File[];
  name: string;
  sourceConfirmed: boolean;
  selectedKeys: string[];
  headerSubcriteria: SubcriterionDefinition[];
  bodySubcriteria: SubcriterionDefinition[];
  selectedHeaderCount: number;
  selectedBodyCount: number;
  subcriteriaLoading: boolean;
  submitError: string | null;
  progressError: string | null;
  submitting: boolean;
  progressCurrent: number;
  progressTotal: number;
  progressRatio: number;
  progressStatus: string;
  statusLabel: string;
  trackedJobId: string | null;
  lastUpload: UploadResponse | null;
  onClose: () => void;
  onNameChange: (value: string) => void;
  onSourceConfirmedChange: (value: boolean) => void;
  onChangeFiles: () => void;
  onContinueFromDetails: () => void;
  onBackToDetails: () => void;
  onToggleKey: (key: string) => void;
  onSelectAll: () => void;
  onSelectNonApiOnly: () => void;
  onClearSelection: () => void;
  onStartAnalysis: () => void;
  onBackFromFailure: () => void;
};

export function UploadFlowModal({
  uploadMode,
  modalStep,
  files,
  name,
  sourceConfirmed,
  selectedKeys,
  headerSubcriteria,
  bodySubcriteria,
  selectedHeaderCount,
  selectedBodyCount,
  subcriteriaLoading,
  submitError,
  progressError,
  submitting,
  progressCurrent,
  progressTotal,
  progressRatio,
  progressStatus,
  statusLabel,
  trackedJobId,
  lastUpload,
  onClose,
  onNameChange,
  onSourceConfirmedChange,
  onChangeFiles,
  onContinueFromDetails,
  onBackToDetails,
  onToggleKey,
  onSelectAll,
  onSelectNonApiOnly,
  onClearSelection,
  onStartAnalysis,
  onBackFromFailure,
}: UploadFlowModalProps) {
  const isProgressActive =
    modalStep === "progress" &&
    (submitting ||
      !lastUpload ||
      (progressStatus !== "completed" && progressStatus !== "failed"));
  const progressLabel =
    lastUpload?.type === "batch"
      ? `${progressCurrent}/${progressTotal} correos completados`
      : `${progressCurrent}/${progressTotal} subcriterios completados`;

  const filesPanel = (
    <div className="rounded-[28px] border border-[var(--color-border)] bg-white/78 p-6">
      <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--color-accent)]">
        Archivos
      </p>
      <h3 className="mt-3 text-2xl font-semibold tracking-[-0.05em]">
        {files.length} seleccionado(s)
      </h3>
      <div className="mt-5 space-y-3">
        {files.slice(0, 6).map((file) => (
          <div
            key={`${file.name}-${file.size}`}
            className="rounded-[20px] border border-[var(--color-border)] bg-[var(--color-panel)] px-4 py-3"
          >
            <p className="truncate text-sm font-medium">{file.name}</p>
          </div>
        ))}
        {files.length > 6 && (
          <p className="text-sm text-[var(--color-muted)]">
            +{files.length - 6} archivos mas
          </p>
        )}
      </div>

      <button
        className="mt-6 rounded-full border border-[var(--color-border)] bg-[var(--color-panel)] px-4 py-2 text-sm font-medium transition hover:border-[var(--color-border-strong)] hover:bg-white"
        onClick={onChangeFiles}
        type="button"
      >
        Cambiar archivos
      </button>
    </div>
  );

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 sm:p-6">
      <div className="absolute inset-0 bg-slate-950/58 backdrop-blur-sm" />

      <div className="relative z-[1] flex max-h-[calc(100vh-2rem)] w-full max-w-5xl flex-col overflow-hidden rounded-[34px] border border-white/25 bg-[var(--color-header)] shadow-[0_40px_120px_rgba(2,8,23,0.45)]">
        <div className="border-b border-[var(--color-border)] px-6 py-5 sm:px-8">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.34em] text-[var(--color-accent)]">
                {uploadMode === "single" ? "Correo individual" : "Lote de correos"}
              </p>
              <h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em]">
                {modalStep === "details" && "Define la subida"}
                {modalStep === "subcriteria" && "Selecciona subcriterios"}
                {modalStep === "progress" && "Sigue el analisis"}
              </h2>
            </div>

            {modalStep !== "progress" && (
              <button
                className="rounded-full border border-[var(--color-border)] bg-white px-4 py-2 text-sm font-medium text-[var(--color-muted)] transition hover:border-[var(--color-border-strong)] hover:text-[var(--color-text)]"
                onClick={onClose}
                type="button"
              >
                Cerrar
              </button>
            )}
          </div>

          <div className="mt-5 grid grid-cols-3 gap-2">
            {[
              { key: "details", label: "Datos" },
              { key: "subcriteria", label: "Subcriterios" },
              { key: "progress", label: "Progreso" },
            ].map((step, index) => {
              const active =
                (modalStep === "details" && step.key === "details") ||
                (modalStep === "subcriteria" &&
                  (step.key === "details" || step.key === "subcriteria")) ||
                modalStep === "progress";

              return (
                <div
                  key={step.key}
                  className={`rounded-full px-4 py-3 text-sm font-medium transition ${
                    active
                      ? "bg-[var(--color-accent)] text-white"
                      : "bg-white/70 text-[var(--color-muted)]"
                  }`}
                >
                  {index + 1}. {step.label}
                </div>
              );
            })}
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-6 sm:px-8 sm:py-8">
          {modalStep === "details" && (
            <div className="space-y-8">
              <div className="grid gap-6">
                <div className="rounded-[28px] border border-[var(--color-border)] bg-white/78 p-6">
                  <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--color-accent)]">
                    Nombre
                  </p>
                  <h3 className="mt-3 text-3xl font-semibold tracking-[-0.05em]">
                    {uploadMode === "single"
                      ? "Ponle nombre al correo"
                      : "Ponle nombre al lote"}
                  </h3>
                  <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--color-muted)]">
                    Este nombre sera el que aparezca despues en los listados y en
                    la pantalla de detalle final.
                  </p>

                  <label className="mt-8 block space-y-2">
                    <span className="text-sm font-semibold text-[var(--color-text)]">
                      {uploadMode === "single" ? "Nombre del correo" : "Nombre del lote"}
                    </span>
                    <input
                      className="w-full rounded-[20px] border border-[var(--color-border)] bg-[var(--color-panel)] px-4 py-4 text-base outline-none transition focus:border-[var(--color-accent)]"
                      onChange={(event) => onNameChange(event.target.value)}
                      placeholder={
                        uploadMode === "single"
                          ? "Correo de acceso universidad"
                          : "Lote marzo 2026"
                      }
                      value={name}
                    />
                  </label>

                  <label className="mt-6 flex items-start gap-3 rounded-[22px] border border-[var(--color-border)] bg-[var(--color-panel)] px-4 py-4">
                    <input
                      checked={sourceConfirmed}
                      className="mt-1"
                      onChange={(event) =>
                        onSourceConfirmedChange(event.target.checked)
                      }
                      type="checkbox"
                    />
                    <span className="text-sm leading-6 text-[var(--color-text)]">
                      <span className="block font-semibold">
                        {uploadMode === "single"
                          ? "Confirma que este correo proviene de una fuente segura"
                          : "Confirma que estos correos provienen de una fuente segura"}
                      </span>
                      <span className="mt-1 block text-[var(--color-muted)]">
                        {uploadMode === "single"
                          ? "Activa esta opcion unicamente si el .eml ha sido exportado directamente desde un servicio de correo (Gmail, Outlook, servidor propio) sin modificaciones."
                          : "Activa esta opcion unicamente si los .eml han sido exportados directamente desde un servicio de correo (Gmail, Outlook, servidor propio) sin modificaciones."}
                      </span>
                    </span>
                  </label>

                  {uploadMode === "batch" && <div className="mt-6">{filesPanel}</div>}
                </div>

                {uploadMode === "single" && <div>{filesPanel}</div>}
              </div>

              {submitError && <ErrorState message={submitError} />}

              <div className="flex flex-wrap items-center justify-between gap-3">
                <button
                  className="rounded-full border border-[var(--color-border)] bg-white px-5 py-3 text-sm font-semibold transition hover:border-[var(--color-border-strong)]"
                  onClick={onClose}
                  type="button"
                >
                  Cancelar
                </button>
                <button
                  className={`rounded-full px-6 py-3 text-sm font-semibold text-white transition ${
                    sourceConfirmed
                      ? "bg-[var(--color-accent)] hover:opacity-92"
                      : "cursor-not-allowed bg-slate-300"
                  }`}
                  disabled={!sourceConfirmed}
                  onClick={onContinueFromDetails}
                  type="button"
                >
                  Continuar
                </button>
              </div>
            </div>
          )}

          {modalStep === "subcriteria" && (
            <div className="space-y-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <p className="max-w-2xl text-sm leading-6 text-[var(--color-muted)]">
                  Marca los subcriterios que quieres ejecutar. Se separan en
                  cabecera y cuerpo para que puedas revisar ambas familias de forma
                  independiente.
                </p>
                <div className="flex flex-wrap gap-2">
                  <button
                    className="rounded-full border border-[var(--color-border)] bg-white px-4 py-2 text-sm font-medium transition hover:border-[var(--color-border-strong)]"
                    onClick={onSelectAll}
                    type="button"
                  >
                    Seleccionar todo
                  </button>
                  <button
                    className="rounded-full border border-[var(--color-border)] bg-white px-4 py-2 text-sm font-medium transition hover:border-[var(--color-border-strong)]"
                    onClick={onSelectNonApiOnly}
                    type="button"
                  >
                    Solo sin API
                  </button>
                  <button
                    className="rounded-full border border-[var(--color-border)] bg-white px-4 py-2 text-sm font-medium transition hover:border-[var(--color-border-strong)]"
                    onClick={onClearSelection}
                    type="button"
                  >
                    Limpiar
                  </button>
                </div>
              </div>

              <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_1px_minmax(0,1fr)]">
                <div className="rounded-[28px] border border-[var(--color-border)] bg-white/78 p-5">
                  <div className="mb-4 flex items-end justify-between gap-4">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--color-accent)]">
                        Cabecera
                      </p>
                      <h3 className="mt-2 text-xl font-semibold tracking-[-0.04em]">
                        Criterio 1
                      </h3>
                    </div>
                    <p className="text-sm text-[var(--color-muted)]">
                      {selectedHeaderCount}/{headerSubcriteria.length}
                    </p>
                  </div>

                  <div className="h-[min(18rem,calc(100vh-26rem))] min-h-[12rem] space-y-3 overflow-y-auto pr-2">
                    {headerSubcriteria.map((item) => {
                      const checked = selectedKeys.includes(item.key);
                      return (
                        <label
                          key={item.key}
                          className={`flex cursor-pointer items-start gap-3 rounded-[22px] border px-4 py-4 transition ${
                            checked
                              ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)]"
                              : "border-[var(--color-border)] bg-[var(--color-panel)]"
                          }`}
                        >
                          <input
                            checked={checked}
                            className="mt-1"
                            onChange={() => onToggleKey(item.key)}
                            type="checkbox"
                          />
                          <span>
                            <span className="block text-sm font-semibold">
                              {item.label}
                            </span>
                            {item.uses_api && (
                              <span className="mt-1 block text-xs font-medium uppercase tracking-[0.18em] text-[var(--color-accent)]">
                                Usa API
                              </span>
                            )}
                          </span>
                        </label>
                      );
                    })}
                  </div>
                </div>

                <div className="hidden bg-[var(--color-border)] lg:block" />

                <div className="rounded-[28px] border border-[var(--color-border)] bg-white/78 p-5">
                  <div className="mb-4 flex items-end justify-between gap-4">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--color-accent)]">
                        Cuerpo
                      </p>
                      <h3 className="mt-2 text-xl font-semibold tracking-[-0.04em]">
                        Criterio 2
                      </h3>
                    </div>
                    <p className="text-sm text-[var(--color-muted)]">
                      {selectedBodyCount}/{bodySubcriteria.length}
                    </p>
                  </div>

                  <div className="h-[min(18rem,calc(100vh-26rem))] min-h-[12rem] space-y-3 overflow-y-auto pr-2">
                    {bodySubcriteria.map((item) => {
                      const checked = selectedKeys.includes(item.key);
                      return (
                        <label
                          key={item.key}
                          className={`flex cursor-pointer items-start gap-3 rounded-[22px] border px-4 py-4 transition ${
                            checked
                              ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)]"
                              : "border-[var(--color-border)] bg-[var(--color-panel)]"
                          }`}
                        >
                          <input
                            checked={checked}
                            className="mt-1"
                            onChange={() => onToggleKey(item.key)}
                            type="checkbox"
                          />
                          <span>
                            <span className="block text-sm font-semibold">
                              {item.label}
                            </span>
                            {item.uses_api && (
                              <span className="mt-1 block text-xs font-medium uppercase tracking-[0.18em] text-[var(--color-accent)]">
                                Usa API
                              </span>
                            )}
                          </span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              </div>

              {subcriteriaLoading &&
                !headerSubcriteria.length &&
                !bodySubcriteria.length && (
                  <div className="flex items-center gap-3 rounded-[20px] border border-[var(--color-border)] bg-white/78 px-4 py-3 text-sm text-[var(--color-muted)]">
                    <Spinner size="sm" />
                    <p>Cargando subcriterios...</p>
                  </div>
                )}

              {!subcriteriaLoading &&
                !headerSubcriteria.length &&
                !bodySubcriteria.length && (
                  <ErrorState message="No se han podido cargar los subcriterios disponibles." />
                )}

              {submitError && <ErrorState message={submitError} />}

              <div className="flex flex-wrap items-center justify-between gap-3">
                <button
                  className="rounded-full border border-[var(--color-border)] bg-white px-5 py-3 text-sm font-semibold transition hover:border-[var(--color-border-strong)]"
                  onClick={onBackToDetails}
                  type="button"
                >
                  Atras
                </button>
                <button
                  className="rounded-full bg-[var(--color-accent)] px-6 py-3 text-sm font-semibold text-white transition hover:opacity-92 disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={subcriteriaLoading || !selectedKeys.length || submitting}
                  onClick={onStartAnalysis}
                  type="button"
                >
                  {submitting ? "Iniciando..." : "Iniciar analisis"}
                </button>
              </div>
            </div>
          )}

          {modalStep === "progress" && (
            <div className="space-y-8">
              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-[24px] border border-[var(--color-border)] bg-white/78 p-5">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-accent)]">
                    Modo
                  </p>
                  <p className="mt-3 text-xl font-semibold">
                    {uploadMode === "single" ? "Correo" : "Lote"}
                  </p>
                </div>
                <div className="rounded-[24px] border border-[var(--color-border)] bg-white/78 p-5">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-accent)]">
                    Nombre
                  </p>
                  <p className="mt-3 truncate text-xl font-semibold">{name}</p>
                </div>
                <div className="rounded-[24px] border border-[var(--color-border)] bg-white/78 p-5">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-accent)]">
                    Seleccion
                  </p>
                  <p className="mt-3 text-xl font-semibold">
                    {uploadMode === "single"
                      ? files[0]?.name ?? "-"
                      : `${files.length} archivos`}
                  </p>
                </div>
              </div>

              <div className="rounded-[30px] border border-[var(--color-border)] bg-white/82 p-6 sm:p-8">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--color-accent)]">
                      Progreso
                    </p>
                    <h3 className="mt-3 text-3xl font-semibold tracking-[-0.05em]">
                      {progressLabel}
                    </h3>
                  </div>
                  <div className="flex items-center gap-3">
                    <div
                      className={`rounded-full px-4 py-2 text-sm font-semibold ${
                        progressStatus === "failed"
                          ? "bg-[var(--color-danger-soft)] text-[var(--color-danger)]"
                          : progressStatus === "completed"
                            ? "bg-[var(--color-success-soft)] text-[var(--color-success)]"
                            : "bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                      }`}
                    >
                      {statusLabel}
                    </div>
                  </div>
                </div>

                {isProgressActive && (
                  <div className="mt-8 flex flex-col items-center justify-center gap-3 rounded-[24px] border border-[var(--color-border)] bg-[var(--color-panel)] px-6 py-6 text-center">
                    <Spinner size="lg" />
                    <p className="text-sm text-[var(--color-muted)]">
                      {lastUpload
                        ? uploadMode === "single"
                          ? "Analizando subcriterios del correo..."
                          : "Analizando correos del lote..."
                        : "Preparando la subida y creando el trabajo..."}
                    </p>
                  </div>
                )}

                <div className="mt-8 rounded-full bg-[var(--color-panel-strong)] p-1">
                  <div
                    className="h-4 rounded-full bg-[var(--color-accent)] transition-[width] duration-500"
                    style={{
                      width: `${lastUpload ? progressRatio : 14}%`,
                    }}
                  />
                </div>

                <div className="mt-5 flex flex-wrap items-center justify-between gap-3 text-sm text-[var(--color-muted)]">
                  <span>
                    {lastUpload
                      ? uploadMode === "single"
                        ? "Se cuentan los subcriterios persistidos del correo."
                        : "Se cuentan los correos del lote ya analizados por completo."
                      : "Creando registros y lanzando el trabajo en segundo plano."}
                  </span>
                  {trackedJobId && (
                    <span className="font-mono text-xs uppercase tracking-[0.18em]">
                      Job {trackedJobId}
                    </span>
                  )}
                </div>
              </div>

              {(submitError || progressError) && (
                <ErrorState message={submitError ?? progressError ?? ""} />
              )}

              {progressStatus === "failed" && (
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <button
                    className="rounded-full border border-[var(--color-border)] bg-white px-5 py-3 text-sm font-semibold transition hover:border-[var(--color-border-strong)]"
                    onClick={onBackFromFailure}
                    type="button"
                  >
                    Volver a subcriterios
                  </button>
                  <button
                    className="rounded-full bg-[var(--color-accent)] px-6 py-3 text-sm font-semibold text-white transition hover:opacity-92"
                    onClick={onClose}
                    type="button"
                  >
                    Cerrar
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
