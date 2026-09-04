package com.example.copilot.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Data
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class RequirementResponseDto {
    private List<RequirementItemDto> requirements = new ArrayList<>();
    private List<Map<String, Object>> userStories = new ArrayList<>();
    private Map<String, Object> functionalDesign;
    private Map<String, Object> technicalDesign;

    // Backward compatibility fields
    private String summary;
    private String userStory;
    private List<Object> acceptanceCriteria;
    private List<Object> assumptions;
    private List<Object> dependencies;
    private List<Object> edgeCases;
}
