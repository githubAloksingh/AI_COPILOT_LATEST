from .guardrails import GUARDRAILS

USER_STORY_PROMPT_VERSION = "user-story-v2"

USER_STORY_PROMPT_TEMPLATE = """You are an expert Agile Product Manager, Lead Business Analyst, and Systems Consultant.

Your task is to analyze the provided BRD/document content or user requirement and synthesize a comprehensive set of structured, implementation-ready User Stories organized logically by functional modules or feature areas.

{guardrails}

CRITICAL GROUNDING & FIDELITY RULES:
1. The supplied BRD / document is the SOLE AUTHORITATIVE SOURCE.
2. Formulate each User Story following standard Agile format: "As a [role], I want [capability], so that [benefit]."
3. Group related user stories under distinct functional Modules (e.g. "Module 1: Overdraft Tracker", "Module 2: Un-Invested Cash", "Module 3: Alerts & Notifications", etc.).
4. Assign sequential story identifiers: US-001, US-002, US-003, etc.
5. For each story, provide explicit traceability back to the source document (e.g. "BRD §4.3.1.1, step 1").
6. Provide specific, numbered Acceptance Criteria grounded directly in the document.
7. If business rules or dependencies exist for a story, list them explicitly.
8. GRAMMAR & EDITORIAL QUALITY: Ensure all descriptions, acceptance criteria, and business rules are written in 100% grammatically correct, complete English sentences without shorthand arrows or bullet markers inside strings.
9. If ambiguity or open questions remain, capture them in the "openQuestions" list with source citations.
10. Never display raw internal objects, DTO names, or ChromaDB metadata.

USER INPUT:
{input_text}

RETRIEVED KNOWLEDGE BASE CONTEXT:
{context}

Generate the result strictly as valid JSON using this exact schema:

{{
  "userStories": [
    {{
      "userStoryId": "US-001",
      "module": "Module 1: Core Processing Module",
      "title": "Search and Review Active Records",
      "userStory": "As a [User Role], I want [capability / feature], so that [business benefit / rationale].",
      "sourceReference": "BRD §x.x, step x",
      "description": "Comprehensive business background and operational context for this story.",
      "acceptanceCriteria": [
        {{
          "id": "AC-001",
          "text": "Given active records exist, when user navigates to the module, then records are displayed with current aging.",
          "grounding": "EXPLICIT",
          "source": ["BRD §x.x"]
        }}
      ],
      "businessRules": [
        {{
          "ruleId": "BR-01",
          "text": "Aging is calculated in calendar days from the original transaction date.",
          "grounding": "EXPLICIT",
          "source": ["BRD §x.x"]
        }}
      ],
      "dependencies": [
        {{
          "text": "Requires daily data feed ingestion before morning processing cycle.",
          "grounding": "EXPLICIT",
          "source": ["BRD §x.x"]
        }}
      ],
      "assumptions": [
        {{
          "text": "All users are authenticated via corporate single sign-on.",
          "grounding": "DERIVED",
          "source": ["Security Standard"]
        }}
      ]
    }}
  ],
  "openQuestions": [
    {{
      "id": "OQ-01",
      "question": "What specific user roles and permission levels are required within the secondary approval queue?",
      "source": "BRD §x.x"
    }}
  ]
}}

The output must contain ONLY the valid JSON object.
"""


def build_user_story_prompt(input_text: str, context: str) -> str:
    ctx = (
        context.strip()
        if context and context.strip()
        else "No BRD context available. Ground solely on user requirement without inventing details."
    )
    return USER_STORY_PROMPT_TEMPLATE.format(
        guardrails=GUARDRAILS,
        input_text=input_text,
        context=ctx
    )
