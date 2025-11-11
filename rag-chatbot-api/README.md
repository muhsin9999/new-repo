# RAG Chatbot API 🤖

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-ready Retrieval Augmented Generation (RAG) chatbot API built with FastAPI, LangChain, and AWS. This project demonstrates enterprise-grade backend AI engineering practices suitable for showcasing to recruiters and technical hiring managers.

## 🌟 Key Features

- **🚀 FastAPI Framework**: High-performance async API with automatic OpenAPI documentation
- **🧠 RAG Architecture**: Retrieval Augmented Generation for context-aware responses
- **📚 Document Processing**: Support for PDF, TXT, and DOCX files with intelligent chunking
- **🔍 Vector Search**: Semantic search using Pinecone vector database
- **💬 Conversation Management**: Persistent chat history with context awareness
- **🔐 Authentication**: API key and JWT-based authentication
- **⚡ Background Workers**: Celery for async document processing
- **📊 Monitoring**: Structured logging, metrics, and health checks
- **🐳 Docker**: Complete containerized deployment
- **☁️ AWS Ready**: S3 integration and infrastructure as code
- **🧪 Testing**: Comprehensive test suite with pytest
- **🔄 CI/CD**: GitHub Actions pipeline for automated deployments

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client    │────▶│   FastAPI    │────▶│  PostgreSQL │
└─────────────┘     │      API     │     └─────────────┘
                    └──────┬───────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐      ┌────▼────┐      ┌────▼────┐
    │ Pinecone│      │  Redis  │      │   S3    │
    │ Vector  │      │  Cache  │      │ Storage │
    │   DB    │      └─────────┘      └─────────┘
    └─────────┘
         ▲
         │
    ┌────┴────┐
    │ Celery  │
    │ Workers │
    └─────────┘
```

## 🛠️ Technology Stack

### Backend Framework
- **FastAPI**: Modern, fast web framework for building APIs
- **Pydantic**: Data validation using Python type annotations
- **Python 3.11+**: Latest Python features and performance improvements

### AI/ML Stack
- **LangChain**: Framework for developing LLM applications
- **OpenAI GPT-4**: Large language model for response generation
- **Sentence Transformers**: Embedding generation
- **tiktoken**: Token counting and management

### Data Storage
- **PostgreSQL**: Relational database for structured data
- **Redis**: Caching and session management
- **Pinecone**: Vector database for semantic search
- **AWS S3**: Object storage for documents

### Infrastructure
- **Docker & Docker Compose**: Containerization
- **Celery**: Distributed task queue
- **Alembic**: Database migrations
- **Terraform**: Infrastructure as code (coming soon)

### DevOps
- **GitHub Actions**: CI/CD pipeline
- **Prometheus**: Metrics collection
- **structlog**: Structured logging

## 📋 Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose
- PostgreSQL 14+
- Redis 7+
- OpenAI API key
- Pinecone API key
- AWS credentials (for S3)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/rag-chatbot-api.git
cd rag-chatbot-api
```

### 2. Environment Setup

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Update the `.env` file with your credentials:

```env
# Required: OpenAI API Key
OPENAI_API_KEY=sk-your-openai-api-key-here

# Required: Pinecone Configuration
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=us-west1-gcp
PINECONE_INDEX_NAME=rag-chatbot

# Required: AWS Configuration (for S3)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET_NAME=your-s3-bucket-name

# Required: Security
SECRET_KEY=your-super-secret-key-min-32-chars
```

### 3. Start with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Check service status
docker-compose ps
```

The API will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Flower (Celery Monitor)**: http://localhost:5555
- **PgAdmin**: http://localhost:5050 (optional, use profile `tools`)

### 4. Run Database Migrations

```bash
# Apply migrations
docker-compose exec api alembic upgrade head

# Or locally
alembic upgrade head
```

### 5. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Get API info
curl http://localhost:8000/

# Access interactive docs
open http://localhost:8000/docs
```

## 💻 Local Development

### Setup Python Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### Run Locally

```bash
# Start dependencies (PostgreSQL, Redis)
docker-compose up -d postgres redis

# Run migrations
alembic upgrade head

# Start the API
uvicorn app.main:app --reload --port 8000

# Start Celery worker (in another terminal)
celery -A app.workers.celery_app worker --loglevel=info

# Start Celery beat (in another terminal)
celery -A app.workers.celery_app beat --loglevel=info
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_auth.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black .
isort .

# Lint
flake8 app/
pylint app/

# Type checking
mypy app/
```

## 📖 API Documentation

### Authentication

Register to get an API key:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json"
```

Response:
```json
{
  "api_key": "your-generated-api-key",
  "message": "API key created successfully"
}
```

Use the API key in subsequent requests:

```bash
curl http://localhost:8000/api/v1/chat \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'
```

### Endpoints

#### Document Management

```bash
# Upload a document
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "X-API-Key: your-api-key" \
  -F "file=@document.pdf"

# List documents
curl http://localhost:8000/api/v1/documents \
  -H "X-API-Key: your-api-key"

# Get document status
curl http://localhost:8000/api/v1/documents/{document_id}/status \
  -H "X-API-Key: your-api-key"
```

#### Chat

```bash
# Send a chat message
curl -X POST http://localhost:8000/api/v1/chat \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is machine learning?",
    "conversation_id": null,
    "context_limit": 5
  }'

