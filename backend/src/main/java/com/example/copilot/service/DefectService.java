package com.example.copilot.service;

import com.example.copilot.client.AiServiceClient;
import com.example.copilot.dto.DefectRequest;
import com.example.copilot.dto.accept.DefectAcceptRequest;
import com.example.copilot.dto.ai.AiDefectResponse;
import com.example.copilot.entity.Defect;
import com.example.copilot.repository.DefectRepository;
import com.example.copilot.util.UserContext;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.nio.charset.StandardCharsets;

@Slf4j
@Service
@RequiredArgsConstructor
public class DefectService {

    private final AiServiceClient aiServiceClient;
    private final DefectRepository defectRepository;
    private final AuditService auditService;

    public AiDefectResponse analyzeUploadedFile(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new IllegalArgumentException("Please provide a valid file to analyze.");
        }
        String fileName = file.getOriginalFilename() != null ? file.getOriginalFilename() : "";
        if (!fileName.toLowerCase().endsWith(".zip")) {
            throw new IllegalArgumentException("Only ZIP files are supported for Codebase.");
        }
        if (file.getSize() > 50 * 1024 * 1024) {
            throw new IllegalArgumentException("File size exceeds the 50MB limit.");
        }

        try {
            String fileContent = "Codebase ZIP Archive: " + fileName;

            DefectRequest request = new DefectRequest();
            request.setTitle("Defect Triage: " + fileName);
            request.setDescription("Automated triage for uploaded codebase: " + fileName);
            request.setLogs(fileContent);
            request.setEnvironment("Codebase Repository");
            request.setDocumentName(fileName);
            request.setInputType("Codebase (ZIP)");

            return analyzeDefect(request);
        } catch (Exception e) {
            log.error("Error analyzing uploaded defect file: ", e);
            throw new RuntimeException("Failed to analyze defect file: " + e.getMessage(), e);
        }
    }

    public AiDefectResponse analyzeDefect(DefectRequest request) {
        if (request.getDocumentName() != null && !request.getDocumentName().isBlank()) {
            if (!request.getDocumentName().toLowerCase().endsWith(".zip")) {
                throw new IllegalArgumentException("Only ZIP files are supported for Codebase.");
            }
        }
        long startTime = System.currentTimeMillis();
        String inputType = request.getInputType() != null ? request.getInputType() : "Defect Context / Logs";
        try {
            AiDefectResponse resp = aiServiceClient.analyzeDefect(request);
            long duration = System.currentTimeMillis() - startTime;
            auditService.logAuditFull(
                    "Defect Triage",
                    "GENERATE",
                    UserContext.getCurrentUser(),
                    UserContext.getCurrentRole(),
                    request.getTitle() != null ? request.getTitle() : "Defect Triage Analysis",
                    resp.getSources(),
                    resp.getModel(),
                    resp.getPrompt_version(),
                    resp.getResult() != null ? resp.getResult().toString() : "",
                    "SUCCESS",
                    duration,
                    null,
                    request.getProjectName(),
                    request.getDocumentName(),
                    request.getDocumentVersion(),
                    inputType,
                    request.getProjectId(),
                    parseDocId(request.getDocumentId())
            );
            return resp;
        } catch (Exception e) {
            long duration = System.currentTimeMillis() - startTime;
            auditService.logAuditFull(
                    "Defect Triage",
                    "GENERATE",
                    UserContext.getCurrentUser(),
                    UserContext.getCurrentRole(),
                    request.getTitle() != null ? request.getTitle() : "Defect Triage Analysis",
                    null,
                    "gemini-3.7-flash",
                    "defect-v1",
                    null,
                    "FAILED",
                    duration,
                    e.getMessage(),
                    request.getProjectName(),
                    request.getDocumentName(),
                    request.getDocumentVersion(),
                    inputType,
                    request.getProjectId(),
                    parseDocId(request.getDocumentId())
            );
            log.error("Error generating defect triage preview: ", e);
            throw new RuntimeException("Failed to analyze defect: " + e.getMessage(), e);
        }
    }

    @Transactional
    public Defect acceptDefect(DefectAcceptRequest request) {
        Defect defect = new Defect();
        defect.setProjectId(request.getProjectId());
        defect.setDocumentId(request.getDocumentId());
        defect.setTitle(request.getTitle() != null ? request.getTitle() : "Defect Triage");
        defect.setDescription(request.getDescription());
        defect.setLogs(request.getLogs());
        defect.setEnvironment(request.getEnvironment());
        defect.setStepsToReproduce(request.getStepsToReproduce());
        defect.setExpectedBehavior(request.getExpectedBehavior());
        defect.setActualBehavior(request.getActualBehavior());
        defect.setProbableRootCause(request.getProbableRootCause());
        defect.setEvidence(request.getEvidence());
        defect.setSuggestedInvestigation(request.getSuggestedInvestigation());
        defect.setSuggestedFix(request.getSuggestedFix());
        defect.setConfidence(request.getConfidence() != null ? request.getConfidence() : "MEDIUM");
        defect.setSeverity(request.getSeverity() != null ? request.getSeverity() : "MEDIUM");
        defect.setPriority(request.getPriority() != null ? request.getPriority() : "P2");
        defect.setRelatedDefects(request.getRelatedDefects());
        defect.setSources(request.getSources());

        Defect saved = defectRepository.save(defect);

        long execTime = request.getExecutionTimeMs() != null ? request.getExecutionTimeMs() : 0L;
        String model = request.getModel() != null ? request.getModel() : "gemini-3.7-flash";
        String promptVersion = request.getPromptVersion() != null ? request.getPromptVersion() : "defect-v1";
        String outputStr = request.getProbableRootCause() != null ? request.getProbableRootCause() : "";

        auditService.logAuditFull(
                "Defect Triage",
                "ACCEPT",
                UserContext.getCurrentUser(),
                UserContext.getCurrentRole(),
                request.getTitle() != null ? request.getTitle() : "Defect Triage",
                request.getSources(),
                model,
                promptVersion,
                outputStr,
                "ACCEPTED",
                execTime,
                null,
                request.getProjectName(),
                request.getDocumentName(),
                request.getDocumentVersion(),
                "Defect Triage Report",
                request.getProjectId(),
                request.getDocumentId()
        );

        return saved;
    }

    private Long parseDocId(String docIdStr) {
        if (docIdStr == null || docIdStr.trim().isEmpty()) return null;
        try {
            return Long.parseLong(docIdStr.trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
