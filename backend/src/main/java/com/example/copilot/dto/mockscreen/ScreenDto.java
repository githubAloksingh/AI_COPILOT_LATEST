package com.example.copilot.dto.mockscreen;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ScreenDto {
    private Long id;
    private Integer sequence;
    private String name;
    private String screenType;
    private String purpose;
    private String userRole;
    private String workflowState;
    private String status;
    private String imageUrl;
    private String errorMessage;
    private String specificationJson;
}
