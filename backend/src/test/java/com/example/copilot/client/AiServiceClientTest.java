package com.example.copilot.client;

import com.example.copilot.dto.*;
import com.example.copilot.dto.ai.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.*;
import static org.springframework.test.web.client.response.MockRestResponseCreators.*;

public class AiServiceClientTest {

    private RestTemplate restTemplate;
    private MockRestServiceServer mockServer;
    private AiServiceClient aiServiceClient;
    private ObjectMapper objectMapper;

    private static final String BASE_URL = "http://localhost:8000";

    @BeforeEach
    void setUp() {
        restTemplate = new RestTemplate();
        mockServer = MockRestServiceServer.createServer(restTemplate);
        aiServiceClient = new AiServiceClient(restTemplate, BASE_URL);
        objectMapper = new ObjectMapper();
    }

    @Test
    void testIngestDocument_Success() throws Exception {
        AiIngestionResponse mockResponse = new AiIngestionResponse();
        mockResponse.setStatus("COMPLETED");
        mockResponse.setDocument_id("101");
        mockResponse.setFile_name("sample.pdf");
        mockResponse.setChunk_count(5);
        mockResponse.setMessage("Success");

        mockServer.expect(requestTo(BASE_URL + "/api/ai/ingest"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess(objectMapper.writeValueAsString(mockResponse), MediaType.APPLICATION_JSON));

        AiIngestionResponse response = aiServiceClient.ingestDocument(101L, "sample.pdf", "application/pdf", "Hello World".getBytes());

        assertNotNull(response);
        assertEquals("COMPLETED", response.getStatus());
        assertEquals(5, response.getChunk_count());
        mockServer.verify();
    }

    @Test
    void testGenerateRequirement_Success() throws Exception {
        RequirementResponseDto resultDto = new RequirementResponseDto();
        resultDto.setSummary("User Auth Summary");
        resultDto.setUserStory("As a user...");
        resultDto.setAcceptanceCriteria(List.of("Crit 1"));

        AiRequirementResponse mockResponse = new AiRequirementResponse();
        mockResponse.setResult(resultDto);
        mockResponse.setSources(List.of("doc 1"));
        mockResponse.setModel("gemini-3.7-flash");
        mockResponse.setPrompt_version("requirement-v1");
        mockResponse.setExecution_time_ms(120);

        mockServer.expect(requestTo(BASE_URL + "/api/ai/requirements/generate"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess(objectMapper.writeValueAsString(mockResponse), MediaType.APPLICATION_JSON));

        RequirementRequest request = new RequirementRequest();
        request.setTitle("User Auth");
        request.setDescription("Support OAuth2 login");

        AiRequirementResponse response = aiServiceClient.generateRequirement(request);

        assertNotNull(response);
        assertNotNull(response.getResult());
        assertEquals("User Auth Summary", response.getResult().getSummary());
        assertEquals(1, response.getSources().size());
        mockServer.verify();
    }

    @Test
    void testAiService_ErrorHandling() {
        mockServer.expect(requestTo(BASE_URL + "/api/ai/requirements/generate"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withServerError());

        RequirementRequest request = new RequirementRequest();
        request.setTitle("Fail Req");
        request.setDescription("Fail Desc");

        assertThrows(RuntimeException.class, () -> aiServiceClient.generateRequirement(request));
        mockServer.verify();
    }
}
