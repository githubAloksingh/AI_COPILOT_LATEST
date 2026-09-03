package com.example.copilot.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import java.util.List;

@Data
public class TestCaseRequest {
    private String requirement;
    private String acceptanceCriteria;
    private List<String> testTypes; // POSITIVE, NEGATIVE, EDGE
    
    @JsonProperty("document_id")
    private String documentId;

    @JsonProperty("zip_document_id")
    private String zipDocumentId;
}
