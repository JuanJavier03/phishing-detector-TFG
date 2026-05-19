import type {
  BatchDetail,
  BatchChartsOverview,
  BatchSubcriterionAnalytics,
  BatchSummary,
  EmailDetail,
  EmailSubcriterionDetail,
  EmailSummary,
  Job,
  MergeBatchesResponse,
  SubcriterionDefinition,
  UploadResponse,
} from "@/lib/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

const BATCH_UPLOAD_CHUNK_SIZE = 50;

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
  });

  await ensureOk(response);
  return (await response.json()) as T;
}

async function ensureOk(response: Response): Promise<void> {
  if (response.ok) {
    return;
  }

  let message = `Error ${response.status}`;
  try {
    const errorPayload = (await response.json()) as { detail?: string };
    if (errorPayload?.detail) {
      message = errorPayload.detail;
    }
  } catch {
    const text = await response.text();
    if (text) {
      message = text;
    }
  }
  throw new Error(message);
}

function extractFilename(contentDisposition: string | null): string | null {
  if (!contentDisposition) {
    return null;
  }

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1]);
  }

  const basicMatch = contentDisposition.match(/filename=\"?([^\";]+)\"?/i);
  return basicMatch?.[1] ?? null;
}

export function fetchSubcriteria(): Promise<SubcriterionDefinition[]> {
  return apiFetch<SubcriterionDefinition[]>("/metadata/subcriteria");
}

export function fetchEmails(limit = 20, offset = 0): Promise<EmailSummary[]> {
  return apiFetch<EmailSummary[]>(`/emails?limit=${limit}&offset=${offset}`);
}

export function fetchEmail(emailId: string): Promise<EmailDetail> {
  return apiFetch<EmailDetail>(`/emails/${emailId}`);
}

export function deleteEmail(
  emailId: string,
): Promise<{ email_id: string; batch_id: string | null }> {
  return apiFetch<{ email_id: string; batch_id: string | null }>(
    `/emails/${emailId}`,
    {
      method: "DELETE",
    },
  );
}

export function fetchEmailSubcriterion(
  emailId: string,
  subcriterionKey: string,
): Promise<EmailSubcriterionDetail> {
  return apiFetch<EmailSubcriterionDetail>(
    `/emails/${emailId}/subcriteria/${subcriterionKey}`,
  );
}

export function analyzeEmailSubcriterion(
  emailId: string,
  subcriterionKey: string,
): Promise<{ email_id: string; job_id: string; subcriterion_key: string }> {
  return apiFetch(`/emails/${emailId}/subcriteria/${subcriterionKey}/analyze`, {
    method: "POST",
  });
}

export function analyzeMissingEmailSubcriteria(
  emailId: string,
): Promise<{ email_id: string; job_id: string; selected_subcriteria: string[] }> {
  return apiFetch(`/emails/${emailId}/subcriteria/analyze-missing`, {
    method: "POST",
  });
}

export function retryEmail(
  emailId: string,
): Promise<{ email_id: string; job_id: string; selected_subcriteria: string[] }> {
  return apiFetch(`/emails/${emailId}/retry`, {
    method: "POST",
  });
}

export function fetchBatches(limit = 20, offset = 0): Promise<BatchSummary[]> {
  return apiFetch<BatchSummary[]>(`/batches?limit=${limit}&offset=${offset}`);
}

export function fetchBatch(
  batchId: string,
  emailLimit = 20,
  emailOffset = 0,
): Promise<BatchDetail> {
  return apiFetch<BatchDetail>(
    `/batches/${batchId}?email_limit=${emailLimit}&email_offset=${emailOffset}`,
  );
}

export function fetchBatchCharts(batchId: string): Promise<BatchChartsOverview> {
  return apiFetch<BatchChartsOverview>(`/batches/${batchId}/charts`);
}

export function deleteBatch(
  batchId: string,
): Promise<{ batch_id: string; emails_deleted: number }> {
  return apiFetch<{ batch_id: string; emails_deleted: number }>(
    `/batches/${batchId}`,
    {
      method: "DELETE",
    },
  );
}

export function mergeBatches(input: {
  name: string;
  batchIds: string[];
}): Promise<MergeBatchesResponse> {
  return apiFetch<MergeBatchesResponse>("/batches/merge", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name: input.name,
      batch_ids: input.batchIds,
    }),
  });
}

export function analyzeMissingBatchSubcriteria(
  batchId: string,
): Promise<{ batch_id: string; job_id: string; selected_subcriteria: string[] }> {
  return apiFetch(`/batches/${batchId}/subcriteria/analyze-missing`, {
    method: "POST",
  });
}

