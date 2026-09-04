from .guardrails import GUARDRAILS

USER_STORY_PROMPT_VERSION = "user-story-v1"

USER_STORY_PROMPT_TEMPLATE = """You are an expert software product manager, business analyst, and Agile Product Owner.

Your task is to analyze the provided BRD/document content or user-provided requirement and convert it into one or more clear, structured, implementation-ready User Stories.

{guardrails}

CRITICAL GROUNDING & FIDELITY RULES:

1. The supplied BRD/document or user input is the SOLE AUTHORITATIVE SOURCE.
2. Use ONLY information directly supported by or reasonably derived from the supplied input.
3. DO NOT invent business requirements, personas, stakeholders, workflows, approvals, SLAs, compliance requirements, technical architecture, database behavior, security behavior, or business rules unless explicitly supported.
4. Do not silently convert assumptions into confirmed requirements.
5. Break large requirements into multiple independent User Stories where appropriate.
6. Each User Story must represent a meaningful business capability.
7. Acceptance Criteria must be directly grounded in the provided input.
8. If information is missing, state "Not specified in the provided input."
9. Clearly distinguish grounded information from derived information.
10. Preserve source identifiers such as BR-001, FR-001, AC-001 if they exist.

USER INPUT:
{input_text}

RETRIEVED KNOWLEDGE BASE CONTEXT:
{context}

Generate the result strictly as valid JSON using this schema:

{{
  "userStories": [
    {{
      "userStoryId": "US-001",
      "title": "Short meaningful title",
      "summary": "Clear summary of the business requirement",
      "userStory": "As a [user/role], I want [capability], so that [business benefit]",
      "description": "Detailed description grounded in the source",
      "acceptanceCriteria": [
        {{
          "id": "AC-001",
          "text": "Testable acceptance criterion",
          "grounding": "EXPLICIT",
          "source": ["AC-001"]
        }}
      ],
      "businessRules": [
        {{
          "text": "Grounded business rule",
          "grounding": "EXPLICIT",
          "source": ["Section Name or null"]
        }}
      ],
      "dependencies": [
        {{
          "text": "Grounded dependency",
          "grounding": "EXPLICIT",
          "source": ["Section Name or null"]
        }}
      ],
      "assumptions": [
        {{
          "text": "Not specified in the provided input.",
          "grounding": "REQUIRES_CONFIRMATION",
          "source": ["null"]
        }}
      ],
      "edgeCases": [
        {{
          "text": "Grounded edge case",
          "grounding": "EXPLICIT",
          "source": ["Section Name or null"]
        }}
      ]
    }}
  ]
}}

The output must contain only the JSON object.
"""


def build_user_story_prompt(input_text: str, context: str) -> str:
    ctx = context.strip() if context and context.strip() else "No BRD context available. Ground solely on user requirement without inventing details."
    return USER_STORY_PROMPT_TEMPLATE.format(
        guardrails=GUARDRAILS,
        input_text=input_text,
        context=ctx
    )
