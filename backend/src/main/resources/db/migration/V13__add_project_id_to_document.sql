ALTER TABLE document ADD COLUMN project_id BIGINT NULL;
ALTER TABLE document ADD COLUMN uploaded_by VARCHAR(255) DEFAULT 'System';
ALTER TABLE document ADD COLUMN version VARCHAR(20) DEFAULT 'v1';
ALTER TABLE document ADD CONSTRAINT fk_document_project FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE;
