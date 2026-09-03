package com.example.copilot.service;

import com.example.copilot.client.AiServiceClient;
import com.example.copilot.dto.DefectRequest;
import com.example.copilot.dto.accept.DefectAcceptRequest;
import com.example.copilot.dto.ai.AiDefectResponse;
import com.example.copilot.entity.Defect;
import com.example.copilot.repository.DefectRepository;
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
        if (file.getSize() > 50 * 1024 * 1024) {
            throw new IllegalArgumentException("File size exceeds the 50MB limit.");
        }

        try {
            String fileName = file.getOriginalFilename() != null ? file.getOriginalFilename() : "uploaded_log.txt";
            String fileContent = new String(file.getBytes(), StandardCharsets.UTF_8);

            // Cap logs at 60,000 characters to fit context window comfortably
            if (fileContent.length() > 60000) {
                fileContent = fileContent.substring(0, 60000) + "\n... [truncated due to size]";
            }

            DefectRequest request = new DefectRequest();
            request.setTitle("Defect Triage: " + fileName);
            request.setDescription("Automated triage for uploaded file: " + fileName);
            request.setLogs(fileContent);
            request.setEnvironment("Uploaded File Environment");

            return aiServiceClient.analyzeDefect(request);
        } catch (Exception e) {
            log.error("Error analyzing uploaded defect file: ", e);
            throw new RuntimeException("Failed to analyze defect file: " + e.getMessage(), e);
        }
    }

    public AiDefectResponse analyzeDefect(DefectRequest request) {
        try {
            return aiServiceClient.analyzeDefect(request);
        } catch (Exception e) {
            log.error("Error generating defect triage preview: ", e);
            throw new RuntimeException("Failed to analyze defect: " + e.getMessage(), e);
        }
    }

    @Transactional
    public Defect acceptDefect(DefectAcceptRequest request) {
        Defect defect = new Defect();
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

        auditService.logAudit(
                "DEFECT_TRIAGE",
                request.getTitle() != null ? request.getTitle() : "Defect triage file",
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

