from .guardrails import GUARDRAILS

DEFECT_PROMPT_VERSION = "defect-v1"

DEFECT_TRIAGE_PROMPT_TEMPLATE = """You are an expert Site Reliability Engineer and software architect. Your task is to analyze the provided defect, logs, and stack trace to identify probable root causes and suggest fixes.

{guardrails}

DEFECT TITLE: {title}
DESCRIPTION: {description}
LOGS: {logs}
STEPS TO REPRODUCE: {steps}
ACTUAL BEHAVIOR: {actual}
EXPECTED BEHAVIOR: {expected}

RETRIEVED CONTEXT (Historical Defects): {context}

Output strictly as a valid JSON object matching this schema:
{{
  "probableRootCause": "explanation",
  "evidence": "what logs or context supports this",
  "suggestedInvestigation": "what to check next",
  "suggestedFix": "how to potentially fix it",
  "confidence": "HIGH, MEDIUM, or LOW",
  "severity": "CRITICAL, HIGH, MEDIUM, or LOW",
  "priority": "P0, P1, P2, or P3"
}}
"""


def build_defect_prompt(
    title: str,
    description: str,
    logs: str,
    steps: str,
    actual: str,
    expected: str,
    context: str
) -> str:
    ctx = context.strip() if context and context.strip() else "No context available."
    return DEFECT_TRIAGE_PROMPT_TEMPLATE.format(
        guardrails=GUARDRAILS,
        title=title or "",
        description=description or "",
        logs=logs or "",
        steps=steps or "",
        actual=actual or "",
        expected=expected or "",
        context=ctx
    )
