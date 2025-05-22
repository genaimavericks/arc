# Gen AI Layer for RSW Platform

This package provides AI capabilities to the RSW platform by integrating with various LLM providers through LangChain.

## Features

- Chat interfaces with multiple LLM providers (OpenAI, Anthropic, MistralAI, etc.)
- Text embeddings and vector search
- Knowledge graph integration with KGInsights
- Data analysis integration with DataPuur
- Document processing and analysis

## API Endpoints

The Gen AI Layer exposes the following API endpoints:

- `POST /api/genai/chat`: Chat with an AI model
- `GET /api/genai/models`: List available AI models

## Configuration

The Gen AI Layer can be configured using environment variables. Add the following variables to your `.env` file:

```
# Default model and provider
GEN_AI_DEFAULT_MODEL=gpt-4
GEN_AI_DEFAULT_PROVIDER=openai

# API keys for different providers
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
MISTRAL_API_KEY=your_mistral_api_key
GOOGLE_API_KEY=your_google_api_key

# Cache configuration
GEN_AI_CACHE_ENABLED=true
GEN_AI_CACHE_TTL=3600
```

## Usage Examples

### Chat with an AI model

```python
import requests
import json

url = "http://localhost:8000/api/genai/chat"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_ACCESS_TOKEN"
}
data = {
    "messages": [
        {"role": "user", "content": "What is a knowledge graph?"}
    ],
    "model": "gpt-4",
    "system_message": "You are a helpful assistant specialized in knowledge graphs."
}

response = requests.post(url, headers=headers, data=json.dumps(data))
print(response.json())
```

### List available models

```python
import requests

url = "http://localhost:8000/api/genai/models"
headers = {
    "Authorization": "Bearer YOUR_ACCESS_TOKEN"
}

response = requests.get(url, headers=headers)
print(response.json())
```

## Integration with RSW Components

The Gen AI Layer is designed to integrate seamlessly with other RSW components:

- **KGInsights**: Enhance knowledge graphs with AI-generated metadata, summaries, and relationships
- **DataPuur**: Analyze data sources, generate insights, and suggest transformations

## Required Permissions

To use the Gen AI Layer, users must have either:
- `datapuur:read` permission OR
- `kginsights:read` permission

This ensures that only authorized users can access the AI capabilities.
