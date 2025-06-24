# /Users/asgiri218/gam-project/rsw/api/utils/llm_provider.py
import os
from typing import Union, Optional
from langchain_core.language_models.chat_models import BaseChatModel

# Attempting to handle potential import errors if libraries aren't installed
try:
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    ChatOpenAI = None # type: ignore
    OPENAI_AVAILABLE = False
    print("Warning: langchain_openai not found. OpenAI provider will not be available.")

try:
    from langchain_google_genai import ChatGoogleGenerativeAI # Corrected import
    GOOGLE_AVAILABLE = True
except ImportError:
    ChatGoogleGenerativeAI = None # type: ignore
    GOOGLE_AVAILABLE = False
    print("Warning: langchain_google_genai not found. Google provider will not be available.")


class LLMConstants:
    """Container for LLM Provider and Model constants."""
    class Providers:
        OPENAI = "openai"
        GOOGLE = "google"

    class OpenAIModels:
        DEFAULT = "gpt-4.1"
        # Add other OpenAI model constants here if needed
        # e.g., GPT_4_TURBO = "gpt-4-turbo"

    class GoogleModels:
        #DEFAULT = "gemini-2.5-pro-exp-03-25"
        DEFAULT = 'gemini-2.5-pro-preview-03-25'
        # Add other Google model constants here if needed
        # e.g., GEMINI_1_5_PRO = "gemini-1.5-pro-latest"


class LLMProvider:
    """Provides instances of LangChain chat models based on a provider flag."""
    
    # Cache for pre-initialized LLM instances
    _openai_instance = None
    _google_instance = None
    _initialized = False

    @staticmethod
    def get_llm(provider_name: str, model_name: Optional[str] = None, temperature: float = 0) -> BaseChatModel:
        """
        Initializes and returns a LangChain chat model instance.

        Args:
            provider_name: The name of the LLM provider (use LLMConstants.Providers).
            model_name: The specific model name (e.g., 'gpt-4', 'gemini-pro').
                        If None, uses the default for the provider.
            temperature: The sampling temperature for the model.

        Returns:
            An instance of BaseChatModel (ChatOpenAI or ChatGoogleGenerativeAI).

        Raises:
            ImportError: If the required langchain library for the provider is not installed.
            ValueError: If the required API key environment variable is not set, or if an
                        unsupported provider_name is given.
            RuntimeError: If an error occurs during the LLM client initialization.
        """
        # Check if we can use cached instances for default settings
        if temperature == 0 and LLMProvider._initialized:
            if provider_name == LLMConstants.Providers.OPENAI and \
               (model_name is None or model_name == LLMConstants.OpenAIModels.DEFAULT) and \
               LLMProvider._openai_instance is not None:
                return LLMProvider._openai_instance
                
            if provider_name == LLMConstants.Providers.GOOGLE and \
               (model_name is None or model_name == LLMConstants.GoogleModels.DEFAULT) and \
               LLMProvider._google_instance is not None:
                return LLMProvider._google_instance
        
        api_key = None
        llm_instance = None

        if provider_name == LLMConstants.Providers.OPENAI:
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI provider selected, but langchain_openai is not installed.")
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set.")
            
            model_to_use = model_name or LLMConstants.OpenAIModels.DEFAULT
            print(f"Initializing ChatOpenAI model: {model_to_use}")
            try:
                llm_instance = ChatOpenAI(model=model_to_use, temperature=temperature, openai_api_key=api_key)
            except Exception as e:
                raise RuntimeError(f"Error initializing ChatOpenAI: {e}") from e

        elif provider_name == LLMConstants.Providers.GOOGLE:
            if not GOOGLE_AVAILABLE:
                raise ImportError("Google provider selected, but langchain_google_genai is not installed.")
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set.")
            
            model_to_use = model_name or LLMConstants.GoogleModels.DEFAULT
            print(f"Initializing ChatGoogleGenerativeAI model: {model_to_use}")
            try:
                # Ensure the API key is passed correctly during initialization
                llm_instance = ChatGoogleGenerativeAI(model=model_to_use, temperature=temperature, google_api_key=api_key)
            except Exception as e:
                raise RuntimeError(f"Error initializing ChatGoogleGenerativeAI: {e}") from e
        else:
            raise ValueError(f"Unsupported LLM provider '{provider_name}'. Supported: '{LLMConstants.Providers.OPENAI}', '{LLMConstants.Providers.GOOGLE}'.")

        # Should not be None if we reached here without raising an exception
        if llm_instance is None:
             # This case should theoretically not be reachable due to prior checks/raises
             raise RuntimeError(f"Failed to initialize LLM for provider {provider_name} for an unknown reason.")
             
        return llm_instance

    @staticmethod
    def get_default_llm(temperature: float = 0) -> BaseChatModel:
        """
        Returns the default Google LLM instance.

        This is a convenience method that calls get_llm with the default Google provider and model.

        Args:
            temperature: The sampling temperature for the model.

        Returns:
            An instance of BaseChatModel (ChatGoogleGenerativeAI).

        Raises:
            ImportError: If langchain_google_genai is not installed.
            ValueError: If GOOGLE_API_KEY environment variable is not set.
            RuntimeError: If an error occurs during the LLM client initialization.
        """
        # If cached instance is available and temperature is 0 (default), return it
        if LLMProvider._initialized and LLMProvider._google_instance is not None and temperature == 0:
            return LLMProvider._google_instance
            
        return LLMProvider.get_llm(
            provider_name=LLMConstants.Providers.GOOGLE,
            model_name=LLMConstants.GoogleModels.DEFAULT,
            temperature=temperature
        )
        
    @staticmethod
    def get_cached_openai() -> BaseChatModel:
        """
        Returns the cached OpenAI LLM instance with default settings.
        If not initialized, returns None.
        """
        if LLMProvider._initialized and LLMProvider._openai_instance is not None:
            return LLMProvider._openai_instance
        return None
        
    @staticmethod
    def get_cached_google() -> BaseChatModel:
        """
        Returns the cached Google LLM instance with default settings.
        If not initialized, returns None.
        """
        if LLMProvider._initialized and LLMProvider._google_instance is not None:
            return LLMProvider._google_instance
        return None
        
    @staticmethod
    def initialize_models():
        """
        Pre-initializes and caches LLM models for faster access.
        Should be called during application startup.
        """
        if LLMProvider._initialized:
            print("LLM models already initialized")
            return
            
        try:
            # Initialize OpenAI model if API key is available
            if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
                print("Pre-initializing OpenAI LLM model...")
                LLMProvider._openai_instance = LLMProvider.get_llm(
                    provider_name=LLMConstants.Providers.OPENAI,
                    model_name=LLMConstants.OpenAIModels.DEFAULT,
                    temperature=0.0
                )
                print("Successfully initialized OpenAI LLM")
            else:
                print("Warning: OpenAI API key not found or langchain_openai not installed. Skipping initialization.")
                
            # Initialize Google model if API key is available
            if GOOGLE_AVAILABLE and os.getenv("GOOGLE_API_KEY"):
                print("Pre-initializing Google LLM model...")
                LLMProvider._google_instance = LLMProvider.get_llm(
                    provider_name=LLMConstants.Providers.GOOGLE,
                    model_name=LLMConstants.GoogleModels.DEFAULT,
                    temperature=0.0
                )
                print("Successfully initialized Google Gemini LLM")
            else:
                print("Warning: GOOGLE_API_KEY environment variable is not set or langchain_google_genai not installed. Skipping initialization.")
                
            LLMProvider._initialized = True
            
        except Exception as e:
            print(f"Error during LLM initialization: {str(e)}")
            # Don't mark as initialized if there was an error

