-- Seed standard test users in MySQL if not present
INSERT INTO users (username, email, password_hash, role, status)
SELECT 'admin', 'admin@example.com', '$2a$10$7Z7Wk2a5M1bW5.7YJgYVeeh9.2o6bM9gZ5Z0Z6.7YJgYVeeh9.2o6', 'ADMIN', 'ACTIVE'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'admin');

INSERT INTO users (username, email, password_hash, role, status)
SELECT 'user1', 'user1@example.com', '$2a$10$7Z7Wk2a5M1bW5.7YJgYVeeh9.2o6bM9gZ5Z0Z6.7YJgYVeeh9.2o6', 'USER', 'ACTIVE'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'user1');

INSERT INTO users (username, email, password_hash, role, status)
SELECT 'user2', 'user2@example.com', '$2a$10$7Z7Wk2a5M1bW5.7YJgYVeeh9.2o6bM9gZ5Z0Z6.7YJgYVeeh9.2o6', 'USER', 'ACTIVE'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'user2');

INSERT INTO users (username, email, password_hash, role, status)
SELECT 'user3', 'user3@example.com', '$2a$10$7Z7Wk2a5M1bW5.7YJgYVeeh9.2o6bM9gZ5Z0Z6.7YJgYVeeh9.2o6', 'USER', 'ACTIVE'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'user3');

INSERT INTO users (username, email, password_hash, role, status)
SELECT 'inactive_user', 'inactive@example.com', '$2a$10$7Z7Wk2a5M1bW5.7YJgYVeeh9.2o6bM9gZ5Z0Z6.7YJgYVeeh9.2o6', 'USER', 'INACTIVE'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'inactive_user');
