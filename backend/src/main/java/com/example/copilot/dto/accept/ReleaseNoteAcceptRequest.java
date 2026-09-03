package com.example.copilot.dto.accept;

import lombok.Data;
import java.util.List;

@Data
public class ReleaseNoteAcceptRequest {
    private String version;
    private String sprintInformation;
    private String summary;
    private List<String> newFeatures;
    private List<String> improvements;
    private List<String> bugFixes;
    private List<String> breakingChanges;
    private List<String> knownIssues;
    private String technicalNotes;
    private List<String> sources;
    private String model;
    private String promptVersion;
    private Long executionTimeMs;
}
