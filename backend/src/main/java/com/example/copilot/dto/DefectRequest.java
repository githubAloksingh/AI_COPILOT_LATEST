package com.example.copilot.dto;

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

    @com.fasterxml.jackson.annotation.JsonProperty("document_id")
    private String documentId;
}
