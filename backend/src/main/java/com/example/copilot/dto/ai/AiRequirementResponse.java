package com.example.copilot.dto.ai;

import com.example.copilot.dto.RequirementResponseDto;
import lombok.Data;
import java.util.List;

@Data
public class AiRequirementResponse {
    private RequirementResponseDto result;
    private List<String> sources;
    private List<AiSourceDto> source_details;
    private String model;
    private String prompt_version;
    private long execution_time_ms;
}
