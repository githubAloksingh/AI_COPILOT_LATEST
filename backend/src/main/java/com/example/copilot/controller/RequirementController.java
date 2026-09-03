package com.example.copilot.controller;

import com.example.copilot.dto.ApiResponse;
import com.example.copilot.dto.RequirementRequest;
import com.example.copilot.dto.accept.RequirementAcceptRequest;
import com.example.copilot.dto.accept.RequirementBulkAcceptRequest;
import com.example.copilot.dto.ai.AiRequirementResponse;
import com.example.copilot.entity.Requirement;
import com.example.copilot.service.RequirementService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/copilot/requirements")
@RequiredArgsConstructor
public class RequirementController {

    private final RequirementService requirementService;

    @PostMapping
    public ApiResponse<AiRequirementResponse> generateRequirement(@RequestBody RequirementRequest request) {
        return ApiResponse.success(requirementService.generateRequirement(request), "Requirement generated successfully");
    }

    /** Accept a single selected requirement (backward compatible) */
    @PostMapping("/accept")
    public ApiResponse<Requirement> acceptRequirement(@RequestBody RequirementAcceptRequest request) {
        return ApiResponse.success(requirementService.acceptRequirement(request), "Requirement accepted and saved successfully");
    }

    /** Accept ALL requirements at once — saves each as a separate DB row */
    @PostMapping("/accept-all")
    public ApiResponse<List<Requirement>> acceptAllRequirements(@RequestBody RequirementBulkAcceptRequest request) {
        return ApiResponse.success(requirementService.acceptAllRequirements(request), "All requirements saved successfully");
    }
}


