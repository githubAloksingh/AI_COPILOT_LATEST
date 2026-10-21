package com.example.copilot.controller;

import com.example.copilot.dto.mockscreen.MockScreenJobResponse;
import com.example.copilot.dto.mockscreen.ScreenDto;
import com.example.copilot.service.MockScreenService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.List;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class MockScreenControllerTest {

    private MockScreenService service;
    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        service = mock(MockScreenService.class);
        mockMvc = MockMvcBuilders.standaloneSetup(new MockScreenController(service)).build();
    }

    @Test
    void generateAndPollUsePipelineAJobContract() throws Exception {
        MockScreenJobResponse queuedJob = MockScreenJobResponse.builder()
                .jobId("JOB-1")
                .status("QUEUED")
                .build();
        MockScreenJobResponse runningJob = MockScreenJobResponse.builder()
                .jobId("JOB-1")
                .status("GENERATING")
                .totalScreens(2)
                .completedScreens(1)
                .build();
        when(service.createGenerationJob(42L, "Alice")).thenReturn(queuedJob);
        when(service.getJobStatus("JOB-1")).thenReturn(runningJob);
        when(service.getJobScreens("JOB-1")).thenReturn(List.of(
                ScreenDto.builder().id(7L).sequence(1).status("COMPLETED").build()
        ));

        mockMvc.perform(post("/api/mock-screens/generate")
                        .contentType(MediaType.APPLICATION_JSON)
                        .header("X-User-Name", "Alice")
                        .content("{\"documentId\":42}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.jobId").value("JOB-1"))
                .andExpect(jsonPath("$.data.status").value("QUEUED"));
        verify(service).processGenerationJobAsync("JOB-1", 42L, "Alice");

        mockMvc.perform(get("/api/mock-screens/jobs/JOB-1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("GENERATING"))
                .andExpect(jsonPath("$.data.completedScreens").value(1));

        mockMvc.perform(get("/api/mock-screens/jobs/JOB-1/screens"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].id").value(7))
                .andExpect(jsonPath("$.data[0].status").value("COMPLETED"));
    }

    @Test
    void retriesScreensAndServesPersistedImagesAndPdfBytes() throws Exception {
        byte[] image = new byte[]{1, 2, 3};
        byte[] pdf = new byte[]{37, 80, 68, 70};
        when(service.retryScreen(7L)).thenReturn(ScreenDto.builder()
                .id(7L)
                .sequence(1)
                .status("COMPLETED")
                .imageUrl("/api/mock-screens/7/image")
                .build());
        when(service.getScreenImageBytes(7L)).thenReturn(image);
        when(service.getPdfBytes("JOB-1")).thenReturn(pdf);

        mockMvc.perform(post("/api/mock-screens/7/retry"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("COMPLETED"));

        mockMvc.perform(get("/api/mock-screens/7/image"))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.IMAGE_PNG))
                .andExpect(content().bytes(image));

        mockMvc.perform(get("/api/mock-screens/jobs/JOB-1/pdf"))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_PDF))
                .andExpect(header().string("Content-Disposition",
                        "attachment; filename=\"mock-screens-JOB-1.pdf\""))
                .andExpect(content().bytes(pdf));
    }

    @Test
    void historyRemainsAvailableAndPipelineBJobRouteIsNotMapped() throws Exception {
        when(service.getGenerationHistory()).thenReturn(List.of(
                MockScreenJobResponse.builder().jobId("JOB-1").status("COMPLETED").build()
        ));

        mockMvc.perform(get("/api/mock-screens/history"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].jobId").value("JOB-1"));

        mockMvc.perform(get("/api/copilot/mock-screens/jobs/JOB-1"))
                .andExpect(status().isNotFound());
    }
}
