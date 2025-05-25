# KG Insights WebSocket Services Integration Guide

This guide explains how to integrate the WebSocket-based services for suggestions, autocomplete, and query handling into existing chat interfaces.

## Overview

We've created a set of modular, pluggable services that can be integrated into any React component:

1. **WebSocketService**: Core service for WebSocket communication
2. **SuggestionService**: Handles query suggestions with filtering
3. **AutocompleteService**: Handles autocomplete suggestions
4. **useKGInsights Hook**: React hook for easy integration

## Integration Steps

### 1. Basic Integration with the useKGInsights Hook

The simplest way to integrate is to use the `useKGInsights` hook:

```tsx
import { useKGInsights } from './components/kginsights/use-kg-insights';

function YourChatComponent() {
  // Get schema ID and token from your authentication system
  const schemaId = "your-schema-id";
  const token = "your-auth-token";
  
  const {
    connected,
    loading,
    error,
    suggestions,
    autocompleteSuggestions,
    getSuggestions,
    getAutocompleteSuggestions,
    sendQuery
  } = useKGInsights(schemaId, token);

  // Use these functions and state in your component
  // ...
}
```

### 2. Using Suggestions in Your Component

```tsx
// Handle input changes
const handleInputChange = (e) => {
  const value = e.target.value;
  setInputValue(value);
  
  // Get cursor position
  const cursorPosition = e.target.selectionStart || value.length;
  
  // Get suggestions based on input
  if (value.trim()) {
    getSuggestions(value, cursorPosition);
  }
};

// Render suggestions
{suggestions.length > 0 && (
  <div className="suggestions-container">
    {suggestions.map((suggestion, index) => (
      <div 
        key={index}
        onClick={() => handleSelectSuggestion(suggestion)}
      >
        {suggestion}
      </div>
    ))}
  </div>
)}
```

### 3. Using Autocomplete in Your Component

```tsx
// Get autocomplete suggestions
const handleInputChange = (e) => {
  const value = e.target.value;
  const cursorPosition = e.target.selectionStart || value.length;
  
  // Get autocomplete suggestions
  if (value.trim()) {
    getAutocompleteSuggestions(value, cursorPosition);
  }
};

// Render autocomplete suggestions
{autocompleteSuggestions.length > 0 && (
  <div className="autocomplete-container">
    {autocompleteSuggestions.map((suggestion, index) => (
      <div 
        key={index}
        onClick={() => handleSelectAutocompleteSuggestion(suggestion)}
      >
        <div>{suggestion.text}</div>
        {suggestion.description && (
          <div className="description">{suggestion.description}</div>
        )}
      </div>
    ))}
  </div>
)}
```

### 4. Sending Queries

```tsx
const handleSendMessage = () => {
  if (!inputValue.trim()) return;
  
  // Add the message to your local state
  setMessages(prev => [...prev, {
    role: 'user',
    content: inputValue
  }]);
  
  // Send the query via WebSocket
  sendQuery(inputValue);
  
  // Clear input
  setInputValue('');
};
```

### 5. Advanced: Using Services Directly

If you need more control, you can use the services directly:

```tsx
import { WebSocketService } from './components/kginsights/websocket-service';
import { SuggestionService } from './components/kginsights/suggestion-service';
import { AutocompleteService } from './components/kginsights/autocomplete-service';

// Create service instances
const webSocketService = new WebSocketService(baseUrl);
const suggestionService = new SuggestionService(webSocketService);
const autocompleteService = new AutocompleteService(webSocketService);

// Connect to WebSocket
webSocketService.connect(schemaId, token)
  .then(() => {
    console.log('Connected!');
  })
  .catch(error => {
    console.error('Connection failed:', error);
  });

// Register handlers for responses
webSocketService.registerHandler('query_result', handleQueryResult);

// Get suggestions
suggestionService.getSuggestions(query, cursorPosition, (suggestions) => {
  // Use the suggestions
});

// Get autocomplete suggestions
autocompleteService.getAutocompleteSuggestions(text, cursorPosition, (suggestions) => {
  // Use the suggestions
});

// Send a query
webSocketService.sendMessage('query', {
  query: 'Your query',
  query_id: 'unique-id'
});

// Clean up when done
webSocketService.disconnect();
suggestionService.destroy();
autocompleteService.destroy();
```

## Example Component

We've included an `ExampleChatComponent` that demonstrates how to use these services. You can refer to it for a complete example of integration.

## Migrating from the Simple Chat Page

To migrate from the Simple Chat page to the main KG Insights page:

1. Import the services and hook into the main page
2. Replace the direct WebSocket handling with our services
3. Keep the same UI elements and styling
4. Update the event handlers to use our services

## Handling WebSocket Authentication

The `WebSocketService` handles authentication by including the token in the WebSocket connection URL. Make sure to provide a valid token when connecting:

```tsx
webSocketService.connect(schemaId, yourAuthToken);
```

## Error Handling and Reconnection

The `WebSocketService` includes automatic reconnection logic and error handling. You can configure this behavior:

```tsx
const webSocketService = new WebSocketService(baseUrl, autoReconnect: true);
```

## Customizing Suggestions and Autocomplete

Both services accept options to customize their behavior:

```tsx
const suggestionService = new SuggestionService(webSocketService, {
  maxSuggestions: 10,
  debounceTime: 300 // milliseconds
});

const autocompleteService = new AutocompleteService(webSocketService, {
  maxSuggestions: 5,
  debounceTime: 150 // milliseconds
});
```

## Preserving Context-Aware Query Handling

The services preserve the context-aware query handling improvements, including:

- Contextual query preprocessing
- Handling of comparative queries
- Special handling for follow-up questions
- Conversation history context in query reformulation

This functionality is built into the backend and our services properly communicate with it.
