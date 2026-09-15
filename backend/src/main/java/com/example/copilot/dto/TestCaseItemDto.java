package com.example.copilot.dto;

import lombok.Data;
import java.util.List;

@Data
public class TestCaseItemDto {
    private String scenario;
    private List<String> preconditions;
    private List<String> steps;
    private String expectedResult;
}
