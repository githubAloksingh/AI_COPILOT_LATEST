# AI Work Copilot - Python AI & RAG Microservice

Dedicated FastAPI microservice responsible for document parsing, chunking, embeddings generation, vector storage in ChromaDB, RAG retrieval, prompt construction, and Gemini structured AI generation.

---

## Features
- **Document Ingestion**: Parsing PDF (PyMuPDF), DOCX (python-docx), CSV (pandas/csv), and TXT/MD/JSON formats.
- **Configurable Chunking**: Sliding-window chunking with configurable `CHUNK_SIZE` and `CHUNK_OVERLAP`.
- **Vector Embeddings**: Gemini batch embedding generation with candidate model fallbacks (`text-embedding-004`).
- **ChromaDB Vector Store**: Remote Chroma HTTP client and embedded persistent storage with document ID and chunk index tracking.
- **RAG Generation**: Context retrieval + prompt guardrails + Google Gemini structured JSON generation.
- **Auditable Source Tracking**: Returns retrieved source chunks and metadata alongside AI responses.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check (service status, Chroma connectivity, Gemini config) |
| `POST` | `/api/ai/ingest` | Upload file multipart, parse, chunk, embed, store in Chroma |
| `POST` | `/api/ai/retrieve` | Vector similarity search returning relevant chunks and source metadata |
| `POST` | `/api/ai/requirements/generate` | Generate structured user stories & acceptance criteria |
| `POST` | `/api/ai/test-cases/generate` | Generate positive, negative, and edge test cases |
| `POST` | `/api/ai/defects/analyze` | Triage defect logs, stack traces, and suggest root cause fixes |
| `POST` | `/api/ai/release-notes/generate` | Generate clean release notes from sprint information |
| `POST` | `/api/ai/daily-status/generate` | Generate structured scrum daily status updates |

---

## Configuration (`.env`)

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.7-flash
GEMINI_EMBEDDING_MODEL=text-embedding-004
CHROMA_URL=http://localhost:8000
CHROMA_COLLECTION=ai_work_copilot
CHUNK_SIZE=1000
CHUNK_OVERLAP=150
TOP_K=5
HOST=0.0.0.0
PORT=8000
```

---

## Running Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run unit tests
pytest

# 3. Start development server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
