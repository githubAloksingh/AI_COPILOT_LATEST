-- V20: Add file_data LONGBLOB column to document table for storing original uploaded PDF binary in MySQL
ALTER TABLE document ADD COLUMN file_data LONGBLOB NULL;
