from fastapi import APIRouter, Depends, HTTPException, Body, Request
from typing import Dict, Any
import json
import asyncio
import httpx
from .auth import get_current_user, has_any_permission
from .admin import load_system_settings
from .utils.llm_provider import LLMProvider, LLMConstants

router = APIRouter(
    prefix="/api/djinni",
    tags=["djinni"]
)

# Helper function to determine query type
async def classify_query_llm(query: str) -> Dict[str, Any]:
    """
    Classify a query using LLM to determine if it's KG Insights, Factory Astro, or Churn Astro.
    Returns the classification with confidence score.
    """
    try:
        # Try to use Google Gemini first, fall back to other providers if not available
        llm = None
        for provider in [LLMConstants.Providers.GOOGLE, LLMConstants.Providers.OPENAI, LLMConstants.Providers.ANTHROPIC]:
            try:
                llm = LLMProvider.get_llm(provider_name=provider, temperature=0)
                if llm:
                    break
            except (ImportError, ValueError, RuntimeError):
                continue
                
        if not llm:
            # If no LLM is available, return None to fall back to rules-based classification
            print("No LLM provider available for query classification")
            return None
        
        # Create a system prompt for the LLM
        system_prompt = """
        You are a query classifier for the Djinni Assistant system. 
        Your task is to determine if a user query should be routed to:
        
        1. KGraph Insights (kginsights) - for factory or churn data related general analytics
        2. Factory Astro (factory_astro) - strictly for predictions related to factory production volume, profit margin and revenue
        3. Churn Astro (churn_astro) - strictly for prediction related to telecom customer retention, churn prediction
        
        Classify the query into exactly one of these categories. Return only a JSON response with:
        - query_type: one of [kginsights, factory_astro, churn_astro]
        - confidence: a number between 0-100 indicating your confidence
        - reasoning: a brief explanation of your classification
        """
        
        # Build the prompt with user's query
        user_message = f"Classify this query: '{query}'"
        
        # Make the LLM call
        response = await asyncio.to_thread(
            lambda: llm.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]).content
        )
        
        # Parse the JSON response
        try:
            # Extract JSON from the response if needed
            if '{' in response and '}' in response:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
            else:
                result = json.loads(response)
                
            # Ensure the response has the required fields
            if 'query_type' not in result or 'confidence' not in result:
                print(f"LLM response missing required fields: {result}")
                return None
            
            # Return a standardized response
            response = {
                "query_type": result["query_type"],
                "confidence": float(result["confidence"]),
                "llm_reasoning": result.get("reasoning", "No reasoning provided"),
                "llm_provider": provider,
                "classification_method": "llm"
            }
            return response
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing LLM response: {e}\nResponse: {response}")
            return None
    except Exception as e:
        print(f"Error in LLM classification: {e}")
        return None

def classify_query_rules(query: str) -> Dict[str, Any]:
    """
    Classify a query using rules/keywords to determine if it's KG Insights, Factory Astro or Churn Astro.
    Returns the classification with confidence score and detected type.
    """
    # Keywords that indicate KG Insights query
    kg_keywords = [
        'graph', 'knowledge', 'relation', 'entity', 'connect', 'linked', 'kgraph', 
        'kg', 'ontology', 'semantic', 'network', 'map', 'links', 'nodes', 'kgraff',
        'visualize', 'entities', 'connected', 'relationship', 'connections'
    ]
    
    # Keywords that indicate Churn Astro query
    churn_keywords = [
        'churn', 'churned', 'leave', 'leaving', 'retention', 'retain', 'customer loss', 
        'dropout', 'attrition', 'turnover', 'cancel', 'cancellation', 'discontinued',
        'subscription', 'subscriber', 'discontinued service'
    ]
    
    # Keywords that indicate Factory Astro query
    factory_keywords = [
        'factory', 'manufacturing', 'production', 'machine', 'equipment', 'assembly', 
        'quality', 'defect', 'yield', 'downtime', 'maintenance', 'output', 'efficiency',
        'throughput', 'productivity', 'operation', 'operator', 'line', 'plant'
    ]
    
    # Normalize the query text
    query_lower = query.lower()
    
    # Count keyword occurrences for each category
    kg_count = sum(1 for keyword in kg_keywords if keyword in query_lower)
    churn_count = sum(1 for keyword in churn_keywords if keyword in query_lower)
    factory_count = sum(1 for keyword in factory_keywords if keyword in query_lower)
    
    # Determine the dominant category
    max_count = max(kg_count, churn_count, factory_count)
    
    # If there's a tie or no keywords matched, use more complex logic
    # For example, check if the query is asking about data relationships or visualizations
    if max_count == 0 or (kg_count == churn_count == factory_count):
        # Check for relationship or visualization patterns in the query
        if re.search(r'(show|display|visualize|draw|plot|graph|connect|related|between)', query_lower):
            kg_count += 1
        # Check for performance metrics which are more likely to be Astro questions
        if re.search(r'(performance|metric|score|predict|forecast|analytics|analyze)', query_lower):
            # If both churn and factory are tied, default to the currently active Astro type
            # We'll determine this in the API endpoint based on the system settings
            if churn_count == factory_count:
                # Default to factory unless we detect churn context
                if re.search(r'(customer|subscription|service|retain|attrition)', query_lower):
                    churn_count += 1
                else:
                    factory_count += 1
    
    # Determine the final category and confidence
    if kg_count > churn_count and kg_count > factory_count:
        category = "kginsights"
        confidence = min(kg_count / 3 * 100, 100)  # Scale confidence, max 100%
    elif churn_count > factory_count:
        category = "churn_astro" 
        confidence = min(churn_count / 3 * 100, 100)
    else:
        category = "factory_astro"
        confidence = min(factory_count / 3 * 100, 100)
    
    # If confidence is too low, increase slightly based on the presence of question format
    if confidence < 50 and re.search(r'(what|how|when|where|why|which|can|could|would|show|tell|explain)', query_lower):
        confidence += 20
    
    return {
        "query_type": category,
        "confidence": confidence,
        "kginsights_score": kg_count,
        "churn_astro_score": churn_count,
        "factory_astro_score": factory_count,
        "classification_method": "rules"
    }

