# LlamaIndex Workflow Agent Integration Guide

This guide outlines best practices and learnings for integrating LlamaIndex workflow agents into a full-stack application with React frontend and database connectivity.

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   React App     │ ←→  │  FastAPI Service │ ←→  │   TimescaleDB   │
│  (Frontend)     │     │  (LlamaIndex)    │     │   (Database)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## 1. LlamaIndex Workflow Agent Setup

### 1.1 Agent Structure
- Create a base agent class that handles common functionality
- Implement session management for stateful conversations
- Use async/await patterns for better performance

```python
class BaseAgent:
    def __init__(self, timeout: int = 600):
        self.timeout = timeout
        self.session_id = str(uuid.uuid4())

    async def run(self, input: str) -> dict:
        # Implementation
```

### 1.2 FastAPI Integration
- Use FastAPI for RESTful API endpoints
- Implement proper CORS handling
- Add middleware for telemetry and monitoring
- Structure routes logically by functionality

Key components:
```python
app = FastAPI(
    title="Data Analysis API",
    description="API endpoints for LlamaIndex workflow agents",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 1.3 Session Management
- Implement session tracking for conversation history
- Use proper cleanup mechanisms
- Store session data efficiently

```python
sessions: Dict[str, Dict[str, Any]] = {}

async def get_or_create_session(session_id: Optional[str] = None) -> dict:
    if session_id and session_id in sessions:
        return sessions[session_id]
    
    new_session_id = session_id or str(uuid.uuid4())
    # Session initialization
```

### 1.4 Workflow Agent Router Patterns
- Separate concerns by creating dedicated routers for each agent type
- Implement proper request/response models using Pydantic
- Handle agent-specific session management
- Implement proper cleanup mechanisms

Example router structure:
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, UTC
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    response: str

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        session = await get_or_create_session(request.session_id)
        agent = session["agent"]
        
        # Run agent workflow
        handler = agent.run(input=request.message)
        result = await handler
        
        # Extract and format response
        response = result["response"].message.content
        
        # Update session history
        session["messages"].append({
            "role": "user",
            "content": request.message
        })
        session["messages"].append({
            "role": "assistant",
            "content": response
        })
        
        return ChatResponse(
            session_id=session["id"],
            response=response
        )
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

### 1.5 Agent Lifecycle Management
- Implement proper initialization and cleanup
- Handle agent timeouts
- Manage agent resources efficiently
- Implement proper error recovery

Example lifecycle management:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    logger.info("Starting up API")
    yield
    logger.info("Shutting down API")
    await cleanup_sessions()

async def cleanup_sessions():
    """Cleanup agent sessions and resources."""
    for session_id, session in sessions.items():
        try:
            if "agent" in session:
                await session["agent"].cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {str(e)}")
    sessions.clear()
```

### 1.6 Telemetry and Monitoring
- Implement proper tracing for agent operations
- Monitor agent performance and resource usage
- Track session metrics
- Implement proper logging

Example telemetry setup:
```python
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from openinference.semconv.resource import ResourceAttributes

# Configure tracing
resource = Resource(attributes={
    ResourceAttributes.PROJECT_NAME: "workflow_agent_api"
})
tracer_provider = trace_sdk.TracerProvider(resource=resource)
tracer_provider.add_span_processor(
    SimpleSpanProcessor(OTLPSpanExporter())
)

# Instrument LlamaIndex operations
LlamaIndexInstrumentor().instrument(tracer_provider=tracer_provider)
```

## 2. React Frontend Integration

### 2.1 Component Structure
- Use TypeScript for better type safety
- Implement proper state management
- Handle loading and error states
- Maintain session persistence

Example component structure:
```typescript
interface Message {
  id: number
  text: string
  sender: "user" | "bot"
}

interface ChatResponse {
  session_id: string
  response: string
}

function ChatComponent() {
  const [messages, setMessages] = useState<Message[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
}
```

### 2.2 API Integration
- Implement proper error handling
- Use TypeScript interfaces for API responses
- Handle session management on frontend
- Implement proper loading states

Example API call:
```typescript
const handleSubmit = async (message: string) => {
  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        session_id: sessionId
      })
    })
    // Handle response
  } catch (error) {
    // Error handling
  }
}
```

### 2.3 Session Persistence
- Use localStorage for session management
- Implement session recovery
- Handle session expiration

```typescript
useEffect(() => {
  const savedSessionId = localStorage.getItem('chatSessionId')
  if (savedSessionId) {
    setSessionId(savedSessionId)
  }
}, [])
```

## 3. Database Integration

### 3.1 Connection Management
- Use connection pooling
- Implement proper error handling
- Use environment variables for configuration
- Implement proper cleanup

Example configuration:
```python
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'database': os.getenv('POSTGRES_DB'),
    'user': os.getenv('POSTGRES_USER'),
    'password': os.getenv('POSTGRES_PASSWORD')
}
```

### 3.2 Query Optimization
- Use prepared statements
- Implement proper indexing
- Use appropriate data types
- Consider caching strategies

### 3.3 Data Access Patterns
- Implement repository pattern
- Use proper abstraction layers
- Handle database migrations
- Implement proper error handling

## 4. Docker Integration

### 4.1 Service Configuration
- Use proper networking between services
- Implement health checks
- Handle service dependencies
- Use proper environment variables

Example docker-compose configuration:
```yaml
services:
  react_app:
    build:
      context: ./app
      dockerfile: Dockerfile
    environment:
      - NODE_ENV=development
    depends_on:
      - api_service

  api_service:
    build:
      context: ./api
      dockerfile: Dockerfile
    environment:
      - DB_HOST=${DB_HOST}
    depends_on:
      database:
        condition: service_healthy

  database:
    image: timescale/timescaledb:latest
    healthcheck:
      test: ["CMD-SHELL", "pg_isready"]
```

### 4.2 Development Workflow
- Use proper volume mounts for development
- Implement hot reloading
- Handle proper cleanup
- Use multi-stage builds

## 5. Best Practices

### 5.1 Error Handling
- Implement proper error boundaries
- Use appropriate error messages
- Handle network errors
- Implement proper logging

### 5.2 Security
- Implement proper CORS policies
- Use environment variables for secrets
- Implement proper authentication
- Handle rate limiting

### 5.3 Performance
- Implement proper caching
- Use connection pooling
- Optimize database queries
- Implement proper cleanup

### 5.4 Monitoring
- Implement proper logging
- Use appropriate metrics
- Monitor system health
- Implement proper alerting

## 6. Common Pitfalls

1. Not handling session cleanup properly
2. Improper error handling in async operations
3. Not implementing proper TypeScript types
4. Missing proper database indexing
5. Not handling network errors properly
6. Missing proper cleanup in React components
7. Not implementing proper CORS policies
8. Missing proper environment variable handling

## 7. Testing Strategies

### 7.1 API Testing
- Implement unit tests
- Use integration tests
- Test error conditions
- Test session management

### 7.2 Frontend Testing
- Implement component tests
- Test error states
- Test loading states
- Test session management

### 7.3 Database Testing
- Test queries
- Test migrations
- Test error conditions
- Use proper test data

## Conclusion

This integration pattern provides a robust foundation for building applications with LlamaIndex workflow agents. Key considerations include:

1. Proper session management
2. Robust error handling
3. Type safety with TypeScript
4. Efficient database access
5. Proper cleanup mechanisms
6. Security considerations
7. Performance optimization
8. Proper monitoring and logging

Remember to adapt these patterns based on specific requirements while maintaining the core principles of robust error handling, proper type safety, and efficient resource management. 