-- V19: Add project_id and document_id to audit_log table for project and document-specific history queries
ALTER TABLE audit_log ADD COLUMN project_id BIGINT NULL;
ALTER TABLE audit_log ADD COLUMN document_id BIGINT NULL;

-- Add index for fast querying by project and feature
CREATE INDEX idx_audit_log_project_feature ON audit_log (project_id, feature);
