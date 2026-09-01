DAILY_STATUS_PROMPT_VERSION = "status-v1"

DAILY_STATUS_PROMPT_TEMPLATE = """You are a scrum master and technical project manager. Generate a structured daily status update based on the raw input.

RAW INPUT: {input}

Output strictly as a valid JSON object matching this schema:
{{
  "completed": ["item 1"],
  "inProgress": ["item 1"],
  "blockers": ["blocker 1"],
  "risks": ["risk 1"],
  "nextSteps": ["step 1"],
  "importantUpdates": "Overall important note"
}}
"""


def build_daily_status_prompt(raw_input: str) -> str:
    return DAILY_STATUS_PROMPT_TEMPLATE.format(input=raw_input or "")
