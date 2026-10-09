import base64
import logging
import time
from fastapi import APIRouter, HTTPException, status
from app.api.schemas import (
    MockScreenCompilePdfRequest,
    MockScreenCompilePdfResponse,
    MockScreenPlanRequest,
    MockScreenPlanResponse,
    MockScreenRenderRequest,
    MockScreenRenderResponse
)
from app.services import (
    screen_plan_service,
    image_generation_service,
    pdf_compilation_service
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai/mock-screens", tags=["Mock Screens AI Engine"])


@router.post("/plan", response_model=MockScreenPlanResponse)
def generate_mock_screen_plan(req: MockScreenPlanRequest):
    """
    Section 4, 5, 6, 20: Complete BRD Analysis and Dynamic Screen Plan Generation.
    Uses Gemini to analyze the complete BRD and produce validated ScreenPlan.
    """
    try:
        if not req.brd_text or not req.brd_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="BRD text is empty. Cannot generate mock screen plan."
            )

        start_time = time.time()
        plan = screen_plan_service.generate_plan(req.brd_text, req.project_name)
        duration_ms = int((time.time() - start_time) * 1000)

        return MockScreenPlanResponse(
            plan=plan,
            total_screens=len(plan.screens),
            model="gemini-3.5-flash-lite",
            execution_time_ms=duration_ms
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to generate mock screen plan: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Screen Plan Generation Failed: {str(e)}"
        )


@router.post("/render-screen", response_model=MockScreenRenderResponse)
def render_screen(req: MockScreenRenderRequest):
    """
    Section 8, 9, 10, 21: Render an individual screen mockup image.
    Uses ImageGenerationService abstraction to produce crisp, presentation-ready PNG image.
    """
    try:
        spec = req.specification
        design = req.design_context
        img_bytes = image_generation_service.generate_screen_image(spec, design)
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")

        return MockScreenRenderResponse(
            screen_id=spec.screen_id,
            sequence=spec.sequence,
            name=spec.name,
            image_base64=img_b64,
            mime_type="image/png",
            width=1600,
            height=920,
            image_prompt=spec.image_prompt
        )
    except Exception as e:
        logger.error("Failed to render screen %s: %s", req.specification.name, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Screen rendering failed for '{req.specification.name}': {str(e)}"
        )


@router.post("/compile-pdf", response_model=MockScreenCompilePdfResponse)
def compile_pdf(req: MockScreenCompilePdfRequest):
    """
    Section 17: Combine all generated screen images in sequence into a single PDF document.
    """
    try:
        pdf_bytes = pdf_compilation_service.compile_pdf(
            application_name=req.application_name,
            project_name=req.project_name,
            brd_name=req.brd_name,
            summary=req.summary,
            screens=req.screens
        )
        pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

        return MockScreenCompilePdfResponse(
            pdf_base64=pdf_b64,
            page_count=len(req.screens) + 1,
            file_size_bytes=len(pdf_bytes)
        )
    except Exception as e:
        logger.error("Failed to compile mock screens PDF: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF compilation failed: {str(e)}"
        )
