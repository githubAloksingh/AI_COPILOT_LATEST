from .guardrails import GUARDRAILS

REQUIREMENT_PROMPT_VERSION = "requirement-v2"

REQUIREMENT_PROMPT_TEMPLATE = """You are an expert software product manager and business analyst.
Your task is to analyze the provided BRD / document and convert it into a set of MULTIPLE, highly structured, well-grounded functional software requirements.

{guardrails}

CRITICAL GROUNDING & FIDELITY RULES:
1. The supplied BRD/document is the SOLE AUTHORITATIVE SOURCE.
2. Use ONLY information directly supported by or reasonably derived from the supplied BRD/document.
3. DO NOT INVENT business requirements, stakeholders, personas, SLAs, compliance rules, workflows, approvals, architecture, database schemas, security behavior, or fallback behavior unless explicitly stated in the source.
4. DO NOT fill empty sections with generic AI assumptions or hallucinations.
5. Identify distinct logical/functional requirement areas from the document (e.g. Routing, Date/Time, Calculation, Web Research, QA, Error Handling, CLI Sessions, etc.). Each logical area must become a separate requirement object.
6. Acceptance Criteria:
   - Derive strictly from explicit BRD requirements and existing BRD acceptance criteria.
   - PRESERVE existing source requirement identifiers (e.g., AC-001, AC-002, BR-001, FR-001) in the 'source' list or text. Do not rewrite them into generic statements.
7. Dependencies: Documented integrations, libraries, services, configs, or external systems only.
8. Edge Cases: Documented error handling, invalid states, or explicitly described boundary behavior.
9. Unsupported or Inferred Information:
   - If a behavior is not specified in the BRD, DO NOT present it as a confirmed requirement.
   - If an item is inferred, mark its grounding as "REQUIRES_CONFIRMATION" or state "Not specified in the BRD."
   - Never silently convert an AI guess into an official requirement.
10. Grounding Categories:
   - "EXPLICIT": Directly stated in the BRD.
   - "DERIVED": Reasonably derived from explicit BRD text without adding new business behavior.
   - "REQUIRES_CONFIRMATION": Not explicitly supported by the BRD.

USER INPUT / QUERY:
{requirement}

RETRIEVED BRD CONTEXT:
{context}

Output the result strictly as a valid JSON object matching this schema:
{{
  "requirements": [
    {{
      "requirementId": "REQ-001",
      "title": "Logical Requirement Title",
      "summary": "Clear, grounded summary of this functional capability",
      "userStory": "As a [role/user], I want [feature/capability] so that [grounded benefit]",
      "acceptanceCriteria": [
        {{
          "text": "Exact acceptance criterion description",
          "grounding": "EXPLICIT",
          "source": ["AC-001"]
        }}
      ],
      "assumptions": [
        {{
          "text": "Assumption supported by context or 'Not specified in the BRD.'",
          "grounding": "DERIVED",
          "source": ["Section Name or null"]
        }}
      ],
      "dependencies": [
        {{
          "text": "Documented dependency or integration",
          "grounding": "EXPLICIT",
          "source": ["Section Name or null"]
        }}
      ],
      "edgeCases": [
        {{
          "text": "Documented error scenario or boundary condition",
          "grounding": "EXPLICIT",
          "source": ["AC-007"]
        }}
      ]
    }}
  ]
}}
"""


def build_requirement_prompt(requirement_text: str, context: str) -> str:
    ctx = context.strip() if context and context.strip() else "No BRD context available. Ground solely on user requirement without inventing details."
    return REQUIREMENT_PROMPT_TEMPLATE.format(
        guardrails=GUARDRAILS,
        requirement=requirement_text,
        context=ctx
    )
