# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Hub Platform is an enterprise-grade AI application platform that aggregates multiple AI models (140+ via OpenRouter) with streaming responses, cost tracking, and session management. Built with FastAPI (backend) and Next.js (frontend), it aims to become a developer API service platform.

**Commercial Strategy**: Transitioning from a chat application to a commercial API service platform targeting developers (25%), enterprises (60%), and individual users (15%).

## Development Commands

### Backend (FastAPI)

```bash
# Start development server
python backend/main.py

# With specific environment
ENVIRONMENT=development DEBUG=true python backend/main.py

# Code quality
black backend/                 # Format code
isort backend/                 # Sort imports
mypy backend/                  # Type checking
pytest backend/tests/          # Run tests
```

**Note**: Backend runs on port 8001 (not 8000) to avoid conflicts. API docs available at http://localhost:8001/api/docs

### Frontend (Next.js)

```bash
cd frontend

# Development
npm run dev                    # Port 3000
npm run build                  # Production build
npm start                      # Production server
npm run lint                   # ESLint
npm run type-check             # TypeScript validation
```

### Docker Deployment

```bash
# Full stack
docker-compose up -d

# With monitoring
docker-compose --profile monitoring up -d

# Production with Nginx
docker-compose --profile production up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Architecture & Key Concepts

### Multi-AI Service Architecture

The platform uses a **service router pattern** to manage multiple AI providers:

```
User Request → AIServiceManager → [OpenRouterService, GeminiService]
                                        ↓
                                   Fallback Chain
```

**Key Implementation**:
- `backend/core/ai_service.py`: AIServiceManager - main orchestration
- `backend/core/openrouter_service.py`: OpenRouterService - 140+ models
- `backend/core/providers/gemini_service.py`: GeminiService - backup
- **Intelligent fallback**: OpenRouter → Gemini if primary fails
- **Model selection**: Prioritizes free models (grok-4-fast:free, deepseek-chat-v3.1:free)

### Session & Cost Management

**Session Persistence**:
- `backend/core/session_manager.py`: Manages conversation history
- Storage: JSON files in `data/sessions/` directory
- Index: `data/sessions_index.json` for fast lookups
- Each session has unique UUID and stores complete message history

**Cost Tracking**:
- `backend/core/cost_tracker.py`: Token counting and cost estimation
- Uses `tiktoken` for accurate token counting
- Tracks per-service usage (OpenRouter vs Gemini)
- Records stored in `data/usage_records/`

### Streaming Response System

Implements **Server-Sent Events (SSE)** for real-time streaming:

```python
# backend/api/v1/chat.py
async def stream_chat(request):
    async for chunk in service.stream_response(prompt):
        yield f"data: {chunk}\n\n"
```

**Frontend consumption** in `frontend/src/components/ChatInterface.tsx` uses EventSource API.

### API Structure

**FastAPI router hierarchy**:
```
/api/v1/
├── /chat          # Chat completions (streaming & non-streaming)
├── /sessions      # Session management (CRUD)
├── /stats         # Usage statistics
├── /search        # Web search integration
└── /models        # Available AI models
```

**Key endpoints**:
- `POST /api/v1/chat/stream` - Streaming chat
- `POST /api/v1/chat/completions` - Non-streaming
- `GET /api/v1/models` - List available models
- `GET /api/v1/sessions/{session_id}` - Get session history

### Configuration System

Uses **Pydantic Settings** with environment variable precedence:

```python
# backend/config/settings.py
@lru_cache()
def get_settings() -> Settings:
    return Settings()  # Auto-loads from .env
```

**Critical environment variables**:
- `OPENROUTER_API_KEY`: Primary AI service (required)
- `GEMINI_API_KEY`: Backup AI service (recommended)
- `ENVIRONMENT`: development/staging/production
- `DEBUG`: Enable detailed logging

**Configuration access pattern**:
```python
from backend.config.settings import get_settings
settings = get_settings()
if settings.openrouter_api_key:
    # Initialize service
```

## Data Persistence

### File-based Storage Structure

```
data/
├── sessions/               # User conversations (JSON)
│   ├── {uuid}.json        # Individual session files
│   └── sessions_index.json # Fast lookup index
├── usage_records/          # Cost tracking (JSON)
│   └── {date}_usage.json
└── uploads/               # User file uploads
```

**Session file format**:
```json
{
  "session_id": "uuid",
  "created_at": "ISO-8601",
  "messages": [
    {"role": "user", "content": "...", "timestamp": "..."},
    {"role": "assistant", "content": "...", "timestamp": "..."}
  ],
  "metadata": {
    "model": "grok-4-fast:free",
    "total_tokens": 1234,
    "estimated_cost": 0.0
  }
}
```

### Migration to Database

**Planned**: PostgreSQL migration for production (see `docker-compose.yml`):
- Database service configured but not yet integrated
- Redis configured for caching
- SQLAlchemy models to be added in future

## Frontend Architecture

### Next.js App Router Structure

```
frontend/src/
├── app/
│   ├── page.tsx           # Home page
│   ├── chat/
│   │   └── page.tsx       # Chat interface
│   └── layout.tsx         # Root layout
└── components/
    └── ChatInterface.tsx  # Main chat component
