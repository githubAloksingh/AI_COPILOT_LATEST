package com.example.copilot.controller;

import com.example.copilot.dto.ApiResponse;
import com.example.copilot.dto.MockScreensJobResponse;
import com.example.copilot.dto.MockScreensStartRequest;
import com.example.copilot.entity.MockScreensJobStatus;
import com.example.copilot.entity.MockScreensPdfArtifact;
import com.example.copilot.exception.MockScreensJobException;
import com.example.copilot.service.MockScreensJobService;
import com.example.copilot.service.MockScreensPdfArtifactService;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;

import java.net.URI;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class MockScreensJobControllerTest {

    private final MockScreensJobService jobService = mock(MockScreensJobService.class);
    private final MockScreensPdfArtifactService pdfArtifactService = mock(MockScreensPdfArtifactService.class);
    private final MockScreensJobController controller = new MockScreensJobController(jobService, pdfArtifactService);

    @Test
    void createJobReturnsAcceptedAndStatusLocation() {
        MockScreensStartRequest request = new MockScreensStartRequest(5L, 9L, "Create screens", "controller-key");
        MockScreensJobResponse job = jobResponse("e77c2dc5-e6bf-4d7c-9a8c-9053a9064438", MockScreensJobStatus.QUEUED);
        when(jobService.createJob(request)).thenReturn(job);

        ResponseEntity<ApiResponse<MockScreensJobResponse>> response = controller.createJob(request);

        assertEquals(HttpStatus.ACCEPTED, response.getStatusCode());
        assertEquals(URI.create(job.getStatusUrl()), response.getHeaders().getLocation());
        assertEquals(MockScreensJobStatus.QUEUED, response.getBody().getData().getStatus());
        verify(jobService).createJob(request);
    }

    @Test
    void getStatusReturnsJobState() {
        String jobId = "e77c2dc5-e6bf-4d7c-9a8c-9053a9064438";
        when(jobService.getJobStatus(jobId)).thenReturn(jobResponse(jobId, MockScreensJobStatus.FAILED));

        ApiResponse<MockScreensJobResponse> response = controller.getJobStatus(jobId);

        assertEquals(MockScreensJobStatus.FAILED, response.getData().getStatus());
        verify(jobService).getJobStatus(jobId);
    }

    @Test
    void pdfPreviewServesThePersistedArtifactBytes() {
        String jobId = "e77c2dc5-e6bf-4d7c-9a8c-9053a9064438";
        byte[] pdf = new byte[]{37, 80, 68, 70};
        MockScreensPdfArtifact artifact = new MockScreensPdfArtifact();
        artifact.setFileName("Mock_Screens_" + jobId + ".pdf");
        artifact.setContentType("application/pdf");
        artifact.setSizeBytes((long) pdf.length);
        artifact.setPdfData(pdf);
        when(pdfArtifactService.getCompletedArtifact(jobId)).thenReturn(artifact);

        ResponseEntity<byte[]> response = controller.previewPdf(jobId);

        assertEquals(MediaType.APPLICATION_PDF, response.getHeaders().getContentType());
        assertArrayEquals(pdf, response.getBody());
        assertEquals("inline; filename=\"" + artifact.getFileName() + "\"",
                response.getHeaders().getFirst("Content-Disposition"));
        verify(pdfArtifactService).getCompletedArtifact(jobId);
    }

    @Test
    void mapsJobErrorsToApiResponseAndStatus() {
        MockScreensJobException exception = new MockScreensJobException(
                HttpStatus.CONFLICT, "BRD_NOT_COMPLETED", "BRD is still processing.");

        ResponseEntity<ApiResponse<Void>> response = controller.handleMockScreensJobException(exception);

        assertEquals(HttpStatus.CONFLICT, response.getStatusCode());
        assertEquals("BRD_NOT_COMPLETED", response.getBody().getError().getCode());
    }

    private MockScreensJobResponse jobResponse(String jobId, MockScreensJobStatus status) {
        return MockScreensJobResponse.builder()
                .jobId(jobId)
                .projectId(5L)
                .brdId(9L)
                .status(status)
                .statusUrl("/api/copilot/mock-screens/jobs/" + jobId)
                .build();
    }
}