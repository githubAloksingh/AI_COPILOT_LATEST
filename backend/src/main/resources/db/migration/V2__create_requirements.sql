CREATE TABLE requirement (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    summary TEXT,
    user_story TEXT,
    acceptance_criteria JSON,
    assumptions JSON,
    dependencies JSON,
    edge_cases JSON,
    sources JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
