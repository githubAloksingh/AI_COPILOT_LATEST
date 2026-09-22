package com.example.copilot.service;

import com.example.copilot.client.AiServiceClient;
import com.example.copilot.dto.TestCaseItemDto;
import com.example.copilot.dto.TestCaseRequest;
import com.example.copilot.dto.accept.TestCaseAcceptRequest;
import com.example.copilot.dto.ai.AiTestCaseResponse;
import com.example.copilot.entity.TestCase;
import com.example.copilot.repository.TestCaseRepository;
import com.example.copilot.util.UserContext;
import com.example.copilot.repository.AuditLogRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

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
    private final AuditLogRepository auditLogRepository;
    private final ObjectMapper objectMapper;

    public String calculateNextTestGeneratorVersion(Long projectId, String projectName, Long docId, String docName) {
        List<String> testGeneratorAliases = java.util.Arrays.asList("test generator", "test_generator", "test case",
                "testcase");
        List<com.example.copilot.entity.AuditLog> existingLogs = auditLogRepository.findByProjectAndDocumentAndFeatures(
                projectId, projectName, docId, docName, testGeneratorAliases);
        int maxMinor = -1;
        int count = 0;
        if (existingLogs != null) {
            for (com.example.copilot.entity.AuditLog l : existingLogs) {
                if ("GENERATE".equalsIgnoreCase(l.getAction())) {
                    count++;
                    String ver = l.getDocumentVersion();
                    if (ver != null && ver.matches("^1\\.(\\d+)$")) {
                        try {
                            int minor = Integer.parseInt(ver.substring(2));
                            if (minor > maxMinor) {
                                maxMinor = minor;
                            }
                        } catch (NumberFormatException ignored) {
                        }
                    }
                }
            }
        }
        if (maxMinor >= 0) {
            return "1." + (maxMinor + 1);
        }
        if (count == 0) {
            return "1.0";
        } else {
            return "1." + count;
        }
    }

    public AiTestCaseResponse generateTestCases(TestCaseRequest request) {
        long startTime = System.currentTimeMillis();
        String inputType = request.getInputType() != null ? request.getInputType() : "Knowledge Base Document";
        Long docId = parseDocId(request.getDocumentId());
        String calculatedVersion = calculateNextTestGeneratorVersion(request.getProjectId(), request.getProjectName(),
                docId, request.getDocumentName());
        try {
            AiTestCaseResponse resp = aiServiceClient.generateTestCases(request);
            long duration = System.currentTimeMillis() - startTime;
            String outputJson = "";
            if (resp.getResult() != null) {
                try {
                    outputJson = objectMapper.writeValueAsString(resp.getResult());
                } catch (Exception ex) {
                    outputJson = resp.getResult().toString();
                }
            }
            auditService.logAuditFull(
                    "Test Generator",
                    "GENERATE",
                    UserContext.getCurrentUser(),
                    UserContext.getCurrentRole(),
                    request.getRequirement() != null ? request.getRequirement() : "Generate test cases",
                    resp.getSources(),
                    resp.getModel(),
                    resp.getPrompt_version(),
                    outputJson,
                    "SUCCESS",
                    duration,
                    null,
                    request.getProjectName(),
                    request.getDocumentName(),
                    calculatedVersion,
                    inputType,
                    request.getProjectId(),
                    docId);
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
                    calculatedVersion,
                    inputType,
                    request.getProjectId(),
                    docId);
            log.error("Error generating test cases preview: ", e);
            throw new RuntimeException("Failed to generate test cases: " + e.getMessage(), e);
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
                tc.setTcId(item.getScenario() != null && !item.getScenario().isEmpty()
                        ? "TC-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase()
                        : "TC-001");
                tc.setRequirementId(request.getRequirementId());
                tc.setType("FUNCTIONAL");
                tc.setPriority("MEDIUM");
                tc.setScenario(item.getScenario());
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
        String outputStr = "";
        if (items != null) {
            try {
                outputStr = objectMapper.writeValueAsString(items);
            } catch (Exception ex) {
                outputStr = items.toString();
            }
        }

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
                request.getDocumentId());

        return savedTestCases;
    }

    private Long parseDocId(String docIdStr) {
        if (docIdStr == null || docIdStr.trim().isEmpty())
            return null;
        try {
            return Long.parseLong(docIdStr.trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
