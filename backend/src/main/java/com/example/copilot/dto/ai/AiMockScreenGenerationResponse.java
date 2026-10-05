package com.example.copilot.dto.ai;

import lombok.Data;

@Data
public class AiMockScreenGenerationResponse {
    private AiMockScreenSpecification screen;
    private String model;
    private String prompt_version;
    private long execution_time_ms;
}