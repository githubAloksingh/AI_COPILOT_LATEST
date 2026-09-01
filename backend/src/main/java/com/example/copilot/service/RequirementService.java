package com.example.copilot.service;

import com.example.copilot.client.AiServiceClient;
import com.example.copilot.dto.RequirementRequest;
import com.example.copilot.dto.RequirementResponseDto;
import com.example.copilot.dto.ai.AiRequirementResponse;
import com.example.copilot.entity.Requirement;
import com.example.copilot.repository.RequirementRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class RequirementService {

    private final AiServiceClient aiServiceClient;
    private final RequirementRepository requirementRepository;
    private final AuditService auditService;

    public Requirement generateRequirement(RequirementRequest request) {
        long startTime = System.currentTimeMillis();
        String feature = "REQUIREMENT_ASSISTANT";
        String status = "SUCCESS";
        String errorMsg = null;
        List<String> sources = null;

        try {
            AiRequirementResponse aiResponse = aiServiceClient.generateRequirement(request);
            RequirementResponseDto parsedResponse = aiResponse.getResult();
            sources = aiResponse.getSources();

            Requirement requirement = new Requirement();
            requirement.setTitle(request.getTitle());
            requirement.setDescription(request.getDescription());
            requirement.setPriority(request.getPriority());

            if (parsedResponse != null) {
                requirement.setSummary(parsedResponse.getSummary());
                requirement.setUserStory(parsedResponse.getUserStory());
                requirement.setAcceptanceCriteria(parsedResponse.getAcceptanceCriteria());
                requirement.setAssumptions(parsedResponse.getAssumptions());
                requirement.setDependencies(parsedResponse.getDependencies());
                requirement.setEdgeCases(parsedResponse.getEdgeCases());
            }
            requirement.setSources(sources);

            Requirement saved = requirementRepository.save(requirement);

            auditService.logAudit(
                    feature,
                    request.getDescription(),
                    sources,
                    aiResponse.getModel() != null ? aiResponse.getModel() : "gemini-3.7-flash",
                    aiResponse.getPrompt_version() != null ? aiResponse.getPrompt_version() : "requirement-v1",
                    parsedResponse != null ? parsedResponse.toString() : "",
                    status,
                    System.currentTimeMillis() - startTime,
                    null
            );
            return saved;

        } catch (Exception e) {
            status = "FAILED";
            errorMsg = e.getMessage();
            log.error("Error generating requirement: ", e);
            auditService.logAudit(
                    feature,
                    request.getDescription(),
                    sources,
                    "gemini-3.7-flash",
                    "requirement-v1",
                    null,
                    status,
                    System.currentTimeMillis() - startTime,
                    errorMsg
            );
            throw new RuntimeException("Failed to generate requirement", e);
        }
    }
}
