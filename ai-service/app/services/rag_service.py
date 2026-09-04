import logging
import time
from typing import List, Optional
from app.config import settings
from app.api.schemas import (
    SourceDto,
    RequirementGenerateRequest,
    RequirementGenerateResponse,
    RequirementResult,
    RequirementItem,
    GroundedItem,
    TestCaseGenerateRequest,
    TestCaseGenerateResponse,
    TestCaseItem,
    DefectAnalyzeRequest,
    DefectAnalyzeResponse,
    DefectResult,
    ReleaseNoteGenerateRequest,
    ReleaseNoteGenerateResponse,
    ReleaseNoteResult,
    DailyStatusGenerateRequest,
    DailyStatusGenerateResponse,
    DailyStatusResult
)
from app.prompts import (
    REQUIREMENT_PROMPT_VERSION,
    build_requirement_prompt,
    USER_STORY_PROMPT_VERSION,
    build_user_story_prompt,
    FUNCTIONAL_DESIGN_PROMPT_VERSION,
    build_functional_design_prompt,
    TECHNICAL_DESIGN_PROMPT_VERSION,
    build_technical_design_prompt,
    TESTCASE_PROMPT_VERSION,
    build_testcase_prompt,
    build_testcase_from_files_prompt,
    DEFECT_PROMPT_VERSION,
    build_defect_prompt,
    RELEASE_NOTE_PROMPT_VERSION,
    build_release_notes_prompt,
    DAILY_STATUS_PROMPT_VERSION,
    build_daily_status_prompt
)
from app.services.retrieval_service import retrieval_service
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)


