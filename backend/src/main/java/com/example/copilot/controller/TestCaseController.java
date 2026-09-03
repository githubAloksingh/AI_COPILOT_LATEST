package com.example.copilot.controller;

import com.example.copilot.dto.ApiResponse;
import com.example.copilot.dto.TestCaseRequest;
import com.example.copilot.dto.accept.TestCaseAcceptRequest;
import com.example.copilot.dto.ai.AiTestCaseResponse;
import com.example.copilot.entity.TestCase;
import com.example.copilot.service.TestCaseService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

@RestController
@RequestMapping("/api/copilot/testcases")
@RequiredArgsConstructor
public class TestCaseController {

    private final TestCaseService testCaseService;

    @PostMapping(consumes = MediaType.APPLICATION_JSON_VALUE)
    public ApiResponse<AiTestCaseResponse> generateTestCases(@RequestBody TestCaseRequest request) {
        return ApiResponse.success(testCaseService.generateTestCases(request), "Test cases generated successfully");
    }

    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ApiResponse<AiTestCaseResponse> generateTestCasesUpload(
            @RequestParam(value = "brdFile", required = false) MultipartFile brdFile,
            @RequestParam(value = "zipFile", required = false) MultipartFile zipFile,
            @RequestParam(value = "testTypes", required = false) List<String> testTypes,
            @RequestParam(value = "inputMode", required = false) String inputMode
    ) {
        return ApiResponse.success(
                testCaseService.generateTestCasesUpload(brdFile, zipFile, testTypes, inputMode),
                "Test cases generated successfully"
        );
    }

    @PostMapping("/accept")
    public ApiResponse<List<TestCase>> acceptTestCases(@RequestBody TestCaseAcceptRequest request) {
        return ApiResponse.success(testCaseService.acceptTestCases(request), "Test cases accepted and saved successfully");
    }
}

