package com.example.copilot.dto.ai;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.Data;

import java.util.List;

@Data
@JsonInclude(JsonInclude.Include.NON_NULL)
public class AiMockScreenSpecification {
    private int sequence;
    private String screenName;
    private String purpose;
    private String layoutDescription;
    private List<AiMockScreenComponent> components;
    private List<String> interactionNotes;
}