export function retryCancelledBatch(
  batchId: string,
): Promise<{ batch_id: string; job_id: string; emails_total: number }> {
  return apiFetch(`/batches/${batchId}/retry-cancelled`, {
    method: "POST",
  });
}

export function recalculateBatchMcdm(
  batchId: string,
): Promise<{ batch_id: string; job_id: string; emails_total: number }> {
  return apiFetch(`/batches/${batchId}/mcdm/recalculate`, {
    method: "POST",
  });
}

export function fetchBatchSubcriterion(
  batchId: string,
  subcriterionKey: string,
): Promise<BatchSubcriterionAnalytics> {
  return apiFetch<BatchSubcriterionAnalytics>(
    `/batches/${batchId}/subcriteria/${subcriterionKey}`,
  );
}

export async function downloadBatchMcdmExport(batchId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/batches/${batchId}/export/mcdm`);
  await ensureOk(response);

  const blob = await response.blob();
  const filename =
    extractFilename(response.headers.get("Content-Disposition")) ??
    `batch-${batchId}-mcdm-export.xlsx`;

  const downloadUrl = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = downloadUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(downloadUrl);
}

export function fetchJob(jobId: string): Promise<Job> {
  return apiFetch<Job>(`/jobs/${jobId}`);
}

export async function uploadSingleEmail(input: {
  file: File;
  name: string;
  selectedSubcriteria: string[];
}): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", input.file);
  formData.append("name", input.name);
  formData.append(
    "selected_subcriteria",
    JSON.stringify(input.selectedSubcriteria),
  );

  return apiFetch<UploadResponse>("/uploads/email", {
    method: "POST",
    body: formData,
  });
}

async function uploadBatchChunk(input: {
  batchId: string;
  files: File[];
  startIndex: number;
  totalFiles: number;
}): Promise<void> {
  const chunkFormData = new FormData();
  chunkFormData.append("expected_start_index", String(input.startIndex));
  for (const file of input.files) {
    chunkFormData.append("files", file);
  }
  try {
    await apiFetch<{
      type: "batch_upload_chunk";
      batch_id: string;
      uploaded_emails: number;
      email_ids: string[];
    }>(`/uploads/batch/${input.batchId}/chunk`, {
      method: "POST",
      body: chunkFormData,
    });
  } catch (error) {
    if (input.files.length > 1) {
      const midpoint = Math.ceil(input.files.length / 2);
      await uploadBatchChunk({
        batchId: input.batchId,
        files: input.files.slice(0, midpoint),
        startIndex: input.startIndex,
        totalFiles: input.totalFiles,
      });
      await uploadBatchChunk({
        batchId: input.batchId,
        files: input.files.slice(midpoint),
        startIndex: input.startIndex + midpoint,
        totalFiles: input.totalFiles,
      });
      return;
    }

    const file = input.files[0];
    const message = error instanceof Error ? error.message : "Error desconocido";
    throw new Error(
      `Fallo subiendo archivo ${input.startIndex}/${input.totalFiles} (${file.name}): ${message}`,
    );
  }
}

export async function uploadBatch(input: {
  files: File[];
  name: string;
  selectedSubcriteria: string[];
}): Promise<UploadResponse> {
  const startFormData = new FormData();
  startFormData.append("name", input.name);
  const start = await apiFetch<{
    type: "batch_upload";
    batch_id: string;
    uploaded_emails: number;
  }>("/uploads/batch/start", {
    method: "POST",
    body: startFormData,
  });

  for (let index = 0; index < input.files.length; index += BATCH_UPLOAD_CHUNK_SIZE) {
    const chunk = input.files.slice(index, index + BATCH_UPLOAD_CHUNK_SIZE);
    try {
      await uploadBatchChunk({
        batchId: start.batch_id,
        files: chunk,
        startIndex: index + 1,
        totalFiles: input.files.length,
      });
    } catch (error) {
      const first = index + 1;
      const last = Math.min(index + chunk.length, input.files.length);
      const message = error instanceof Error ? error.message : "Error desconocido";
      throw new Error(`Fallo subiendo archivos ${first}-${last}: ${message}`);
    }
  }

  const finalizeFormData = new FormData();
  finalizeFormData.append(
    "selected_subcriteria",
    JSON.stringify(input.selectedSubcriteria),
  );

  return apiFetch<UploadResponse>(`/uploads/batch/${start.batch_id}/finalize`, {
    method: "POST",
    body: finalizeFormData,
  });
}