```

**Component Architecture**:
- `ChatInterface.tsx`: Handles all chat logic (streaming, history, model selection)
- Uses React hooks for state management (no Redux/Zustand yet)
- Tailwind CSS for styling

### API Communication

**Frontend → Backend**:
```typescript
// Streaming example
const eventSource = new EventSource(
  `${API_URL}/api/v1/chat/stream?prompt=${encodeURIComponent(message)}&model=${model}`
);

eventSource.onmessage = (event) => {
  const chunk = event.data;
  // Append to UI
};
```

## Important Patterns & Conventions

### Async Service Initialization

All AI services use **lazy initialization**:

```python
class OpenRouterService:
    async def initialize(self):
        if self._initialized:
            return
        # Setup aiohttp session
        self._initialized = True
```

**Why**: Avoids blocking app startup; allows graceful degradation if API keys missing.

### Error Handling Pattern

Use **HTTPException** for API errors:

```python
from fastapi import HTTPException

if not settings.openrouter_api_key:
    raise HTTPException(
        status_code=500,
        detail="OpenRouter API key not configured"
    )
```

### Service Manager Pattern

Access AI services through the **global manager**:

```python
from backend.core.ai_service import ai_manager

service = await ai_manager.get_service("openrouter")
response = await service.generate_response(prompt)
```

## Testing Strategy

### Current Test Setup

**Backend tests** in `backend/tests/`:
```bash
pytest backend/tests/                    # All tests
pytest backend/tests/test_chat.py        # Specific file
pytest -v -s                             # Verbose with print output
```

**Frontend tests**: Not yet implemented (TODO)

### Test Data

- Use `TEST_DATABASE_URL` for isolated test database
- Mock AI API calls to avoid costs
- Session fixtures in `backend/tests/fixtures/`

## Common Development Tasks

### Adding a New AI Provider

1. Create provider file: `backend/core/providers/your_provider.py`
2. Implement `generate_response()` and `stream_response()` methods
3. Add to `AIServiceManager._services` dict in `ai_service.py`
4. Add API key to `.env.example` and `settings.py`
5. Update fallback logic if needed

### Adding New API Endpoint

1. Create route in `backend/api/v1/your_route.py`
2. Define request/response models using Pydantic
3. Add router to `backend/api/v1/router.py`
4. Document with FastAPI docstrings (auto-generates OpenAPI)

### Environment-Specific Behavior

Check environment in code:
```python
settings = get_settings()
if settings.is_production():
    # Production-only logic
elif settings.is_development():
    # Development-only logic
```

## Security Considerations

- **API Keys**: Never commit `.env` file; always use environment variables
- **CORS**: Restrict origins in production (see `settings.cors_origins`)
- **Rate Limiting**: Configured but not yet enforced (TODO)
- **JWT Auth**: Configured but not yet implemented (TODO)

## Deployment Notes

### Production Checklist

1. Set `ENVIRONMENT=production` and `DEBUG=false`
2. Generate strong `SECRET_KEY` and `JWT_SECRET_KEY`
3. Configure actual `ALLOWED_HOSTS` and `CORS_ORIGINS`
4. Use PostgreSQL instead of SQLite
5. Enable Nginx reverse proxy profile
6. Set up SSL certificates in `deployment/ssl/`
7. Configure monitoring with Prometheus/Grafana

### Docker Services

- **Backend**: Port 8000 (internal), proxied via Nginx
- **Frontend**: Port 3000 (internal), proxied via Nginx
- **PostgreSQL**: Port 5432
- **Redis**: Port 6379
- **Nginx**: Ports 80/443 (production profile only)

## Roadmap Context

**Current Stage**: v1.0 - Basic chat functionality complete

**Next Stage**: v2.0 - API commercialization:
- Add API key authentication
- Implement usage quotas
- Rate limiting
- Developer documentation
- Billing system integration

**Business Model**: Multi-tier pricing (Free/Developer $29/Pro $99/Enterprise custom)

## Documentation Structure

```
docs/
├── business/              # Commercial strategy (NEW - being created)
├── planning/              # Project plans (moved from learning/)
├── technical-analysis/    # Architecture docs (moved from learning/)
├── progress/              # Progress tracking (moved from learning/)
├── development/           # Development guides (existing)
├── deployment/            # Deployment guides (existing)
├── api/                   # API documentation (existing)
└── user-guides/           # User documentation (existing)
```

**Note**: `learning/` directory being consolidated into `docs/` for better organization.

## Critical Files

- `backend/main.py`: Application entry point
- `backend/core/ai_service.py`: Core AI orchestration logic
- `backend/api/v1/chat.py`: Chat API implementation
- `frontend/src/components/ChatInterface.tsx`: Main UI component
- `.env`: Environment configuration (create from `.env.example`)
- `docker-compose.yml`: Full deployment configuration

## Troubleshooting

### Backend won't start
- Check `.env` file exists and has required API keys
- Verify port 8001 is available
- Check `data/` directory permissions

### Streaming not working
- Ensure CORS headers allow streaming
- Check EventSource browser compatibility
- Verify SSE format: `data: {content}\n\n`

### AI service errors
- Validate API keys with test request
- Check service `_initialized` flag
- Review fallback chain execution

## Contact & Support

- **GitHub**: [@grass2036](https://github.com/grass2036)
- **Project**: AI Hub Platform
- **Tech Stack**: FastAPI + Next.js + OpenRouter + Gemini