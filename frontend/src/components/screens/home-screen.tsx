"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  fetchJob,
  fetchSubcriteria,
  uploadBatch,
  uploadSingleEmail,
} from "@/lib/api";
import {
  playAnalysisFinishedSound,
  primeAnalysisSound,
} from "@/lib/analysis-sounds";
import type {
  Job,
  JobStatus,
  SubcriterionDefinition,
  UploadResponse,
} from "@/lib/types";
import { usePollingQuery } from "@/hooks/use-polling-query";
import {
  ModalStep,
  UploadFlowModal,
  UploadMode,
} from "@/components/screens/upload-flow-modal";
import { ErrorState } from "@/components/ui/error-state";
import { hasActiveJob } from "@/lib/polling";

function SingleMailIllustration() {
  return (
    <div className="flex aspect-square h-[96px] w-[96px] flex-none items-center justify-center rounded-[24px] border border-[var(--color-border)] bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(236,242,247,0.92))] transition group-hover:border-[var(--color-accent)]">
      <div className="relative h-[84px] w-[84px] translate-x-[4px] translate-y-[2px]">
        <svg
          aria-hidden="true"
          className="h-[84px] w-[84px]"
          fill="none"
          viewBox="0 0 68 68"
        >
          <rect
            x="22"
            y="20"
            width="24"
            height="18"
            rx="6"
            fill="white"
            stroke="#102231"
            strokeWidth="1.5"
          />
          <path
            d="M25.5 24.5l8.1 5.8a1.4 1.4 0 0 0 1.6 0l8.3-5.8"
            stroke="#102231"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="1.25"
          />
        </svg>
        <div className="absolute left-[14px] top-[37px] flex h-[20px] min-w-[20px] items-center justify-center rounded-full bg-[#102231] px-[6px] text-[10px] font-semibold text-white shadow-[0_10px_20px_rgba(16,34,49,0.18)]">
          1
        </div>
      </div>
    </div>
  );
}

function BatchMailIllustration() {
  return (
    <div className="flex aspect-square h-[96px] w-[96px] flex-none items-center justify-center rounded-[24px] border border-[var(--color-border)] bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(236,242,247,0.92))] transition group-hover:border-[var(--color-accent)]">
      <svg
        aria-hidden="true"
        className="h-[78px] w-[78px]"
        fill="none"
        viewBox="0 0 68 68"
      >
        <rect x="13" y="12" width="24" height="18" rx="6" fill="#EEF4F8" stroke="#B8C7D4" />
        <path d="M16.5 16.5l8.1 5.8a1.4 1.4 0 0 0 1.6 0l8.3-5.8" stroke="#90A4B4" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" />
        <rect x="22" y="20" width="24" height="18" rx="6" fill="white" stroke="#8EA2B3" strokeWidth="1.25" />
        <path d="M25.5 24.5l8.1 5.8a1.4 1.4 0 0 0 1.6 0l8.3-5.8" stroke="#5F7385" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" />
        <rect x="31" y="28" width="24" height="18" rx="6" fill="white" stroke="#102231" strokeWidth="1.5" />
        <path d="M34.5 32.5l8.1 5.8a1.4 1.4 0 0 0 1.6 0l8.3-5.8" stroke="#102231" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="20" cy="47" r="8" fill="#102231" />
        <path d="M17.7 47h4.6M20 44.7v4.6" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    </div>
  );
}

function buildDefaultName(mode: UploadMode, files: File[]) {
  if (!files.length) {
    return mode === "single" ? "" : "Nuevo lote";
  }

  if (mode === "single") {
    return files[0].name.replace(/\.eml$/i, "");
  }

  return `Lote ${new Date().toLocaleDateString("es-ES")}`;
}

function hasVectorPrefix(item: SubcriterionDefinition, prefix: "c1_" | "c2_") {
  const vectorFields = Array.isArray(item.vector_fields) ? item.vector_fields : [];
  if (vectorFields.some((field) => field.startsWith(prefix))) {
    return true;
  }
  return item.vector_field.startsWith(prefix);
}

function isHeaderSubcriterion(item: SubcriterionDefinition) {
  if (item.family === "criterio1") {
    return true;
  }
  return hasVectorPrefix(item, "c1_");
}

