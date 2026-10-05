ALTER TABLE mock_screens_job ADD COLUMN pdf_artifact_id BIGINT NULL;

CREATE TABLE mock_screens_pdf_artifact (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    mock_screens_job_id BIGINT NOT NULL,
    job_id VARCHAR(36) NOT NULL,
    project_id BIGINT NOT NULL,
    brd_id BIGINT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    size_bytes BIGINT NOT NULL,
    pdf_data LONGBLOB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uk_mock_screens_pdf_job UNIQUE (mock_screens_job_id),
    CONSTRAINT fk_mock_screens_pdf_job FOREIGN KEY (mock_screens_job_id)
        REFERENCES mock_screens_job (id) ON DELETE CASCADE,
    INDEX idx_mock_screens_pdf_project_brd (project_id, brd_id)
);