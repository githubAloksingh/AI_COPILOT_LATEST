package com.example.copilot.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
public class RequirementRequest {
    private String title;
    private String description;
    private String priority;
    
    @JsonProperty("document_id")
    private String documentId;
}
