package com.example.copilot.client;

import com.example.copilot.dto.*;
import com.example.copilot.dto.ai.*;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.*;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

@Slf4j
@Component
public class AiServiceClient {

    @Value("${copilot.ai-service.url:http://localhost:8000}")
    private String aiServiceUrl;

    private final RestTemplate restTemplate;

    public AiServiceClient() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(10000);
        factory.setReadTimeout(900000);
        this.restTemplate = new RestTemplate(factory);
    }

    public AiServiceClient(RestTemplate restTemplate, String aiServiceUrl) {
        this.restTemplate = restTemplate;
        this.aiServiceUrl = aiServiceUrl;
    }

    public AiIngestionResponse ingestDocument(Long documentId, String fileName, String fileType, byte[] content) {
        try {
            Path temporaryUpload = Files.createTempFile("ai-upload-", ".bin");
            Files.write(temporaryUpload, content);
            try {
                return ingestDocument(documentId, fileName, fileType, temporaryUpload);
            } finally {
                Files.deleteIfExists(temporaryUpload);
            }
        } catch (Exception e) {
            throw new RuntimeException("Could not prepare AI service upload: " + e.getMessage(), e);
        }
    }

    public AiIngestionResponse ingestDocument(Long documentId, String fileName, String fileType, Path contentPath) {
        String url = aiServiceUrl + "/api/ai/ingest";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        FileSystemResource fileResource = new FileSystemResource(contentPath.toFile()) {
            @Override
            public String getFilename() {
                return fileName != null ? fileName : super.getFilename();
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

    public String getDocumentContent(Long documentId) {
        String url = aiServiceUrl + "/api/ai/documents/" + documentId + "/content";
        try {
            ResponseEntity<Object> response = restTemplate.getForEntity(url, Object.class);
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                Object content = response.getBody() instanceof java.util.Map<?, ?> responseBody
                        ? responseBody.get("content")
                        : null;
                return content != null ? content.toString() : "";
            }
            return "";
        } catch (Exception e) {
            log.error("Failed to retrieve content for document {} from AI service: {}", documentId, e.getMessage());
            return "Unable to retrieve content for document " + documentId + ": " + e.getMessage();
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
            String detail = extractErrorDetail(e);
            log.error("Failed to generate requirement via AI service: {}", detail);
            throw new RuntimeException("AI Service Requirement Generation Failed: " + detail, e);
        }
    }

    public AiRequirementResponse generateUserStory(RequirementRequest request) {
        String url = aiServiceUrl + "/api/ai/user-story/generate";
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
            String detail = extractErrorDetail(e);
            log.error("Failed to generate user story via AI service: {}", detail);
            throw new RuntimeException("AI Service User Story Generation Failed: " + detail, e);
        }
    }

    public AiRequirementResponse generateFunctionalDesign(RequirementRequest request) {
        String url = aiServiceUrl + "/api/ai/functional-design/generate";
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
            String detail = extractErrorDetail(e);
            log.error("Failed to generate functional design via AI service: {}", detail);
            throw new RuntimeException("AI Service Functional Design Generation Failed: " + detail, e);
        }
    }

    public AiRequirementResponse generateTechnicalDesign(RequirementRequest request) {
        String url = aiServiceUrl + "/api/ai/technical-design/generate";
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
            String detail = extractErrorDetail(e);
            log.error("Failed to generate technical design via AI service: {}", detail);
            throw new RuntimeException("AI Service Technical Design Generation Failed: " + detail, e);
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
            String detail = extractErrorDetail(e);
            log.error("Failed to generate test cases via AI service: {}", detail);
            throw new RuntimeException("AI Service Test Case Generation Failed: " + detail, e);
        }
    }

    public AiTestCaseResponse generateTestCasesUpload(MultipartFile brdFile, MultipartFile zipFile, List<String> testTypes, String inputMode) {
        String url = aiServiceUrl + "/api/ai/test-cases/generate-upload";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        Path brdPath = null;
        Path zipPath = null;

        try {
            if (brdFile != null && !brdFile.isEmpty()) {
                brdPath = copyUploadToTempFile(brdFile, "ai-brd-upload-", ".bin");
                Path finalBrdPath = brdPath;
                FileSystemResource brdResource = new FileSystemResource(finalBrdPath.toFile()) {
                    @Override
                    public String getFilename() {
                        return brdFile.getOriginalFilename() != null ? brdFile.getOriginalFilename() : "document.pdf";
                    }
                };
                body.add("brd_file", brdResource);
            }

            if (zipFile != null && !zipFile.isEmpty()) {
                zipPath = copyUploadToTempFile(zipFile, "ai-zip-upload-", ".zip");
                Path finalZipPath = zipPath;
                FileSystemResource zipResource = new FileSystemResource(finalZipPath.toFile()) {
                    @Override
                    public String getFilename() {
                        return zipFile.getOriginalFilename() != null ? zipFile.getOriginalFilename() : "project.zip";
                    }
                };
                body.add("zip_file", zipResource);
            }

            if (inputMode != null) {
                body.add("input_mode", inputMode);
            }
            if (testTypes != null && !testTypes.isEmpty()) {
                body.add("test_types", String.join(",", testTypes));
            }

            HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);
            ResponseEntity<AiTestCaseResponse> response = restTemplate.postForEntity(url, requestEntity, AiTestCaseResponse.class);
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                return response.getBody();
            }
            throw new RuntimeException("AI service returned status: " + response.getStatusCode());
        } catch (Exception e) {
            String detail = extractErrorDetail(e);
            log.error("Failed to generate test cases via upload from AI service: {}", detail);
            throw new RuntimeException("AI Service Test Case Upload Generation Failed: " + detail, e);
        } finally {
            deleteTempFile(brdPath);
            deleteTempFile(zipPath);
        }
    }

    private Path copyUploadToTempFile(MultipartFile upload, String prefix, String suffix) {
        try {
            Path path = Files.createTempFile(prefix, suffix);
            try (java.io.InputStream input = upload.getInputStream()) {
                Files.copy(input, path, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
            }
            return path;
        } catch (Exception e) {
            throw new RuntimeException("Failed to stage uploaded file: " + e.getMessage(), e);
        }
    }

    private void deleteTempFile(Path path) {
        if (path != null) {
            try {
                Files.deleteIfExists(path);
            } catch (Exception e) {
                log.warn("Could not delete temporary AI upload {}: {}", path, e.getMessage());
            }
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
            String detail = extractErrorDetail(e);
            log.error("Failed to analyze defect via AI service: {}", detail);
            if (e instanceof org.springframework.web.client.HttpStatusCodeException statusEx
                    && statusEx.getStatusCode().value() == 429) {
                throw new com.example.copilot.exception.AiServiceQuotaExceededException(detail, e);
            }
            throw new RuntimeException("AI Service Defect Analysis Failed: " + detail, e);
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
            String detail = extractErrorDetail(e);
            log.error("Failed to generate release notes via AI service: {}", detail);
            throw new RuntimeException("AI Service Release Notes Generation Failed: " + detail, e);
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
            String detail = extractErrorDetail(e);
            log.error("Failed to generate daily status via AI service: {}", detail);
            throw new RuntimeException("AI Service Daily Status Generation Failed: " + detail, e);
        }
    }

    private String extractErrorDetail(Exception e) {
        if (e instanceof org.springframework.web.client.HttpStatusCodeException statusEx) {
            String body = statusEx.getResponseBodyAsString();
            if (body != null && !body.isBlank()) {
                try {
                    com.fasterxml.jackson.databind.JsonNode node = new com.fasterxml.jackson.databind.ObjectMapper().readTree(body);
                    if (node.has("detail")) {
                        return node.get("detail").asText();
                    }
                } catch (Exception ignored) {
                }
                return body;
            }
        }
        return e.getMessage() != null ? e.getMessage() : "Unknown error";
    }
}
