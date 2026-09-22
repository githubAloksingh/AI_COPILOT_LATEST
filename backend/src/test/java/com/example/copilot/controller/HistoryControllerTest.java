package com.example.copilot.controller;

import com.example.copilot.dto.ApiResponse;
import com.example.copilot.dto.HistoryItemDto;
import com.example.copilot.entity.AuditLog;
import com.example.copilot.entity.Document;
import com.example.copilot.entity.Project;
import com.example.copilot.repository.AuditLogRepository;
import com.example.copilot.repository.DocumentRepository;
import com.example.copilot.repository.ProjectRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import org.springframework.http.ResponseEntity;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

public class HistoryControllerTest {

    @Mock
    private AuditLogRepository auditLogRepository;

    @Mock
    private ProjectRepository projectRepository;

    @Mock
    private DocumentRepository documentRepository;

    @InjectMocks
    private HistoryController historyController;

    private Project testProject;
    private Document testDoc;

    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);

        testProject = new Project();
        testProject.setId(1L);
        testProject.setProjectName("Project Alpha");

        testDoc = new Document();
        testDoc.setId(10L);
        testDoc.setFileName("BRD_FeatureX.pdf");
        testDoc.setVersion("2.0");

        when(projectRepository.findById(1L)).thenReturn(Optional.of(testProject));
        when(documentRepository.findByProjectIdOrderByCreatedAtDesc(1L)).thenReturn(List.of(testDoc));
    }

    @Test
    void testGetFeatureHistory_TechnicalDesign_NoDocument_ReturnsEmptyMessage() {
        ApiResponse<List<HistoryItemDto>> response = historyController.getFeatureHistory(1L, null, "technical_design");

        assertNotNull(response);
        assertTrue(response.isSuccess());
        assertEquals("No Technical Design generated yet.", response.getMessage());
        assertTrue(response.getData().isEmpty());
    }

    @Test
    void testGetFeatureHistory_TechnicalDesign_ReturnsPersistedGenerationsOnly() {
        AuditLog gen1 = new AuditLog();
        gen1.setId(101L);
        gen1.setAction("GENERATE");
        gen1.setFeature("Technical Design");
        gen1.setDocumentId(10L);
        gen1.setDocumentName("BRD_FeatureX.pdf");
        gen1.setDocumentVersion("1.0");
        gen1.setOutput("{\"technicalDesign\":{\"title\":\"TD 1\"}}");
        gen1.setCreatedAt(LocalDateTime.now().minusHours(2));

        AuditLog gen2 = new AuditLog();
        gen2.setId(102L);
        gen2.setAction("GENERATE");
        gen2.setFeature("Technical Design");
        gen2.setDocumentId(10L);
        gen2.setDocumentName("BRD_FeatureX.pdf");
        gen2.setDocumentVersion("1.1");
        gen2.setOutput("{\"technicalDesign\":{\"title\":\"TD 2\"}}");
        gen2.setCreatedAt(LocalDateTime.now().minusHours(1));

        AuditLog nonGen = new AuditLog();
        nonGen.setId(103L);
        nonGen.setAction("ACCEPT");
        nonGen.setFeature("Technical Design");
        nonGen.setDocumentId(10L);

        when(auditLogRepository.findByProjectAndDocumentAndFeatures(eq(1L), eq("Project Alpha"), eq(10L), eq("BRD_FeatureX.pdf"), anyList()))
                .thenReturn(List.of(gen1, gen2, nonGen));

        ApiResponse<List<HistoryItemDto>> response = historyController.getFeatureHistory(1L, 10L, "technical_design");

        assertNotNull(response);
        assertTrue(response.isSuccess());
        assertEquals(2, response.getData().size());

        HistoryItemDto item1 = response.getData().get(0);
        assertEquals(101L, item1.getId());
        assertEquals("1.0", item1.getVersion());
        assertEquals("BRD_FeatureX.pdf", item1.getDocumentName());
        assertEquals("technical_design", item1.getFeature());
        assertTrue(item1.isCanView());

        HistoryItemDto item2 = response.getData().get(1);
        assertEquals(102L, item2.getId());
        assertEquals("1.1", item2.getVersion());
    }

    @Test
    void testDownloadHistoryContent_TechnicalDesign_ReturnsCorrectFilename() {
        AuditLog log = new AuditLog();
        log.setId(201L);
        log.setFeature("Technical Design");
        log.setDocumentVersion("1.1");
        log.setOutput("{\"technicalDesign\":{}}");

        when(auditLogRepository.findById(201L)).thenReturn(Optional.of(log));

        ResponseEntity<byte[]> response = historyController.downloadHistoryContent(201L);

        assertNotNull(response);
        assertEquals(200, response.getStatusCode().value());
        assertTrue(response.getHeaders().getContentDisposition().getFilename().contains("Technical_Design_v1.1.json"));
    }

    @Test
    void testGetFeatureHistory_FunctionalDesign_NoDocumentId_ReturnsEmptyWithNoFunctionalDesignsGeneratedYet() {
        Project project = new Project();
        project.setId(1L);
        project.setProjectName("Project Alpha");
        when(projectRepository.findById(1L)).thenReturn(Optional.of(project));

        ApiResponse<List<HistoryItemDto>> response = historyController.getFeatureHistory(1L, null, "functional_design");

        assertNotNull(response);
        assertTrue(response.isSuccess());
        assertTrue(response.getData().isEmpty());
        assertEquals("No Functional Designs generated yet.", response.getMessage());
    }

    @Test
    void testGetFeatureHistory_FunctionalDesign_FiltersOnlyGenerateAndFormatsVersions() {
        Project project = new Project();
        project.setId(1L);
        project.setProjectName("Project Alpha");
        when(projectRepository.findById(1L)).thenReturn(Optional.of(project));

        Document doc = new Document();
        doc.setId(10L);
        doc.setFileName("BRD_FeatureY.pdf");
        when(documentRepository.findByProjectIdOrderByCreatedAtDesc(1L)).thenReturn(List.of(doc));

        AuditLog gen1 = new AuditLog();
        gen1.setId(301L);
        gen1.setAction("GENERATE");
        gen1.setFeature("Functional Design");
        gen1.setDocumentId(10L);
        gen1.setDocumentName("BRD_FeatureY.pdf");
        gen1.setDocumentVersion("1.0");
        gen1.setOutput("{\"functionalDesign\":{\"title\":\"FD 1\"}}");
        gen1.setCreatedAt(LocalDateTime.now().minusHours(2));

        AuditLog gen2 = new AuditLog();
        gen2.setId(302L);
        gen2.setAction("GENERATE");
        gen2.setFeature("Functional Design");
        gen2.setDocumentId(10L);
        gen2.setDocumentName("BRD_FeatureY.pdf");
        gen2.setDocumentVersion("1.1");
        gen2.setOutput("{\"functionalDesign\":{\"title\":\"FD 2\"}}");
        gen2.setCreatedAt(LocalDateTime.now().minusHours(1));

        AuditLog nonGen = new AuditLog();
        nonGen.setId(303L);
        nonGen.setAction("ACCEPT");
        nonGen.setFeature("Functional Design");
        nonGen.setDocumentId(10L);

        when(auditLogRepository.findByProjectAndDocumentAndFeatures(eq(1L), eq("Project Alpha"), eq(10L), eq("BRD_FeatureY.pdf"), anyList()))
                .thenReturn(List.of(gen1, gen2, nonGen));

        ApiResponse<List<HistoryItemDto>> response = historyController.getFeatureHistory(1L, 10L, "functional_design");

        assertNotNull(response);
        assertTrue(response.isSuccess());
        assertEquals(2, response.getData().size());

        HistoryItemDto item1 = response.getData().get(0);
        assertEquals(301L, item1.getId());
        assertEquals("1.0", item1.getVersion());
        assertEquals("BRD_FeatureY.pdf", item1.getDocumentName());
        assertEquals("functional_design", item1.getFeature());
        assertTrue(item1.isCanView());

        HistoryItemDto item2 = response.getData().get(1);
        assertEquals(302L, item2.getId());
        assertEquals("1.1", item2.getVersion());
    }

    @Test
    void testDownloadHistoryContent_FunctionalDesign_ReturnsCorrectFilename() {
        AuditLog log = new AuditLog();
        log.setId(401L);
        log.setFeature("Functional Design");
        log.setDocumentVersion("1.0");
        log.setOutput("{\"functionalDesign\":{}}");

        when(auditLogRepository.findById(401L)).thenReturn(Optional.of(log));

        ResponseEntity<byte[]> response = historyController.downloadHistoryContent(401L);

        assertNotNull(response);
        assertEquals(200, response.getStatusCode().value());
        assertTrue(response.getHeaders().getContentDisposition().getFilename().contains("Functional_Design_v1.0.json"));
    }

    @Test
    void testGetFeatureHistory_RequirementAssistant_NoDocumentId_ReturnsEmptyWithNoRequirementAssistantOutputsGeneratedYet() {
        Project project = new Project();
        project.setId(1L);
        project.setProjectName("Project Alpha");
        when(projectRepository.findById(1L)).thenReturn(Optional.of(project));

        ApiResponse<List<HistoryItemDto>> response = historyController.getFeatureHistory(1L, null, "requirement_assistant");

        assertNotNull(response);
        assertTrue(response.isSuccess());
        assertTrue(response.getData().isEmpty());
        assertEquals("No Requirement Assistant outputs generated yet.", response.getMessage());
    }

    @Test
    void testGetFeatureHistory_RequirementAssistant_FiltersOnlyGenerateAndFormatsVersions() {
        Project project = new Project();
        project.setId(1L);
        project.setProjectName("Project Alpha");
        when(projectRepository.findById(1L)).thenReturn(Optional.of(project));

        Document doc = new Document();
        doc.setId(10L);
        doc.setFileName("BRD_FeatureZ.pdf");
        when(documentRepository.findByProjectIdOrderByCreatedAtDesc(1L)).thenReturn(List.of(doc));

        AuditLog gen1 = new AuditLog();
        gen1.setId(501L);
        gen1.setAction("GENERATE");
        gen1.setFeature("Requirement Assistant");
        gen1.setDocumentId(10L);
        gen1.setDocumentName("BRD_FeatureZ.pdf");
        gen1.setDocumentVersion("1.0");
        gen1.setOutput("{\"requirements\":[{\"title\":\"Req 1\"}]}");
        gen1.setCreatedAt(LocalDateTime.now().minusHours(2));

        AuditLog gen2 = new AuditLog();
        gen2.setId(502L);
        gen2.setAction("GENERATE");
        gen2.setFeature("Requirement Assistant");
        gen2.setDocumentId(10L);
        gen2.setDocumentName("BRD_FeatureZ.pdf");
        gen2.setDocumentVersion("1.1");
        gen2.setOutput("{\"requirements\":[{\"title\":\"Req 2\"}]}");
        gen2.setCreatedAt(LocalDateTime.now().minusHours(1));

        AuditLog nonGen = new AuditLog();
        nonGen.setId(503L);
        nonGen.setAction("ACCEPT");
        nonGen.setFeature("Requirement Assistant");
        nonGen.setDocumentId(10L);

        when(auditLogRepository.findByProjectAndDocumentAndFeatures(eq(1L), eq("Project Alpha"), eq(10L), eq("BRD_FeatureZ.pdf"), anyList()))
                .thenReturn(List.of(gen1, gen2, nonGen));

        ApiResponse<List<HistoryItemDto>> response = historyController.getFeatureHistory(1L, 10L, "requirement_assistant");

        assertNotNull(response);
        assertTrue(response.isSuccess());
        assertEquals(2, response.getData().size());

        HistoryItemDto item1 = response.getData().get(0);
        assertEquals(501L, item1.getId());
        assertEquals("1.0", item1.getVersion());
        assertEquals("BRD_FeatureZ.pdf", item1.getDocumentName());
        assertEquals("requirement_assistant", item1.getFeature());
        assertTrue(item1.isCanView());

        HistoryItemDto item2 = response.getData().get(1);
        assertEquals(502L, item2.getId());
        assertEquals("1.1", item2.getVersion());
    }

    @Test
    void testDownloadHistoryContent_RequirementAssistant_ReturnsCorrectFilename() {
        AuditLog log = new AuditLog();
        log.setId(601L);
        log.setFeature("Requirement Assistant");
        log.setDocumentVersion("1.0");
        log.setOutput("{\"requirements\":[]}");

        when(auditLogRepository.findById(601L)).thenReturn(Optional.of(log));

        ResponseEntity<byte[]> response = historyController.downloadHistoryContent(601L);

        assertNotNull(response);
        assertEquals(200, response.getStatusCode().value());
        assertTrue(response.getHeaders().getContentDisposition().getFilename().contains("Requirement_Assistant_v1.0.json"));
    }
}
