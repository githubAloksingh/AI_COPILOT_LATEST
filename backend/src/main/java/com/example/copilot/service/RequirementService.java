package com.example.copilot.service;

import com.example.copilot.client.AiServiceClient;
import com.example.copilot.dto.RequirementRequest;
import com.example.copilot.dto.accept.RequirementAcceptRequest;
import com.example.copilot.dto.accept.RequirementBulkAcceptRequest;
import com.example.copilot.dto.accept.RequirementItemRequest;
import com.example.copilot.dto.ai.AiRequirementResponse;
import com.example.copilot.entity.Requirement;
import com.example.copilot.repository.RequirementRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class RequirementService {

    private final AiServiceClient aiServiceClient;
    private final RequirementRepository requirementRepository;
    private final AuditService auditService;

    public AiRequirementResponse generateRequirement(RequirementRequest request) {
        try {
            return aiServiceClient.generateRequirement(request);
        } catch (Exception e) {
            log.error("Error generating requirement preview: ", e);
            throw new RuntimeException("Failed to generate requirement: " + e.getMessage(), e);
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Single accept (backward compatible — kept for any existing callers)
    // ─────────────────────────────────────────────────────────────────────────
    @Transactional
    public Requirement acceptRequirement(RequirementAcceptRequest request) {
        Requirement requirement = new Requirement();
        requirement.setTitle(request.getTitle());
        requirement.setDescription(request.getDescription());
        requirement.setPriority(request.getPriority() != null ? request.getPriority() : "Medium");
        requirement.setSummary(request.getSummary());
        requirement.setUserStory(request.getUserStory());
        requirement.setAcceptanceCriteria(toGroundedList(request.getAcceptanceCriteria()));
        requirement.setAssumptions(toGroundedList(request.getAssumptions()));
        requirement.setDependencies(toGroundedList(request.getDependencies()));
        requirement.setEdgeCases(toGroundedList(request.getEdgeCases()));
        requirement.setSources(request.getSources());
        requirement.setModel(request.getModel());
        requirement.setPromptVersion(request.getPromptVersion());

        Requirement saved = requirementRepository.save(requirement);

        long execTime = request.getExecutionTimeMs() != null ? request.getExecutionTimeMs() : 0L;
        String model = request.getModel() != null ? request.getModel() : "gemini-3.7-flash";
        String promptVersion = request.getPromptVersion() != null ? request.getPromptVersion() : "requirement-v2";
        String outputStr = request.getSummary() != null ? request.getSummary() : "";

        auditService.logAudit(
                "REQUIREMENT_ASSISTANT",
                request.getDescription() != null ? request.getDescription() : request.getTitle(),
                request.getSources(),
                model,
                promptVersion,
                outputStr,
                "SUCCESS",
                execTime,
                null
        );

        return saved;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Bulk accept — saves EACH requirement as a SEPARATE row
    // ─────────────────────────────────────────────────────────────────────────
    @Transactional
    public List<Requirement> acceptAllRequirements(RequirementBulkAcceptRequest request) {
        List<RequirementItemRequest> items = request.getItems();
        if (items == null || items.isEmpty()) {
            throw new RuntimeException("No requirements provided for bulk accept.");
        }

        String brdName      = request.getBrdName() != null ? request.getBrdName() : "Unknown BRD";
        String model        = request.getModel() != null ? request.getModel() : "gemini-3.7-flash";
        String promptVer    = request.getPromptVersion() != null ? request.getPromptVersion() : "requirement-v2";
        long   execTime     = request.getExecutionTimeMs() != null ? request.getExecutionTimeMs() : 0L;
        List<String> sources = request.getSources() != null ? request.getSources() : new ArrayList<>();

        List<Requirement> savedList = new ArrayList<>();

        for (RequirementItemRequest item : items) {
            Requirement req = new Requirement();
            req.setBrdName(brdName);
            req.setRequirementId(item.getRequirementId());
            req.setTitle(item.getTitle());
            req.setDescription(item.getSummary());            // description = summary text
            req.setPriority(item.getPriority() != null ? item.getPriority() : "Medium");
            req.setSummary(item.getSummary());
            req.setUserStory(item.getUserStory());
            req.setAcceptanceCriteria(toGroundedList(item.getAcceptanceCriteria()));
            req.setAssumptions(toGroundedList(item.getAssumptions()));
            req.setDependencies(toGroundedList(item.getDependencies()));
            req.setEdgeCases(toGroundedList(item.getEdgeCases()));
            req.setSources(sources);
            req.setModel(model);
            req.setPromptVersion(promptVer);

            Requirement saved = requirementRepository.save(req);
            savedList.add(saved);

            // One audit log entry per requirement for full traceability
            auditService.logAudit(
                    "REQUIREMENT_ASSISTANT",
                    "[" + brdName + "] " + (item.getRequirementId() != null ? item.getRequirementId() : "") + " " + (item.getTitle() != null ? item.getTitle() : ""),
                    sources,
                    model,
                    promptVer,
                    item.getSummary() != null ? item.getSummary() : "",
                    "SUCCESS",
                    execTime,
                    null
            );
        }

        log.info("Bulk accepted {} requirements from BRD: {}", savedList.size(), brdName);
        return savedList;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Convert List<Object> of grounded items to List<Map<String,Object>>
    // Preserves {text, grounding, source[]} — NO data loss
    // ─────────────────────────────────────────────────────────────────────────
    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> toGroundedList(List<Object> list) {
        if (list == null) return new ArrayList<>();
        List<Map<String, Object>> result = new ArrayList<>();
        for (Object item : list) {
            if (item == null) continue;
            if (item instanceof Map) {
                // Already a grounded item map — store as-is
                Map<String, Object> map = new HashMap<>((Map<String, Object>) item);
                // Ensure required fields exist
                map.putIfAbsent("text", "");
                map.putIfAbsent("grounding", "EXPLICIT");
                map.putIfAbsent("source", new ArrayList<>());
                result.add(map);
            } else if (item instanceof String) {
                // Plain string — wrap as EXPLICIT grounded item
                Map<String, Object> map = new HashMap<>();
                map.put("text", item);
                map.put("grounding", "EXPLICIT");
                map.put("source", new ArrayList<>());
                result.add(map);
            } else {
                // Fallback
                Map<String, Object> map = new HashMap<>();
                map.put("text", item.toString());
                map.put("grounding", "EXPLICIT");
                map.put("source", new ArrayList<>());
                result.add(map);
            }
        }
        return result;
    }
}


