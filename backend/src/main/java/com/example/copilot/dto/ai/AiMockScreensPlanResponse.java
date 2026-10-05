package com.example.copilot.dto.ai;

import lombok.Data;

import java.util.List;

@Data
public class AiMockScreensPlanResponse {
    private List<AiMockScreenPlanItem> screens;
    private String model;
    private String prompt_version;
    private long execution_time_ms;
}