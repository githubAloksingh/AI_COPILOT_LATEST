import logging
from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from app.config import settings
from app.api.schemas import (
    HealthResponse,
    IngestionResponse,
    RetrieveRequest,
    RetrieveResponse,
    RequirementGenerateRequest,
    RequirementGenerateResponse,
    TestCaseGenerateRequest,
    TestCaseGenerateResponse,
    DefectAnalyzeRequest,
    DefectAnalyzeResponse,
    ReleaseNoteGenerateRequest,
    ReleaseNoteGenerateResponse,
    DailyStatusGenerateRequest,
    DailyStatusGenerateResponse
)
from app.services import (
    document_service,
    chunking_service,
    retrieval_service,
    rag_service
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai", tags=["AI & RAG"])


@router.post("/ingest", response_model=IngestionResponse)
async def ingest_document(
    file: UploadFile = File(...),
    document_id: str = Form(...),
    file_name: Optional[str] = Form(None),
    file_type: Optional[str] = Form(None)
):
    """Ingest a document: parse -> clean -> chunk -> embed -> store in Chroma."""
    try:
        content_bytes = await file.read()
        if not content_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty"
            )

        name = file_name or file.filename or "unknown"
        m_type = file_type or file.content_type or ""

        # 1. Parse text
        text = document_service.extract_text(content_bytes, file_name=name, file_type=m_type)
        if not text or not text.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Document contains no readable text"
            )

        # 2. Chunk text
        chunks = chunking_service.chunk_text(text)
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Chunking produced no content chunks"
            )

        # 3. Embed and store in Chroma
        stored_count = retrieval_service.store_chunks(
            document_id=document_id,
            file_name=name,
            chunks=chunks
        )

        return IngestionResponse(
            status="COMPLETED",
            document_id=document_id,
            file_name=name,
            chunk_count=stored_count,
            message=f"Successfully ingested and embedded {stored_count} chunks"
        )
    except HTTPException:
        raise
    except ValueError as ve:
        logger.error("Document parsing error for doc ID %s: %s", document_id, ve)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error("Ingestion failed for doc ID %s: %s", document_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}"
        )


@router.post("/retrieve", response_model=RetrieveResponse)
def retrieve_context(req: RetrieveRequest):
    """Perform vector similarity search against ChromaDB."""
    try:
        chunks, sources = retrieval_service.retrieve_relevant_context(
            query=req.query,
            top_k=req.top_k,
            document_id=req.document_id
        )
        return RetrieveResponse(query=req.query, chunks=chunks, sources=sources)
    except Exception as e:
        logger.error("Retrieval failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Context retrieval failed: {str(e)}"
        )


@router.post("/requirements/generate", response_model=RequirementGenerateResponse)
def generate_requirements(req: RequirementGenerateRequest):
    """Generate structured software requirement with RAG context."""
    try:
        return rag_service.generate_requirement(req)
    except Exception as e:
        logger.error("Requirement generation failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Requirement generation failed: {str(e)}"
        )


@router.post("/test-cases/generate", response_model=TestCaseGenerateResponse)
def generate_test_cases(req: TestCaseGenerateRequest):
    """Generate structured test cases (positive, negative, edge) with RAG context."""
    try:
        return rag_service.generate_test_cases(req)
    except Exception as e:
        logger.error("Test case generation failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test case generation failed: {str(e)}"
        )


@router.post("/defects/analyze", response_model=DefectAnalyzeResponse)
def analyze_defect(req: DefectAnalyzeRequest):
    """Analyze defect logs and stack trace with RAG context."""
    try:
        return rag_service.analyze_defect(req)
    except Exception as e:
        logger.error("Defect analysis failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Defect analysis failed: {str(e)}"
        )


@router.post("/release-notes/generate", response_model=ReleaseNoteGenerateResponse)
def generate_release_notes(req: ReleaseNoteGenerateRequest):
    """Generate structured release notes based on sprint info."""
    try:
        return rag_service.generate_release_notes(req)
    except Exception as e:
        logger.error("Release note generation failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Release note generation failed: {str(e)}"
        )


@router.post("/daily-status/generate", response_model=DailyStatusGenerateResponse)
def generate_daily_status(req: DailyStatusGenerateRequest):
    """Generate structured scrum daily status update."""
    try:
        return rag_service.generate_daily_status(req)
    except Exception as e:
        logger.error("Daily status generation failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Daily status generation failed: {str(e)}"
        )


@router.get("/inspect", tags=["Chroma Inspection"])
def inspect_chroma_contents(limit: int = 50):
    """Inspect all chunks, metadata, and document snippets stored inside ChromaDB."""
    try:
        retrieval_service.ensure_collection()
        if retrieval_service._local_collection:
            count = retrieval_service._local_collection.count()
            data = retrieval_service._local_collection.get(limit=limit, include=["metadatas", "documents"])
            return {
                "storage_type": "local_persistent",
                "collection_name": retrieval_service.collection_name,
                "total_chunks": count,
                "chunks": [
                    {
                        "id": data["ids"][i],
                        "metadata": data["metadatas"][i] if i < len(data["metadatas"]) else {},
                        "preview": data["documents"][i][:200] if i < len(data["documents"]) else ""
                    }
                    for i in range(len(data.get("ids", [])))
                ]
            }
        elif retrieval_service.base_collection_url:
            import httpx
            with httpx.Client(timeout=retrieval_service.timeout) as client:
                fetch_url = f"{retrieval_service.base_collection_url}/get"
                resp = client.post(fetch_url, json={"limit": limit, "include": ["metadatas", "documents"]})
                if resp.status_code == 200:
                    data = resp.json()
                    ids = data.get("ids", [])
                    metas = data.get("metadatas", [])
                    docs = data.get("documents", [])
                    return {
                        "storage_type": "remote_chroma_server",
                        "collection_name": retrieval_service.collection_name,
                        "total_chunks": len(ids),
                        "chunks": [
                            {
                                "id": ids[i],
                                "metadata": metas[i] if i < len(metas) else {},
                                "preview": docs[i][:200] if i < len(docs) else ""
                            }
                            for i in range(len(ids))
                        ]
                    }
        return {"message": "No Chroma collection currently initialized."}
    except Exception as e:
        logger.error("Inspection error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

