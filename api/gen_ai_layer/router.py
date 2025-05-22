"""
FastAPI router for the Gen AI Layer.
Provides API endpoints for interacting with AI models.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Response
from fastapi.responses import StreamingResponse
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
import logging
import json
import time
import uuid
from datetime import datetime

from .models import create_model, AIResponse, GenAIModel
from .config import ModelProvider, default_config
from ..auth import get_current_user, has_any_permission

# Create router
router = APIRouter(prefix="/api/genai", tags=["genai"])

logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str = "user"  # user, assistant, or system
    content: str


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    messages: List[ChatMessage]
    model: Optional[str] = None
    system_message: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: bool = False


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    id: str
    response: str
    model: str
    provider: str
    usage: Dict[str, int] = Field(default_factory=dict)
    created_at: str


# Cache for conversation history
conversation_cache = {}


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user = Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
    _: dict = Depends(has_any_permission(["datapuur:read", "kginsights:read"])),
):
    """
    Chat with an AI model.
    
    Requires either datapuur:read OR kginsights:read permission.
    """
    # Log the request
    logger.info(
        f"GenAI chat request from user {current_user.username} "
        f"with model {request.model or default_config.default_model}"
    )
    
    # Convert Pydantic messages to dict format expected by model
    messages = [msg.dict() for msg in request.messages]
    
    try:
        # Create model configuration
        model_config = {}
        if request.temperature is not None:
            model_config["temperature"] = request.temperature
        if request.max_tokens is not None:
            model_config["max_tokens"] = request.max_tokens
            
        # Create model instance
        model = create_model(
            model_name=request.model,
            **model_config
        )
        
        # Handle streaming if requested
        if request.stream:
            return StreamingResponse(
                _stream_chat_response(model, messages, request.system_message),
                media_type="text/event-stream",
            )
        
        # Get response from model
        ai_response = model.chat(
            messages=messages,
            system_message=request.system_message,
        )
        
        # Create response object
        response_id = str(uuid.uuid4())
        chat_response = ChatResponse(
            id=response_id,
            response=ai_response.content,
            model=ai_response.model,
            provider=ai_response.provider,
            usage=ai_response.usage,
            created_at=datetime.now().isoformat(),
        )
        
        # Store in cache for history
        background_tasks.add_task(
            _store_conversation,
            response_id,
            current_user.username,
            request.messages,
            ai_response.content,
            ai_response.model,
        )
        
        return chat_response
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}",
        )


async def _stream_chat_response(model, messages, system_message):
    """Stream the chat response."""
    try:
        # Send SSE format for streaming
        for chunk in model.stream_chat(messages, system_message):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield f"data: {json.dumps({'content': '[DONE]'})}\n\n"
    except Exception as e:
        logger.error(f"Error streaming response: {str(e)}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


def _store_conversation(
    conversation_id: str,
    username: str,
    messages: List[Dict[str, str]],
    response: str,
    model: str,
):
    """Store conversation in cache."""
    conversation_cache[conversation_id] = {
        "username": username,
        "messages": messages,
        "response": response,
        "model": model,
        "timestamp": datetime.now().isoformat(),
    }


class ModelListResponse(BaseModel):
    """Response model for listing available models."""
    models: List[Dict[str, Any]]
    default_model: str


@router.get("/models", response_model=ModelListResponse)
async def list_models(
    current_user = Depends(get_current_user),
    _: dict = Depends(has_any_permission(["datapuur:read", "kginsights:read"])),
):
    """
    List available AI models.
    
    Requires either datapuur:read OR kginsights:read permission.
    """
    # Get models from config
    models = []
    for model_name, model_config in default_config.models.items():
        models.append({
            "id": model_name,
            "name": model_name,
            "provider": model_config.provider,
            "capabilities": {
                "streaming": True,
                "function_calling": model_config.provider in [ModelProvider.OPENAI, ModelProvider.ANTHROPIC],
                "vision": model_config.provider in [ModelProvider.OPENAI, ModelProvider.ANTHROPIC, ModelProvider.GOOGLE],
            }
        })
    
    return ModelListResponse(
        models=models,
        default_model=default_config.default_model,
    )