function isBodySubcriterion(item: SubcriterionDefinition) {
  if (item.family === "criterio2") {
    return true;
  }
  return hasVectorPrefix(item, "c2_");
}

function nonApiSubcriterionKeys(items: SubcriterionDefinition[]) {
  return items.filter((item) => !item.uses_api).map((item) => item.key);
}

export function HomeScreen() {
  const router = useRouter();
  const singleInputRef = useRef<HTMLInputElement | null>(null);
  const batchInputRef = useRef<HTMLInputElement | null>(null);

  const {
    data: subcriteria,
    error: subcriteriaError,
    loading: subcriteriaLoading,
  } = usePollingQuery<SubcriterionDefinition[]>(
    fetchSubcriteria,
    "subcriteria",
    300000,
    true,
    { shouldPoll: () => false },
  );

  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
  const [hasInitializedSelection, setHasInitializedSelection] = useState(false);
  const [uploadMode, setUploadMode] = useState<UploadMode | null>(null);
  const [modalStep, setModalStep] = useState<ModalStep | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [name, setName] = useState("");
  const [sourceConfirmed, setSourceConfirmed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [lastUpload, setLastUpload] = useState<UploadResponse | null>(null);
  const [trackedJobId, setTrackedJobId] = useState<string | null>(null);
  const notifiedTerminalStatusRef = useRef<{
    jobId: string | null;
    status: JobStatus | null;
  }>({
    jobId: null,
    status: null,
  });

  const jobQuery = usePollingQuery<Job>(
    () => fetchJob(trackedJobId ?? ""),
    trackedJobId ?? "no-job",
    1500,
    Boolean(trackedJobId) && modalStep === "progress",
    { shouldPoll: hasActiveJob },
  );

  useEffect(() => {
    if (subcriteria && !hasInitializedSelection) {
      setSelectedKeys(subcriteria.map((item) => item.key));
      setHasInitializedSelection(true);
    }
  }, [hasInitializedSelection, subcriteria]);

  useEffect(() => {
    if (!modalStep) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [modalStep]);

  useEffect(() => {
    if (!lastUpload || jobQuery.data?.status !== "completed") {
      return;
    }

    if (lastUpload.type === "email") {
      router.push(`/correos/${lastUpload.email_id}`);
      return;
    }

    router.push(`/lotes/${lastUpload.batch_id}`);
  }, [jobQuery.data?.status, lastUpload, router]);

  useEffect(() => {
    if (!trackedJobId) {
      notifiedTerminalStatusRef.current = { jobId: null, status: null };
      return;
    }

    const status = jobQuery.data?.status;
    if (status !== "completed" && status !== "failed") {
      return;
    }

    const lastNotification = notifiedTerminalStatusRef.current;
    if (
      lastNotification.jobId === trackedJobId &&
      lastNotification.status === status
    ) {
      return;
    }

    notifiedTerminalStatusRef.current = {
      jobId: trackedJobId,
      status,
    };
    void playAnalysisFinishedSound(status === "completed" ? "success" : "error");
  }, [jobQuery.data?.status, trackedJobId]);

  function resetFileInputs() {
    if (singleInputRef.current) {
      singleInputRef.current.value = "";
    }
    if (batchInputRef.current) {
      batchInputRef.current.value = "";
    }
  }

  function openSelection(mode: UploadMode) {
    if (mode === "single") {
      singleInputRef.current?.click();
      return;
    }

    batchInputRef.current?.click();
  }

  function closeModal() {
    if (submitting) {
      return;
    }

    setUploadMode(null);
    setModalStep(null);
    setFiles([]);
    setName("");
    setSourceConfirmed(false);
    setSubmitError(null);
    setLastUpload(null);
    setTrackedJobId(null);
    resetFileInputs();
  }

  function handleFileSelection(mode: UploadMode, nextFiles: File[]) {
    if (!nextFiles.length) {
      return;
    }

    setUploadMode(mode);
    setFiles(nextFiles);
    setName(buildDefaultName(mode, nextFiles));
    setSourceConfirmed(false);
    setSubmitError(null);
    setLastUpload(null);
    setTrackedJobId(null);
    setModalStep("details");
  }

  function toggleKey(key: string) {
    setSelectedKeys((current) =>
      current.includes(key)
        ? current.filter((item) => item !== key)
        : [...current, key],
    );
  }

  async function handleStartAnalysis() {
    if (!uploadMode) {
      return;
    }

    if (!files.length) {
      setSubmitError("Debes seleccionar al menos un archivo .eml.");
      return;
    }

    if (!name.trim()) {
      setSubmitError(
        uploadMode === "single"
          ? "Debes indicar un nombre para el correo."
          : "Debes indicar un nombre para el lote.",
      );
      return;
    }

    if (!sourceConfirmed) {
      setSubmitError(
        "Debes confirmar que el .eml proviene de una fuente segura antes de continuar.",
      );
      return;
    }

    if (!selectedKeys.length) {
      setSubmitError("Debes seleccionar al menos un subcriterio.");
      return;
    }

    setSubmitError(null);
    void primeAnalysisSound();
    setSubmitting(true);
    setModalStep("progress");
    setLastUpload(null);
    setTrackedJobId(null);

    try {
      const payload =
        uploadMode === "single"
          ? await uploadSingleEmail({
              file: files[0],
              name: name.trim(),
              selectedSubcriteria: selectedKeys,
            })
          : await uploadBatch({
              files,
              name: name.trim(),
              selectedSubcriteria: selectedKeys,
            });

      setLastUpload(payload);
      setTrackedJobId(payload.job_id);
      resetFileInputs();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "No se pudo iniciar el analisis.");
    } finally {
      setSubmitting(false);
    }
  }

  const headerSubcriteria = (subcriteria ?? []).filter(isHeaderSubcriterion);
  const bodySubcriteria = (subcriteria ?? []).filter(isBodySubcriterion);

  const singleProgressTotal =
    jobQuery.data?.progress_total ?? selectedKeys.length;
  const singleProgressCurrent = jobQuery.data?.progress_current ?? 0;
  const batchProgressTotal =
    jobQuery.data?.progress_total ??
    (lastUpload?.type === "batch" ? lastUpload.email_ids.length : files.length);
  const batchProgressCurrent = jobQuery.data?.progress_current ?? 0;

  const progressTotal =
    lastUpload?.type === "batch" ? batchProgressTotal : singleProgressTotal;
  const progressCurrent =
    lastUpload?.type === "batch" ? batchProgressCurrent : singleProgressCurrent;
  const progressRatio =
    progressTotal > 0 ? Math.min((progressCurrent / progressTotal) * 100, 100) : 0;
  const progressStatus = jobQuery.data?.status ?? "queued";

  const statusLabel =
    progressStatus === "completed"
      ? "Analisis finalizado. Abriendo resultado..."
      : progressStatus === "failed"
        ? "El analisis ha fallado"
        : lastUpload
          ? "Analizando en segundo plano"
          : "Preparando la subida";

  const selectedHeaderCount = headerSubcriteria.filter((item) =>
    selectedKeys.includes(item.key),
  ).length;
  const selectedBodyCount = bodySubcriteria.filter((item) =>
    selectedKeys.includes(item.key),
  ).length;

  const isModalOpen = modalStep !== null && uploadMode !== null;
  const progressError = jobQuery.error ?? null;

  return (
    <>
      <div className="flex min-h-[calc(100vh-9rem)] items-center justify-center py-8">
        <div className="w-full max-w-5xl text-center">
          <div className="mx-auto max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.38em] text-[var(--color-accent)]">
              Analisis de phishing
            </p>
            <h1 className="mt-5 text-5xl font-semibold tracking-[-0.08em] text-[var(--color-text)] sm:text-7xl">
              PHISHING DETECTOR
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-base leading-7 text-[var(--color-muted)] sm:text-lg">
              Sube correos .eml, selecciona los subcriterios que quieres ejecutar
              y deja que la aplicacion procese el analisis hasta llevarte
              automaticamente al resultado final.
            </p>
          </div>

          {subcriteriaError && (
            <div className="mx-auto mt-8 max-w-3xl">
              <ErrorState message={subcriteriaError} />
            </div>
          )}

          <div className="mt-12 grid gap-5 lg:grid-cols-2">
            <button
              className="group rounded-[32px] border border-[var(--color-border)] bg-[var(--color-panel)] px-8 py-10 text-left shadow-[0_28px_80px_rgba(16,34,49,0.11)] transition hover:-translate-y-1 hover:border-[var(--color-border-strong)] hover:bg-white"
              onClick={() => openSelection("single")}
              type="button"
            >
              <div className="flex items-start justify-between gap-6">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--color-accent)]">
                    Opcion 01
                  </p>
                  <h2 className="mt-4 text-3xl font-semibold tracking-[-0.05em]">
                    Subir un correo
                  </h2>
                  <p className="mt-4 max-w-xl text-sm leading-6 text-[var(--color-muted)]">
                    Selecciona un unico archivo .eml, define su nombre y elige
                    exactamente que subcriterios se analizaran.
                  </p>
                </div>
                <SingleMailIllustration />
              </div>
            </button>

            <button
              className="group rounded-[32px] border border-[var(--color-border)] bg-[var(--color-panel)] px-8 py-10 text-left shadow-[0_28px_80px_rgba(16,34,49,0.11)] transition hover:-translate-y-1 hover:border-[var(--color-border-strong)] hover:bg-white"
              onClick={() => openSelection("batch")}
              type="button"
            >
              <div className="flex items-start justify-between gap-6">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--color-accent)]">
                    Opcion 02
                  </p>
                  <h2 className="mt-4 text-3xl font-semibold tracking-[-0.05em]">
                    Subir un lote
                  </h2>
                  <p className="mt-4 max-w-xl text-sm leading-6 text-[var(--color-muted)]">
                    Selecciona varios .eml, asigna un nombre comun al lote y
                    analiza todos los correos con la misma configuracion.
                  </p>
                </div>
                <BatchMailIllustration />
              </div>
            </button>
          </div>
        </div>
      </div>

      <input
        ref={singleInputRef}
        accept=".eml"
        className="hidden"
        onChange={(event) =>
          handleFileSelection("single", Array.from(event.target.files ?? []))
        }
        suppressHydrationWarning
        type="file"
      />
      <input
        ref={batchInputRef}
        accept=".eml"
        className="hidden"
        multiple
        onChange={(event) =>
          handleFileSelection("batch", Array.from(event.target.files ?? []))
        }
        suppressHydrationWarning
        type="file"
      />

      {isModalOpen && uploadMode && modalStep && (
        <UploadFlowModal
          bodySubcriteria={bodySubcriteria}
          files={files}
          headerSubcriteria={headerSubcriteria}
          lastUpload={lastUpload}
          modalStep={modalStep}
          name={name}
          sourceConfirmed={sourceConfirmed}
          onBackFromFailure={() => {
            setSubmitError(null);
            setModalStep("subcriteria");
            setLastUpload(null);
            setTrackedJobId(null);
          }}
          onBackToDetails={() => {
            setSubmitError(null);
            setModalStep("details");
          }}
          onChangeFiles={() => openSelection(uploadMode)}
          onClearSelection={() => setSelectedKeys([])}
          onClose={closeModal}
          onContinueFromDetails={() => {
            if (!sourceConfirmed) {
              setSubmitError(
                "Debes confirmar que el .eml proviene de una fuente segura antes de continuar.",
              );
              return;
            }
            setSubmitError(null);
            setModalStep("subcriteria");
          }}
          onNameChange={setName}
          onSourceConfirmedChange={(value) => {
            setSourceConfirmed(value);
            if (value) {
              setSubmitError(null);
            }
          }}
          onSelectAll={() => setSelectedKeys((subcriteria ?? []).map((item) => item.key))}
          onSelectNonApiOnly={() => setSelectedKeys(nonApiSubcriterionKeys(subcriteria ?? []))}
          onStartAnalysis={() => void handleStartAnalysis()}
          onToggleKey={toggleKey}
          progressCurrent={progressCurrent}
          progressError={progressError}
          progressRatio={progressRatio}
          progressStatus={progressStatus}
          progressTotal={progressTotal}
          selectedBodyCount={selectedBodyCount}
          selectedHeaderCount={selectedHeaderCount}
          selectedKeys={selectedKeys}
          statusLabel={statusLabel}
          submitError={submitError}
          submitting={submitting}
          subcriteriaLoading={subcriteriaLoading}
          trackedJobId={trackedJobId}
          uploadMode={uploadMode}
        />
      )}
    </>
  );
}
