import type { BatchSummary, EmailSummary, Job } from "@/lib/types";

const ACTIVE_JOB_STATUSES = new Set(["queued", "running"]);

type JobCarrier = {
  job: Job | null;
  status: string;
};

export function hasActiveJob(job: Job | null | undefined): boolean {
  return job ? ACTIVE_JOB_STATUSES.has(job.status) : false;
}

export function hasActiveEmail(email: JobCarrier | null | undefined): boolean {
  return Boolean(
    email &&
      (hasActiveJob(email.job) ||
        email.status === "queued" ||
        email.status === "running"),
  );
}

export function hasActiveBatch(batch: JobCarrier | null | undefined): boolean {
  return Boolean(
    batch &&
      (hasActiveJob(batch.job) ||
        batch.status === "queued" ||
        batch.status === "running"),
  );
}

export function hasAnyActiveEmails(
  emails: EmailSummary[] | null | undefined,
): boolean {
  return (emails ?? []).some((email) => hasActiveEmail(email));
}

export function hasAnyActiveBatches(
  batches: BatchSummary[] | null | undefined,
): boolean {
  return (batches ?? []).some((batch) => hasActiveBatch(batch));
}
