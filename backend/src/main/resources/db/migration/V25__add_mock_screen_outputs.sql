ALTER TABLE mock_screens_job ADD COLUMN failed_sequence INT NULL;

CREATE TABLE mock_screens_screen_output (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    mock_screens_job_id BIGINT NOT NULL,
    sequence_number INT NOT NULL,
    screen_name VARCHAR(200) NOT NULL,
    purpose TEXT NOT NULL,
    specification_json LONGTEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uk_mock_screens_output_job_sequence UNIQUE (mock_screens_job_id, sequence_number),
    CONSTRAINT fk_mock_screens_output_job FOREIGN KEY (mock_screens_job_id)
        REFERENCES mock_screens_job (id) ON DELETE CASCADE
);