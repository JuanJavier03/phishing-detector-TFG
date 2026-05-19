from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


def _updated_at(nullable: bool = False) -> Mapped[Optional[datetime]]:
    return mapped_column(DateTime(timezone=True), nullable=nullable, server_default=func.now())


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = _created_at()
    total_emails: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    emails: Mapped[list["Email"]] = relationship("Email", back_populates="batch", cascade="all, delete-orphan")
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="batch")


class Email(Base):
    __tablename__ = "emails"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(998), nullable=True)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    selected_subcriteria: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    processing_state: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'ready'"))
    processing_error_code: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    processing_error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processing_error_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = _created_at()

    batch: Mapped[Optional["Batch"]] = relationship("Batch", back_populates="emails")
    enrichment: Mapped[Optional["EmailEnrichment"]] = relationship(
        "EmailEnrichment",
        back_populates="email",
        cascade="all, delete-orphan",
        uselist=False,
    )
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="email")
    analysis_metrics: Mapped[list["EmailAnalysisMetric"]] = relationship("EmailAnalysisMetric", back_populates="email")


class EmailEnrichment(Base):
    __tablename__ = "email_enrichments"
    __table_args__ = (UniqueConstraint("email_id", name="uq_email_enrichments_email_id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emails.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at(nullable=False)
    mcdm_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mcdm_is_mock: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    mcdm_method: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    sub_spf: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_dkim: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_dmarc: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_domain_age: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_domain_reputation: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_ip_reputation: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_from_return_path_subdomain_match: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_sender_subdomain_count: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_sender_numeric_subdomain: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_received_hops_count: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_received_time_delta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_php_mailer_or_similar_header_indicator: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_domain_vs_ip_country: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_routing_domain_reputation: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_routing_ip_reputation: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_routing_domain_age: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_routing_country_mismatch: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_routing_subdomain_count: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_attachment_types: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_body_keywords: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_body_obfuscation_unicode: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_body_obfuscation_base64: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_link_count: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_html_tag_count: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_html_beacon_count: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_link_subdomain_count: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_link_numeric_subdomain: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_link_domain_reputation: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_link_domain_match_modal: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_link_domain_country_vs_modal: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_link_domain_age: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sub_link_captcha: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    email: Mapped["Email"] = relationship("Email", back_populates="enrichment")
    vector: Mapped[Optional["EmailMcdmVector"]] = relationship(
        "EmailMcdmVector",
        back_populates="enrichment",
        cascade="all, delete-orphan",
        uselist=False,
    )


class EmailMcdmVector(Base):
    __tablename__ = "email_mcdm_vectors"
    __table_args__ = (UniqueConstraint("enrichment_id", name="uq_email_mcdm_vectors_enrichment_id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    enrichment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("email_enrichments.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at(nullable=False)
    vector_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("5"))

    c1_spf: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    c1_dkim: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    c1_dmarc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    c1_php_mailer_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    c1_ip_reputation: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c1_domain_reputation: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c1_domain_vs_ip_country_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    c1_domain_age_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c1_sender_subdomain_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c1_sender_numeric_subdomain_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c1_from_return_path_mismatch: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c1_received_hops_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c1_routing_domain_reputation: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c1_routing_ip_reputation: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c1_routing_domain_age_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c1_routing_country_mismatch: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    c1_routing_subdomain_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c1_received_time_delta_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c2_body_keywords_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c2_obfuscation_base64_present: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c2_obfuscation_unicode_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c2_link_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c2_link_domain_reputation: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c2_link_domain_country_vs_modal_mismatch: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    c2_link_domain_age_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c2_link_subdomain_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c2_link_numeric_subdomain_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c2_link_domain_match_modal_mismatch: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c2_attachment_suspicious_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c2_html_tag_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c2_link_captcha_present: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    c2_html_beacon_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    enrichment: Mapped["EmailEnrichment"] = relationship("EmailEnrichment", back_populates="vector")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    email_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emails.id", ondelete="SET NULL"),
        nullable=True,
    )
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    selected_subcriteria: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'queued'"))
    progress_current: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    progress_total: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    queue_name: Mapped[str] = mapped_column(String(64), nullable=False, server_default=text("'default'"))
    queue_priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("100"))
    queue_available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    queue_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    queue_max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("3"))
    queue_worker_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    queue_lease_token: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    queue_lease_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = _created_at()
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    email: Mapped[Optional["Email"]] = relationship("Email", back_populates="jobs")
    batch: Mapped[Optional["Batch"]] = relationship("Batch", back_populates="jobs")
    analysis_metrics: Mapped[list["EmailAnalysisMetric"]] = relationship("EmailAnalysisMetric", back_populates="job")
    mcdm_runtime_metrics: Mapped[list["McdmRuntimeMetric"]] = relationship("McdmRuntimeMetric", back_populates="job")


class EmailAnalysisMetric(Base):
    __tablename__ = "email_analysis_metrics"

    id: Mapped[uuid.UUID] = _uuid_pk()
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emails.id", ondelete="CASCADE"),
        nullable=False,
    )
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    selected_subcriteria: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    subcriteria_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    api_call_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    api_endpoints: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = _created_at()

    email: Mapped["Email"] = relationship("Email", back_populates="analysis_metrics")
    job: Mapped[Optional["Job"]] = relationship("Job", back_populates="analysis_metrics")
    api_calls: Mapped[list["ApiCallMetric"]] = relationship(
        "ApiCallMetric",
        back_populates="analysis_metric",
        cascade="all, delete-orphan",
    )


class ApiCallMetric(Base):
    __tablename__ = "api_call_metrics"

    id: Mapped[uuid.UUID] = _uuid_pk()
    analysis_metric_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("email_analysis_metrics.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emails.id", ondelete="CASCADE"),
        nullable=False,
    )
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(512), nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    success: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = _created_at()

    analysis_metric: Mapped["EmailAnalysisMetric"] = relationship("EmailAnalysisMetric", back_populates="api_calls")


class McdmRuntimeMetric(Base):
    __tablename__ = "mcdm_runtime_metrics"

    id: Mapped[uuid.UUID] = _uuid_pk()
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    email_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    duration_per_email_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = _created_at()

    job: Mapped[Optional["Job"]] = relationship("Job", back_populates="mcdm_runtime_metrics")


class NeutrinoApiCache(Base):
    __tablename__ = "neutrino_api_cache"

    cache_key: Mapped[str] = mapped_column(Text, primary_key=True)
    endpoint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    response: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


__all__ = [
    "Batch",
    "Email",
    "EmailEnrichment",
    "EmailMcdmVector",
    "EmailAnalysisMetric",
    "ApiCallMetric",
    "McdmRuntimeMetric",
    "Job",
    "NeutrinoApiCache",
]
