-- V11: Add BRD tracking columns and metadata to requirement table
-- brd_name: which BRD document this requirement was generated from
-- requirement_id: AI-assigned ID e.g. REQ-001
-- model: AI model used e.g. gemini-3.7-flash
-- prompt_version: prompt version e.g. requirement-v2

ALTER TABLE requirement
    ADD COLUMN brd_name       VARCHAR(255) NULL COMMENT 'BRD document name the requirement was generated from',
    ADD COLUMN requirement_id VARCHAR(50)  NULL COMMENT 'AI-assigned requirement identifier e.g. REQ-001',
    ADD COLUMN model          VARCHAR(100) NULL COMMENT 'AI model used for generation',
    ADD COLUMN prompt_version VARCHAR(50)  NULL COMMENT 'Prompt version used e.g. requirement-v2',
    MODIFY COLUMN title       VARCHAR(255) NULL,
    MODIFY COLUMN description TEXT         NULL;
