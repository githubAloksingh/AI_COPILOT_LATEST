package com.example.copilot.service;

import com.example.copilot.client.AiServiceClient;
import com.example.copilot.dto.ReleaseNoteRequest;
import com.example.copilot.dto.ReleaseNoteResponseDto;
import com.example.copilot.dto.ai.AiReleaseNoteResponse;
import com.example.copilot.entity.ReleaseNote;
import com.example.copilot.repository.ReleaseNoteRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class ReleaseNoteService {

    private final AiServiceClient aiServiceClient;
    private final ReleaseNoteRepository releaseNoteRepository;
    private final AuditService auditService;

    public ReleaseNote generateReleaseNotes(ReleaseNoteRequest request) {
        long startTime = System.currentTimeMillis();
        String feature = "RELEASE_NOTES";
        String status = "SUCCESS";
        String errorMsg = null;
        List<String> sources = null;

        try {
            AiReleaseNoteResponse aiResponse = aiServiceClient.generateReleaseNotes(request);
            ReleaseNoteResponseDto parsedResponse = aiResponse.getResult();
            sources = aiResponse.getSources();

            ReleaseNote releaseNote = new ReleaseNote();
            releaseNote.setVersion(request.getVersion());
            releaseNote.setSprintInformation(request.getSprintInformation());

            if (parsedResponse != null) {
                releaseNote.setSummary(parsedResponse.getSummary());
                releaseNote.setNewFeatures(parsedResponse.getNewFeatures());
                releaseNote.setImprovements(parsedResponse.getImprovements());
                releaseNote.setBugFixes(parsedResponse.getBugFixes());
                releaseNote.setBreakingChanges(parsedResponse.getBreakingChanges());
                releaseNote.setKnownIssues(parsedResponse.getKnownIssues());
                releaseNote.setTechnicalNotes(parsedResponse.getTechnicalNotes());
            }

            ReleaseNote saved = releaseNoteRepository.save(releaseNote);

            auditService.logAudit(
                    feature,
                    request.getSprintInformation(),
                    sources,
                    aiResponse.getModel() != null ? aiResponse.getModel() : "gemini-3.7-flash",
                    aiResponse.getPrompt_version() != null ? aiResponse.getPrompt_version() : "release-v1",
                    parsedResponse != null ? parsedResponse.toString() : "",
                    status,
                    System.currentTimeMillis() - startTime,
                    null
            );
            return saved;

        } catch (Exception e) {
            status = "FAILED";
            errorMsg = e.getMessage();
            log.error("Error generating release notes: ", e);
            auditService.logAudit(
                    feature,
                    request.getSprintInformation(),
                    sources,
                    "gemini-3.7-flash",
                    "release-v1",
                    null,
                    status,
                    System.currentTimeMillis() - startTime,
                    errorMsg
            );
            throw new RuntimeException("Failed to generate release notes", e);
        }
    }
}
