# Knowledge Graph Insights Chat Enhancement Implementation Plan

## Overview

This document outlines the implementation plan for three key user stories to enhance the Knowledge Graph Insights chat interface:

1. **SCRUM-48**: Autocomplete functionality for entity names and common phrases
2. **SCRUM-49**: Related query suggestions to broaden or narrow analysis
3. **SCRUM-50**: Error detection and highlighting for query improvement

All features will be implemented with real-time functionality to provide immediate feedback and suggestions as users type.

## Current System Architecture

### Backend (api/kgdatainsights)
- FastAPI-based API endpoints for processing knowledge graph queries
- Neo4j integration for graph database operations
- LLM-based query processing using schema-aware agents

### Frontend (app/kginsights/insights)
- React-based chat interface
- Components for message display, input, and history management
- No current autocomplete, suggestions, or error detection functionality

## Implementation Phases

### Phase 1: Backend Infrastructure (Week 1)

#### Step 1: Create WebSocket API for Real-time Features

1. **Create WebSocket Manager**
   - Implement a unified WebSocket endpoint for all real-time features
   - Add message routing based on message type (autocomplete, suggestions, validation)
   - Implement connection state management and authentication

2. **Implement Autocomplete Backend**
   - Create entity name extraction from Neo4j schema
   - Implement common phrase suggestion based on schema and history
   - Add caching mechanisms for frequently accessed entities

3. **Implement Query Suggestion Backend**
   - Create logic to analyze current query context
   - Implement algorithms to generate related dimension/metric suggestions
   - Add functionality to suggest query modifications (broaden/narrow)

4. **Implement Query Validation Backend**
   - Create incremental syntax checking for partial queries
   - Implement schema-aware validation for entity and property references
   - Add suggestion generation for error correction

#### Step 2: Optimize for Real-time Performance

1. **Database Optimization**
   - Create pre-computed indexes for entity names and properties
   - Implement connection pooling for concurrent requests
   - Add query result caching with appropriate TTL

2. **Processing Optimization**
   - Implement worker threads for CPU-intensive operations
   - Add priority-based processing for critical features
   - Create progressive result delivery for long-running operations

### Phase 2: Frontend Components (Week 2)

#### Step 3: Create Real-time WebSocket Client

1. **Implement WebSocket Connection Manager**
   - Create a React context provider for WebSocket state
   - Implement message handling and routing
   - Add reconnection logic and connection state management

2. **Create Debounced Input Handling**
   - Implement input debouncing to avoid excessive API calls
   - Add input tokenization for context-aware suggestions
   - Create cursor position tracking for targeted suggestions

#### Step 4: Implement Autocomplete UI (SCRUM-48)

1. **Create Autocomplete Dropdown Component**
   - Implement a dropdown that appears as users type
   - Add keyboard navigation for suggestion selection
   - Create different styling for different suggestion types

2. **Enhance Chat Input Component**
   - Modify InsightsChatInput to integrate with autocomplete
   - Implement token highlighting for matched entities
   - Add suggestion acceptance with keyboard shortcuts

#### Step 5: Implement Query Suggestion UI (SCRUM-49)

1. **Create Suggestion Chips Component**
   - Develop a component to display related query suggestions
   - Implement click handlers to modify or replace current query
   - Add animations for suggestion appearance and updates

2. **Enhance Chat Messages Component**
   - Add suggestion display after assistant responses
   - Implement UI for dimension/metric addition
   - Create visual indicators for query broadening/narrowing

#### Step 6: Implement Error Detection UI (SCRUM-50)

1. **Create Syntax Highlighting Component**
   - Implement token-based rendering with syntax highlighting
   - Add visual indicators for errors as they are detected
   - Create inline suggestion display for quick fixes

2. **Enhance Input Validation**
   - Add client-side validation for common errors
   - Implement visual feedback for error correction
   - Create suggestion mechanism for fixing detected errors

### Phase 3: Integration and Testing (Week 3)

#### Step 7: End-to-End Integration

1. **Connect Frontend to Backend Services**
   - Integrate all UI components with WebSocket API
   - Implement proper error handling and fallbacks
   - Add loading states and progress indicators

2. **Optimize State Management**
   - Enhance state management for real-time updates
   - Implement efficient rendering to prevent UI lag
   - Add proper cleanup for component lifecycle

#### Step 8: Testing and Refinement

1. **Develop Test Cases**
   - Create unit tests for backend services
   - Implement integration tests for frontend components
   - Develop end-to-end tests for complete features

2. **Performance Optimization**
   - Optimize WebSocket message frequency and size
   - Improve rendering performance for real-time updates
   - Enhance error detection efficiency

