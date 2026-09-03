package com.example.copilot.dto.accept;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.Data;
import java.util.List;

@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class RequirementItemRequest {
    /** AI-assigned ID e.g. REQ-001 */
    private String requirementId;
    private String title;
    private String summary;
    private String userStory;
    private String priority;

    /** Full grounded items: [{text, grounding, source[]}] */
    private List<Object> acceptanceCriteria;
    private List<Object> assumptions;
    private List<Object> dependencies;
    private List<Object> edgeCases;
}
