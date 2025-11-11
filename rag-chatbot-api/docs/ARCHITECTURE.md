# RAG Chatbot API - Architecture Documentation

## Overview

The RAG Chatbot API is a production-ready backend service that implements Retrieval Augmented Generation (RAG) for intelligent document-based conversations. The system is built with FastAPI, uses PostgreSQL for structured data, Pinecone for vector search, and integrates with OpenAI's GPT models.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Client Layer                          │
│                   (Web, Mobile, CLI, etc.)                   │
└─────────────────────┬──────────────────────────────────────┘
                      │ HTTPS/REST API
┌─────────────────────▼──────────────────────────────────────┐
│                      API Gateway Layer                       │
│               (Load Balancer, Rate Limiting)                 │
└─────────────────────┬──────────────────────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────────────┐
│                     FastAPI Application                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           API Endpoints (v1)                         │  │
│  │  - Authentication  - Chat  - Documents  - Health    │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                Core Services                         │  │
│  │  - RAG Service - LLM Service - Embedding Service    │  │
│  │  - Document Service - Storage Service              │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Middleware & Dependencies               │  │
│  │  - Authentication - Rate Limiting - Logging         │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────┬────────────┬────────────┬────────────┬───────────┘
          │            │            │            │
     ┌────▼───┐  ┌────▼────┐  ┌────▼────┐  ┌───▼────┐
     │PostgreSQL Redis   │Pinecone│   AWS S3│
     │  (RDS) │  (Cache) │ (Vector)│(Storage)│
     └────────┘  └─────────┘  └─────────┘  └────────┘
                      │
                 ┌────▼────┐
                 │  Celery │
                 │ Workers │
                 └─────────┘
```

### Component Breakdown

#### 1. API Layer
- **FastAPI Application**: Async web framework for high performance
- **Routing**: Versioned API routes (v1)
- **Middleware Stack**:
  - CORS handling
  - Request/response logging
  - Exception handling
  - Rate limiting
  - Authentication

#### 2. Core Services

**RAG Service** (`app/services/rag_service.py`)
- Orchestrates the RAG pipeline
- Retrieves relevant context from vector store
- Generates responses using LLM with context
- Manages conversation history
- Formats responses with source citations

**LLM Service** (`app/services/llm_service.py`)
- Integrates with OpenAI API
- Handles chat completions
- Manages streaming responses
- Token counting and cost estimation
- Prompt engineering

**Embedding Service** (`app/services/embedding_service.py`)
- Generates vector embeddings using Sentence Transformers
- Batch processing for efficiency
- Similarity computation
- Supports multiple embedding models

**Document Service** (`app/services/document_service.py`)
- End-to-end document processing pipeline
- File parsing (PDF, TXT, DOCX)
- Text chunking with overlap
- Embedding generation
- Vector indexing

**Vector Store Service** (`app/services/vector_store_service.py`)
- Pinecone integration
- Vector upsert, query, and deletion
- Metadata filtering
- Index management

**Storage Service** (`app/services/storage_service.py`)
- AWS S3 integration
- File upload/download
- Presigned URLs
- Object lifecycle management

#### 3. Data Layer

**PostgreSQL Database**
- User management
- Document metadata
- Conversation history
- Message storage
- Processing job tracking
- API usage analytics

**Redis Cache**
- Rate limiting
- Session management
- Temporary data storage
- Background task queuing

**Pinecone Vector Database**
- Vector storage and search
- Semantic similarity
- Fast retrieval (< 100ms)
- Metadata filtering

**AWS S3**
- Raw document storage
- Long-term archival
- Versioning support

#### 4. Background Workers

**Celery Workers** (`app/workers/celery_app.py`)
- Asynchronous document processing
- Scheduled tasks
- Resource-intensive operations
- Failure recovery and retries

### Data Flow

#### Document Upload Flow

```
1. User uploads document via API
   ↓
2. File validated (size, type)
   ↓
3. Uploaded to S3
   ↓
4. Database record created (status: pending)
   ↓
5. Celery task queued
   ↓
6. Worker downloads from S3
   ↓
7. Parse document content
   ↓
8. Split into chunks
   ↓
9. Generate embeddings
   ↓
10. Store in Pinecone
    ↓
11. Update database (status: completed)
```

#### Chat Request Flow

```
1. User sends message
   ↓
2. Authenticate user
   ↓
3. Check rate limit
   ↓
4. Generate query embedding
   ↓
5. Search Pinecone for relevant chunks
   ↓
6. Retrieve top K results
   ↓
7. Build context from chunks
   ↓
8. Assemble prompt with context + history
   ↓
9. Send to OpenAI LLM
   ↓
10. Receive response
    ↓
11. Save conversation to database
    ↓
