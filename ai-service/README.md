# AI Work Copilot - Python AI & RAG Microservice

Dedicated FastAPI microservice responsible for document parsing, chunking, embeddings generation, vector storage in ChromaDB, RAG retrieval, prompt construction, and Gemini structured AI generation.

---

## Features
- **Document Ingestion**: Parsing PDF (PyMuPDF), DOCX (python-docx), CSV (pandas/csv), and TXT/MD/JSON formats.
- **Configurable Chunking**: Sliding-window chunking with configurable `CHUNK_SIZE` and `CHUNK_OVERLAP`.
- **Vector Embeddings**: Local batched `sentence-transformers/paraphrase-MiniLM-L3-v2` embeddings.
- **Large Uploads**: Knowledge-base uploads up to 1 GB, including ZIP archives, with ZIP parsing from the upload stream.
- **ChromaDB Vector Store**: Remote Chroma HTTP client and embedded persistent storage with document ID and chunk index tracking.
- **RAG Generation**: Context retrieval + prompt guardrails + Google Gemini structured JSON generation.
- **Auditable Source Tracking**: Returns retrieved source chunks and metadata alongside AI responses.
- **BRD Mock Screens**: Gemini returns a schema-constrained, validated screen plan; Chromium renders exact specification text and controls with HTML/CSS, including responsive pie, diverging bar, and line charts on relevant analytical screens. Chart values identify their BRD/screen-data/illustrative source; illustrative values are labeled and source-defined units are rendered. Stability AI produces optional, layout-aware decorative artwork only. PDFs use consistent landscape pages, readable wrapped specification sections, and automatic pagination for long requirements.

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
| `POST` | `/api/ai/mock-screens/plan` | Plan BRD-driven screens with Gemini text generation |
| `POST` | `/api/ai/mock-screens/render-screen` | Render a specification-faithful PNG with HTML/CSS and optional Stability artwork |
| `POST` | `/api/ai/mock-screens/compile-pdf` | Compile generated screen PNGs in sequence |

---

## Configuration (`.env`)

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.7-flash
IMAGE_GENERATOR_PROVIDER=stability
STABILITY_API_KEY=your_stability_api_key_here
STABILITY_TIMEOUT_SECONDS=180
STABILITY_ASSET_DIR=./data/stability-assets
TRANSFORMER_EMBEDDING_MODEL=sentence-transformers/paraphrase-MiniLM-L3-v2
MAX_UPLOAD_SIZE_MB=1024
CHROMA_URL=http://localhost:8000
CHROMA_COLLECTION=ai_work_copilot
CHUNK_SIZE=1000
CHUNK_OVERLAP=150
TOP_K=5
HOST=127.0.0.1
PORT=8000
FRONTEND_ORIGINS=http://localhost:4200,http://127.0.0.1:4200
```

`GEMINI_API_KEY` is used for BRD analysis and screen planning. Stability is selected by default and requires `STABILITY_API_KEY`; its Bearer credential is read only by the backend. Stability prompts describe generic layout artwork and do not contain BRD-derived text. Returned PNG assets are validated and cached under `STABILITY_ASSET_DIR`; Chromium overlays the actual BRD-derived text, fields, tables, and actions before returning the existing screen PNG. Stability failures are returned explicitly; there is no silent fallback. Set `IMAGE_GENERATOR_PROVIDER=pymupdf` to explicitly select the legacy native fallback. Run `python -m playwright install chromium` outside Docker before rendering.

---

## Running Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run unit tests
pytest

# 3. Start development server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

In deployments, connect Spring Boot and the AI service over a private network and do not publish port 8000.