## Detailed Technical Specifications

### 1. WebSocket API (Backend)

```python
# websocket_manager.py
from fastapi import WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List, Any, Optional
import asyncio
import json
from ..auth import get_current_user_ws
from ..models import User

class ConnectionManager:
    """Manager for WebSocket connections with authentication and message routing."""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str, schema_id: str):
        await websocket.accept()
        if schema_id not in self.active_connections:
            self.active_connections[schema_id] = []
        self.active_connections[schema_id].append((websocket, user_id))
        
    async def disconnect(self, websocket: WebSocket, schema_id: str):
        for schema, connections in self.active_connections.items():
            if schema == schema_id:
                self.active_connections[schema] = [
                    (ws, user_id) for ws, user_id in connections if ws != websocket
                ]
                
    async def route_message(self, message: Dict[str, Any], schema_id: str, user_id: str):
        """Route message to appropriate handler based on message type."""
        message_type = message.get("type", "")
        query = message.get("query", "")
        
        if not query:
            return None
            
        if message_type == "autocomplete":
            return await self.handle_autocomplete(query, schema_id)
        elif message_type == "suggestions":
            history = message.get("history", [])
            return await self.handle_suggestions(query, history, schema_id)
        elif message_type == "validation":
            return await self.handle_validation(query, schema_id)
        
        return None
        
    async def handle_autocomplete(self, query: str, schema_id: str):
        """Process autocomplete requests."""
        # Implementation will query Neo4j for entities matching the input
        # Will use schema information to prioritize relevant entities
        
    async def handle_suggestions(self, query: str, history: List[str], schema_id: str):
        """Process query suggestion requests."""
        # Implementation will analyze the current query
        # Will use schema information and LLM to generate relevant suggestions
        
    async def handle_validation(self, query: str, schema_id: str):
        """Process query validation requests."""
        # Implementation will use NLP and schema awareness
        # Will detect common errors and provide suggestions

manager = ConnectionManager()

async def get_connection_manager():
    return manager

@router.websocket("/ws/{schema_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    schema_id: str,
    manager: ConnectionManager = Depends(get_connection_manager),
    current_user: User = Depends(get_current_user_ws)
):
    """
    WebSocket endpoint for real-time features.
    Handles autocomplete, suggestions, and validation in a single connection.
    """
    await manager.connect(websocket, current_user.id, schema_id)
    try:
        while True:
            data = await websocket.receive_json()
            response = await manager.route_message(data, schema_id, current_user.id)
            if response:
                await websocket.send_json(response)
    except WebSocketDisconnect:
        await manager.disconnect(websocket, schema_id)
```

### 2. Real-time Frontend Components

```typescript
// realtime-context.tsx
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useDebouncedCallback } from 'use-debounce';

interface RealtimeContextType {
  autocomplete: {
    suggestions: AutocompleteItem[];
    loading: boolean;
    request: (text: string) => void;
  };
  suggestions: {
    suggestions: QuerySuggestion[];
    loading: boolean;
    request: (query: string, history?: string[]) => void;
  };
  validation: {
    errors: QueryError[];
    loading: boolean;
    request: (text: string) => void;
  };
  connectionStatus: number;
}

export const RealtimeContext = createContext<RealtimeContextType | undefined>(undefined);

export function RealtimeProvider({ children, schemaId }) {
  // WebSocket connection setup
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [connectionStatus, setConnectionStatus] = useState(WebSocket.CONNECTING);
  
  // State for different feature types
  const [autocompleteState, setAutocompleteState] = useState({ suggestions: [], loading: false });
  const [suggestionsState, setSuggestionsState] = useState({ suggestions: [], loading: false });
  const [validationState, setValidationState] = useState({ errors: [], loading: false });
  
  // Initialize WebSocket connection
  useEffect(() => {
    const token = localStorage.getItem('token');
    const ws = new WebSocket(`/api/datainsights/ws/${schemaId}?token=${token}`);
    
    ws.onopen = () => setConnectionStatus(WebSocket.OPEN);
    ws.onclose = () => setConnectionStatus(WebSocket.CLOSED);
    ws.onerror = () => setConnectionStatus(WebSocket.CLOSED);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'autocomplete':
          setAutocompleteState({ suggestions: data.suggestions, loading: false });
          break;
        case 'suggestions':
          setSuggestionsState({ suggestions: data.suggestions, loading: false });
          break;
        case 'validation':
          setValidationState({ errors: data.errors, loading: false });
          break;
      }
    };
    
    setSocket(ws);
    
    // Cleanup on unmount
    return () => {
      ws.close();
    };
  }, [schemaId]);
  
  // Debounced request functions
  const requestAutocomplete = useDebouncedCallback((text: string) => {
    if (socket && connectionStatus === WebSocket.OPEN) {
      setAutocompleteState(prev => ({ ...prev, loading: true }));
      socket.send(JSON.stringify({ type: 'autocomplete', query: text }));
    }
  }, 150);
  
  const requestSuggestions = useDebouncedCallback((query: string, history?: string[]) => {
    if (socket && connectionStatus === WebSocket.OPEN) {
      setSuggestionsState(prev => ({ ...prev, loading: true }));
      socket.send(JSON.stringify({ type: 'suggestions', query, history }));
    }
  }, 300);
  
  const requestValidation = useDebouncedCallback((text: string) => {
    if (socket && connectionStatus === WebSocket.OPEN) {
      setValidationState(prev => ({ ...prev, loading: true }));
      socket.send(JSON.stringify({ type: 'validation', query: text }));
    }
  }, 200);
  
  // Context value
  const contextValue = {
    autocomplete: {
      ...autocompleteState,
      request: requestAutocomplete
    },
    suggestions: {
      ...suggestionsState,
      request: requestSuggestions
    },
    validation: {
      ...validationState,
      request: requestValidation
    },
    connectionStatus
  };
  
  return (
    <RealtimeContext.Provider value={contextValue}>
      {children}
    </RealtimeContext.Provider>
  );
}

export const useRealtime = () => {
  const context = useContext(RealtimeContext);
  if (context === undefined) {
    throw new Error('useRealtime must be used within a RealtimeProvider');
  }
  return context;
};
```

