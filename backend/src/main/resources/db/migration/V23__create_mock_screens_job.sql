CREATE TABLE mock_screens_job (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    job_id VARCHAR(36) NOT NULL,
    project_id BIGINT NOT NULL,
    brd_id BIGINT NOT NULL,
    prompt LONGTEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    error_code VARCHAR(64),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uk_mock_screens_job_job_id UNIQUE (job_id),
    INDEX idx_mock_screens_job_project_brd (project_id, brd_id)
);