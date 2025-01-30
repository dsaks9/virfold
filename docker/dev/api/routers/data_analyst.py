from typing import Optional, Dict, Any
import uuid
from datetime import datetime, UTC
import logging
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.agent_data_analyst import DataAnalystAgent
from llama_index.core.llms import ChatMessage

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()

# Store active sessions
sessions: Dict[str, Dict[str, Any]] = {}

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    response: str
    
async def get_or_create_session(session_id: Optional[str] = None) -> dict:
    """Get existing session or create new one."""
    if session_id and session_id in sessions:
        return sessions[session_id]
    
    new_session_id = session_id or str(uuid.uuid4())
    agent = DataAnalystAgent(timeout=600)
    
    session = {
        "id": new_session_id,
        "agent": agent,
        "created_at": datetime.now(UTC),
        "messages": []
    }
    sessions[new_session_id] = session
    return session

async def cleanup_sessions():
    """Cleanup sessions when shutting down."""
    logger.info("Cleaning up data analyst sessions")
    sessions.clear()

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint for data analyst agent."""
    try:
        session = await get_or_create_session(request.session_id)
        agent = session["agent"]
        
        # Convert message to ChatMessage format
        chat_message = request.message
        
        # Run the agent workflow
        handler = agent.run(input=chat_message)
        result = await handler
        
        # Extract response from result
        response = result["response"].message.content
        
        # Store message history
        session["messages"].append({
            "role": "user",
            "content": chat_message
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