package com.example.copilot.dto.ai;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.Data;

import java.util.List;

@Data
@JsonInclude(JsonInclude.Include.NON_NULL)
public class AiMockScreenComponent {
    private String componentType;
    private String label;
    private String description;
    private boolean required;
    private List<String> options;
}