package com.example.copilot.service;

import com.example.copilot.client.AiServiceClient;
import com.example.copilot.dto.mockscreen.BrdDocumentDto;
import com.example.copilot.dto.mockscreen.MockScreenJobResponse;
import com.example.copilot.dto.mockscreen.ScreenDto;
import com.example.copilot.entity.Document;
import com.example.copilot.entity.MockScreen;
import com.example.copilot.entity.MockScreenGeneration;
import com.example.copilot.entity.Project;
import com.example.copilot.repository.DocumentChunkRepository;
import com.example.copilot.repository.DocumentRepository;
import com.example.copilot.repository.MockScreenGenerationRepository;
import com.example.copilot.repository.MockScreenRepository;
import com.example.copilot.repository.ProjectRepository;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class MockScreenService {

    private final DocumentRepository documentRepository;
    private final DocumentChunkRepository documentChunkRepository;
    private final ProjectRepository projectRepository;
    private final MockScreenGenerationRepository generationRepository;
    private final MockScreenRepository mockScreenRepository;
    private final DocumentService documentService;
    private final AiServiceClient aiServiceClient;
    private final AuditService auditService;
    private final ObjectMapper objectMapper;

    /**
     * Section 2 & 19: Return ONLY BRD documents from Knowledge Base.
     * Grounded in existing document metadata/fileType/source-type.
     */
    public List<BrdDocumentDto> getBrdDocuments() {
        List<Document> allDocs = documentRepository.findAllByOrderByCreatedAtDesc();
        Map<Long, String> projectNames = projectRepository.findAll().stream()
                .collect(Collectors.toMap(Project::getId, Project::getProjectName, (p1, p2) -> p1));

        return allDocs.stream()
                .filter(this::isBrdDocument)
                .map(doc -> BrdDocumentDto.builder()
                        .id(doc.getId())
                        .fileName(doc.getFileName())
                        .projectId(doc.getProjectId())
                        .projectName(doc.getProjectId() != null ? projectNames.getOrDefault(doc.getProjectId(), "General") : "General")
                        .uploadedBy(doc.getUploadedBy())
                        .createdAt(doc.getCreatedAt())
                        .status(doc.getStatus())
                        .chunkCount(doc.getChunkCount())
                        .fileSize(doc.getFileSize())
                        .fileType(doc.getFileType())
                        .build())
                .collect(Collectors.toList());
    }

    public boolean isBrdDocument(Document doc) {
        if (doc == null) return false;
        String type = doc.getFileType() != null ? doc.getFileType().trim().toUpperCase() : "";
        String name = doc.getFileName() != null ? doc.getFileName().trim().toLowerCase() : "";

        // Reject zip archives, technical/functional design, user story, defect, release notes exports
        if (name.endsWith(".zip") || type.contains("ZIP") || type.contains("CODEBASE")) {
            return false;
        }

        // Must be explicitly BRD or PDF requirements document
        if ("BRD".equalsIgnoreCase(type) || type.contains("BRD")) {
            return true;
        }

        if (name.contains("brd") || name.contains("business_requirement") || name.contains("requirements")) {
            return true;
        }

        // If uploaded as general PDF and completed, check if it's a requirements document
        return "COMPLETED".equalsIgnoreCase(doc.getStatus()) && name.endsWith(".pdf");
    }

    /**
     * Section 15: Create an asynchronous generation job.
     */
    @Transactional
    public MockScreenJobResponse createGenerationJob(Long documentId, String userName) {
        Document doc = documentRepository.findById(documentId)
                .orElseThrow(() -> new IllegalArgumentException("Document not found with ID: " + documentId));

        if (!isBrdDocument(doc)) {
            throw new IllegalArgumentException("Only Business Requirements Documents (BRD) can be processed for Mock Screens.");
        }

        String jobId = "JOB-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();
        MockScreenGeneration gen = new MockScreenGeneration();
        gen.setJobId(jobId);
        gen.setDocumentId(documentId);
        gen.setProjectId(doc.getProjectId());
        gen.setStatus("QUEUED");
        gen.setTotalScreens(0);
        gen.setCompletedScreens(0);

        MockScreenGeneration saved = generationRepository.save(gen);
        log.info("Created mock screen generation job {} for document ID {}", jobId, documentId);

        return buildJobResponse(saved, Collections.emptyList(), doc);
    }

    /**
     * Background asynchronous workflow execution (Sections 3, 4, 5, 8, 14, 15, 17).
     */
    @Async("documentTaskExecutor")
    public void processGenerationJobAsync(String jobId, Long documentId, String userName) {
        long startTime = System.currentTimeMillis();
        log.info("Starting background execution for mock screen job: {}", jobId);

        MockScreenGeneration gen = generationRepository.findByJobId(jobId).orElse(null);
        if (gen == null) {
            log.error("Job {} not found for asynchronous execution", jobId);
            return;
        }

        Document doc = documentRepository.findById(documentId).orElse(null);
        String docName = doc != null ? doc.getFileName() : "Document #" + documentId;
        String projName = "General Enterprise";
        if (doc != null && doc.getProjectId() != null) {
            projName = projectRepository.findById(doc.getProjectId())
                    .map(Project::getProjectName).orElse("General Enterprise");
        }

        try {
            // STEP 1: RETRIEVE & ANALYZE COMPLETE BRD
            updateJobStatus(gen, "ANALYZING", null, null);
            String fullBrdText = retrieveCompleteBrdText(documentId, doc);
            if (fullBrdText == null || fullBrdText.trim().isEmpty()) {
                throw new IllegalStateException("Failed to extract readable text from the complete BRD.");
            }
            log.info("Retrieved complete BRD content for job {}: {} characters", jobId, fullBrdText.length());

            // STEP 2: GEMINI SCREEN PLANNING
            updateJobStatus(gen, "PLANNING", null, null);
            Map<String, Object> planRequest = new HashMap<>();
            planRequest.put("document_id", String.valueOf(documentId));
            planRequest.put("brd_text", fullBrdText);
            planRequest.put("project_name", projName);

            Map<String, Object> planResponse = aiServiceClient.generateMockScreenPlan(planRequest);
            @SuppressWarnings("unchecked")
            Map<String, Object> plan = (Map<String, Object>) planResponse.get("plan");
            if (plan == null) {
                throw new IllegalStateException("AI Service returned empty Screen Plan.");
            }

            String appName = (String) plan.getOrDefault("application_name", "Enterprise Application");
            String appSummary = (String) plan.getOrDefault("application_summary", "");
            @SuppressWarnings("unchecked")
            Map<String, Object> designContext = (Map<String, Object>) plan.get("design_context");
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> screensList = (List<Map<String, Object>>) plan.get("screens");

            if (screensList == null || screensList.isEmpty()) {
                throw new IllegalStateException("Screen Plan contains 0 screens.");
            }

            gen.setApplicationName(appName);
            gen.setApplicationSummary(appSummary);
            gen.setDesignSystemJson(objectMapper.writeValueAsString(designContext));
            gen.setScreenPlanJson(objectMapper.writeValueAsString(plan));
            gen.setTotalScreens(screensList.size());
            gen.setCompletedScreens(0);
            gen = generationRepository.save(gen);

            // Pre-create Screen records in DB
            List<MockScreen> screenEntities = new ArrayList<>();
            for (int i = 0; i < screensList.size(); i++) {
                Map<String, Object> sMap = screensList.get(i);
                MockScreen sc = new MockScreen();
                sc.setGeneration(gen);
                sc.setSequence(i + 1);
                sc.setScreenName((String) sMap.getOrDefault("name", "Screen " + (i + 1)));
                sc.setScreenType((String) sMap.getOrDefault("screen_type", "dashboard"));
                sc.setPurpose((String) sMap.getOrDefault("purpose", ""));
                sc.setUserRole((String) sMap.getOrDefault("user_role", "Enterprise User"));
                sc.setWorkflowState((String) sMap.getOrDefault("workflow_state", ""));
                sc.setSpecificationJson(objectMapper.writeValueAsString(sMap));
                sc.setStatus("PENDING");
                screenEntities.add(mockScreenRepository.save(sc));
            }

            // STEP 3: RENDER SCREENS ONE BY ONE (Section 8)
            updateJobStatus(gen, "GENERATING", null, null);
            Path jobDir = getStorageDirectory(jobId);
            Files.createDirectories(jobDir);

            int completedCount = 0;
            for (MockScreen sc : screenEntities) {
                gen.setCurrentScreen(sc.getScreenName());
                gen.setCurrentScreenSequence(sc.getSequence());
                generationRepository.save(gen);

                sc.setStatus("GENERATING");
                mockScreenRepository.save(sc);

                try {
                    Map<String, Object> specMap = objectMapper.readValue(sc.getSpecificationJson(), new TypeReference<>() {});
                    Map<String, Object> renderReq = new HashMap<>();
                    renderReq.put("specification", specMap);
                    renderReq.put("design_context", designContext);

                    Map<String, Object> renderResp = aiServiceClient.renderMockScreen(renderReq);
                    String imgB64 = (String) renderResp.get("image_base64");
                    if (imgB64 != null && !imgB64.isBlank()) {
                        byte[] imgBytes = Base64.getDecoder().decode(imgB64);
                        sc.setImageData(imgBytes);

                        Path imgPath = jobDir.resolve("screen-" + sc.getSequence() + ".png");
                        Files.write(imgPath, imgBytes);
                        sc.setImagePath(imgPath.toString());
                        sc.setStatus("COMPLETED");
                        sc.setErrorMessage(null);
                        completedCount++;
                    } else {
                        throw new RuntimeException("AI service returned empty image data");
                    }
                } catch (Exception screenErr) {
                    log.error("Failed to render screen {} ({}): {}", sc.getSequence(), sc.getScreenName(), screenErr.getMessage());
                    sc.setStatus("FAILED");
                    sc.setErrorMessage(screenErr.getMessage());
                }
                mockScreenRepository.save(sc);

                gen.setCompletedScreens(completedCount);
                generationRepository.save(gen);
            }

            // STEP 4: COMBINE INTO CONSOLIDATED PDF (Section 17)
            updateJobStatus(gen, "COMBINING", null, null);
            List<MockScreen> finalScreens = mockScreenRepository.findByGenerationIdOrderBySequenceAsc(gen.getId());
            List<Map<String, Object>> pdfScreens = new ArrayList<>();
            for (MockScreen s : finalScreens) {
                if ("COMPLETED".equalsIgnoreCase(s.getStatus()) && s.getImageData() != null) {
                    Map<String, Object> ps = new HashMap<>();
                    ps.put("sequence", s.getSequence());
                    ps.put("name", s.getScreenName());
                    ps.put("screenType", s.getScreenType());
                    ps.put("purpose", s.getPurpose());
                    ps.put("userRole", s.getUserRole());
                    ps.put("workflowState", s.getWorkflowState());
                    ps.put("image_base64", Base64.getEncoder().encodeToString(s.getImageData()));
                    pdfScreens.add(ps);
                }
            }

            if (!pdfScreens.isEmpty()) {
                try {
                    Map<String, Object> pdfReq = new HashMap<>();
                    pdfReq.put("application_name", appName);
                    pdfReq.put("project_name", projName);
                    pdfReq.put("brd_name", docName);
                    pdfReq.put("summary", appSummary);
                    pdfReq.put("screens", pdfScreens);

                    Map<String, Object> pdfResp = aiServiceClient.compileMockScreenPdf(pdfReq);
                    String pdfB64 = (String) pdfResp.get("pdf_base64");
                    if (pdfB64 != null) {
                        byte[] pdfBytes = Base64.getDecoder().decode(pdfB64);
                        gen.setPdfData(pdfBytes);
                        Path pdfPath = jobDir.resolve("mock-screens-" + jobId + ".pdf");
                        Files.write(pdfPath, pdfBytes);
                        gen.setPdfPath(pdfPath.toString());
                    }
                } catch (Exception pdfErr) {
                    log.error("PDF combination failed for job {}: {}", jobId, pdfErr.getMessage());
                }
            }

            String finalStatus = completedCount == screenEntities.size() ? "COMPLETED"
                    : (completedCount > 0 ? "PARTIAL_SUCCESS" : "FAILED");
            gen.setStatus(finalStatus);
            gen.setCompletedAt(LocalDateTime.now());
            generationRepository.save(gen);

            long duration = System.currentTimeMillis() - startTime;
            auditService.logAuditFull("Mock Screens", "GENERATE_MOCK_SCREENS", userName != null ? userName : "User",
                    "USER", "Generated " + completedCount + " mock screens from BRD: " + docName,
                    null, "Gemini", "v3.5", "COMPLETED", finalStatus, duration, null, projName, docName, "v1.0", "BRD");

            log.info("Finished mock screen generation for job {} with status {} in {} ms", jobId, finalStatus, duration);

        } catch (Exception e) {
            log.error("Fatal failure during mock screen generation for job {}: {}", jobId, e.getMessage(), e);
            gen.setStatus("FAILED");
            gen.setErrorMessage(e.getMessage());
            gen.setCompletedAt(LocalDateTime.now());
            generationRepository.save(gen);

            long duration = System.currentTimeMillis() - startTime;
            auditService.logAuditFull("Mock Screens", "GENERATE_MOCK_SCREENS", userName != null ? userName : "User",
                    "USER", "Failed mock screen generation: " + e.getMessage(), null, "Gemini", "v3.5",
                    null, "FAILED", duration, e.getMessage(), projName, docName, "v1.0", "BRD");
        }
    }

    public MockScreenJobResponse getJobStatus(String jobId) {
        MockScreenGeneration gen = generationRepository.findByJobId(jobId)
                .orElseThrow(() -> new IllegalArgumentException("Job not found: " + jobId));

        List<MockScreen> screens = mockScreenRepository.findByGenerationIdOrderBySequenceAsc(gen.getId());
        Document doc = documentRepository.findById(gen.getDocumentId()).orElse(null);
        return buildJobResponse(gen, screens, doc);
    }

    public List<ScreenDto> getJobScreens(String jobId) {
        MockScreenGeneration gen = generationRepository.findByJobId(jobId)
                .orElseThrow(() -> new IllegalArgumentException("Job not found: " + jobId));

        return mockScreenRepository.findByGenerationIdOrderBySequenceAsc(gen.getId()).stream()
                .map(this::mapToScreenDto)
                .collect(Collectors.toList());
    }

    public byte[] getPdfBytes(String jobId) {
        MockScreenGeneration gen = generationRepository.findByJobId(jobId)
                .orElseThrow(() -> new IllegalArgumentException("Job not found: " + jobId));

        byte[] pdf = generationRepository.findPdfDataByJobId(jobId);
        if (pdf != null && pdf.length > 0) return pdf;

        if (gen.getPdfPath() != null) {
            try {
                Path p = Path.of(gen.getPdfPath());
                if (Files.exists(p)) return Files.readAllBytes(p);
            } catch (IOException ignored) {}
        }
        throw new IllegalStateException("PDF is not ready or failed to generate for job " + jobId);
    }

    public byte[] getScreenImageBytes(Long screenId) {
        MockScreen sc = mockScreenRepository.findById(screenId)
                .orElseThrow(() -> new IllegalArgumentException("Mock screen not found: " + screenId));

        byte[] img = mockScreenRepository.findImageDataById(screenId);
        if (img != null && img.length > 0) return img;

        if (sc.getImagePath() != null) {
            try {
                Path p = Path.of(sc.getImagePath());
                if (Files.exists(p)) return Files.readAllBytes(p);
            } catch (IOException ignored) {}
        }
        throw new IllegalStateException("Screen image not available for screen ID " + screenId);
    }

    /**
     * Section 16 & 26: Retry generation for a single failed screen.
     */
    @Transactional
    public ScreenDto retryScreen(Long screenId) {
        MockScreen sc = mockScreenRepository.findById(screenId)
                .orElseThrow(() -> new IllegalArgumentException("Screen not found: " + screenId));

        MockScreenGeneration gen = sc.getGeneration();
        sc.setStatus("GENERATING");
        mockScreenRepository.save(sc);

        try {
            Map<String, Object> specMap = objectMapper.readValue(sc.getSpecificationJson(), new TypeReference<>() {});
            Map<String, Object> designMap = gen.getDesignSystemJson() != null
                    ? objectMapper.readValue(gen.getDesignSystemJson(), new TypeReference<>() {})
                    : Collections.emptyMap();

            Map<String, Object> renderReq = new HashMap<>();
            renderReq.put("specification", specMap);
            renderReq.put("design_context", designMap);

            Map<String, Object> renderResp = aiServiceClient.renderMockScreen(renderReq);
            String imgB64 = (String) renderResp.get("image_base64");
            if (imgB64 != null) {
                byte[] imgBytes = Base64.getDecoder().decode(imgB64);
                sc.setImageData(imgBytes);

                Path jobDir = getStorageDirectory(gen.getJobId());
                Files.createDirectories(jobDir);
                Path imgPath = jobDir.resolve("screen-" + sc.getSequence() + ".png");
                Files.write(imgPath, imgBytes);
                sc.setImagePath(imgPath.toString());
                sc.setStatus("COMPLETED");
                sc.setErrorMessage(null);
                mockScreenRepository.save(sc);

                // Re-compile PDF if all screens are completed
                recompilePdfForJob(gen);
            }
        } catch (Exception e) {
            sc.setStatus("FAILED");
            sc.setErrorMessage(e.getMessage());
            mockScreenRepository.save(sc);
            throw new RuntimeException("Screen retry failed: " + e.getMessage(), e);
        }

        return mapToScreenDto(sc);
    }

    private void recompilePdfForJob(MockScreenGeneration gen) {
        try {
            List<MockScreen> screens = mockScreenRepository.findByGenerationIdOrderBySequenceAsc(gen.getId());
            List<Map<String, Object>> pdfScreens = new ArrayList<>();
            for (MockScreen s : screens) {
                if ("COMPLETED".equalsIgnoreCase(s.getStatus()) && s.getImageData() != null) {
                    Map<String, Object> ps = new HashMap<>();
                    ps.put("sequence", s.getSequence());
                    ps.put("name", s.getScreenName());
                    ps.put("screenType", s.getScreenType());
                    ps.put("purpose", s.getPurpose());
                    ps.put("userRole", s.getUserRole());
                    ps.put("workflowState", s.getWorkflowState());
                    ps.put("image_base64", Base64.getEncoder().encodeToString(s.getImageData()));
                    pdfScreens.add(ps);
                }
            }
            if (!pdfScreens.isEmpty()) {
                Map<String, Object> pdfReq = new HashMap<>();
                pdfReq.put("application_name", gen.getApplicationName() != null ? gen.getApplicationName() : "Enterprise App");
                pdfReq.put("project_name", "Enterprise Project");
                pdfReq.put("brd_name", "BRD Specification");
                pdfReq.put("summary", gen.getApplicationSummary());
                pdfReq.put("screens", pdfScreens);

                Map<String, Object> pdfResp = aiServiceClient.compileMockScreenPdf(pdfReq);
                String pdfB64 = (String) pdfResp.get("pdf_base64");
                if (pdfB64 != null) {
                    byte[] pdfBytes = Base64.getDecoder().decode(pdfB64);
                    gen.setPdfData(pdfBytes);
                    generationRepository.save(gen);
                }
            }
        } catch (Exception ignored) {}
    }

    public List<MockScreenJobResponse> getGenerationHistory() {
        List<MockScreenGeneration> history = generationRepository.findAllByOrderByCreatedAtDesc();
        return history.stream().map(g -> {
            Document doc = documentRepository.findById(g.getDocumentId()).orElse(null);
            List<MockScreen> screens = mockScreenRepository.findByGenerationIdOrderBySequenceAsc(g.getId());
            return buildJobResponse(g, screens, doc);
        }).collect(Collectors.toList());
    }

    private String retrieveCompleteBrdText(Long documentId, Document doc) {
        // 1. Try Document content API (concatenated Chroma chunks)
        try {
            String content = documentService.getDocumentContent(documentId);
            if (content != null && content.length() > 500) {
                return content;
            }
        } catch (Exception ignored) {}

        // 2. Try DB Chunks
        List<com.example.copilot.entity.DocumentChunk> chunks = documentChunkRepository.findByDocumentIdOrderByChunkIndexAsc(documentId);
        if (chunks != null && !chunks.isEmpty()) {
            return chunks.stream().map(com.example.copilot.entity.DocumentChunk::getChunkText).collect(Collectors.joining("\n\n"));
        }

        // 3. Extract directly from stored original file bytes
        try {
            byte[] fileBytes = documentService.getOriginalFileBytes(documentId);
            if (fileBytes != null && fileBytes.length > 0) {
                // If it's plain text
                String text = new String(fileBytes, java.nio.charset.StandardCharsets.UTF_8);
                if (text.contains("Business Requirements") || text.contains("Requirement") || text.length() > 200) {
                    return text;
                }
            }
        } catch (Exception ignored) {}

        return doc != null ? doc.getFileName() : "";
    }

    private void updateJobStatus(MockScreenGeneration gen, String status, String currentScreen, Integer currentSeq) {
        gen.setStatus(status);
        if (currentScreen != null) gen.setCurrentScreen(currentScreen);
        if (currentSeq != null) gen.setCurrentScreenSequence(currentSeq);
        generationRepository.save(gen);
    }

    private Path getStorageDirectory(String jobId) {
        Path root = Path.of("backend", "uploads", "mock-screens", jobId).toAbsolutePath().normalize();
        if (!Files.exists(root.getParent())) {
            root = Path.of("uploads", "mock-screens", jobId).toAbsolutePath().normalize();
        }
        return root;
    }

    private MockScreenJobResponse buildJobResponse(MockScreenGeneration gen, List<MockScreen> screens, Document doc) {
        String projName = "General Enterprise";
        if (gen.getProjectId() != null) {
            projName = projectRepository.findById(gen.getProjectId()).map(Project::getProjectName).orElse("General Enterprise");
        }

        List<ScreenDto> screenDtos = screens.stream().map(this::mapToScreenDto).collect(Collectors.toList());
        String pdfUrl = ("COMPLETED".equalsIgnoreCase(gen.getStatus()) || "PARTIAL_SUCCESS".equalsIgnoreCase(gen.getStatus()))
                ? "/api/mock-screens/jobs/" + gen.getJobId() + "/pdf"
                : null;

        return MockScreenJobResponse.builder()
                .jobId(gen.getJobId())
                .documentId(gen.getDocumentId())
                .documentName(doc != null ? doc.getFileName() : "BRD #" + gen.getDocumentId())
                .projectName(projName)
                .status(gen.getStatus())
                .totalScreens(gen.getTotalScreens())
                .completedScreens(gen.getCompletedScreens())
                .currentScreen(gen.getCurrentScreen())
                .currentScreenSequence(gen.getCurrentScreenSequence())
                .applicationName(gen.getApplicationName())
                .applicationSummary(gen.getApplicationSummary())
                .screens(screenDtos)
                .pdfUrl(pdfUrl)
                .error(gen.getErrorMessage())
                .createdAt(gen.getCreatedAt())
                .completedAt(gen.getCompletedAt())
                .build();
    }

    private ScreenDto mapToScreenDto(MockScreen sc) {
        String imgUrl = "COMPLETED".equalsIgnoreCase(sc.getStatus())
                ? "/api/mock-screens/" + sc.getId() + "/image"
                : null;

        return ScreenDto.builder()
                .id(sc.getId())
                .sequence(sc.getSequence())
                .name(sc.getScreenName())
                .screenType(sc.getScreenType())
                .purpose(sc.getPurpose())
                .userRole(sc.getUserRole())
                .workflowState(sc.getWorkflowState())
                .status(sc.getStatus())
                .imageUrl(imgUrl)
                .errorMessage(sc.getErrorMessage())
                .specificationJson(sc.getSpecificationJson())
                .build();
    }
}
