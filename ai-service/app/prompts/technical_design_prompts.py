from .guardrails import GUARDRAILS

TECHNICAL_DESIGN_PROMPT_VERSION = "technical-design-v1"

TECHNICAL_DESIGN_PROMPT_TEMPLATE = """You are a Senior Software Architect and Technical Lead.

Your task is to analyze the provided BRD/document content or user-provided requirement and create a detailed Technical Design.

{guardrails}

CRITICAL GROUNDING & FIDELITY RULES:

1. The supplied BRD/document or user input is the SOLE AUTHORITATIVE SOURCE.
2. Use ONLY information directly supported by or reasonably derived from the supplied input.
3. DO NOT invent APIs, database schemas, services, technologies, architecture, integrations, security behavior, infrastructure, or implementation details unless supported by the input or explicitly marked as a recommendation.
4. Clearly distinguish documented requirements from technical recommendations.
5. If the technology stack is already established by the existing project, use the existing project architecture instead of inventing another stack.
6. Preserve source identifiers where available.
7. Do not silently assume missing technical details.
8. If something is not specified, state "Not specified in the provided input."
9. Technical Design should explain HOW the functionality can be implemented.
10. Keep the design implementation-ready but grounded.

USER INPUT:
{input_text}

RETRIEVED KNOWLEDGE BASE CONTEXT:
{context}

Generate the result strictly as valid JSON:

{{
  "technicalDesign": {{
    "title": "Technical Design Title",
    "objective": "Technical objective",
    "requirementSummary": "Grounded technical summary",

    "components": [
      {{
        "name": "Component",
        "responsibility": "Responsibility",
        "source": ["Section Name or null"]
      }}
    ],

    "architectureFlow": [
      {{
        "step": 1,
        "component": "Component name",
        "action": "Technical action",
        "source": ["Section Name or null"]
      }}
    ],

    "apis": [
      {{
        "name": "API name",
        "method": "GET/POST/PUT/DELETE or Not specified",
        "endpoint": "Endpoint or Not specified",
        "purpose": "Purpose",
        "request": "Request details or Not specified",
        "response": "Response details or Not specified",
        "statusCodes": [
          "200",
          "400",
          "500"
        ],
        "source": ["Section Name or null"]
      }}
    ],

    "dataModel": [
      {{
        "entity": "Entity/Table",
        "fields": [
          {{
            "name": "field",
            "type": "type or Not specified",
            "required": true,
            "description": "Description"
          }}
        ],
        "relationships": [
          "Grounded relationship or Not specified"
        ]
      }}
    ],

    "businessLogic": [
      {{
        "rule": "Technical implementation logic",
        "source": ["Section Name or null"]
      }}
    ],

    "validation": [
      {{
        "validation": "Grounded validation",
        "source": ["Section Name or null"]
      }}
    ],

    "errorHandling": [
      {{
        "scenario": "Error scenario",
        "handling": "Expected handling",
        "source": ["Section Name or null"]
      }}
    ],

    "security": [
      {{
        "consideration": "Security consideration",
        "grounding": "EXPLICIT"
      }}
    ],

    "databaseChanges": [
      {{
        "change": "Database change",
        "grounding": "EXPLICIT",
        "source": ["Section Name or null"]
      }}
    ],

    "integrations": [
      {{
        "system": "System/service",
        "purpose": "Purpose",
        "source": ["Section Name or null"]
      }}
    ],

    "performanceConsiderations": [
      {{
        "consideration": "Relevant performance consideration",
        "grounding": "EXPLICIT"
      }}
    ],

    "dependencies": [
      {{
        "dependency": "Technical dependency",
        "source": ["Section Name or null"]
      }}
    ],

    "assumptions": [
      {{
        "text": "Not specified in the provided input.",
        "grounding": "REQUIRES_CONFIRMATION"
      }}
    ],

    "implementationNotes": [
      {{
        "note": "Implementation consideration",
        "grounding": "EXPLICIT"
      }}
    ]
  }}
}}

The output must contain only the JSON object.
"""


def build_technical_design_prompt(input_text: str, context: str) -> str:
    ctx = context.strip() if context and context.strip() else "No BRD context available. Ground solely on user requirement without inventing details."
    return TECHNICAL_DESIGN_PROMPT_TEMPLATE.format(
        guardrails=GUARDRAILS,
        input_text=input_text,
        context=ctx
    )
