package com.example.copilot.dto.accept;

import com.example.copilot.dto.TestCaseItemDto;
import lombok.Data;
import java.util.List;

@Data
public class TestCaseAcceptRequest {
    private String requirement;
    private Long requirementId;
    private List<TestCaseItemDto> testCases;
    private List<String> sources;
    private String model;
    private String promptVersion;
    private Long executionTimeMs;
}
