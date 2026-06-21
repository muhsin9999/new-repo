# Production RAG Chatbot API

A production-grade Retrieval-Augmented Generation (RAG) API built for real workloads — not a tutorial.

**Stack:** Python · FastAPI · LangChain · Pinecone · OpenAI GPT-4 · Celery · Redis · AWS S3 · PostgreSQL · Docker · Alembic · GitHub Actions

---

## What it does

Accepts document uploads, ingests them through a full RAG pipeline, and answers natural language questions with grounded, source-cited responses.

**Pipeline:**
```
Document Upload → Recursive Chunking → OpenAI Embedding
    → Pinecone Vector Storage → Semantic Retrieval → GPT-4 Synthesis
```

**Key design decisions:**
- Async document ingestion via **Celery + Redis** — uploads return immediately, processing happens in the background
- **Pinecone** for vector storage — sub-100ms semantic retrieval at scale
- **S3** for raw document storage, **PostgreSQL** for metadata and conversation history
- Database migrations via **Alembic**
- Full test suite + **GitHub Actions CI/CD** on every push

---

## Architecture

```
Client
  │
  ▼
FastAPI (main API)
  ├── POST /documents     → S3 upload + Celery task
  ├── GET  /documents     → list from PostgreSQL
  ├── POST /chat          → retrieve from Pinecone → GPT-4 → response
  └── GET  /chat/history  → conversation history from PostgreSQL
         │
         ▼
   Celery Worker (Redis broker)
         │
         ├── Chunk document (RecursiveCharacterTextSplitter)
         ├── Generate embeddings (OpenAI text-embedding-3-small)
         └── Upsert to Pinecone
```

---

## Run locally

```bash
git clone https://github.com/muhsin9999/rag-chatbot-api
cd rag-chatbot-api/rag-chatbot-api
cp .env.example .env          # add your API keys
docker-compose up --build     # starts FastAPI + Celery + Redis + PostgreSQL
```

**Required env vars:**
```
OPENAI_API_KEY=
PINECONE_API_KEY=
PINECONE_INDEX_NAME=
DATABASE_URL=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
S3_BUCKET_NAME=
```

---

## Tech stack detail

| Layer | Technology | Why |
|---|---|---|
| API | FastAPI | Async-native, automatic OpenAPI docs |
| LLM Orchestration | LangChain | Retrieval chains, text splitters |
| Vector Store | Pinecone | Managed, fast, production-ready |
| LLM | OpenAI GPT-4 | Best-in-class reasoning |
| Task Queue | Celery + Redis | Non-blocking document ingestion |
| Object Storage | AWS S3 | Scalable raw document storage |
| Database | PostgreSQL + SQLAlchemy | Metadata and conversation history |
| Migrations | Alembic | Schema version control |
| Containerisation | Docker Compose | Single-command local setup |
| CI/CD | GitHub Actions | Automated test + build on push |

---

Built by [Mustapha Muhsin](https://github.com/muhsin9999) · [LinkedIn](https://linkedin.com/in/mustapha-muhsin-2288bb33b)
