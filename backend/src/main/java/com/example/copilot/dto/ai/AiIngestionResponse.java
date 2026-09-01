package com.example.copilot.dto.ai;

import lombok.Data;

@Data
public class AiIngestionResponse {
    private String status;
    private String document_id;
    private String file_name;
    private int chunk_count;
    private String message;
}
