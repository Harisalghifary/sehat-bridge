-- 0003_outbox_active_index — allow repeated failures in job history.
-- Replaces the original UNIQUE(kind, local_id, status), which allowed only one
-- failed row per resource and broke a second retry. Active jobs stay unique.

ALTER TABLE sync_jobs DROP CONSTRAINT IF EXISTS sync_jobs_kind_local_status_key;

CREATE UNIQUE INDEX IF NOT EXISTS sync_jobs_active_key
    ON sync_jobs (kind, local_id)
    WHERE status IN ('queued', 'running');