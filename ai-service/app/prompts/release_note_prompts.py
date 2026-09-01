from .guardrails import GUARDRAILS

RELEASE_NOTE_PROMPT_VERSION = "release-v1"

RELEASE_NOTES_PROMPT_TEMPLATE = """You are an expert technical writer and release manager. Your task is to generate clean, professional release notes based on sprint information.

{guardrails}

VERSION: {version}
SPRINT INFORMATION: {sprintInfo}

Output strictly as a valid JSON object matching this schema:
{{
  "summary": "Overall release summary",
  "newFeatures": ["feature 1"],
  "improvements": ["improvement 1"],
  "bugFixes": ["fix 1"],
  "breakingChanges": ["breaking 1"],
  "knownIssues": ["issue 1"],
  "technicalNotes": "Any technical instructions"
}}
"""


def build_release_notes_prompt(version: str, sprint_info: str, context: str = "") -> str:
    return RELEASE_NOTES_PROMPT_TEMPLATE.format(
        guardrails=GUARDRAILS,
        version=version or "",
        sprintInfo=sprint_info or ""
    )
