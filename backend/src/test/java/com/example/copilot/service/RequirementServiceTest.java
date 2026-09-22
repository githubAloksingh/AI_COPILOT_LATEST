package com.example.copilot.service;

import com.example.copilot.client.AiServiceClient;
import com.example.copilot.dto.RequirementRequest;
import com.example.copilot.dto.RequirementResponseDto;
import com.example.copilot.dto.ai.AiRequirementResponse;
import com.example.copilot.repository.RequirementRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

public class RequirementServiceTest {

    @Mock
    private AiServiceClient aiServiceClient;

    @Mock
    private RequirementRepository requirementRepository;

    @Mock
    private AuditService auditService;

    @Mock
    private com.example.copilot.repository.AuditLogRepository auditLogRepository;

    @Mock
    private com.fasterxml.jackson.databind.ObjectMapper objectMapper;

    @InjectMocks
    private RequirementService requirementService;

    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);
    }

    @Test
    void testGenerateRequirement_ReturnsAiResponse() {
        RequirementRequest request = new RequirementRequest();
        request.setTitle("Feature X");
        request.setDescription("Feature description");

        RequirementResponseDto resultDto = new RequirementResponseDto();
        resultDto.setSummary("Summary X");
        resultDto.setUserStory("As a dev...");

        AiRequirementResponse aiResponse = new AiRequirementResponse();
        aiResponse.setResult(resultDto);
        aiResponse.setSources(List.of("Source 1"));
        aiResponse.setModel("gemini-3.7-flash");
        aiResponse.setPrompt_version("requirement-v1");

        when(aiServiceClient.generateRequirement(any())).thenReturn(aiResponse);

        AiRequirementResponse response = requirementService.generateRequirement(request);

        assertNotNull(response);
        assertEquals("gemini-3.7-flash", response.getModel());
        assertEquals(1, response.getSources().size());

        verify(aiServiceClient, times(1)).generateRequirement(any());
    }

    @Test
    void testCalculateNextTechnicalDesignVersion_FirstGeneration_ReturnsOnePointZero() {
        when(auditLogRepository.findByProjectAndDocumentAndFeatures(eq(1L), any(), eq(10L), any(), any()))
                .thenReturn(List.of());

        String version = requirementService.calculateNextTechnicalDesignVersion(1L, "Proj", 10L, "doc.pdf");
        assertEquals("1.0", version);
    }

    @Test
    void testCalculateNextTechnicalDesignVersion_SecondGeneration_ReturnsOnePointOne() {
        com.example.copilot.entity.AuditLog log1 = new com.example.copilot.entity.AuditLog();
        log1.setAction("GENERATE");
        log1.setDocumentVersion("1.0");

        when(auditLogRepository.findByProjectAndDocumentAndFeatures(eq(1L), any(), eq(10L), any(), any()))
                .thenReturn(List.of(log1));

        String version = requirementService.calculateNextTechnicalDesignVersion(1L, "Proj", 10L, "doc.pdf");
        assertEquals("1.1", version);
    }

    @Test
    void testCalculateNextTechnicalDesignVersion_SubsequentGeneration_ReturnsNextMinor() {
        com.example.copilot.entity.AuditLog log1 = new com.example.copilot.entity.AuditLog();
        log1.setAction("GENERATE");
        log1.setDocumentVersion("1.0");

        com.example.copilot.entity.AuditLog log2 = new com.example.copilot.entity.AuditLog();
        log2.setAction("GENERATE");
        log2.setDocumentVersion("1.1");

        when(auditLogRepository.findByProjectAndDocumentAndFeatures(eq(1L), any(), eq(10L), any(), any()))
                .thenReturn(List.of(log1, log2));

        String version = requirementService.calculateNextTechnicalDesignVersion(1L, "Proj", 10L, "doc.pdf");
        assertEquals("1.2", version);
    }

    @Test
    void testGenerateTechnicalDesign_Success_CalculatesDynamicVersionAndLogsJson() throws Exception {
        RequirementRequest request = new RequirementRequest();
        request.setProjectId(1L);
        request.setProjectName("Project Alpha");
        request.setDocumentId("10");
        request.setDocumentName("BRD.pdf");
        request.setTitle("Technical Design Spec");

        when(auditLogRepository.findByProjectAndDocumentAndFeatures(eq(1L), any(), eq(10L), any(), any()))
                .thenReturn(List.of());

        AiRequirementResponse aiResponse = new AiRequirementResponse();
        aiResponse.setModel("gemini-3.7-flash");
        aiResponse.setPrompt_version("technical-v4");
        RequirementResponseDto responseDto = new RequirementResponseDto();
        responseDto.setTechnicalDesign(java.util.Map.of("title", "TD Title"));
        aiResponse.setResult(responseDto);
        aiResponse.setSources(List.of("BRD source"));

        when(aiServiceClient.generateTechnicalDesign(any())).thenReturn(aiResponse);
        when(objectMapper.writeValueAsString(any())).thenReturn("{\"technicalDesign\":{\"title\":\"TD Title\"}}");

        AiRequirementResponse result = requirementService.generateTechnicalDesign(request);

        assertNotNull(result);
        verify(auditService, times(1)).logAuditFull(
                eq("Technical Design"),
                eq("GENERATE"),
                any(),
                any(),
                any(),
                any(),
                eq("gemini-3.7-flash"),
                eq("technical-v4"),
                eq("{\"technicalDesign\":{\"title\":\"TD Title\"}}"),
                eq("SUCCESS"),
                anyLong(),
                isNull(),
                eq("Project Alpha"),
                eq("BRD.pdf"),
                eq("1.0"),
                any(),
                eq(1L),
                eq(10L)
        );
    }

    @Test
    void testCalculateNextFunctionalDesignVersion_NoPreviousLogs_ReturnsOnePointZero() {
        when(auditLogRepository.findByProjectAndDocumentAndFeatures(eq(1L), any(), eq(10L), any(), any()))
                .thenReturn(List.of());

        String version = requirementService.calculateNextFunctionalDesignVersion(1L, "Proj", 10L, "doc.pdf");
        assertEquals("1.0", version);
    }

    @Test
    void testCalculateNextFunctionalDesignVersion_ExistingLogs_IncrementsVersion() {
        com.example.copilot.entity.AuditLog log1 = new com.example.copilot.entity.AuditLog();
        log1.setAction("GENERATE");
        log1.setDocumentVersion("1.0");

        com.example.copilot.entity.AuditLog log2 = new com.example.copilot.entity.AuditLog();
        log2.setAction("GENERATE");
        log2.setDocumentVersion("1.1");

        when(auditLogRepository.findByProjectAndDocumentAndFeatures(eq(1L), any(), eq(10L), any(), any()))
                .thenReturn(List.of(log1, log2));

        String version = requirementService.calculateNextFunctionalDesignVersion(1L, "Proj", 10L, "doc.pdf");
        assertEquals("1.2", version);
    }

    @Test
    void testGenerateFunctionalDesign_Success_CalculatesDynamicVersionAndLogsJson() throws Exception {
        RequirementRequest request = new RequirementRequest();
        request.setProjectId(1L);
        request.setProjectName("Project Alpha");
        request.setDocumentId("10");
        request.setDocumentName("BRD.pdf");
        request.setTitle("Functional Design Spec");

        when(auditLogRepository.findByProjectAndDocumentAndFeatures(eq(1L), any(), eq(10L), any(), any()))
                .thenReturn(List.of());

        AiRequirementResponse aiResponse = new AiRequirementResponse();
        aiResponse.setModel("gemini-3.7-flash");
        aiResponse.setPrompt_version("functional-v2");
        RequirementResponseDto responseDto = new RequirementResponseDto();
        responseDto.setFunctionalDesign(java.util.Map.of("title", "FD Title"));
        aiResponse.setResult(responseDto);
        aiResponse.setSources(List.of("BRD source"));

        when(aiServiceClient.generateFunctionalDesign(any())).thenReturn(aiResponse);
        when(objectMapper.writeValueAsString(any())).thenReturn("{\"functionalDesign\":{\"title\":\"FD Title\"}}");

        AiRequirementResponse result = requirementService.generateFunctionalDesign(request);

        assertNotNull(result);
        verify(auditService, times(1)).logAuditFull(
                eq("Functional Design"),
                eq("GENERATE"),
                any(),
                any(),
                any(),
                any(),
                eq("gemini-3.7-flash"),
                eq("functional-v2"),
                eq("{\"functionalDesign\":{\"title\":\"FD Title\"}}"),
                eq("SUCCESS"),
                anyLong(),
                isNull(),
                eq("Project Alpha"),
                eq("BRD.pdf"),
                eq("1.0"),
                any(),
                eq(1L),
                eq(10L)
        );
    }

    @Test
    void testCalculateNextRequirementAssistantVersion_NoPreviousLogs_ReturnsOnePointZero() {
        when(auditLogRepository.findByProjectAndDocumentAndFeatures(eq(1L), any(), eq(10L), any(), any()))
                .thenReturn(List.of());

        String version = requirementService.calculateNextRequirementAssistantVersion(1L, "Proj", 10L, "doc.pdf");
        assertEquals("1.0", version);
    }

    @Test
    void testCalculateNextRequirementAssistantVersion_ExistingLogs_IncrementsVersion() {
        com.example.copilot.entity.AuditLog log1 = new com.example.copilot.entity.AuditLog();
        log1.setAction("GENERATE");
        log1.setDocumentVersion("1.0");

        com.example.copilot.entity.AuditLog log2 = new com.example.copilot.entity.AuditLog();
        log2.setAction("GENERATE");
        log2.setDocumentVersion("1.1");

        when(auditLogRepository.findByProjectAndDocumentAndFeatures(eq(1L), any(), eq(10L), any(), any()))
                .thenReturn(List.of(log1, log2));

        String version = requirementService.calculateNextRequirementAssistantVersion(1L, "Proj", 10L, "doc.pdf");
        assertEquals("1.2", version);
    }

    @Test
    void testGenerateRequirement_Success_CalculatesDynamicVersionAndLogsJson() throws Exception {
        RequirementRequest request = new RequirementRequest();
        request.setProjectId(1L);
        request.setProjectName("Project Alpha");
        request.setDocumentId("10");
        request.setDocumentName("BRD.pdf");
        request.setTitle("Requirement Spec");

        when(auditLogRepository.findByProjectAndDocumentAndFeatures(eq(1L), any(), eq(10L), any(), any()))
                .thenReturn(List.of());

        AiRequirementResponse aiResponse = new AiRequirementResponse();
        aiResponse.setModel("gemini-3.7-flash");
        aiResponse.setPrompt_version("requirement-v2");
        RequirementResponseDto responseDto = new RequirementResponseDto();
        aiResponse.setResult(responseDto);
        aiResponse.setSources(List.of("BRD source"));

        when(aiServiceClient.generateRequirement(any())).thenReturn(aiResponse);
        when(objectMapper.writeValueAsString(any())).thenReturn("{\"requirements\":[]}");

        AiRequirementResponse result = requirementService.generateRequirement(request);

        assertNotNull(result);
        verify(auditService, times(1)).logAuditFull(
                eq("Requirement Assistant"),
                eq("GENERATE"),
                any(),
                any(),
                any(),
                any(),
                eq("gemini-3.7-flash"),
                eq("requirement-v2"),
                eq("{\"requirements\":[]}"),
                eq("SUCCESS"),
                anyLong(),
                isNull(),
                eq("Project Alpha"),
                eq("BRD.pdf"),
                eq("1.0"),
                any(),
                eq(1L),
                eq(10L)
        );
    }
}