12. Return response with sources
```

## Security Architecture

### Authentication & Authorization

1. **API Key Authentication**
   - Generated during registration
   - Hashed using bcrypt before storage
   - Provided via `X-API-Key` header

2. **JWT Token Authentication**
   - Exchange API key for JWT
   - Short-lived access tokens (1 hour)
   - Long-lived refresh tokens (30 days)
   - Provided via `Authorization: Bearer` header

3. **Rate Limiting**
   - Per-user and per-IP limits
   - Redis-backed sliding window
   - Tiered limits (free, basic, premium, enterprise)

### Data Security

1. **Encryption**
   - TLS 1.2+ for data in transit
   - S3 encryption at rest
   - Database encryption at rest

2. **Access Control**
   - User-scoped document access
   - Private S3 buckets
   - VPC isolation for databases

3. **Secret Management**
   - Environment-based configuration
   - AWS Secrets Manager (production)
   - No secrets in code or logs

## Scalability

### Horizontal Scaling

1. **API Servers**
   - Stateless design
   - Load balanced
   - Auto-scaling based on CPU/memory

2. **Celery Workers**
   - Multiple worker instances
   - Queue-based distribution
   - Independent scaling

3. **Database**
   - Read replicas for PostgreSQL
   - Connection pooling
   - Query optimization

### Vertical Scaling

1. **Database**
   - Upgrade instance types
   - Increased storage
   - Enhanced I/O

2. **Cache**
   - Larger Redis instances
   - Cluster mode for Redis

## Monitoring & Observability

### Metrics
- Request latency (p50, p95, p99)
- Error rates by endpoint
- Token usage and costs
- Document processing times
- Vector search performance

### Logging
- Structured JSON logs
- Request/response logging
- Error tracking with stack traces
- Audit logs for sensitive operations

### Health Checks
- `/health` - Basic health
- `/health/ready` - Readiness probe
- `/health/live` - Liveness probe

## Performance Optimization

### Caching Strategy
1. **Application-level**: Frequent queries
2. **Database**: Query results
3. **CDN**: Static assets (if applicable)
4. **Vector embeddings**: Reuse for similar queries

### Database Optimization
1. **Indexing**: Strategic indexes on frequently queried columns
2. **Connection pooling**: Reuse connections
3. **Query optimization**: Use EXPLAIN ANALYZE
4. **Partitioning**: For large tables

### API Optimization
1. **Async operations**: Non-blocking I/O
2. **Batch processing**: Group operations
3. **Pagination**: Limit result sets
4. **Compression**: GZip for responses

## Deployment Architecture

### AWS ECS Deployment

```
┌─────────────────────────────────────────────┐
│         Application Load Balancer            │
│              (HTTPS/TLS)                     │
└─────────────┬───────────────────────────────┘
              │
┌─────────────▼───────────────────────────────┐
│            ECS Cluster                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │   Task   │  │   Task   │  │   Task   │  │
│  │   API    │  │   API    │  │   API    │  │
│  └──────────┘  └──────────┘  └──────────┘  │
│  ┌──────────┐  ┌──────────┐                │
│  │  Worker  │  │  Worker  │                │
│  │  (Celery)│  │  (Celery)│                │
│  └──────────┘  └──────────┘                │
└─────────────────────────────────────────────┘
```

### Infrastructure as Code
- Terraform for AWS resources
- Docker for containerization
- GitHub Actions for CI/CD

## Future Enhancements

1. **Advanced RAG Techniques**
   - HyDE (Hypothetical Document Embeddings)
   - Multi-query retrieval
   - Re-ranking algorithms

2. **Features**
   - WebSocket support for real-time chat
   - Multi-language support
   - Custom embedding models
   - Fine-tuned models

3. **Infrastructure**
   - Kubernetes deployment
   - Multi-region support
   - Edge caching
   - GraphQL API

4. **Analytics**
   - Usage dashboards
   - Cost tracking
   - Performance analytics
   - User behavior insights

## Technology Stack Summary

| Component | Technology | Purpose |
|-----------|-----------|---------|
| API Framework | FastAPI | High-performance async API |
| Language | Python 3.11+ | Application logic |
| Database | PostgreSQL | Structured data storage |
| Cache | Redis | Session & rate limiting |
| Vector DB | Pinecone | Semantic search |
| Storage | AWS S3 | Document storage |
| LLM | OpenAI GPT-4 | Response generation |
| Embeddings | Sentence Transformers | Vector embeddings |
| Background Jobs | Celery | Async processing |
| Orchestration | LangChain | RAG pipeline |
| Containerization | Docker | Deployment |
| Infrastructure | Terraform | AWS resources |
| CI/CD | GitHub Actions | Automation |

---

**Document Version**: 1.0
**Last Updated**: 2024-01-01
**Maintained By**: Development Team
