package com.example.copilot.controller;

import com.example.copilot.dto.ApiResponse;
import com.example.copilot.dto.DefectRequest;
import com.example.copilot.dto.accept.DefectAcceptRequest;
import com.example.copilot.dto.ai.AiDefectResponse;
import com.example.copilot.entity.Defect;
import com.example.copilot.service.DefectService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/copilot/defects")
@RequiredArgsConstructor
public class DefectController {

    private final DefectService defectService;

    @PostMapping("/upload-triage")
    public ApiResponse<AiDefectResponse> analyzeUploadedFile(@RequestParam("file") MultipartFile file) {
        return ApiResponse.success(defectService.analyzeUploadedFile(file), "Defect file triaged successfully");
    }

    @PostMapping("/triage")
    public ApiResponse<AiDefectResponse> analyzeDefect(@RequestBody DefectRequest request) {
        return ApiResponse.success(defectService.analyzeDefect(request), "Defect triaged successfully");
    }

    @PostMapping("/accept")
    public ApiResponse<Defect> acceptDefect(@RequestBody DefectAcceptRequest request) {
        return ApiResponse.success(defectService.acceptDefect(request), "Defect triage accepted and saved successfully");
    }
}