### 3. Enhanced Chat Input with Real-time Features

```typescript
// enhanced-chat-input.tsx
import React, { useState, useRef, useEffect } from 'react';
import { useRealtime } from './realtime-context';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Send, Loader2 } from 'lucide-react';
import { AutocompleteDropdown } from './autocomplete-dropdown';
import { SyntaxHighlighter } from './syntax-highlighter';

interface EnhancedChatInputProps {
  onSendMessage: (message: string) => Promise<void>;
  loading: boolean;
  sourceId: string;
}

export function EnhancedChatInput({ 
  onSendMessage, 
  loading,
  sourceId
}: EnhancedChatInputProps) {
  const [message, setMessage] = useState('');
  const [cursorPosition, setCursorPosition] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  // Get real-time context
  const { 
    autocomplete, 
    validation,
    suggestions 
  } = useRealtime();
  
  // Track input changes and cursor position
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    setMessage(newValue);
    setCursorPosition(e.target.selectionStart || 0);
    
    // Request autocomplete and validation
    autocomplete.request(newValue);
    validation.request(newValue);
    
    // Only request suggestions for complete sentences
    if (newValue.endsWith('.') || newValue.endsWith('?')) {
      suggestions.request(newValue);
    }
  };
  
  // Handle cursor position changes
  const handleSelect = (e: React.SyntheticEvent<HTMLTextAreaElement>) => {
    setCursorPosition(e.currentTarget.selectionStart || 0);
  };
  
  // Apply a suggestion to the input
  const applySuggestion = (suggestion: AutocompleteItem) => {
    // Get the current word being typed
    const textBeforeCursor = message.substring(0, cursorPosition);
    const textAfterCursor = message.substring(cursorPosition);
    
    // Find the start of the current word
    const wordStartRegex = /\S*$/;
    const match = textBeforeCursor.match(wordStartRegex);
    
    if (match && match[0]) {
      const wordStart = textBeforeCursor.length - match[0].length;
      const newText = textBeforeCursor.substring(0, wordStart) + 
                     suggestion.text + 
                     textAfterCursor;
      
      setMessage(newText);
      
      // Set cursor position after the inserted suggestion
      setTimeout(() => {
        if (textareaRef.current) {
          const newPosition = wordStart + suggestion.text.length;
          textareaRef.current.focus();
          textareaRef.current.setSelectionRange(newPosition, newPosition);
          setCursorPosition(newPosition);
        }
      }, 0);
    } else {
      // If no word is being typed, just insert the suggestion
      const newText = textBeforeCursor + suggestion.text + textAfterCursor;
      setMessage(newText);
      
      // Set cursor position after the inserted suggestion
      setTimeout(() => {
        if (textareaRef.current) {
          const newPosition = textBeforeCursor.length + suggestion.text.length;
          textareaRef.current.focus();
          textareaRef.current.setSelectionRange(newPosition, newPosition);
          setCursorPosition(newPosition);
        }
      }, 0);
    }
  };
  
  // Apply a fix for a validation error
  const applyFix = (fix: string) => {
    setMessage(fix);
    
    // Request validation for the fixed text
    validation.request(fix);
  };
  
  // Handle sending message
  const handleSendMessage = async () => {
    if (!message.trim() || loading) return;
    
    try {
      await onSendMessage(message);
      setMessage('');
    } catch (error) {
      console.error('Error sending message:', error);
    }
  };
  
  // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Send message on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
      return;
    }
    
    // Handle autocomplete navigation with arrow keys
    if (autocomplete.suggestions.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        // Navigate to next suggestion
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        // Navigate to previous suggestion
      } else if (e.key === 'Tab') {
        e.preventDefault();
        // Apply selected suggestion
        applySuggestion(autocomplete.suggestions[0]);
      }
    }
  };

  return (
    <div className="relative">
      {/* Syntax highlighting overlay */}
      <SyntaxHighlighter 
        text={message} 
        errors={validation.errors}
        onFix={applyFix}
      />
      
      {/* Autocomplete dropdown */}
      {autocomplete.suggestions.length > 0 && (
        <AutocompleteDropdown
          suggestions={autocomplete.suggestions}
          loading={autocomplete.loading}
          onSelect={applySuggestion}
          position={cursorPosition}
        />
      )}
      
      <div className="flex items-end gap-2">
        <div className="relative flex-grow">
          <Textarea
            ref={textareaRef}
            value={message}
            onChange={handleInputChange}
            onSelect={handleSelect}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your knowledge graph..."
            className="flex-grow resize-none min-h-[60px] max-h-[200px] overflow-y-auto"
            disabled={loading}
          />
        </div>
        <Button
          className="flex-shrink-0"
          onClick={handleSendMessage}
          disabled={!message.trim() || loading}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
          <span className="ml-2 hidden md:inline">Send</span>
        </Button>
      </div>
    </div>
  );
}
```

