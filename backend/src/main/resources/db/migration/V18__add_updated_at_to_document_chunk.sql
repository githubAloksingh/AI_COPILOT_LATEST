-- V18: Add missing updated_at column to document_chunk table
-- Required because DocumentChunk extends BaseEntity which maps both created_at and updated_at
ALTER TABLE document_chunk ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;
