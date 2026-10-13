ALTER TABLE mock_screens_job ADD COLUMN idempotency_key VARCHAR(128) NULL;
ALTER TABLE mock_screens_job ADD COLUMN lease_token VARCHAR(36) NULL;
ALTER TABLE mock_screens_job ADD COLUMN lease_until DATETIME(6) NULL;
ALTER TABLE mock_screens_job
    ADD CONSTRAINT uk_mock_screens_job_idempotency_key UNIQUE (idempotency_key);
CREATE INDEX idx_mock_screens_job_queue_status_created_id
    ON mock_screens_job (status, created_at, id);

DELETE FROM mock_screens_pdf_artifact
WHERE NOT EXISTS (
    SELECT 1 FROM project
    WHERE project.id = mock_screens_pdf_artifact.project_id
)
   OR NOT EXISTS (
    SELECT 1 FROM document
    WHERE document.id = mock_screens_pdf_artifact.brd_id
)
   OR NOT EXISTS (
    SELECT 1 FROM mock_screens_job
    WHERE mock_screens_job.id = mock_screens_pdf_artifact.mock_screens_job_id
      AND mock_screens_job.project_id = mock_screens_pdf_artifact.project_id
      AND mock_screens_job.brd_id = mock_screens_pdf_artifact.brd_id
);

DELETE FROM mock_screens_job
WHERE NOT EXISTS (
    SELECT 1 FROM project
    WHERE project.id = mock_screens_job.project_id
)
   OR NOT EXISTS (
    SELECT 1 FROM document
    WHERE document.id = mock_screens_job.brd_id
);

ALTER TABLE mock_screens_job
    ADD CONSTRAINT fk_mock_screens_job_project FOREIGN KEY (project_id)
        REFERENCES project (id) ON DELETE CASCADE;
ALTER TABLE mock_screens_job
    ADD CONSTRAINT fk_mock_screens_job_brd FOREIGN KEY (brd_id)
        REFERENCES document (id) ON DELETE CASCADE;

ALTER TABLE mock_screens_pdf_artifact
    ADD CONSTRAINT fk_mock_screens_pdf_project FOREIGN KEY (project_id)
        REFERENCES project (id) ON DELETE CASCADE;
ALTER TABLE mock_screens_pdf_artifact
    ADD CONSTRAINT fk_mock_screens_pdf_brd FOREIGN KEY (brd_id)
        REFERENCES document (id) ON DELETE CASCADE;