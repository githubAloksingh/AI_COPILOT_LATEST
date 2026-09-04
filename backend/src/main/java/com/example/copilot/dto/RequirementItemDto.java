package com.example.copilot.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class RequirementItemDto {
    private String requirementId;
    private String userStoryId;
    private String title;
    private String summary;
    private String userStory;
    private String description;
    private List<Object> acceptanceCriteria = new ArrayList<>();
    private List<Object> businessRules = new ArrayList<>();
    private List<Object> assumptions = new ArrayList<>();
    private List<Object> dependencies = new ArrayList<>();
    private List<Object> edgeCases = new ArrayList<>();
    private List<String> sources = new ArrayList<>();
}
