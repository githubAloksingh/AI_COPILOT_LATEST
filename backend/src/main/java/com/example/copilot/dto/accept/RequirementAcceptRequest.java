package com.example.copilot.dto.accept;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.Data;
import java.util.List;

@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class RequirementAcceptRequest {
    private String title;
    private String description;
    private String priority;
    private String summary;
    private String userStory;
    private List<Object> acceptanceCriteria;
    private List<Object> assumptions;
    private List<Object> dependencies;
    private List<Object> edgeCases;
    private List<String> sources;
    private String model;
    private String promptVersion;
    private Long executionTimeMs;
}
