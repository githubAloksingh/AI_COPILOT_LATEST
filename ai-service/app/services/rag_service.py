import logging
import time
from typing import List, Optional
from app.config import settings
from app.api.schemas import (
    SourceDto,
    RequirementGenerateRequest,
    RequirementGenerateResponse,
    RequirementResult,
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
    TESTCASE_PROMPT_VERSION,
    build_testcase_prompt,
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
        combined_query = f"{req.title}\n{req.description}"
        chunks, sources = self.retrieval.retrieve_relevant_context(req.description)
        combined_context = "\n\n---\n\n".join(chunks)

        prompt = build_requirement_prompt(combined_query, combined_context)
        result = self.gemini.generate_structured(prompt, RequirementResult)
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

    def generate_test_cases(self, req: TestCaseGenerateRequest) -> TestCaseGenerateResponse:
        start_time = time.time()
        chunks, sources = self.retrieval.retrieve_relevant_context(req.requirement)
        combined_context = "\n\n---\n\n".join(chunks)

        prompt = build_testcase_prompt(
            requirement=req.requirement,
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

    def analyze_defect(self, req: DefectAnalyzeRequest) -> DefectAnalyzeResponse:
        start_time = time.time()
        combined_input = f"{req.title or ''}\n{req.description or ''}\n{req.logs or ''}"
        chunks, sources = self.retrieval.retrieve_relevant_context(combined_input)
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
        chunks, sources = self.retrieval.retrieve_relevant_context(req.sprintInformation)
        combined_context = "\n\n---\n\n".join(chunks)

        prompt = build_release_notes_prompt(
            version=req.version,
            sprint_info=req.sprintInformation,
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
