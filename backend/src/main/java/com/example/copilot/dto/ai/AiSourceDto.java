package com.example.copilot.dto.ai;

import lombok.Data;

@Data
public class AiSourceDto {
    private String document_id;
    private String file_name;
    private Integer chunk_index;
    private String snippet;
}
