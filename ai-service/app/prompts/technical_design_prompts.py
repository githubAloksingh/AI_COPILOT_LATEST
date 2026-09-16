from .guardrails import GUARDRAILS

TECHNICAL_DESIGN_PROMPT_VERSION = "technical-design-v4-brd-document-blueprint"

TECHNICAL_DESIGN_PROMPT_TEMPLATE = """You are generating a Technical Design from one selected Business Requirements Document (BRD).

The selected BRD context below is the complete and only factual source for this response.
Do not use application source code, existing project architecture, previous outputs, templates,
model memory, or unrelated documents. Do not treat the generation application's own stack as
the system being designed.

{guardrails}

BRD-ONLY RULES:
1. Use only facts, terminology, actors, requirements, rules, constraints, integrations, and process steps supported by the supplied BRD context.
2. Preserve requirement IDs and BRD terminology where available.
3. Do not invent technologies, frameworks, components, APIs, endpoints, database tables, services, integrations, security controls, or architecture.
4. Generate a flow or flowchart only from a process or decision explicitly described in the BRD.
5. Generate tables only from BRD-derived data. Use an empty list when the BRD does not provide rows.
6. For unsupported details use exactly \"Not specified in BRD\". Do not provide generic recommendations as facts.
7. Do not reuse or summarize a previous Technical Design. Start from the supplied BRD context for every request.
8. The user input is only a query about the selected BRD; it is not permission to add external project context.

REFERENCE DOCUMENT BLUEPRINT:
Use the following order and level of detail as a presentation blueprint inspired by the supplied
reference document. This describes structure only; it does not provide facts or example content.
Every title, row, module, actor, flow step, API, table, field, technology, and decision must be
created dynamically from the selected BRD.

1. Document title and metadata: derive the system/product name, project/program name, source
  document, version, and relevant date only when present in the BRD. Use "Not specified in BRD"
  when absent. Never use a fixed project name or version.
2. System Overview: explain the BRD-supported purpose, scope, users/actors, objectives, and
  high-level business process. Add a high-level architecture or process diagram only when the
  BRD supports one. Do not turn a business-only BRD into a made-up software architecture.
3. Key Architectural Principles: derive concise principles from explicit BRD constraints,
  rules, roles, controls, and operating requirements. Use an empty list when none are stated.
4. Component Design: create one subsection per BRD-derived capability, module, process area,
  or responsibility. For each, include responsibility and key logic derived from the BRD.
  Do not create components merely because this application has frontend, backend, database, or
  AI modules.
5. Process and decision flows: represent BRD-described sequences, branches, queues, approvals,
  calculations, and outcomes in their original terminology. Each flow must have a dynamic list
  of steps and decisions. Do not add a generic Start/End flow when no process is described.
6. API and integration contracts: include a table only for interfaces or integrations named or
  required by the BRD. Derive direction, purpose, payload, protocol, and open details. If the
  BRD names an integration but omits its protocol or payload, preserve the integration and mark
  only that missing detail as "Not specified in BRD".
7. Database and data design: include entities, fields, relationships, constraints, indexes,
  and migration considerations only when the BRD provides data requirements. Never invent a
  schema from the generation application's database.
8. Rules, validation, error handling, security, dependencies, assumptions, risks, and open
  questions: derive each row from the BRD. Put uncertain but BRD-originated interpretations in
  assumptions or open questions and label them clearly.
9. Do not create empty placeholder rows. Omit unsupported subsections or return empty arrays so
  the renderer can omit them.

OUTPUT QUALITY RULES:
- Prefer clear numbered sections and subsections with short descriptive headings.
- Use human-readable paragraphs for explanations and arrays for independently numbered points.
- Keep long descriptions concise enough for tables; place detailed explanations in the relevant
  component or subsection instead of forcing them into a single table cell.
- Preserve traceable BRD wording and IDs instead of replacing them with generic labels.
- Mark inferred technical interpretation as an assumption; never present inference as an explicit
  BRD fact.
- Return only current-generation content derived from the supplied context.

USER REQUEST ABOUT THE SELECTED BRD:
{input_text}

SELECTED BRD CONTEXT:
{context}

Return only valid JSON matching this structure. Keep arrays empty when unsupported and use
\"Not specified in BRD\" for unsupported scalar values:

{{
  \"technicalDesign\": {{
    \"title\": \"BRD-supported technical design title\",
    \"objective\": \"BRD-supported technical objective or Not specified in BRD\",
    \"requirementSummary\": \"Technical interpretation of the selected BRD\",
    \"technicalOverview\": {{
      \"whatIsBeingImplemented\": \"BRD-supported description\",
      \"technicalObjective\": \"BRD-supported objective or Not specified in BRD\",
      \"scopeOfImplementation\": [],
      \"outOfScope\": [],
      \"highLevelApproach\": \"BRD-supported approach or Not specified in BRD\",
      \"relationshipToUserStory\": \"BRD-supported relationship or Not specified in BRD\"
    }},
    \"keyArchitecturalPrinciples\": [],
    \"systemOverview\": {{
      \"highLevelArchitecture\": \"BRD-supported architecture or Not specified in BRD\",
      \"flowchartSteps\": []
    }},
    \"architectureOverview\": {{
      \"frontendComponents\": [],
      \"backendServices\": [],
      \"apis\": [],
      \"databaseStorage\": \"Not specified in BRD\",
      \"externalSystems\": [],
      \"communicationFlow\": \"Not specified in BRD\",
      \"textFlowDiagram\": \"Not specified in BRD\"
    }},
    \"components\": [],
    \"componentDesign\": [],
    \"frontendDesign\": {{
      \"angularComponents\": [], \"services\": [], \"models\": [],
      \"formsAndState\": \"Not specified in BRD\", \"apiIntegration\": \"Not specified in BRD\",
      \"editModeBehavior\": \"Not specified in BRD\", \"validation\": [],
      \"loadingAndErrorStates\": \"Not specified in BRD\", \"uiStateTransitions\": \"Not specified in BRD\"
    }},
    \"backendDesign\": {{
      \"endpoints\": [], \"controllers\": [], \"businessServices\": [], \"repositoryLayer\": [],
      \"validation\": [], \"errorHandling\": [], \"security\": []
    }},
    \"apis\": [],
    \"dataModel\": [],
    \"dataFlow\": [],
    \"processFlows\": [],
    \"integrations\": [],
    \"validation\": [],
    \"validationRules\": {{}},
    \"businessLogic\": [],
    \"businessRuleMappings\": [],
    \"acceptanceCriteriaMappings\": [],
    \"errorHandling\": [],
    \"edgeCases\": [],
    \"security\": [],
    \"databaseChanges\": [],
    \"dependencies\": [],
    \"assumptions\": [],
    \"implementationNotes\": [],
    \"implementationPlan\": [],
    \"testingStrategy\": [],
    \"technicalRisks\": [],
    \"openQuestions\": []
  }}
}}
"""


def build_technical_design_prompt(input_text: str, context: str) -> str:
    ctx = context.strip() if context and context.strip() else ""
    return TECHNICAL_DESIGN_PROMPT_TEMPLATE.format(
        guardrails=GUARDRAILS,
        input_text=input_text,
        context=ctx
    )
