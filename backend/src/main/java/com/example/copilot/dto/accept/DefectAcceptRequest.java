package com.example.copilot.dto.accept;

import lombok.Data;
import java.util.List;
import java.util.Map;

@Data
public class DefectAcceptRequest {
    private String title;
    private String description;
    private String logs;
    private String environment;
    private String stepsToReproduce;
    private String expectedBehavior;
    private String actualBehavior;
    private String severity;
    private String priority;
    private String probableRootCause;
    private String evidence;
    private String suggestedInvestigation;
    private String suggestedFix;
    private String confidence;
    private List<Map<String, Object>> relatedDefects;
    private List<String> sources;
    private String model;
    private String promptVersion;
    private Long executionTimeMs;
}
