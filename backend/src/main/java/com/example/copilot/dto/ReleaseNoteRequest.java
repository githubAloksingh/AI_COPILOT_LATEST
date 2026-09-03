package com.example.copilot.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
public class ReleaseNoteRequest {
    private String version;
    private String sprintInformation;
    
    @JsonProperty("document_id")
    private String documentId;
}
