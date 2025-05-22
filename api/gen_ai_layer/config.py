"""
Configuration module for the Gen AI Layer.
Handles model selection, API keys, and other configuration parameters.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union
from enum import Enum
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ModelProvider(str, Enum):
    """Supported model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MISTRAL = "mistral"
    OLLAMA = "ollama"
    GOOGLE = "google"
    BEDROCK = "bedrock"
    HUGGINGFACE = "huggingface"


class ModelConfig(BaseModel):
    """Configuration for a specific model."""
    provider: ModelProvider
    model_name: str
    api_key_env: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    timeout: int = 60
    additional_params: Dict = Field(default_factory=dict)


class GenAIConfig(BaseModel):
    """Main configuration for the Gen AI Layer."""
    default_model: str = "gpt-4"
    default_provider: ModelProvider = ModelProvider.OPENAI
    models: Dict[str, ModelConfig] = Field(default_factory=dict)
    cache_enabled: bool = True
    cache_ttl: int = 3600  # Time to live in seconds

    @classmethod
    def from_environment(cls) -> "GenAIConfig":
        """Create a configuration from environment variables."""
        # Default configuration with common models
        config = cls(
            models={
                "gpt-4": ModelConfig(
                    provider=ModelProvider.OPENAI,
                    model_name="gpt-4",
                    api_key_env="OPENAI_API_KEY",
                ),
                "gpt-3.5-turbo": ModelConfig(
                    provider=ModelProvider.OPENAI,
                    model_name="gpt-3.5-turbo",
                    api_key_env="OPENAI_API_KEY",
                ),
                "claude-3-opus": ModelConfig(
                    provider=ModelProvider.ANTHROPIC,
                    model_name="claude-3-opus",
                    api_key_env="ANTHROPIC_API_KEY",
                ),
                "claude-3-sonnet": ModelConfig(
                    provider=ModelProvider.ANTHROPIC,
                    model_name="claude-3-sonnet",
                    api_key_env="ANTHROPIC_API_KEY",
                ),
                "mistral-large": ModelConfig(
                    provider=ModelProvider.MISTRAL,
                    model_name="mistral-large-latest",
                    api_key_env="MISTRAL_API_KEY",
                ),
                "gemini-pro": ModelConfig(
                    provider=ModelProvider.GOOGLE,
                    model_name="gemini-pro",
                    api_key_env="GOOGLE_API_KEY",
                ),
            }
        )
        
        # Override with environment variables if present
        if os.getenv("GEN_AI_DEFAULT_MODEL"):
            config.default_model = os.getenv("GEN_AI_DEFAULT_MODEL")
            
        if os.getenv("GEN_AI_DEFAULT_PROVIDER"):
            config.default_provider = ModelProvider(os.getenv("GEN_AI_DEFAULT_PROVIDER"))
            
        if os.getenv("GEN_AI_CACHE_ENABLED"):
            config.cache_enabled = os.getenv("GEN_AI_CACHE_ENABLED").lower() == "true"
            
        if os.getenv("GEN_AI_CACHE_TTL"):
            config.cache_ttl = int(os.getenv("GEN_AI_CACHE_TTL"))
            
        return config


# Default configuration instance
default_config = GenAIConfig.from_environment()
