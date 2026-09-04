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
    void testGenerateRequirement_ReturnsAiResponse() {
        RequirementRequest request = new RequirementRequest();
        request.setTitle("Feature X");
        request.setDescription("Feature description");
        request.setPriority("HIGH");

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
}
