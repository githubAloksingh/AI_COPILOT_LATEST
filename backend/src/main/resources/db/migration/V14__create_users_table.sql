CREATE TABLE IF NOT EXISTS users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'USER',
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Insert default admin and standard user accounts if not present
INSERT INTO users (username, email, password_hash, role, status)
SELECT 'admin', 'admin@newgen.com', '$2a$10$7Z7Wk2a5M1bW5.7YJgYVeeh9.2o6bM9gZ5Z0Z6.7YJgYVeeh9.2o6', 'ADMIN', 'ACTIVE'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'admin');

INSERT INTO users (username, email, password_hash, role, status)
SELECT 'userA', 'usera@newgen.com', '$2a$10$7Z7Wk2a5M1bW5.7YJgYVeeh9.2o6bM9gZ5Z0Z6.7YJgYVeeh9.2o6', 'USER', 'ACTIVE'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'userA');

INSERT INTO users (username, email, password_hash, role, status)
SELECT 'userB', 'userb@newgen.com', '$2a$10$7Z7Wk2a5M1bW5.7YJgYVeeh9.2o6bM9gZ5Z0Z6.7YJgYVeeh9.2o6', 'USER', 'ACTIVE'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'userB');

INSERT INTO users (username, email, password_hash, role, status)
SELECT 'userC', 'userc@newgen.com', '$2a$10$7Z7Wk2a5M1bW5.7YJgYVeeh9.2o6bM9gZ5Z0Z6.7YJgYVeeh9.2o6', 'USER', 'ACTIVE'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'userC');
