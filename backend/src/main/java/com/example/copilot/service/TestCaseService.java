package com.example.copilot.service;

import com.example.copilot.client.AiServiceClient;
import com.example.copilot.dto.TestCaseItemDto;
import com.example.copilot.dto.TestCaseRequest;
import com.example.copilot.dto.accept.TestCaseAcceptRequest;
import com.example.copilot.dto.ai.AiTestCaseResponse;
import com.example.copilot.entity.TestCase;
import com.example.copilot.repository.TestCaseRepository;
import com.example.copilot.util.UserContext;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class TestCaseService {

    private final AiServiceClient aiServiceClient;
    private final TestCaseRepository testCaseRepository;
    private final AuditService auditService;

    public AiTestCaseResponse generateTestCases(TestCaseRequest request) {
        long startTime = System.currentTimeMillis();
        String inputType = request.getInputType() != null ? request.getInputType() : "Knowledge Base Document";
        try {
            AiTestCaseResponse resp = aiServiceClient.generateTestCases(request);
            long duration = System.currentTimeMillis() - startTime;
            auditService.logAuditFull(
                    "Test Generator",
                    "GENERATE",
                    UserContext.getCurrentUser(),
                    UserContext.getCurrentRole(),
                    request.getRequirement() != null ? request.getRequirement() : "Generate test cases",
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
                    "Test Generator",
                    "GENERATE",
                    UserContext.getCurrentUser(),
                    UserContext.getCurrentRole(),
                    request.getRequirement() != null ? request.getRequirement() : "Generate test cases",
                    null,
                    "gemini-3.7-flash",
                    "testcase-v1",
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
            log.error("Error generating test cases preview: ", e);
            throw new RuntimeException("Failed to generate test cases: " + e.getMessage(), e);
        }
    }

    public AiTestCaseResponse generateTestCasesUpload(MultipartFile brdFile, MultipartFile zipFile, List<String> testTypes, String inputMode) {
        String mode = inputMode != null ? inputMode.trim().toLowerCase() : "brd";
        if ("brd".equals(mode) && (brdFile == null || brdFile.isEmpty())) {
            throw new IllegalArgumentException("BRD document is required for BRD mode.");
        }
        if ("zip".equals(mode) && (zipFile == null || zipFile.isEmpty())) {
            throw new IllegalArgumentException("Project ZIP file is required for ZIP mode.");
        }
        if ("both".equals(mode)) {
            if (brdFile == null || brdFile.isEmpty()) {
                throw new IllegalArgumentException("BRD document is required for BRD + Project mode.");
            }
            if (zipFile == null || zipFile.isEmpty()) {
                throw new IllegalArgumentException("Project ZIP file is required for BRD + Project mode.");
            }
        }

        long startTime = System.currentTimeMillis();
        try {
            AiTestCaseResponse resp = aiServiceClient.generateTestCasesUpload(brdFile, zipFile, testTypes, inputMode);
            long duration = System.currentTimeMillis() - startTime;
            auditService.logAuditFull(
                    "Test Generator",
                    "GENERATE",
                    UserContext.getCurrentUser(),
                    UserContext.getCurrentRole(),
                    "Direct file upload test cases generation",
                    resp.getSources(),
                    resp.getModel(),
                    resp.getPrompt_version(),
                    resp.getResult() != null ? resp.getResult().toString() : "",
                    "SUCCESS",
                    duration,
                    null,
                    null,
                    brdFile != null ? brdFile.getOriginalFilename() : (zipFile != null ? zipFile.getOriginalFilename() : null),
                    "v1",
                    inputMode != null ? inputMode : "Direct File Upload"
            );
            return resp;
        } catch (Exception e) {
            long duration = System.currentTimeMillis() - startTime;
            auditService.logAuditFull(
                    "Test Generator",
                    "GENERATE",
                    UserContext.getCurrentUser(),
                    UserContext.getCurrentRole(),
                    "Direct file upload test cases generation",
                    null,
                    "gemini-3.7-flash",
                    "testcase-v1",
                    null,
                    "FAILED",
                    duration,
                    e.getMessage(),
                    null,
                    brdFile != null ? brdFile.getOriginalFilename() : (zipFile != null ? zipFile.getOriginalFilename() : null),
                    "v1",
                    inputMode != null ? inputMode : "Direct File Upload"
            );
            log.error("Error generating test cases upload preview: ", e);
            throw new RuntimeException("Failed to generate test cases from files: " + e.getMessage(), e);
        }
    }

    @Transactional
    public List<TestCase> acceptTestCases(TestCaseAcceptRequest request) {
        List<TestCase> savedTestCases = new ArrayList<>();
        List<TestCaseItemDto> items = request.getTestCases();

        if (items != null) {
            for (TestCaseItemDto item : items) {
                TestCase tc = new TestCase();
                tc.setProjectId(request.getProjectId());
                tc.setDocumentId(request.getDocumentId());
                tc.setTcId(item.getScenario() != null && !item.getScenario().isEmpty() ? 
                        "TC-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase() : "TC-001");
                tc.setRequirementId(request.getRequirementId());
                tc.setScenario(item.getScenario());
                tc.setType(item.getType() != null ? item.getType() : "POSITIVE");
                tc.setPriority(item.getPriority() != null ? item.getPriority() : "MEDIUM");
                tc.setPreconditions(item.getPreconditions());
                tc.setSteps(item.getSteps());
                tc.setExpectedResult(item.getExpectedResult());
                tc.setSources(request.getSources());
                savedTestCases.add(testCaseRepository.save(tc));
            }
        }

        long execTime = request.getExecutionTimeMs() != null ? request.getExecutionTimeMs() : 0L;
        String model = request.getModel() != null ? request.getModel() : "gemini-3.7-flash";
        String promptVersion = request.getPromptVersion() != null ? request.getPromptVersion() : "testcase-v1";
        String outputStr = items != null ? items.toString() : "";

        auditService.logAuditFull(
                "Test Generator",
                "ACCEPT",
                UserContext.getCurrentUser(),
                UserContext.getCurrentRole(),
                request.getRequirement() != null ? request.getRequirement() : "Accepted test cases",
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
                "Test Suite",
                request.getProjectId(),
                request.getDocumentId()
        );

        return savedTestCases;
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
