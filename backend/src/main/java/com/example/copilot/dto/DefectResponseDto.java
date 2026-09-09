package com.example.copilot.dto;

import lombok.Data;
import java.util.List;

@Data
public class DefectResponseDto {
    private List<DefectItemDto> defects;
    private String summary;
    private String probableRootCause;
    private String evidence;
    private String suggestedInvestigation;
    private String suggestedFix;
    private String confidence;
    private String severity;
    private String priority;
}
