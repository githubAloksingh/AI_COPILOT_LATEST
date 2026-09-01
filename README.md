# AI Work Copilot

AI Work Copilot is an end-to-end Generative AI & RAG assistant tailored for software development lifecycle (SDLC) teams. It transforms unstructured requirements, triages defects, generates test cases, drafts release notes, and formulates daily sprint updates using team knowledge stored in Chroma Vector DB and MySQL.

---

## 🌟 Target Architecture

The project is cleanly decoupled into two backend tiers:
1. **Spring Boot Java Backend**: Core business application gateway, REST APIs for Frontend, SQL/JPA persistence (MySQL/H2), audit logging, and business entities.
2. **Python AI / RAG Microservice (`ai-service/`)**: Document parsing, text extraction, chunking, embeddings generation, vector storage in ChromaDB, RAG retrieval, prompt guardrails, and Google Gemini structured generation.

```mermaid
graph TD
    Frontend[Angular Frontend (Port 4200)] -->|REST API| SB[Spring Boot Backend (Port 8080)]
    SB -->|AiServiceClient (HTTP)| PyAI[Python AI/RAG Service (Port 8000)]
    PyAI -->|Chunk Embeddings / Vector Search| Chroma[(ChromaDB Vector Store)]
    PyAI -->|Prompts + RAG Context| Gemini[Google Gemini API]
    Gemini -->|Structured JSON| PyAI
    PyAI -->|AI Results + Retrieved Sources| SB
    SB -->|JPA Persistence / Audit Logs| SQL[(SQL Database - MySQL / H2)]
    SB -->|Response DTOs| Frontend
```

---

## 🏛️ Responsibility Matrix

| Responsibility Layer | Spring Boot Java Backend | Python AI/RAG Service | Chroma Vector DB | SQL (MySQL / H2) | Google Gemini |
|---|---|---|---|---|---|
| **Public REST APIs for Frontend** | ✅ Yes (Port 8080) | ❌ No | ❌ No | ❌ No | ❌ No |
| **Document Ingestion Parsing** | ❌ No | ✅ Yes (PyMuPDF, docx, pandas) | ❌ No | ❌ No | ❌ No |
| **Text Chunking & Embeddings** | ❌ No | ✅ Yes | ❌ No | ❌ No | ✅ Models |
| **Vector Similarity Search (RAG)**| ❌ No | ✅ Yes | ✅ Vector Index | ❌ No | ❌ No |
| **Prompt Engineering & Guardrails** | ❌ No | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Structured Output Generation** | ❌ No | ✅ Yes (Pydantic validated) | ❌ No | ❌ No | ✅ LLM Engine |
| **Business Logic & CRUD** | ✅ Yes | ❌ No | ❌ No | ❌ No | ❌ No |
| **Persistence (Requirements, Tests, Defects)** | ✅ Yes | ❌ No | ❌ No | ✅ Tables | ❌ No |
| **Audit Logging & Feedback** | ✅ Yes | ❌ No | ❌ No | ✅ Tables | ❌ No |

---

## 🚀 Prerequisites

1. **Java 17**: Ensure JDK 17 is installed.
2. **Python 3.11+**: For the `ai-service/` FastAPI microservice.
3. **Node.js**: (Node.js 20+ or 22+).
4. **Google Gemini API Key**: From Google AI Studio.
5. **Database**: Embedded H2 (default) or MySQL 8.4.

---

## 🛠️ Step-by-Step Local Setup

### 1. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Fill in your `GEMINI_API_KEY`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.7-flash
GEMINI_EMBEDDING_MODEL=text-embedding-004
CHROMA_URL=http://localhost:8000
AI_SERVICE_URL=http://localhost:8000
```

---

### 2. Start Python AI / RAG Microservice (Port 8000)

```bash
cd ai-service
pip install -r requirements.txt

# Run unit tests
pytest

# Start the service
# On Windows (PowerShell):
.\start-ai-service.ps1
# Or on Linux/macOS:
./start-ai-service.sh
```
_FastAPI Swagger docs available at: `http://localhost:8000/docs`._

---

### 3. Start Spring Boot Java Backend (Port 8080)

```bash
cd backend
# On Windows (PowerShell):
.\start-backend.ps1
# Or on Linux/macOS:
./start-backend.sh
```
_Backend API health available at: `http://localhost:8080/api/health`._

---

### 4. Start Angular Frontend (Port 4200)

```bash
cd frontend
# On Windows (PowerShell):
.\start-frontend.ps1
# Or on Linux/macOS:
./start-frontend.sh
```
_Frontend will open at `http://localhost:4200`._

---

## 📂 Testing End-to-End Workflow

1. **Document Ingestion (`/knowledge-base`)**:
   - Upload any `.pdf`, `.docx`, `.csv`, or `.txt` file.
   - Spring Boot records metadata in SQL (`status=PROCESSING`), delegates parsing and embedding to Python `ai-service`, and updates status to `COMPLETED` when indexed in ChromaDB.
2. **Requirement Assistant (`/requirements`)**:
   - Enter title & requirement details.
   - Python RAG retrieves relevant document chunks from Chroma, prompts Gemini with guardrails, returns structured user stories & acceptance criteria, and Spring Boot persists the result in SQL.
3. **Test Generator (`/test-generator`)**:
   - Generates positive, negative, and edge test cases linked to requirement context.
4. **Defect Triage (`/defect-triage`)**:
   - Analyzes logs, stack traces, and historical defect context to output probable root causes and fixes.
5. **Release Notes & Daily Status (`/release-notes`)**:
   - Generates sprint release notes and daily standup summaries.
6. **Audit & History (`/audit-history`)**:
   - Spring Boot logs request ID, feature, model, execution time, and retrieved sources for full auditability.

---

## 🔒 Guardrails & Security

- **Prompt Injection Defense**: Guardrails in `ai-service/app/prompts/guardrails.py` ensure all retrieved documents are strictly treated as reference context, preventing instructions inside documents from overriding system directives.
- **Structured Validation**: Pydantic models in Python and Jackson DTOs in Java validate JSON responses before persistence.
- **Zero Secret Exposure**: Health checks and audit logs never expose API keys or credentials.
