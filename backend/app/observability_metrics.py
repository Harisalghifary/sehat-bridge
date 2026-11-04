"""Domain metrics shared by routers and services."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

AUTH_LOGIN_TOTAL = Counter("auth_login_total", "Login attempts", ["result"])
TENANT_PROVISION_DURATION = Histogram(
    "tenant_provision_duration_seconds",
    "Tenant provisioning duration",
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 60),
)
TENANT_PROVISION_FAILURES = Counter(
    "tenant_provision_failures_total", "Tenant provisioning failures"
)
FILE_UPLOAD_BYTES_TOTAL = Counter("file_upload_bytes_total", "Completed upload bytes", ["tenant"])
FILE_QUOTA_REJECTIONS_TOTAL = Counter(
    "file_quota_rejections_total", "Upload reservations rejected by quota"
)
DB_POOL_IN_USE = Gauge("db_pool_in_use", "Checked-out database connections")

TENANT_LABEL_CARDINALITY = 20
_known_tenants: list[str] = []


def tenant_label(slug: str | None) -> str:
    """Cap tenant label cardinality at the first N distinct slugs plus ``other``."""
    if not slug:
        return "other"
    if slug in _known_tenants:
        return slug
    if len(_known_tenants) < TENANT_LABEL_CARDINALITY:
        _known_tenants.append(slug)
        return slug
    return "other"
