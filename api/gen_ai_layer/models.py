"""
Models module for the Gen AI Layer.
Provides interfaces to different LLM providers through LangChain.
"""

from typing import Dict, List, Optional, Union, Any, Callable
from pydantic import BaseModel, Field
import logging
from abc import ABC, abstractmethod

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.callbacks import CallbackManager
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableConfig

# Import specific model implementations
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_mistralai import ChatMistralAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatOllama
from langchain_aws import ChatBedrock

from .config import ModelProvider, ModelConfig, default_config

logger = logging.getLogger(__name__)


class AIResponse(BaseModel):
    """Standardized response from AI models."""
    content: str
    model: str
    provider: str
    usage: Dict[str, int] = Field(default_factory=dict)
    raw_response: Optional[Any] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GenAIModel:
    """Base class for all Gen AI models."""
    
    def __init__(
        self,
        model_name: str = None,
        provider: ModelProvider = None,
        config: Dict[str, Any] = None,
    ):
        """Initialize the model with configuration."""
        self.model_name = model_name or default_config.default_model
        self.provider = provider or default_config.default_provider
        self.config = config or {}
        self._model = self._initialize_model()
        
    def _initialize_model(self) -> BaseChatModel:
        """Initialize the appropriate LangChain model based on provider."""
        if self.model_name in default_config.models:
            model_config = default_config.models[self.model_name]
        else:
            # Use default model configuration
            model_config = default_config.models[default_config.default_model]
            self.model_name = default_config.default_model
            
        # Merge config with default model config
        merged_config = {
            "temperature": model_config.temperature,
            "top_p": model_config.top_p,
        }
        if model_config.max_tokens:
            merged_config["max_tokens"] = model_config.max_tokens
            
        # Add any additional parameters
        merged_config.update(model_config.additional_params)
        
        # Override with instance config
        merged_config.update(self.config)
        
        # Initialize the appropriate model based on provider
        if model_config.provider == ModelProvider.OPENAI:
            return ChatOpenAI(
                model_name=model_config.model_name,
                **merged_config
            )
        elif model_config.provider == ModelProvider.ANTHROPIC:
            return ChatAnthropic(
                model=model_config.model_name,
                **merged_config
            )
        elif model_config.provider == ModelProvider.MISTRAL:
            return ChatMistralAI(
                model=model_config.model_name,
                **merged_config
            )
        elif model_config.provider == ModelProvider.GOOGLE:
            return ChatGoogleGenerativeAI(
                model=model_config.model_name,
                **merged_config
            )
        elif model_config.provider == ModelProvider.OLLAMA:
            return ChatOllama(
                model=model_config.model_name,
                **merged_config
            )
        elif model_config.provider == ModelProvider.BEDROCK:
            return ChatBedrock(
                model_id=model_config.model_name,
                **merged_config
            )
        else:
            raise ValueError(f"Unsupported provider: {model_config.provider}")
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        system_message: Optional[str] = None,
        **kwargs
    ) -> AIResponse:
        """
        Send a chat message to the model and get a response.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            system_message: Optional system message to prepend
            **kwargs: Additional parameters to pass to the model
            
        Returns:
            AIResponse object with the model's response
        """
        # Convert messages to LangChain format
        lc_messages = []
        
        # Add system message if provided
        if system_message:
            lc_messages.append(SystemMessage(content=system_message))
            
        # Add the rest of the messages
        for msg in messages:
            role = msg.get("role", "user").lower()
            content = msg.get("content", "")
            
            if role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            elif role == "system":
                lc_messages.append(SystemMessage(content=content))
                
        # Get response from the model
        try:
            response = self._model.invoke(lc_messages)
            
            # Extract usage information if available
            usage = {}
            if hasattr(response, "usage") and response.usage:
                usage = response.usage
                
            # Create standardized response
            return AIResponse(
                content=response.content,
                model=self.model_name,
                provider=str(self.provider),
                usage=usage,
                raw_response=response,
                metadata={"messages_count": len(messages)}
            )
        except Exception as e:
            logger.error(f"Error calling LLM: {str(e)}")
            raise
            
    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system_message: Optional[str] = None,
        **kwargs
    ):
        """
        Stream a chat response from the model.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            system_message: Optional system message to prepend
            **kwargs: Additional parameters to pass to the model
            
        Returns:
            Generator yielding chunks of the response
        """
        # Convert messages to LangChain format
        lc_messages = []
        
        # Add system message if provided
        if system_message:
            lc_messages.append(SystemMessage(content=system_message))
            
        # Add the rest of the messages
        for msg in messages:
            role = msg.get("role", "user").lower()
            content = msg.get("content", "")
            
            if role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            elif role == "system":
                lc_messages.append(SystemMessage(content=content))
                
        # Stream response from the model
        try:
            for chunk in self._model.stream(lc_messages):
                if hasattr(chunk, "content"):
                    yield chunk.content
        except Exception as e:
            logger.error(f"Error streaming from LLM: {str(e)}")
            raise


# Factory function to create model instances
def create_model(
    model_name: Optional[str] = None,
    provider: Optional[ModelProvider] = None,
    **kwargs
) -> GenAIModel:
    """
    Create a model instance based on the specified model name and provider.
    
    Args:
        model_name: Name of the model to use
        provider: Provider of the model
        **kwargs: Additional configuration parameters
        
    Returns:
        GenAIModel instance
    """
    return GenAIModel(
        model_name=model_name,
        provider=provider,
        config=kwargs
    )
