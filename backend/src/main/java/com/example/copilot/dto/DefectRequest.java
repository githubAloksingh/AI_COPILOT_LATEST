package com.example.copilot.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
public class DefectRequest {
    private String title;
    private String description;
    private String logs;
    private String environment;
    private String stepsToReproduce;
    private String expectedBehavior;
    private String actualBehavior;

    @JsonProperty("document_id")
    private String documentId;

    private Long projectId;
    private String projectName;
    private String documentName;
    private String documentVersion;
    private String inputType;
}
