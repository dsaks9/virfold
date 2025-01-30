# Converting LlamaIndex Async Workflow to FastAPI Endpoints: Insights and Lessons

## Overview

This document details the process, challenges, and insights gained while converting LlamaIndex async workflows (`AmateurFollowAgent` and `ProPlayerDataAgent`) into FastAPI endpoints. The goal is to provide guidance for similar conversions of async workflows to API endpoints.

## Key Components

### 1. Project Structure
```
api/
├── main.py              # FastAPI app initialization and router registration
├── requirements.txt     # API-specific dependencies
├── Dockerfile          # API service configuration
├── routers/           # API route modules
│   ├── amateur_data.py
│   └── pro_player_data.py
└── app_modules/       # Shared business logic
    ├── amateur_data_agent.py
    ├── pro_player_data_agent.py
    ├── tools.py
    └── prompts.py
```

### 2. Module Organization
- **Routers**: Separate router modules for different agent types
- **App Modules**: Shared business logic and agent implementations
- **Main App**: Central configuration and router registration

### 3. API Architecture
- FastAPI application with lifespan management
- Session-based chat management
- Stateful agent instances per session
- RESTful endpoints for chat interaction

## Major Milestones and Solutions

### 1. Module Access and Imports
**Challenge**: Making workflow modules accessible to API
**Solution**:
```python
import sys
from pathlib import Path

# Add app_modules to Python path
app_modules_path = Path("/app/app_modules")
sys.path.append(str(app_modules_path))

# Use relative imports within app_modules
from app_modules.prompts import system_prompt_amateur_follow_agent
from app_modules.tools import query_evaluation_reports, PlayerEvaluation
```

**Key Insights**: 
- Mount required modules in Docker
- Use relative imports within app_modules
- Add module path to Python path in main.py
- Keep module structure flat when possible

### 2. Router-Based Organization
**Challenge**: Managing multiple agent types and endpoints
**Solution**:
```python
# main.py
from routers import amateur_data, pro_player_data

app = FastAPI(
    title="Baseball Scouting API",
    description="API endpoints for amateur data and pro player data analysis",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(amateur_data.router, prefix="/amateur-data", tags=["Amateur Data"])
app.include_router(pro_player_data.router, prefix="/pro-player-data", tags=["Pro Player Data"])
```

**Key Insights**:
- Separate routers for different agent types
- Consistent endpoint structure across routers
- Clear prefix and tagging for API documentation
- Shared session management patterns

### 3. Docker Configuration
**Challenge**: Setting up the correct environment and dependencies
**Solution**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p routers app_modules

# Copy application code
COPY main.py .
COPY routers/ routers/
COPY app_modules/ app_modules/

# Add app_modules to Python path
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Key Insights**:
- Use multi-stage builds for efficiency
- Mount app_modules for shared access
- Set PYTHONPATH environment variable
- Organize file copying for cache optimization

### 4. Session Management
**Challenge**: Managing stateful agent instances across requests
**Solution**:
```python
async def get_or_create_session(session_id: Optional[str] = None) -> dict:
    if session_id and session_id in sessions:
        return sessions[session_id]
    
    new_session_id = session_id or str(uuid.uuid4())
    agent = AmateurDataAgent(timeout=600, verbose=True)
    
    session = {
        "id": new_session_id,
        "agent": agent,
        "created_at": datetime.now(UTC),
        "messages": []
    }
    sessions[new_session_id] = session
    return session
```

**Key Insights**:
- Use UUID for session identification
- Store session creation timestamp
- Maintain message history
- Implement proper cleanup

### 5. Resource Management
**Challenge**: Proper cleanup of resources and sessions
**Solution**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up API")
    yield
    logger.info("Shutting down API")
    await amateur_data.cleanup_sessions()
    await pro_player_data.cleanup_sessions()
```

**Key Insights**:
- Use FastAPI's lifespan for resource management
- Implement cleanup for each router
- Handle cleanup errors gracefully
- Log cleanup operations

## Best Practices

1. **Project Structure**:
   - Organize by functionality (routers, modules)
   - Keep related code together
   - Use clear naming conventions
   - Maintain separation of concerns

2. **Import Management**:
   - Use relative imports within app_modules
   - Add app_modules to PYTHONPATH
   - Avoid circular dependencies
   - Keep import paths consistent

3. **Docker Configuration**:
   - Use multi-stage builds
   - Optimize layer caching
   - Mount shared modules
   - Set appropriate environment variables

4. **Session Management**:
   - Implement proper cleanup
   - Use unique session IDs
   - Store minimal required data
   - Handle concurrent access

5. **Error Handling**:
   - Log errors comprehensively
   - Return appropriate HTTP status codes
   - Provide meaningful error messages
   - Handle cleanup errors gracefully

## Common Pitfalls

1. **Import Issues**:
   - Absolute vs relative imports
   - Missing PYTHONPATH configuration
   - Circular dependencies
   - Inconsistent import paths

2. **Docker Configuration**:
   - Missing dependencies
   - Incorrect file copying
   - Wrong Python path
   - Missing environment variables

3. **Session Management**:
   - Memory leaks
   - Missing cleanup
   - Race conditions
   - Inconsistent state

## Future Improvements

1. **Session Management**:
   - Implement session expiration
   - Add persistence
   - Improve concurrent access
   - Add session monitoring

2. **Error Handling**:
   - Add more specific error types
   - Improve error recovery
   - Enhance logging
   - Add error metrics

3. **Performance**:
   - Add caching
   - Optimize resource usage
   - Implement rate limiting
   - Add performance monitoring

## Conclusion

Converting async workflows to API endpoints requires careful consideration of project structure, import management, Docker configuration, and session handling. The key to success is maintaining clean separation of concerns while ensuring proper resource management throughout the application lifecycle. Following these patterns and best practices will help create maintainable and scalable API services. 