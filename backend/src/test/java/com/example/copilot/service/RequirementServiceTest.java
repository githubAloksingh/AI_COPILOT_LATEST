package com.example.copilot.service;

import com.example.copilot.client.AiServiceClient;
import com.example.copilot.dto.RequirementRequest;
import com.example.copilot.dto.RequirementResponseDto;
import com.example.copilot.dto.ai.AiRequirementResponse;
import com.example.copilot.entity.Requirement;
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

    @InjectMocks
    private RequirementService requirementService;

    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);
    }

    @Test
    void testGenerateRequirement_PersistsToSql() {
        RequirementRequest request = new RequirementRequest();
        request.setTitle("Feature X");
        request.setDescription("Feature description");
        request.setPriority("HIGH");

        RequirementResponseDto resultDto = new RequirementResponseDto();
        resultDto.setSummary("Summary X");
        resultDto.setUserStory("As a dev...");
        resultDto.setAcceptanceCriteria(List.of("Must pass"));

        AiRequirementResponse aiResponse = new AiRequirementResponse();
        aiResponse.setResult(resultDto);
        aiResponse.setSources(List.of("Source 1"));
        aiResponse.setModel("gemini-3.7-flash");
        aiResponse.setPrompt_version("requirement-v1");

        when(aiServiceClient.generateRequirement(any())).thenReturn(aiResponse);
        when(requirementRepository.save(any(Requirement.class))).thenAnswer(invocation -> invocation.getArgument(0));

        Requirement saved = requirementService.generateRequirement(request);

        assertNotNull(saved);
        assertEquals("Feature X", saved.getTitle());
        assertEquals("Summary X", saved.getSummary());
        assertEquals(1, saved.getSources().size());

        verify(requirementRepository, times(1)).save(any(Requirement.class));
        verify(auditService, times(1)).logAudit(
                eq("REQUIREMENT_ASSISTANT"),
                eq("Feature description"),
                any(),
                eq("gemini-3.7-flash"),
                eq("requirement-v1"),
                any(),
                eq("SUCCESS"),
                anyLong(),
                isNull()
        );
    }
}
