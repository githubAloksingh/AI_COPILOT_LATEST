package com.example.copilot.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class GroundedItemDto {
    private String text;
    private String grounding = "EXPLICIT"; // EXPLICIT, DERIVED, REQUIRES_CONFIRMATION
    private List<String> source = new ArrayList<>();

    @Override
    public String toString() {
        return text != null ? text : "";
    }
}
