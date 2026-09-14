from .guardrails import GUARDRAILS

TECHNICAL_DESIGN_PROMPT_VERSION = "technical-design-v2"

TECHNICAL_DESIGN_PROMPT_TEMPLATE = """You are a Principal Software Architect and Lead Systems Engineer.

Your task is to analyze the provided requirement, user stories, acceptance criteria, BRD/document content, and existing project codebase context to create a DETAILED, TECHNICAL, STRUCTURED, and IMPLEMENTATION-READY Technical Design.

The output must provide enough technical detail that a developer can understand and implement the approach without needing to guess missing technical details.

{guardrails}

==================================================
PROJECT CODEBASE CONTEXT (GROUNDING ANCHOR)
==================================================
This application uses the following actual architecture and technologies:
- Frontend: Angular 19 (Standalone Components, TypeScript, RxJS, SCSS). Key components include TechnicalDesignComponent, FunctionalDesignComponent, RequirementAssistantComponent, UserStoryComponent, TestGeneratorComponent, and ResponseModal.
- Backend: Java 21 / Spring Boot 3.x (Spring Data JPA, REST Controllers e.g. RequirementController, RequirementService, AuditService, Jackson JSON serialization).
- AI Service: Python 3.11+, FastAPI, Google Gemini 3.7 Flash API (Generative Language v1beta), ChromaDB vector store, sentence-transformers, json-repair.
- Persistence: Relational DB (PostgreSQL / H2) with JPA Entities (Requirement, Project, Document, AuditLog).
- HTTP Integration: RestTemplate / Angular HttpClient.

CRITICAL GROUNDING & FIDELITY RULES:
1. The supplied requirement, user story, and BRD content are the PRIMARY AUTHORITATIVE SOURCE.
2. DO NOT invent unrelated generic architecture or unsupported frameworks/technologies. Use the established project stack above.
3. DO NOT hard-code fake or placeholder designs. Every section must directly reflect the actual requirement.
4. If a technical decision cannot be determined from the available information, explicitly state "To Be Confirmed" instead of inventing a fact.
5. If the requirement does not require database changes, explicitly state: "Database changes: None required."
6. Provide concrete, developer-usable details (e.g. realistic API payload JSON schemas with types, concrete method names, step-by-step numbered flows, exact validation logic, and failure handling).
7. Do not fill sections with generic filler. If a section is genuinely not applicable to the requirement, mark it as "Not Applicable: [brief reason]".

USER REQUIREMENT & INPUT:
{input_text}

RETRIEVED KNOWLEDGE BASE / BRD CONTEXT:
{context}

Generate the result strictly as valid JSON matching this exact structure:

{{
  "technicalDesign": {{
    "title": "Clear, technical title reflecting the feature",
    "objective": "Concise technical objective",
    "requirementSummary": "Grounded technical summary connecting the requirement to architecture",

    "technicalOverview": {{
      "whatIsBeingImplemented": "Precise explanation of what is being built or modified",
      "technicalObjective": "Primary engineering goals (e.g. scalability, low latency, idempotent updates)",
      "scopeOfImplementation": [
        "In-scope technical deliverable 1",
        "In-scope technical deliverable 2"
      ],
      "outOfScope": [
        "Explicitly excluded item or 'Not specified'"
      ],
      "highLevelApproach": "Architecture pattern and overall technical strategy",
      "relationshipToUserStory": "Direct relationship between user story acceptance criteria and technical components"
    }},

    "architectureOverview": {{
      "frontendComponents": [
        "Affected Angular component(s) e.g. TechnicalDesignComponent, ResponseModal"
      ],
      "backendServices": [
        "Affected Spring Boot service(s) e.g. RequirementController, RequirementService"
      ],
      "apis": [
        "Relevant HTTP endpoints"
      ],
      "databaseStorage": "Database tables or 'None required'",
      "externalSystems": [
        "External system or 'Google Gemini 3.7 Flash API'"
      ],
      "communicationFlow": "How frontend, backend, AI service, and database interact",
      "textFlowDiagram": "User -> Angular Component -> ApiService -> Spring Boot Controller -> Business Service -> Repository/Database -> Response -> Angular UI"
    }},

    "components": [
      {{
        "name": "Component/Service Name (e.g. TechnicalDesignComponent)",
        "responsibility": "Core technical responsibility",
        "inputs": ["Input parameters or data properties"],
        "outputs": ["Events, return types, or emitted values"],
        "importantMethods": [
          "methodName1() - detailed purpose and behavior",
          "methodName2() - detailed purpose and behavior"
        ],
        "dependencies": ["Injected services, models, or libraries"],
        "stateDataHandled": "State properties and lifecycle data managed",
        "interactionWithOtherComponents": "How it communicates with parent/child/sibling components"
      }}
    ],

    "frontendDesign": {{
      "angularComponents": [
        "Component structure and lifecycle hooks used"
      ],
      "services": [
        "Angular service and HTTP methods"
      ],
      "models": [
        "TypeScript interfaces and DTOs"
      ],
      "formsAndState": "Form handling, reactivity, and local state management",
      "apiIntegration": "HttpClient Observable handling, error catchError, and response unwrap",
      "editModeBehavior": "Inline editing mechanism, draft state caching, save validation, and cancel restore",
      "validation": [
        "Client-side field validation rules and immediate feedback"
      ],
      "loadingAndErrorStates": "Spinner states, disabled buttons during in-flight requests, toast alerts",
      "uiStateTransitions": "State sequence: Idle -> In-Progress -> Success -> Edit -> Persisted"
    }},

    "backendDesign": {{
      "endpoints": [
        "HTTP method and path"
      ],
      "controllers": [
        "Controller class, request mapping annotations, parameter annotations"
      ],
      "businessServices": [
        "Business logic flow, validation orchestration, transaction boundaries"
      ],
      "repositoryLayer": [
        "JPA Repository interface, queries, persistence calls"
      ],
      "validation": [
        "Server-side DTO validation, business constraint checks"
      ],
      "errorHandling": [
        "Exception handling, HTTP status codes, structured error payload"
      ],
      "security": [
        "Authentication context, role-based authorization, or 'To Be Confirmed'"
      ]
    }},

    "apis": [
      {{
        "name": "Descriptive API Name",
        "method": "POST/GET/PUT/DELETE",
        "endpoint": "/api/copilot/...",
        "purpose": "Precise API purpose",
        "request": "{{\\n  \\"field\\": \\"string (required) - description\\"\\n}}",
        "response": "{{\\n  \\"success\\": true,\\n  \\"data\\": {{}}\\n}}",
        "statusCodes": [
          "200 OK - Successful operation",
          "400 Bad Request - Validation failure",
          "500 Internal Server Error - Downstream or processing failure"
        ],
        "validationRules": [
          "Field 'x' must not be blank"
        ],
        "errorScenarios": [
          "Scenario description -> expected HTTP status and message"
        ]
      }}
    ],

    "dataModel": [
      {{
        "entity": "Entity name or 'None'",
        "databaseChangesSummary": "Schema modification details or 'Database changes: None required.'",
        "fields": [
          {{
            "name": "field_name",
            "type": "VARCHAR(255) / BIGINT / TEXT / JSONB",
            "primaryKey": false,
            "foreignKey": "null or parent table",
            "required": true,
            "description": "Column purpose and constraints"
          }}
        ],
        "relationships": [
          "One-to-Many / Many-to-One or 'None'"
        ],
        "indexes": [
          "Index details or 'None required'"
        ],
        "persistenceBehavior": "JPA cascade, auditing timestamps, soft delete"
      }}
    ],

    "dataFlow": [
      {{
        "step": 1,
        "source": "User / Browser",
        "target": "Angular Component",
        "action": "User initiates action (e.g. clicks Generate or Edit)",
        "payload": "User inputs and parameters"
      }},
      {{
        "step": 2,
        "source": "Angular Component",
        "target": "Backend Controller",
        "action": "HTTP request sent via ApiService",
        "payload": "Validated JSON request body"
      }},
      {{
        "step": 3,
        "source": "Backend Controller",
        "target": "Business Service / AI Service",
        "action": "Processing, validation, and orchestration",
        "payload": "Domain DTO"
      }},
      {{
        "step": 4,
        "source": "Business Service",
        "target": "Database / Repository",
        "action": "Data persistence or query",
        "payload": "JPA Entity"
      }},
      {{
        "step": 5,
        "source": "Backend Controller",
        "target": "Angular UI",
        "action": "HTTP response returned and rendered to user",
        "payload": "ApiResponse with structured result"
      }}
    ],

    "aiLlmIntegration": {{
      "modelUsed": "Gemini 3.7 Flash",
      "promptConstruction": "Structured system instructions + guardrails + contextual chunks + user input",
      "inputContext": "Context retrieved from BRD document via vector embeddings and sliding window chunks",
      "outputStructure": "Strict JSON schema returned with responseMimeType application/json",
      "responseParsing": "JSON repair and clean parsing to tolerate minor formatting variations",
      "validationAndSanitization": "Grounding verification against source text and hallucination suppression",
      "errorAndRetryHandling": "HTTP timeout handling and failover across candidate models",
      "fallbackBehavior": "User-facing toast/error banner with non-blocking UI recovery"
    }},

    "promptLogic": {{
      "promptIntent": "Direct the model to act as a software architect producing production-ready blueprints",
      "guidingPrinciples": [
        "Ground in actual project stack without inventing unsupported libraries",
        "Explicitly distinguish confirmed requirements from recommendations",
        "Provide concrete data schemas and method signatures"
      ],
      "edgeCasesTargeted": [
        "Missing BRD context handling",
        "Empty or malformed inputs"
      ]
    }},

    "securityDesign": {{
      "existingControls": [
        "Backend input validation on incoming requests",
        "Separation of AI keys into environment configuration (never exposed to browser)"
      ],
      "recommendedControls": [
        "Rate limiting on generation endpoints",
        "Strict CORS restrictions on backend API"
      ],
      "inputValidation": "Sanitize all text inputs at Angular forms and Spring Boot DTO validators",
      "secretsManagement": "GEMINI_API_KEY managed via environment variables/application.properties, not in version control",
      "loggingSecurity": "Prevent sensitive user data or API keys from being logged in console or log files"
    }},

    "validationRules": {{
      "frontend": [
        {{
          "field": "Field name",
          "rule": "Required, non-empty, length boundary",
          "errorMsg": "Validation message displayed to user"
        }}
      ],
      "backend": [
        {{
          "field": "Field name",
          "rule": "Server-side check",
          "errorMsg": "HTTP 400 validation error"
        }}
      ],
      "database": [
        {{
          "constraint": "NOT NULL / UNIQUE / FOREIGN KEY or 'None required'",
          "description": "Database-level enforcement"
        }}
      ]
    }},

    "errorHandling": [
      {{
        "scenario": "Invalid or missing input",
        "whereItOccurs": "Frontend / Backend",
        "handling": "Validation checks intercept request before processing",
        "responseReturned": "HTTP 400 with descriptive error message",
        "userExperience": "Error banner or validation message highlighted near input"
      }},
      {{
        "scenario": "AI Service or Gemini API timeout",
        "whereItOccurs": "AI Service Client",
        "handling": "Catch timeout exception and return structured error response",
        "responseReturned": "HTTP 500 / 504 with retry suggestion",
        "userExperience": "Toast notification: 'Generation timed out. Please try again.'"
      }},
      {{
        "scenario": "Database persistence failure",
        "whereItOccurs": "Spring Data JPA Repository",
        "handling": "Transaction rollback and log error",
        "responseReturned": "HTTP 500 with sanitized message",
        "userExperience": "Toast notification: 'Failed to save changes.'"
      }}
    ],

    "edgeCases": [
      {{
        "scenario": "Very large input or BRD document",
        "impact": "Context window or latency increase",
        "handling": "Sliding window chunking with top_k context retrieval"
      }},
      {{
        "scenario": "Empty or whitespace-only input",
        "impact": "Unnecessary processing",
        "handling": "Frontend button disabled and backend validation guard"
      }},
      {{
        "scenario": "Special characters or script tags in input",
        "impact": "Potential injection",
        "handling": "Angular template escaping and Jackson JSON encoding"
      }}
    ],

    "businessRuleMappings": [
      {{
        "businessRule": "Business rule from requirements",
        "technicalImplementation": "How technically enforced (e.g. backend validation guard, frontend form check)"
      }}
    ],

    "acceptanceCriteriaMappings": [
      {{
        "acceptanceCriterion": "Acceptance criterion from requirements",
        "technicalImplementation": "Specific technical component, method, and flow that satisfies this criterion"
      }}
    ],

    "dependencies": {{
      "frontend": ["@angular/core", "@angular/common", "@angular/forms", "rxjs", "jspdf"],
      "backend": ["spring-boot-starter-web", "spring-boot-starter-data-jpa", "jackson-databind", "lombok"],
      "aiService": ["fastapi", "httpx", "json-repair", "chromadb", "sentence-transformers"],
      "externalApis": ["Google Gemini API (v1beta)"]
    }},

    "assumptions": [
      {{
        "assumption": "Technical assumption based on requirement",
        "status": "CONFIRMED / TO_BE_CONFIRMED",
        "impactIfInvalid": "Impact if this assumption proves incorrect"
      }}
    ],

    "implementationPlan": [
      {{
        "step": 1,
        "phase": "Phase name (e.g. Backend DTO & API)",
        "action": "Concrete implementation action",
        "deliverable": "File or artifact updated",
        "verification": "How to test and verify this step"
      }},
      {{
        "step": 2,
        "phase": "Phase name (e.g. Frontend UI & Integration)",
        "action": "Concrete implementation action",
        "deliverable": "File or artifact updated",
        "verification": "How to test and verify this step"
      }}
    ],

    "testingStrategy": {{
      "unitTesting": [
        "Frontend component/service unit tests with Jasmine/Karma or Vitest",
        "Backend service unit tests with JUnit 5 and Mockito"
      ],
      "integrationTesting": [
        "Spring Boot MockMvc API integration tests",
        "AI service endpoint tests"
      ],
      "functionalTesting": [
        "End-to-end user flow: generate, edit, save, and export"
      ],
      "negativeTesting": [
        "Invalid payload submission, missing fields, timeout handling"
      ],
      "edgeCaseTesting": [
        "Empty inputs, boundary lengths, concurrent updates"
      ]
    }},

    "performanceConsiderations": [
      {{
        "area": "AI Generation Latency",
        "consideration": "Asynchronous loading state, fast top_k retrieval from vector DB"
      }},
      {{
        "area": "Frontend Rendering",
        "consideration": "ChangeDetectionStrategy.OnPush / markForCheck for snappy UI responsiveness"
      }}
    ],

    "loggingAndMonitoring": [
      {{
        "event": "Generation requested / completed",
        "level": "INFO",
        "details": "Execution time in ms, model name, prompt version (no secrets or PII)"
      }},
      {{
        "event": "API or AI failure",
        "level": "ERROR",
        "details": "Error message, status code, correlation ID"
      }}
    ],

    "configuration": [
      {{
        "name": "GEMINI_API_KEY",
        "purpose": "API key for Google Gemini model access",
        "example": "Configured in environment / .env (never hardcoded)"
      }},
      {{
        "name": "GEMINI_MODEL",
        "purpose": "Selected model identifier",
        "example": "gemini-3.7-flash"
      }}
    ],

    "technicalRisks": [
      {{
        "risk": "Downstream AI service latency or temporary unavailability",
        "impact": "Medium",
        "mitigation": "Candidate model failover, descriptive error toast, retry without data loss"
      }}
    ],

    "fileImpact": {{
      "frontend": [
        "src/app/knowledge-base/technical-design/technical-design.ts",
        "src/app/knowledge-base/technical-design/technical-design.html",
        "src/app/core/components/response-modal/response-modal.html",
        "src/app/core/components/response-modal/response-modal.ts"
      ],
      "backend": [
        "com.example.copilot.controller.RequirementController",
        "com.example.copilot.service.RequirementService",
        "com.example.copilot.client.AiServiceClient"
      ],
      "aiService": [
        "app/prompts/technical_design_prompts.py",
        "app/services/rag_service.py"
      ]
    }},

    "technicalDecisions": [
      {{
        "decision": "Technical approach decision",
        "reason": "Core justification grounded in requirement",
        "alternativeConsidered": "Alternative approach evaluated",
        "whySelected": "Why the chosen approach was superior"
      }}
    ],

    "architectureFlow": [
      {{
        "step": 1,
        "component": "Angular Component",
        "action": "User submits requirement"
      }},
      {{
        "step": 2,
        "component": "ApiService",
        "action": "Sends POST request to backend"
      }},
      {{
        "step": 3,
        "component": "RequirementController",
        "action": "Validates request and delegates to RequirementService"
      }},
      {{
        "step": 4,
        "component": "AiServiceClient",
        "action": "Calls AI Service RAG endpoint"
      }},
      {{
        "step": 5,
        "component": "Gemini 3.7 Flash",
        "action": "Processes grounded prompt and generates technical specification"
      }},
      {{
        "step": 6,
        "component": "ResponseModal",
        "action": "Renders structured technical design with full editing support"
      }}
    ],

    "businessLogic": [
      {{
        "rule": "Primary business and technical implementation logic rule"
      }}
    ],

    "validation": [
      {{
        "validation": "Primary validation rule"
      }}
    ],

    "security": [
      {{
        "consideration": "Key security consideration"
      }}
    ],

    "databaseChanges": [
      {{
        "change": "Database changes: None required."
      }}
    ],

    "integrations": [
      {{
        "system": "Google Gemini 3.7 Flash API",
        "purpose": "AI generation of technical design specifications"
      }}
    ],

    "implementationNotes": [
      {{
        "note": "Implementation detail note"
      }}
    ]
  }}
}}

The output must contain ONLY the valid JSON object. Do not wrap in markdown or prose outside the JSON.
"""


def build_technical_design_prompt(input_text: str, context: str) -> str:
    ctx = (
        context.strip()
        if context and context.strip()
        else "No BRD context available. Ground solely on user requirement without inventing details."
    )
    return TECHNICAL_DESIGN_PROMPT_TEMPLATE.format(
        guardrails=GUARDRAILS,
        input_text=input_text,
        context=ctx
    )
