from .guardrails import GUARDRAILS

REQUIREMENT_PROMPT_VERSION = "requirement-v1"

REQUIREMENT_PROMPT_TEMPLATE = """You are an expert software product manager and business analyst. Your task is to convert the provided user requirement into a highly structured requirement document.

{guardrails}

USER REQUIREMENT: {requirement}

RETRIEVED CONTEXT: {context}

Output the result strictly as a valid JSON object matching this schema:
{{
  "summary": "A short summary of the requirement",
  "userStory": "As a [role], I want [feature] so that [benefit]",
  "acceptanceCriteria": ["criteria 1", "criteria 2"],
  "assumptions": ["assumption 1", "assumption 2"],
  "dependencies": ["dependency 1"],
  "edgeCases": ["edge case 1"]
}}
"""


def build_requirement_prompt(requirement_text: str, context: str) -> str:
    ctx = context.strip() if context and context.strip() else "No context available."
    return REQUIREMENT_PROMPT_TEMPLATE.format(
        guardrails=GUARDRAILS,
        requirement=requirement_text,
        context=ctx
    )
