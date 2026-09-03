package com.example.copilot.controller;

import com.example.copilot.dto.ApiResponse;
import com.example.copilot.dto.ReleaseNoteRequest;
import com.example.copilot.dto.accept.ReleaseNoteAcceptRequest;
import com.example.copilot.dto.ai.AiReleaseNoteResponse;
import com.example.copilot.entity.ReleaseNote;
import com.example.copilot.service.ReleaseNoteService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/copilot/release-notes")
@RequiredArgsConstructor
public class ReleaseController {

    private final ReleaseNoteService releaseNoteService;

    @PostMapping
    public ApiResponse<AiReleaseNoteResponse> generateReleaseNotes(@RequestBody ReleaseNoteRequest request) {
        return ApiResponse.success(releaseNoteService.generateReleaseNotes(request), "Release notes generated successfully");
    }

    @PostMapping("/accept")
    public ApiResponse<ReleaseNote> acceptReleaseNotes(@RequestBody ReleaseNoteAcceptRequest request) {
        return ApiResponse.success(releaseNoteService.acceptReleaseNotes(request), "Release notes accepted and saved successfully");
    }
}

