package com.example.copilot.service;

import com.example.copilot.client.AiServiceClient;
import com.example.copilot.dto.DefectRequest;
import com.example.copilot.dto.DefectResponseDto;
import com.example.copilot.dto.ai.AiDefectResponse;
import com.example.copilot.entity.Defect;
import com.example.copilot.repository.DefectRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class DefectService {

    private final AiServiceClient aiServiceClient;
    private final DefectRepository defectRepository;
    private final AuditService auditService;

    public Defect analyzeDefect(DefectRequest request) {
        long startTime = System.currentTimeMillis();
        String feature = "DEFECT_TRIAGE";
        String status = "SUCCESS";
        String errorMsg = null;
        List<String> sources = null;

        try {
            String combinedInput = (request.getTitle() != null ? request.getTitle() : "") + "\n"
                    + (request.getDescription() != null ? request.getDescription() : "") + "\n"
                    + (request.getLogs() != null ? request.getLogs() : "");

            AiDefectResponse aiResponse = aiServiceClient.analyzeDefect(request);
            DefectResponseDto parsedResponse = aiResponse.getResult();
            sources = aiResponse.getSources();

            Defect defect = new Defect();
            defect.setTitle(request.getTitle());
            defect.setDescription(request.getDescription());
            defect.setLogs(request.getLogs());
            defect.setEnvironment(request.getEnvironment());
            defect.setStepsToReproduce(request.getStepsToReproduce());
            defect.setExpectedBehavior(request.getExpectedBehavior());
            defect.setActualBehavior(request.getActualBehavior());

            if (parsedResponse != null) {
                defect.setProbableRootCause(parsedResponse.getProbableRootCause());
                defect.setEvidence(parsedResponse.getEvidence());
                defect.setSuggestedInvestigation(parsedResponse.getSuggestedInvestigation());
                defect.setSuggestedFix(parsedResponse.getSuggestedFix());
                defect.setConfidence(parsedResponse.getConfidence());
                defect.setSeverity(parsedResponse.getSeverity());
                defect.setPriority(parsedResponse.getPriority());
            }
            defect.setSources(sources);

            Defect saved = defectRepository.save(defect);

            auditService.logAudit(
                    feature,
                    combinedInput,
                    sources,
                    aiResponse.getModel() != null ? aiResponse.getModel() : "gemini-3.7-flash",
                    aiResponse.getPrompt_version() != null ? aiResponse.getPrompt_version() : "defect-v1",
                    parsedResponse != null ? parsedResponse.toString() : "",
                    status,
                    System.currentTimeMillis() - startTime,
                    null
            );
            return saved;

        } catch (Exception e) {
            status = "FAILED";
            errorMsg = e.getMessage();
            log.error("Error triaging defect: ", e);
            auditService.logAudit(
                    feature,
                    request.getTitle(),
                    sources,
                    "gemini-3.7-flash",
                    "defect-v1",
                    null,
                    status,
                    System.currentTimeMillis() - startTime,
                    errorMsg
            );
            throw new RuntimeException("Failed to analyze defect", e);
        }
    }
}
