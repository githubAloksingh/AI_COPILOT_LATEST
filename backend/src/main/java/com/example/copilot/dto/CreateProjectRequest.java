package com.example.copilot.dto;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class CreateProjectRequest {
    private String projectName;
    private String department;
    private String projectOwner;
    private String createdBy;
    private String status;
}
