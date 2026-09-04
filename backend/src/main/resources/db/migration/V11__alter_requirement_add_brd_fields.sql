-- V11: Add BRD tracking columns and metadata to requirement table
ALTER TABLE requirement ADD COLUMN brd_name VARCHAR(255) NULL;
ALTER TABLE requirement ADD COLUMN requirement_id VARCHAR(50) NULL;
ALTER TABLE requirement ADD COLUMN model VARCHAR(100) NULL;
ALTER TABLE requirement ADD COLUMN prompt_version VARCHAR(50) NULL;
ALTER TABLE requirement MODIFY COLUMN title VARCHAR(255) NULL;
ALTER TABLE requirement MODIFY COLUMN description TEXT NULL;