# Initialize LLM models during module import
# This ensures models are pre-initialized when the application starts
LLMProvider.initialize_models()

# Example Usage (Optional - for testing)
if __name__ == '__main__':
    print("Testing LLMProvider...")
    
    # Ensure API keys are set in your environment for testing
    # Example: export OPENAI_API_KEY='your_key'
    # Example: export GOOGLE_API_KEY='your_key'
    
    # Test OpenAI
    print("\n--- Testing OpenAI ---")
    try:
        openai_llm_default = LLMProvider.get_llm(LLMConstants.Providers.OPENAI)
        if openai_llm_default:
            print(f"Successfully got default OpenAI model: {openai_llm_default.model_name}")
    except (ImportError, ValueError, RuntimeError) as e:
        print(f"Failed to get default OpenAI model: {e}")
    
    # Test Google
    print("\n--- Testing Google ---")
    try:
        google_llm_default = LLMProvider.get_llm(LLMConstants.Providers.GOOGLE)
        if google_llm_default:
            print(f"Successfully got default Google model: {google_llm_default.model}") # Note: attribute might differ
    except (ImportError, ValueError, RuntimeError) as e:
        print(f"Failed to get default Google model: {e}")

    # Test specific model (if desired and key is set)
    # print("\n--- Testing Specific OpenAI Model ---")
    # try:
    #    openai_llm_specific = LLMProvider.get_llm(LLMConstants.Providers.OPENAI, model_name='gpt-3.5-turbo')
    #    if openai_llm_specific:
    #        print(f"Successfully got specific OpenAI model: {openai_llm_specific.model_name}")
    # except (ImportError, ValueError, RuntimeError) as e:
    #        print(f"Failed to get specific OpenAI model: {e}")

    # Test invalid provider
    print("\n--- Testing Invalid Provider ---")
    try:
        invalid_llm = LLMProvider.get_llm("invalid_provider")
        # If it gets here, the error wasn't raised as expected
        print("Error: Did not raise expected exception for invalid provider.") 
    except ValueError as e:
        print(f"Correctly handled invalid provider: {e}")
    except Exception as e:
        print(f"Caught unexpected exception for invalid provider: {e}")

    print("\nTesting finished.")
