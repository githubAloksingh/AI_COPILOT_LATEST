-- V17: Add project/document linkage to all artifacts, chunk_count to document, and create document_chunk table

-- 1. Add chunk_count to document table
ALTER TABLE document ADD COLUMN chunk_count INT DEFAULT 0;

-- 2. Create document_chunk table for storing chunk text directly in MySQL
CREATE TABLE IF NOT EXISTS document_chunk (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    document_id BIGINT NOT NULL,
    chunk_index INT NOT NULL,
    chunk_text LONGTEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_chunk_document FOREIGN KEY (document_id) REFERENCES document(id) ON DELETE CASCADE
);

-- 3. Add project_id and document_id to requirement table
ALTER TABLE requirement ADD COLUMN project_id BIGINT NULL;
ALTER TABLE requirement ADD COLUMN document_id BIGINT NULL;
ALTER TABLE requirement ADD CONSTRAINT fk_requirement_project FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE SET NULL;
ALTER TABLE requirement ADD CONSTRAINT fk_requirement_document FOREIGN KEY (document_id) REFERENCES document(id) ON DELETE SET NULL;

-- 4. Add project_id and document_id to test_case table
ALTER TABLE test_case ADD COLUMN project_id BIGINT NULL;
ALTER TABLE test_case ADD COLUMN document_id BIGINT NULL;
ALTER TABLE test_case ADD CONSTRAINT fk_test_case_project FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE SET NULL;
ALTER TABLE test_case ADD CONSTRAINT fk_test_case_document FOREIGN KEY (document_id) REFERENCES document(id) ON DELETE SET NULL;

-- 5. Add project_id and document_id to defect table
ALTER TABLE defect ADD COLUMN project_id BIGINT NULL;
ALTER TABLE defect ADD COLUMN document_id BIGINT NULL;
ALTER TABLE defect ADD CONSTRAINT fk_defect_project FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE SET NULL;
ALTER TABLE defect ADD CONSTRAINT fk_defect_document FOREIGN KEY (document_id) REFERENCES document(id) ON DELETE SET NULL;

-- 6. Add project_id and document_id to release_note table
ALTER TABLE release_note ADD COLUMN project_id BIGINT NULL;
ALTER TABLE release_note ADD COLUMN document_id BIGINT NULL;
ALTER TABLE release_note ADD CONSTRAINT fk_release_note_project FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE SET NULL;
ALTER TABLE release_note ADD CONSTRAINT fk_release_note_document FOREIGN KEY (document_id) REFERENCES document(id) ON DELETE SET NULL;

-- 7. Add project_id and document_id to daily_status table
ALTER TABLE daily_status ADD COLUMN project_id BIGINT NULL;
ALTER TABLE daily_status ADD COLUMN document_id BIGINT NULL;
ALTER TABLE daily_status ADD CONSTRAINT fk_daily_status_project FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE SET NULL;
ALTER TABLE daily_status ADD CONSTRAINT fk_daily_status_document FOREIGN KEY (document_id) REFERENCES document(id) ON DELETE SET NULL;