# Get conversation history
curl http://localhost:8000/api/v1/chat/conversations/{conversation_id} \
  -H "X-API-Key: your-api-key"

# List all conversations
curl http://localhost:8000/api/v1/chat/conversations \
  -H "X-API-Key: your-api-key"
```

For complete API documentation, visit `/docs` when the server is running.

## 🗂️ Project Structure

```
rag-chatbot-api/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/      # API endpoint handlers
│   │       │   ├── auth.py
│   │       │   ├── chat.py
│   │       │   ├── documents.py
│   │       │   └── health.py
│   │       └── router.py       # API router configuration
│   ├── core/
│   │   ├── exceptions.py       # Custom exceptions
│   │   ├── security.py         # Auth & security
│   │   └── rate_limiter.py     # Rate limiting
│   ├── db/
│   │   ├── session.py          # Database session
│   │   └── repositories/       # Data access layer
│   ├── models/
│   │   ├── database.py         # SQLAlchemy models
│   │   └── schemas.py          # Pydantic schemas
│   ├── services/
│   │   ├── rag_service.py      # RAG orchestration
│   │   ├── document_service.py # Document processing
│   │   ├── embedding_service.py# Embedding generation
│   │   ├── llm_service.py      # LLM integration
│   │   └── conversation_service.py
│   ├── utils/
│   │   ├── logging.py          # Logging configuration
│   │   ├── text_splitter.py    # Document chunking
│   │   └── file_parser.py      # File parsing
│   ├── workers/
│   │   └── document_processor.py # Background tasks
│   ├── config.py               # Application configuration
│   └── main.py                 # FastAPI application
├── tests/
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── e2e/                    # End-to-end tests
├── infrastructure/
│   ├── docker/
│   │   └── Dockerfile
│   └── terraform/              # IaC for AWS
├── alembic/                    # Database migrations
├── docs/                       # Additional documentation
├── .github/
│   └── workflows/              # CI/CD pipelines
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## 🔧 Configuration

All configuration is managed through environment variables. See `.env.example` for available options.

### Key Configuration Options

- **APP_NAME**: Application name
- **ENVIRONMENT**: development, staging, production
- **DEBUG**: Enable debug mode
- **DATABASE_URL**: PostgreSQL connection string
- **REDIS_URL**: Redis connection string
- **OPENAI_API_KEY**: OpenAI API key
- **PINECONE_API_KEY**: Pinecone API key
- **AWS credentials**: For S3 access
- **CHUNK_SIZE**: Document chunk size (default: 800)
- **RETRIEVAL_TOP_K**: Number of context chunks (default: 5)

## 📊 Monitoring & Observability

### Logs

Structured JSON logging with contextual information:

```python
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "app": "RAG Chatbot API",
  "environment": "production",
  "message": "request_completed",
  "method": "POST",
  "path": "/api/v1/chat",
  "status_code": 200
}
```

### Metrics

Prometheus metrics available at `/metrics`:

- Request latency (p50, p95, p99)
- Error rates by endpoint
- Token usage
- Background task performance

### Health Checks

- `/health` - Basic health check
- `/health/ready` - Readiness probe (checks dependencies)
- `/health/live` - Liveness probe (for Kubernetes)

## 🚢 Deployment

### AWS ECS (Recommended)

1. Build and push Docker image:

```bash
# Build image
docker build -t rag-chatbot-api -f infrastructure/docker/Dockerfile .

# Tag for ECR
docker tag rag-chatbot-api:latest {account}.dkr.ecr.{region}.amazonaws.com/rag-chatbot-api:latest

# Push to ECR
docker push {account}.dkr.ecr.{region}.amazonaws.com/rag-chatbot-api:latest
```

2. Deploy using Terraform (coming soon):

```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

### Docker Compose (Production)

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 🧪 Testing

### Test Structure

- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test API endpoints and database interactions
- **E2E Tests**: Test complete user workflows

### Running Tests

```bash
# All tests
pytest

# Specific test types
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# With markers
pytest -m "not slow"
pytest -m integration

# Coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**Your Name**

- GitHub: [@yourusername](https://github.com/yourusername)
- LinkedIn: [Your Name](https://linkedin.com/in/yourprofile)
- Email: your.email@example.com

## 🙏 Acknowledgments

- FastAPI for the amazing web framework
- LangChain for RAG capabilities
- OpenAI for GPT models
- Pinecone for vector database

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangChain Documentation](https://python.langchain.com/)
- [Pinecone Documentation](https://docs.pinecone.io/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

**⭐ If you find this project useful, please consider giving it a star!**

## 🎯 Roadmap

- [ ] Streaming responses with Server-Sent Events
- [ ] Multi-language support
- [ ] Custom embedding models
- [ ] Advanced RAG techniques (HyDE, Multi-Query)
- [ ] GraphQL API
- [ ] WebSocket support for real-time chat
- [ ] Admin dashboard
- [ ] Usage analytics and reporting
- [ ] Cost optimization features
- [ ] Multi-tenancy support

## 📞 Support

For questions or issues, please:
1. Check the [documentation](docs/)
2. Search [existing issues](https://github.com/yourusername/rag-chatbot-api/issues)
3. Create a [new issue](https://github.com/yourusername/rag-chatbot-api/issues/new)
