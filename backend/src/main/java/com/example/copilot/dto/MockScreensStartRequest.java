package com.example.copilot.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class MockScreensStartRequest {
    private Long projectId;
    private Long brdId;
    private String prompt;
    private String idempotencyKey;

    public MockScreensStartRequest(Long projectId, Long brdId, String prompt) {
        this.projectId = projectId;
        this.brdId = brdId;
        this.prompt = prompt;
    }
}