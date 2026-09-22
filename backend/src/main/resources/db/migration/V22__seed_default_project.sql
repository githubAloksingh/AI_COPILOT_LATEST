-- Seed default project in MySQL if not present
INSERT INTO project (id, project_name, department, project_owner, created_by, status)
SELECT 1, 'Core Banking & Payments', 'Engineering', 'System Admin', 'System', 'ACTIVE'
WHERE NOT EXISTS (SELECT 1 FROM project WHERE id = 1);

