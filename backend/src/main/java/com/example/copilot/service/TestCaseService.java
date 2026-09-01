package com.example.copilot.service;

import com.example.copilot.client.AiServiceClient;
import com.example.copilot.dto.TestCaseItemDto;
import com.example.copilot.dto.TestCaseRequest;
import com.example.copilot.dto.ai.AiTestCaseResponse;
import com.example.copilot.entity.TestCase;
import com.example.copilot.repository.TestCaseRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

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

    public List<TestCase> generateTestCases(TestCaseRequest request) {
        long startTime = System.currentTimeMillis();
        String feature = "TEST_GENERATOR";
        String status = "SUCCESS";
        String errorMsg = null;
        List<String> sources = null;

        try {
            AiTestCaseResponse aiResponse = aiServiceClient.generateTestCases(request);
            List<TestCaseItemDto> items = aiResponse.getResult();
            sources = aiResponse.getSources();

            List<TestCase> savedTestCases = new ArrayList<>();
            if (items != null) {
                for (TestCaseItemDto item : items) {
                    TestCase tc = new TestCase();
                    tc.setTcId("TC-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());
                    tc.setScenario(item.getScenario());
                    tc.setType(item.getType());
                    tc.setPriority(item.getPriority());
                    tc.setPreconditions(item.getPreconditions());
                    tc.setSteps(item.getSteps());
                    tc.setExpectedResult(item.getExpectedResult());
                    tc.setSources(sources);
                    savedTestCases.add(testCaseRepository.save(tc));
                }
            }

            auditService.logAudit(
                    feature,
                    request.getRequirement(),
                    sources,
                    aiResponse.getModel() != null ? aiResponse.getModel() : "gemini-3.7-flash",
                    aiResponse.getPrompt_version() != null ? aiResponse.getPrompt_version() : "testcase-v1",
                    items != null ? items.toString() : "",
                    status,
                    System.currentTimeMillis() - startTime,
                    null
            );
            return savedTestCases;

        } catch (Exception e) {
            status = "FAILED";
            errorMsg = e.getMessage();
            log.error("Error generating test cases: ", e);
            auditService.logAudit(
                    feature,
                    request.getRequirement(),
                    sources,
                    "gemini-3.7-flash",
                    "testcase-v1",
                    null,
                    status,
                    System.currentTimeMillis() - startTime,
                    errorMsg
            );
            throw new RuntimeException("Failed to generate test cases", e);
        }
    }
}
