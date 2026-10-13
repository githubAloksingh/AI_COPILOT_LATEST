package com.example.copilot.dto.ai;

import lombok.Data;

import java.util.List;

@Data
public class AiMockScreenPlanItem {
    private int sequence;
    private String screenName;
    private String purpose;
    private List<String> relevantRequirements;
}