## Feature Details

### SCRUM-48: Autocomplete Functionality

#### Backend Implementation
- Entity name extraction from Neo4j graph schema
- Common phrase suggestion based on query history
- Keyword suggestion based on Cypher/query patterns
- Real-time suggestion delivery via WebSocket

#### Frontend Implementation
- Dropdown menu that appears as users type
- Different styling for different suggestion types
- Keyboard navigation for suggestion selection
- Token-based input parsing for context-aware suggestions

### SCRUM-49: Related Query Suggestions

#### Backend Implementation
- Query intent detection for suggestion relevance
- Dimension and metric suggestion based on schema
- Query modification suggestions (broaden/narrow)
- Progressive suggestion delivery for immediate feedback

#### Frontend Implementation
- Suggestion chips that appear after responses
- Visual indicators for suggestion types
- Click handlers to modify or replace current query
- Animations for suggestion updates

### SCRUM-50: Error Detection and Highlighting

#### Backend Implementation
- Incremental syntax checking for partial queries
- Schema-aware validation for entity references
- Error categorization by severity and type
- Suggestion generation for error correction

#### Frontend Implementation
- Real-time syntax highlighting with error indicators
- Tooltips with error details on hover
- Quick-fix buttons for common errors
- Visual feedback for error correction

## Implementation Timeline

### Week 1: Backend Infrastructure
- Day 1-2: Implement WebSocket API and connection management
- Day 3-4: Implement autocomplete and suggestion services
- Day 5: Implement query validation service

### Week 2: Frontend Components
- Day 1-2: Implement WebSocket client and context provider
- Day 3: Implement autocomplete dropdown component
- Day 4: Implement suggestion chips component
- Day 5: Implement syntax highlighting component

### Week 3: Integration and Testing
- Day 1-2: Integrate all components and optimize state management
- Day 3-4: Implement comprehensive testing
- Day 5: Performance optimization and final refinements

## Conclusion

This implementation plan provides a comprehensive approach to enhancing the Knowledge Graph Insights chat interface with real-time autocomplete functionality, related query suggestions, and error detection. By implementing these features, we will significantly improve the user experience for Data Engineers, making it faster and easier to construct accurate queries and discover valuable insights.

The plan focuses on:
1. Real-time responsiveness through WebSocket communication
2. Efficient state management for immediate feedback
3. Context-aware suggestions based on the user's current input
4. Seamless integration with the existing chat interface

By following this plan, we can successfully implement all three user stories (SCRUM-48, SCRUM-49, and SCRUM-50) to create a more powerful and user-friendly Knowledge Graph Insights experience.
