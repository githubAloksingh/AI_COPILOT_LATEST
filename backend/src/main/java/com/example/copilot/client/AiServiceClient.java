package com.example.copilot.client;

import com.example.copilot.dto.*;
import com.example.copilot.dto.ai.*;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.*;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;

@Slf4j
@Component
public class AiServiceClient {

    @Value("${copilot.ai-service.url:http://localhost:8000}")
    private String aiServiceUrl;

    private final RestTemplate restTemplate;

    public AiServiceClient() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(10000);
        factory.setReadTimeout(120000);
        this.restTemplate = new RestTemplate(factory);
    }

    public AiServiceClient(RestTemplate restTemplate, String aiServiceUrl) {
        this.restTemplate = restTemplate;
        this.aiServiceUrl = aiServiceUrl;
    }

    public AiIngestionResponse ingestDocument(Long documentId, String fileName, String fileType, byte[] content) {
        String url = aiServiceUrl + "/api/ai/ingest";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        ByteArrayResource fileResource = new ByteArrayResource(content) {
            @Override
            public String getFilename() {
                return fileName != null ? fileName : "document";
            }
        };

        body.add("file", fileResource);
        body.add("document_id", String.valueOf(documentId));
        if (fileName != null) {
            body.add("file_name", fileName);
        }
        if (fileType != null) {
            body.add("file_type", fileType);
        }

        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);
        try {
            ResponseEntity<AiIngestionResponse> response = restTemplate.postForEntity(url, requestEntity, AiIngestionResponse.class);
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                return response.getBody();
            }
            throw new RuntimeException("AI service returned status: " + response.getStatusCode());
        } catch (Exception e) {
            log.error("Failed to ingest document {} via AI service: {}", documentId, e.getMessage());
            throw new RuntimeException("AI Service Ingestion Failed: " + e.getMessage(), e);
        }
    }

    public AiRequirementResponse generateRequirement(RequirementRequest request) {
        String url = aiServiceUrl + "/api/ai/requirements/generate";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        HttpEntity<RequirementRequest> requestEntity = new HttpEntity<>(request, headers);
        try {
            ResponseEntity<AiRequirementResponse> response = restTemplate.postForEntity(url, requestEntity, AiRequirementResponse.class);
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                return response.getBody();
            }
            throw new RuntimeException("AI service returned status: " + response.getStatusCode());
        } catch (Exception e) {
            log.error("Failed to generate requirement via AI service: {}", e.getMessage());
            throw new RuntimeException("AI Service Requirement Generation Failed: " + e.getMessage(), e);
        }
    }

    public AiTestCaseResponse generateTestCases(TestCaseRequest request) {
        String url = aiServiceUrl + "/api/ai/test-cases/generate";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        HttpEntity<TestCaseRequest> requestEntity = new HttpEntity<>(request, headers);
        try {
            ResponseEntity<AiTestCaseResponse> response = restTemplate.postForEntity(url, requestEntity, AiTestCaseResponse.class);
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                return response.getBody();
            }
            throw new RuntimeException("AI service returned status: " + response.getStatusCode());
        } catch (Exception e) {
            log.error("Failed to generate test cases via AI service: {}", e.getMessage());
            throw new RuntimeException("AI Service Test Case Generation Failed: " + e.getMessage(), e);
        }
    }

    public AiDefectResponse analyzeDefect(DefectRequest request) {
        String url = aiServiceUrl + "/api/ai/defects/analyze";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        HttpEntity<DefectRequest> requestEntity = new HttpEntity<>(request, headers);
        try {
            ResponseEntity<AiDefectResponse> response = restTemplate.postForEntity(url, requestEntity, AiDefectResponse.class);
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                return response.getBody();
            }
            throw new RuntimeException("AI service returned status: " + response.getStatusCode());
        } catch (Exception e) {
            log.error("Failed to analyze defect via AI service: {}", e.getMessage());
            throw new RuntimeException("AI Service Defect Analysis Failed: " + e.getMessage(), e);
        }
    }

    public AiReleaseNoteResponse generateReleaseNotes(ReleaseNoteRequest request) {
        String url = aiServiceUrl + "/api/ai/release-notes/generate";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        HttpEntity<ReleaseNoteRequest> requestEntity = new HttpEntity<>(request, headers);
        try {
            ResponseEntity<AiReleaseNoteResponse> response = restTemplate.postForEntity(url, requestEntity, AiReleaseNoteResponse.class);
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                return response.getBody();
            }
            throw new RuntimeException("AI service returned status: " + response.getStatusCode());
        } catch (Exception e) {
            log.error("Failed to generate release notes via AI service: {}", e.getMessage());
            throw new RuntimeException("AI Service Release Notes Generation Failed: " + e.getMessage(), e);
        }
    }

    public AiDailyStatusResponse generateDailyStatus(DailyStatusRequest request) {
        String url = aiServiceUrl + "/api/ai/daily-status/generate";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        HttpEntity<DailyStatusRequest> requestEntity = new HttpEntity<>(request, headers);
        try {
            ResponseEntity<AiDailyStatusResponse> response = restTemplate.postForEntity(url, requestEntity, AiDailyStatusResponse.class);
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                return response.getBody();
            }
            throw new RuntimeException("AI service returned status: " + response.getStatusCode());
        } catch (Exception e) {
            log.error("Failed to generate daily status via AI service: {}", e.getMessage());
            throw new RuntimeException("AI Service Daily Status Generation Failed: " + e.getMessage(), e);
        }
    }
}