class RagService:
    def __init__(self):
        self.retrieval = retrieval_service
        self.gemini = gemini_service

    def generate_requirement(self, req: RequirementGenerateRequest) -> RequirementGenerateResponse:
        start_time = time.time()
        combined_query = f"{req.title or ''}\n{req.description or ''}".strip()
        top_k = 15 if req.document_id else None
        chunks, sources = self.retrieval.retrieve_relevant_context(
            query=combined_query or "requirement functional requirements user stories acceptance criteria",
            top_k=top_k,
            document_id=req.document_id
        )
        combined_context = "\n\n---\n\n".join(chunks)

        prompt = build_requirement_prompt(combined_query or "Requirement from knowledge base", combined_context)
        raw_result = self.gemini.generate_structured(prompt, RequirementResult)
        result = self._validate_and_sanitize_grounding(raw_result, combined_context)
        exec_time_ms = int((time.time() - start_time) * 1000)

        source_strings = [s.snippet or s.file_name or "" for s in sources if s.snippet or s.file_name]

        return RequirementGenerateResponse(
            result=result,
            sources=source_strings,
            source_details=sources,
            model=settings.gemini_model,
            prompt_version=REQUIREMENT_PROMPT_VERSION,
            execution_time_ms=exec_time_ms
        )

    def generate_user_story(self, req: RequirementGenerateRequest) -> RequirementGenerateResponse:
        start_time = time.time()
        combined_query = f"{req.title or ''}\n{req.description or ''}".strip()
        top_k = 15 if req.document_id else None
        chunks, sources = self.retrieval.retrieve_relevant_context(
            query=combined_query or "user story requirement functional requirements acceptance criteria",
            top_k=top_k,
            document_id=req.document_id
        )
        combined_context = "\n\n---\n\n".join(chunks)

        prompt = build_user_story_prompt(combined_query or "User Story from requirement", combined_context)
        parsed_dict = self.gemini.generate_dict(prompt)
        user_stories_raw = parsed_dict.get("userStories", [])
        if not isinstance(user_stories_raw, list):
            user_stories_raw = [user_stories_raw] if user_stories_raw else []

        requirements = []
        for idx, us in enumerate(user_stories_raw):
            if isinstance(us, dict):
                req_item = RequirementItem(
                    requirementId=us.get("userStoryId") or f"US-{idx+1:03d}",
                    userStoryId=us.get("userStoryId") or f"US-{idx+1:03d}",
                    title=us.get("title") or f"User Story {idx+1}",
                    summary=us.get("summary") or us.get("description") or "",
                    userStory=us.get("userStory") or "",
                    description=us.get("description") or "",
                    acceptanceCriteria=[GroundedItem.from_any(ac) for ac in us.get("acceptanceCriteria", [])],
                    businessRules=[GroundedItem.from_any(br) for br in us.get("businessRules", [])],
                    assumptions=[GroundedItem.from_any(asump) for asump in us.get("assumptions", [])],
                    dependencies=[GroundedItem.from_any(dep) for dep in us.get("dependencies", [])],
                    edgeCases=[GroundedItem.from_any(ec) for ec in us.get("edgeCases", [])],
                )
                requirements.append(req_item)

        raw_result = RequirementResult(
            requirements=requirements,
            userStories=user_stories_raw
        )
        result = self._validate_and_sanitize_grounding(raw_result, combined_context)
        exec_time_ms = int((time.time() - start_time) * 1000)

        source_strings = [s.snippet or s.file_name or "" for s in sources if s.snippet or s.file_name]

        return RequirementGenerateResponse(
            result=result,
            sources=source_strings,
            source_details=sources,
            model=settings.gemini_model,
            prompt_version=USER_STORY_PROMPT_VERSION,
            execution_time_ms=exec_time_ms
        )

    def generate_functional_design(self, req: RequirementGenerateRequest) -> RequirementGenerateResponse:
        start_time = time.time()
        combined_query = f"{req.title or ''}\n{req.description or ''}".strip()
        top_k = 15 if req.document_id else None
        chunks, sources = self.retrieval.retrieve_relevant_context(
            query=combined_query or "functional design workflow actors preconditions validations rules",
            top_k=top_k,
            document_id=req.document_id
        )
        combined_context = "\n\n---\n\n".join(chunks)

        prompt = build_functional_design_prompt(combined_query or "Functional Design requirement", combined_context)
        parsed_dict = self.gemini.generate_dict(prompt)
        fd_raw = parsed_dict.get("functionalDesign", parsed_dict)
        if not isinstance(fd_raw, dict):
            fd_raw = {}

        title = fd_raw.get("title", "Functional Design")
        objective = fd_raw.get("objective", "")
        scope = fd_raw.get("scope", [])

        req_item = RequirementItem(
            requirementId="FD-001",
            title=title,
            summary=objective or ("\n".join(scope) if isinstance(scope, list) else str(scope)),
            userStory=f"Objective: {objective}",
            description=objective,
            acceptanceCriteria=[GroundedItem.from_any(v) for v in fd_raw.get("validations", [])],
            businessRules=[GroundedItem.from_any(br) for br in fd_raw.get("businessRules", [])],
            assumptions=[GroundedItem.from_any(a) for a in fd_raw.get("assumptions", [])],
            dependencies=[GroundedItem.from_any(d) for d in fd_raw.get("dependencies", [])],
            edgeCases=[GroundedItem.from_any(eh.get("scenario", "") if isinstance(eh, dict) else eh) for eh in fd_raw.get("errorHandling", [])]
        )

        raw_result = RequirementResult(
            requirements=[req_item],
            functionalDesign=fd_raw
        )
        result = self._validate_and_sanitize_grounding(raw_result, combined_context)
        exec_time_ms = int((time.time() - start_time) * 1000)

        source_strings = [s.snippet or s.file_name or "" for s in sources if s.snippet or s.file_name]

        return RequirementGenerateResponse(
            result=result,
            sources=source_strings,
            source_details=sources,
            model=settings.gemini_model,
            prompt_version=FUNCTIONAL_DESIGN_PROMPT_VERSION,
            execution_time_ms=exec_time_ms
        )

    def generate_technical_design(self, req: RequirementGenerateRequest) -> RequirementGenerateResponse:
        start_time = time.time()
        combined_query = f"{req.title or ''}\n{req.description or ''}".strip()
        top_k = 15 if req.document_id else None
        chunks, sources = self.retrieval.retrieve_relevant_context(
            query=combined_query or "technical design architecture apis data model components security",
            top_k=top_k,
            document_id=req.document_id
        )
        combined_context = "\n\n---\n\n".join(chunks)

        prompt = build_technical_design_prompt(combined_query or "Technical Design requirement", combined_context)
        parsed_dict = self.gemini.generate_dict(prompt)
        td_raw = parsed_dict.get("technicalDesign", parsed_dict)
        if not isinstance(td_raw, dict):
            td_raw = {}

        title = td_raw.get("title", "Technical Design")
        objective = td_raw.get("objective", "")
        summary = td_raw.get("requirementSummary", objective)

        req_item = RequirementItem(
            requirementId="TD-001",
            title=title,
            summary=summary,
            userStory=f"Objective: {objective}",
            description=summary,
            acceptanceCriteria=[GroundedItem.from_any(v) for v in td_raw.get("validation", [])],
            businessRules=[GroundedItem.from_any(bl) for bl in td_raw.get("businessLogic", [])],
            assumptions=[GroundedItem.from_any(a) for a in td_raw.get("assumptions", [])],
            dependencies=[GroundedItem.from_any(d) for d in td_raw.get("dependencies", [])],
            edgeCases=[GroundedItem.from_any(eh.get("scenario", "") if isinstance(eh, dict) else eh) for eh in td_raw.get("errorHandling", [])]
        )

        raw_result = RequirementResult(
            requirements=[req_item],
            technicalDesign=td_raw
        )
        result = self._validate_and_sanitize_grounding(raw_result, combined_context)
        exec_time_ms = int((time.time() - start_time) * 1000)

        source_strings = [s.snippet or s.file_name or "" for s in sources if s.snippet or s.file_name]

        return RequirementGenerateResponse(
            result=result,
            sources=source_strings,
            source_details=sources,
            model=settings.gemini_model,
            prompt_version=TECHNICAL_DESIGN_PROMPT_VERSION,
            execution_time_ms=exec_time_ms
        )

    def _validate_and_sanitize_grounding(self, result: RequirementResult, context_text: str) -> RequirementResult:
        if not result or not result.requirements:
            return result

        context_lower = context_text.lower() if context_text else ""

        # Specific known unsupported hallucination patterns to catch and flag
        unsupported_patterns = [
            ("default to route d", "Classifier failure defaults to Route D"),
            ("defaults to route d", "Classifier failure defaults to Route D"),
            ("empty input is ignored", "Empty input behavior"),
            ("synchronous and single-user", "Synchronous single-user assumption"),
            ("division-by-zero", "Division by zero handling"),
            ("invalid api key necessarily prevents startup", "API key startup validation"),
        ]

        for req in result.requirements:
            for item_list in [req.acceptanceCriteria, req.assumptions, req.dependencies, req.edgeCases]:
                for item in item_list:
                    item_text_lower = (item.text or "").lower()

                    # 1. Check against known unsupported hallucination patterns
                    for pattern, label in unsupported_patterns:
                        if pattern in item_text_lower and pattern not in context_lower:
                            item.grounding = "REQUIRES_CONFIRMATION"
                            if "Not specified in BRD" not in item.text and "Requires Confirmation" not in item.text:
                                item.text = f"{item.text} (Requires Confirmation: Not explicitly specified in BRD)"

                    # 2. Check explicit source claims
                    if item.grounding == "EXPLICIT" and item.source:
                        valid_sources = []
                        for src in item.source:
                            if src and src.lower() in context_lower:
                                valid_sources.append(src)
                        # If sources were claimed (like AC-099) but do not exist in context
                        if item.source and not valid_sources and context_lower:
                            item.grounding = "DERIVED"
                            item.source = []

                    # 3. If text says "not specified in the brd", ensure it's not marked EXPLICIT
                    if "not specified" in item_text_lower:
                        item.grounding = "REQUIRES_CONFIRMATION"

        return result

    def generate_test_cases(self, req: TestCaseGenerateRequest) -> TestCaseGenerateResponse:
        start_time = time.time()
        query_text = (req.requirement or "").strip()

        doc_ids = []
        if req.document_id:
            doc_ids.append(str(req.document_id))
        if req.zip_document_id:
            doc_ids.append(str(req.zip_document_id))

        target_doc_id = doc_ids if doc_ids else None
        top_k = 25 if doc_ids else None

        chunks, sources = self.retrieval.retrieve_relevant_context(
            query=query_text or "test cases functional edge security performance scenarios",
            top_k=top_k,
            document_id=target_doc_id
        )
        combined_context = "\n\n---\n\n".join(chunks)

        prompt = build_testcase_prompt(
            requirement=query_text or "Generate test cases for provided context",
            acceptance_criteria=req.acceptanceCriteria or "",
            test_types=req.testTypes,
            context=combined_context
        )
        result = self.gemini.generate_structured_list(prompt, TestCaseItem)
        exec_time_ms = int((time.time() - start_time) * 1000)

        source_strings = [s.snippet or s.file_name or "" for s in sources if s.snippet or s.file_name]

        return TestCaseGenerateResponse(
            result=result,
            sources=source_strings,
            source_details=sources,
            model=settings.gemini_model,
            prompt_version=TESTCASE_PROMPT_VERSION,
            execution_time_ms=exec_time_ms
        )

    def generate_test_cases_from_files(
        self,
        mode: str,
        brd_text: str = "",
        brd_filename: str = "",
        zip_summary: str = "",
        zip_sources: List[str] = None,
        test_types: List[str] = None
    ) -> TestCaseGenerateResponse:
        start_time = time.time()
        prompt = build_testcase_from_files_prompt(
            mode=mode,
            brd_text=brd_text,
            zip_summary=zip_summary,
            test_types=test_types
        )
        result = self.gemini.generate_structured_list(prompt, TestCaseItem)
        exec_time_ms = int((time.time() - start_time) * 1000)

        sources = []
        if brd_filename:
            sources.append(f"BRD: {brd_filename}")
        if zip_sources:
            sources.extend([f"ZIP: {s}" for s in zip_sources[:10]])

        return TestCaseGenerateResponse(
            result=result,
            sources=sources,
            source_details=[],
            model=settings.gemini_model,
            prompt_version=TESTCASE_PROMPT_VERSION,
            execution_time_ms=exec_time_ms
        )

    def analyze_defect(self, req: DefectAnalyzeRequest) -> DefectAnalyzeResponse:
        start_time = time.time()
        combined_input = f"{req.title or ''}\n{req.description or ''}\n{req.logs or ''}".strip()
        top_k = 25 if req.document_id else None

        chunks, sources = self.retrieval.retrieve_relevant_context(
            query=combined_input or "defect error stacktrace exception root cause fix investigation",
            top_k=top_k,
            document_id=req.document_id
        )
        combined_context = "\n\n---\n\n".join(chunks)

        prompt = build_defect_prompt(
            title=req.title,
            description=req.description or "",
            logs=req.logs or "",
            steps=req.stepsToReproduce or "",
            actual=req.actualBehavior or "",
            expected=req.expectedBehavior or "",
            context=combined_context
        )
        result = self.gemini.generate_structured(prompt, DefectResult)
        exec_time_ms = int((time.time() - start_time) * 1000)

        source_strings = [s.snippet or s.file_name or "" for s in sources if s.snippet or s.file_name]

        return DefectAnalyzeResponse(
            result=result,
            sources=source_strings,
            source_details=sources,
            model=settings.gemini_model,
            prompt_version=DEFECT_PROMPT_VERSION,
            execution_time_ms=exec_time_ms
        )

    def generate_release_notes(self, req: ReleaseNoteGenerateRequest) -> ReleaseNoteGenerateResponse:
        start_time = time.time()
        query_text = (req.sprintInformation or "").strip()
        chunks, sources = self.retrieval.retrieve_relevant_context(
            query=query_text or "release notes",
            document_id=req.document_id
        )
        combined_context = "\n\n---\n\n".join(chunks)

        prompt = build_release_notes_prompt(
            version=req.version or "1.0.0",
            sprint_info=query_text or "Generate release notes from provided context",
            context=combined_context
        )
        result = self.gemini.generate_structured(prompt, ReleaseNoteResult)
        exec_time_ms = int((time.time() - start_time) * 1000)

        source_strings = [s.snippet or s.file_name or "" for s in sources if s.snippet or s.file_name]

        return ReleaseNoteGenerateResponse(
            result=result,
            sources=source_strings,
            source_details=sources,
            model=settings.gemini_model,
            prompt_version=RELEASE_NOTE_PROMPT_VERSION,
            execution_time_ms=exec_time_ms
        )

    def generate_daily_status(self, req: DailyStatusGenerateRequest) -> DailyStatusGenerateResponse:
        start_time = time.time()
        chunks, sources = self.retrieval.retrieve_relevant_context(req.sprintInformation)
        
        prompt = build_daily_status_prompt(req.sprintInformation)
        result = self.gemini.generate_structured(prompt, DailyStatusResult)
        exec_time_ms = int((time.time() - start_time) * 1000)

        source_strings = [s.snippet or s.file_name or "" for s in sources if s.snippet or s.file_name]

        return DailyStatusGenerateResponse(
            result=result,
            sources=source_strings,
            source_details=sources,
            model=settings.gemini_model,
            prompt_version=DAILY_STATUS_PROMPT_VERSION,
            execution_time_ms=exec_time_ms
        )


rag_service = RagService()
