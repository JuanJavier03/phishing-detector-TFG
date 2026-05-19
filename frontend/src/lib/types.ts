export type JobStatus = "queued" | "running" | "completed" | "failed";

export type ProcessingError = {
  state?: string | null;
  code: string | null;
  message: string | null;
  at: string | null;
};

export type Job = {
  id: string;
  job_type: string;
  target_type: string;
  target_id: string | null;
  email_id: string | null;
  batch_id: string | null;
  selected_subcriteria: string[];
  status: JobStatus;
  progress_current: number;
  progress_total: number;
  error_message: string | null;
  created_at: string | null;
  started_at: string | null;
  finished_at: string | null;
};

export type BatchReference = {
  id: string;
  name: string;
};

export type EmailSummary = {
  id: string;
  name: string;
  subject: string | null;
  created_at: string;
  batch: BatchReference | null;
  selected_subcriteria: string[];
  status: string;
  mcdm_score: number | null;
  mcdm_is_mock: boolean;
  mcdm_method: string | null;
  processing_error: ProcessingError | null;
  job: Job | null;
};

export type EmailDetail = EmailSummary & {
  metadata: Record<string, unknown>;
  headers_summary: Record<string, string | null>;
  missing_subcriteria: string[];
  vector: {
    version: number | null;
    by_key: Record<string, number | null>;
  };
  subcriteria: Array<{
    key: string;
    label: string;
    family: string;
    vector_field: string;
    value_type: "int" | "float";
    mcdm_objective: "maximize" | "minimize";
    mcdm_weight: number;
    measurement: string;
    value: number | null;
    mcdm_score: number | null;
    updated_at: string | null;
    has_result: boolean;
    selected: boolean;
    status: "completed" | "not_analyzed" | "available" | "error" | "cancelled";
  }>;
};

export type EmailSubcriterionDetail = {
  email_id: string;
  subcriterion: {
    key: string;
    label: string;
    family: string;
    vector_field: string;
    value_type: "int" | "float";
    mcdm_objective: "maximize" | "minimize";
    mcdm_weight: number;
    measurement: string;
  };
  status: "completed" | "not_analyzed" | "available" | "error" | "cancelled";
  value: number | null;
  result: Record<string, unknown> | null;
};

export type BatchSummary = {
  id: string;
  name: string;
  created_at: string;
  total_emails: number;
  processable_emails: number;
  discarded_emails: number;
  completed_emails: number;
  mcdm_score: number | null;
  status: string;
  job: Job | null;
};

export type MergeBatchesResponse = {
  batch_id: string;
  email_ids: string[];
  total_emails: number;
  deduplicated_emails: number;
};

export type BatchDetail = BatchSummary & {
  selected_subcriteria: string[];
  missing_subcriteria: string[];
  emails: EmailSummary[];
  subcriteria: Array<{
    key: string;
    label: string;
    family: string;
    vector_field: string;
    value_type: "int" | "float";
    mcdm_objective: "maximize" | "minimize";
    mcdm_weight: number;
    measurement: string;
  }>;
};

export type BatchSubcriterionAnalytics = {
  batch_id: string;
  batch_name: string;
  subcriterion: {
    key: string;
    label: string;
    family: string;
    vector_field: string;
    value_type: "int" | "float";
    mcdm_objective: "maximize" | "minimize";
    mcdm_weight: number;
    measurement: string;
  };
  series: Array<{
    metric_key: string;
    metric_label: string;
    emails_total: number;
    emails_with_value: number;
    emails_without_value: number;
    distribution: Array<{
      label: string;
      count: number;
    }>;
  }>;
};

export type BatchChartType =
  | "histogram"
  | "donut"
  | "pie"
  | "bubble_lane"
  | "pyramid"
  | "stacked_bar"
  | "box_plot"
  | "waffle"
  | "band_bars";

export type BatchScoreBin = {
  label: string;
  start: number;
  end: number;
  center: number;
  count: number;
  ratio: number;
};

export type BatchScoreSegment = {
  label: string;
  value: number;
  count: number;
  ratio: number;
};

export type BatchScoreStats = {
  min: number;
  q1: number;
  median: number;
  mean: number;
  q3: number;
  max: number;
};

export type BatchScoreAnalyticsItem = {
  subcriterion: {
    key: string;
    label: string;
    family: string;
    vector_field: string;
    value_type: "int" | "float";
    mcdm_objective: "maximize" | "minimize";
    mcdm_weight: number;
    measurement: string;
  };
  chart_type: BatchChartType;
  value_source: string;
  emails_total: number;
  emails_with_value: number;
  emails_without_value: number;
  coverage_ratio: number;
  value_stats: BatchScoreStats | null;
  bins: BatchScoreBin[];
  segments: BatchScoreSegment[];
  points: BatchScoreSegment[];
};

export type BatchChartsOverview = {
  batch_id: string;
  batch_name: string;
  items: BatchScoreAnalyticsItem[];
};

export type SubcriterionDefinition = {
  key: string;
  label: string;
  family: string;
  enrichment_column: string;
  vector_field: string;
  vector_fields: string[];
  value_type: "int" | "float";
  mcdm_objective: "maximize" | "minimize";
  mcdm_weight: number;
  measurement: string;
  uses_api: boolean;
};

export type UploadResponse =
  | {
      type: "email";
      email_id: string;
      job_id: string;
    }
  | {
      type: "batch";
      batch_id: string;
      job_id: string;
      email_ids: string[];
    };
