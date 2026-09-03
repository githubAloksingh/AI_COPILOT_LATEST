package com.example.copilot.service;

import com.example.copilot.client.AiServiceClient;
import com.example.copilot.dto.ReleaseNoteRequest;
import com.example.copilot.dto.accept.ReleaseNoteAcceptRequest;
import com.example.copilot.dto.ai.AiReleaseNoteResponse;
import com.example.copilot.entity.ReleaseNote;
import com.example.copilot.repository.ReleaseNoteRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Slf4j
@Service
@RequiredArgsConstructor
public class ReleaseNoteService {

    private final AiServiceClient aiServiceClient;
    private final ReleaseNoteRepository releaseNoteRepository;
    private final AuditService auditService;

    public AiReleaseNoteResponse generateReleaseNotes(ReleaseNoteRequest request) {
        try {
            return aiServiceClient.generateReleaseNotes(request);
        } catch (Exception e) {
            log.error("Error generating release notes preview: ", e);
            throw new RuntimeException("Failed to generate release notes: " + e.getMessage(), e);
        }
    }

    @Transactional
    public ReleaseNote acceptReleaseNotes(ReleaseNoteAcceptRequest request) {
        ReleaseNote releaseNote = new ReleaseNote();
        releaseNote.setVersion(request.getVersion() != null ? request.getVersion() : "1.0.0");
        releaseNote.setSprintInformation(request.getSprintInformation());
        releaseNote.setSummary(request.getSummary());
        releaseNote.setNewFeatures(request.getNewFeatures());
        releaseNote.setImprovements(request.getImprovements());
        releaseNote.setBugFixes(request.getBugFixes());
        releaseNote.setBreakingChanges(request.getBreakingChanges());
        releaseNote.setKnownIssues(request.getKnownIssues());
        releaseNote.setTechnicalNotes(request.getTechnicalNotes());

        ReleaseNote saved = releaseNoteRepository.save(releaseNote);

        long execTime = request.getExecutionTimeMs() != null ? request.getExecutionTimeMs() : 0L;
        String model = request.getModel() != null ? request.getModel() : "gemini-3.7-flash";
        String promptVersion = request.getPromptVersion() != null ? request.getPromptVersion() : "release-v1";
        String outputStr = request.getSummary() != null ? request.getSummary() : "";

        auditService.logAudit(
                "RELEASE_NOTES",
                request.getSprintInformation() != null ? request.getSprintInformation() : "Release notes",
                request.getSources(),
                model,
                promptVersion,
                outputStr,
                "SUCCESS",
                execTime,
                null
        );

        return saved;
    }
}

