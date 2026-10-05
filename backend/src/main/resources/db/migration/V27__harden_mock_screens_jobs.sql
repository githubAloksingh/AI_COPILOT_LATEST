ALTER TABLE mock_screens_job
    ADD COLUMN idempotency_key VARCHAR(128) NULL,
    ADD COLUMN lease_token VARCHAR(36) NULL,
    ADD COLUMN lease_until DATETIME(6) NULL,
    ADD CONSTRAINT uk_mock_screens_job_idempotency_key UNIQUE (idempotency_key),
    ADD INDEX idx_mock_screens_job_queue_status_created_id (status, created_at, id);

DELETE artifact
FROM mock_screens_pdf_artifact artifact
LEFT JOIN project ON project.id = artifact.project_id
LEFT JOIN document ON document.id = artifact.brd_id
LEFT JOIN mock_screens_job job ON job.id = artifact.mock_screens_job_id
WHERE project.id IS NULL OR document.id IS NULL OR job.id IS NULL
   OR job.project_id <> artifact.project_id OR job.brd_id <> artifact.brd_id;

DELETE job
FROM mock_screens_job job
LEFT JOIN project ON project.id = job.project_id
LEFT JOIN document ON document.id = job.brd_id
WHERE project.id IS NULL OR document.id IS NULL;

ALTER TABLE mock_screens_job
    ADD CONSTRAINT fk_mock_screens_job_project FOREIGN KEY (project_id)
        REFERENCES project (id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_mock_screens_job_brd FOREIGN KEY (brd_id)
        REFERENCES document (id) ON DELETE CASCADE;

ALTER TABLE mock_screens_pdf_artifact
    ADD CONSTRAINT fk_mock_screens_pdf_project FOREIGN KEY (project_id)
        REFERENCES project (id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_mock_screens_pdf_brd FOREIGN KEY (brd_id)
        REFERENCES document (id) ON DELETE CASCADE;