@router.post("/classify-query", response_model=Dict[str, Any])
async def classify_user_query(
    request: Request,
    query_data: Dict[str, Any] = Body(...),
    current_user = Depends(get_current_user)
):
    """
    Classify a user query as either KG Insights or Astro (factory/churn) related.
    """
    query = query_data.get("query", "")
    # source_id is optional and not used in classification but included in request
    source_id = query_data.get("source_id", "default")
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    # Get the current active Astro type from system settings
    # This will be used as a fallback when classification confidence is low
    active_astro = await get_active_astro_type()
    
    # First try LLM-based classification
    llm_classification = await classify_query_llm(query)
    
    # Use LLM classification if available with sufficient confidence
    if llm_classification and llm_classification["confidence"] > 60:
        print(f"Using LLM classification: {llm_classification['query_type']} with confidence {llm_classification['confidence']}")
        classification = llm_classification
    else:
        # Fall back to rules-based classification
        print("Falling back to rules-based classification")
        classification = classify_query_rules(query)
    
    # If confidence is very low and it's an Astro type, use the active Astro setting
    if classification["confidence"] < 30 and classification["query_type"] in ["factory_astro", "churn_astro"]:
        classification["query_type"] = active_astro
        classification["note"] = "Low confidence classification, defaulting to active Astro type"
    
    print(f"Final classification: {classification}")

    return classification

@router.post("/astro-query", response_model=Dict[str, Any])
async def astro_query(
    request: Request,
    payload: Dict[str, Any] = Body(...),
    current_user=Depends(get_current_user)
):
    """
    Route an Astro query to the appropriate backend service.
    """
    query = payload.get("query")
    astro_type = payload.get("astro_type")

    if not query or not astro_type:
        raise HTTPException(status_code=400, detail="Query and astro_type are required")

    # Determine the correct endpoint based on astro_type
    if astro_type == "factory_astro":
        endpoint = "/api/factory-astro/predict"
    elif astro_type == "churn_astro":
        endpoint = "/api/churn-astro/predict"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown astro_type: {astro_type}")

    base_url = str(request.base_url)
    full_url = f"{base_url.rstrip('/')}{endpoint}"
    
    downstream_payload = {"query": query, "question": query}

    headers = {
        "Content-Type": "application/json",
        "Authorization": request.headers.get("Authorization")
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                full_url,
                json=downstream_payload,
                headers=headers,
                timeout=60.0,
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"An error occurred while requesting {exc.request.url!r}.")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.")

@router.get("/astro-examples", response_model=Dict[str, Any])
async def get_astro_examples(
    request: Request,
    current_user=Depends(has_any_permission(["datapuur:read", "djinni:read"]))
):
    """
    Get example questions from the currently active Astro type.
    This endpoint determines the active Astro type and returns example questions
    from that specific model only.
    """
    try:
        # Get the active Astro type
        active_astro = await get_active_astro_type()
        
        # Determine the correct endpoint based on active_astro type
        if active_astro == "churn_astro":
            endpoint = "/api/churn-astro/examples"
        else:  # Default to factory_astro
            endpoint = "/api/factory-astro/examples"
        
        # Construct the full URL using the base URL from the request
        base_url = str(request.base_url)
        full_url = f"{base_url.rstrip('/')}{endpoint}"
        
        # Add authorization header from the original request
        headers = {
            "Authorization": request.headers.get("Authorization")
        }
        
        # Call the appropriate API endpoint
        async with httpx.AsyncClient() as client:
            response = await client.get(
                full_url,
                headers=headers,
                timeout=30.0,
            )
            
            response.raise_for_status()
            examples_data = response.json()
            
            # Return the examples with the active Astro type information
            return {
                "status": "success",
                "active_astro": active_astro,
                "examples": examples_data.get("examples", [])
            }
    except httpx.RequestError as exc:
        raise HTTPException(status_code=500, detail=f"An error occurred while requesting examples: {str(exc)}")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=f"Error response {exc.response.status_code} while requesting examples")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting examples: {str(e)}")

async def get_active_astro_type() -> str:
    """
    Get the currently active Astro type from system settings by direct function call.
    Returns 'factory_astro' or 'churn_astro'
    """
    try:
        settings = load_system_settings()
        active_model = settings.get("djinni_active_model", "factory_astro")
        
        if active_model == "churn_astro":
            return "churn_astro"
        return "factory_astro"
    except Exception:
        # Default to factory_astro if we can't determine the setting
        return "factory_astro"
