package com.example.copilot.dto.accept;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.Data;
import java.util.List;

@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class RequirementBulkAcceptRequest {
    /** BRD document name e.g. "Project1_BRD.pdf" */
    private String brdName;

    /** AI model used */
    private String model;

    /** Prompt version */
    private String promptVersion;

    /** Execution time in ms */
    private Long executionTimeMs;

    /** Retrieved BRD sources */
    private List<String> sources;

    /** All requirement items to be saved as separate rows */
    private List<RequirementItemRequest> items;
}
