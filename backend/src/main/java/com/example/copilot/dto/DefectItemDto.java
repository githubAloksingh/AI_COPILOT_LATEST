package com.example.copilot.dto;

import lombok.Data;

@Data
public class DefectItemDto {
    private String defectId;
    private String title;
    private String status;
    private String component;
    private String location;
    private String trigger;
    private String rootCause;
    private String impact;
    private String evidence;
    private String investigation;
    private String fix;
    private String confidence;
    private String severity;
    private String priority;
}