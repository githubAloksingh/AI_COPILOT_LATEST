package com.example.copilot.service;

import com.example.copilot.client.AiServiceClient;
import com.example.copilot.dto.DailyStatusRequest;
import com.example.copilot.dto.DailyStatusResponseDto;
import com.example.copilot.dto.ai.AiDailyStatusResponse;
import com.example.copilot.entity.DailyStatus;
import com.example.copilot.repository.DailyStatusRepository;
import com.example.copilot.util.UserContext;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class DailyStatusService {

    private final AiServiceClient aiServiceClient;
    private final DailyStatusRepository dailyStatusRepository;
    private final AuditService auditService;

    public DailyStatus generateDailyStatus(DailyStatusRequest request) {
        long startTime = System.currentTimeMillis();
        String feature = "Daily Status";
        String status = "SUCCESS";
        String errorMsg = null;
        List<String> sources = null;
        String inputType = request.getInputType() != null ? request.getInputType() : "Daily Scrum Updates";

        try {
            AiDailyStatusResponse aiResponse = aiServiceClient.generateDailyStatus(request);
            DailyStatusResponseDto parsedResponse = aiResponse.getResult();
            sources = aiResponse.getSources();

            DailyStatus dailyStatus = new DailyStatus();
            dailyStatus.setProjectId(request.getProjectId());
            dailyStatus.setDocumentId(request.getDocumentId() != null ? Long.parseLong(request.getDocumentId()) : null);
            dailyStatus.setSprintInformation(request.getSprintInformation());

            if (parsedResponse != null) {
                dailyStatus.setCompleted(parsedResponse.getCompleted());
                dailyStatus.setInProgress(parsedResponse.getInProgress());
                dailyStatus.setBlockers(parsedResponse.getBlockers());
                dailyStatus.setRisks(parsedResponse.getRisks());
                dailyStatus.setNextSteps(parsedResponse.getNextSteps());
                dailyStatus.setImportantUpdates(parsedResponse.getImportantUpdates());
            }

            DailyStatus saved = dailyStatusRepository.save(dailyStatus);

            long duration = System.currentTimeMillis() - startTime;
            auditService.logAuditFull(
                    feature,
                    "GENERATE",
                    UserContext.getCurrentUser(),
                    UserContext.getCurrentRole(),
                    request.getSprintInformation() != null ? request.getSprintInformation() : "Daily Status Generation",
                    sources,
                    aiResponse.getModel() != null ? aiResponse.getModel() : "gemini-3.7-flash",
                    aiResponse.getPrompt_version() != null ? aiResponse.getPrompt_version() : "status-v1",
                    parsedResponse != null ? parsedResponse.toString() : "",
                    status,
                    duration,
                    null,
                    request.getProjectName(),
                    request.getDocumentName(),
                    request.getDocumentVersion(),
                    inputType
            );
            return saved;

        } catch (Exception e) {
            status = "FAILED";
            errorMsg = e.getMessage();
            long duration = System.currentTimeMillis() - startTime;
            log.error("Error generating daily status: ", e);
            auditService.logAuditFull(
                    feature,
                    "GENERATE",
                    UserContext.getCurrentUser(),
                    UserContext.getCurrentRole(),
                    request.getSprintInformation() != null ? request.getSprintInformation() : "Daily Status Generation",
                    sources,
                    "gemini-3.7-flash",
                    "status-v1",
                    null,
                    status,
                    duration,
                    errorMsg,
                    request.getProjectName(),
                    request.getDocumentName(),
                    request.getDocumentVersion(),
                    inputType
            );
            throw new RuntimeException("Failed to generate daily status", e);
        }
    }
}
