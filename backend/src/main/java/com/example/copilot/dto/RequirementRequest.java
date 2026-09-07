package com.example.copilot.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
public class RequirementRequest {
    private String title;
    private String description;

    @JsonProperty("document_id")
    private String documentId;

    private Long projectId;
    private String projectName;
    private String documentName;
    private String documentVersion;
    private String inputType;
}
