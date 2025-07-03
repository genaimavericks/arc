"use client"

import { useState, useRef, useEffect, forwardRef, useImperativeHandle } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Send, Loader2, BotMessageSquare, User } from "lucide-react"
import { useToast } from "@/components/ui/use-toast"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"

// Message type for chat history
export interface ChatMessage {
  id: string
  role: "user" | "assistant" | "system"
  content: string
  timestamp: Date
  metadata?: {
    schema?: any
    cypher?: string
    changes?: Array<{
      type: string
      entity: string
      details: string
    }>
  }
}

// Define the ref type for external access
export interface SchemaChatRef {
  handleSendMessage: () => Promise<void>;
  setMessage: (message: string) => void;
}

interface SchemaChatProps {
  selectedSource: string
  selectedSourceName: string
  selectedDatasetType?: "source" | "transformed" | ""
  domain: string
  customDomainFiles?: { [key: string]: string }
  onSchemaGenerated: (schema: any, cypher: string) => void
  loading: boolean
  setLoading: (loading: boolean) => void
}

export const SchemaChat = forwardRef<SchemaChatRef, SchemaChatProps>(function SchemaChat({ 
  selectedSource, 
  selectedSourceName,
  selectedDatasetType = "source",
  domain,
  customDomainFiles = {},
  onSchemaGenerated,
  loading,
  setLoading
}, ref) {
  // Error message state
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showError, setShowError] = useState(false);
  // Debug initial props
  console.log("SchemaChat initialized with:", {
    selectedSource,
    selectedSourceName,
    selectedDatasetType,
    domain
  });
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [message, setMessage] = useState("")
  const [currentSchema, setCurrentSchema] = useState<any>(null)
  const [filePath, setFilePath] = useState<string>("")  // Store file path for reuse
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const { toast } = useToast()
  
  // Initialize component
  useEffect(() => {
    // Initialize with a welcome message if messages is empty
    if (messages.length === 0) {
      setMessages([
        {
          id: "welcome",
          role: "assistant",
          content: "How can I help with your schema design?",
          timestamp: new Date(),
        }
      ])
    }
  }, [])

  // Scroll to bottom of messages when messages change
  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Handle auto-resize of textarea with improved resize behavior
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      // Save current scroll position before resizing
      const scrollPos = window.scrollY
      
      // Reset height to auto for proper calculation
      textarea.style.height = "auto"
      
      // Set new height based on content
      const newHeight = Math.min(textarea.scrollHeight, 200)
      textarea.style.height = `${newHeight}px`
      
      // Restore scroll position
      window.scrollTo(0, scrollPos)
      
      // Log for debugging
      console.log("Textarea resized to:", newHeight, "px")
    }
  }, [message])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }
  
  // Format timestamps
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  // Function to check if message is a simple greeting or farewell
  const isGreetingOrFarewell = (text: string): boolean => {
    // Normalize text: trim, lowercase, and remove punctuation
    const normalizedText = text.trim().toLowerCase().replace(/[.,!?;:]/g, '');
    
    // Check if the message is too short (likely a greeting)
    if (normalizedText.length <= 5) {
      // Very short messages are likely greetings
      console.log("Detected greeting (short text):", normalizedText);
      return true;
    }
    
    // List of common greetings and farewells
    const greetings = [
      'hi', 'hello', 'hey', 'howdy', 'hiya', 'morning', 'afternoon', 'evening',
      'greetings', 'sup', 'whats up', 'yo', 'hola', 'bonjour', 'ciao', 'namaste',
      'bye', 'goodbye', 'see you', 'farewell', 'later', 'take care', 'cheers', 'adios',
      'have a good day', 'have a nice day', 'good night', 'catch you later', 'ttyl',
      'thanks', 'thank you', 'thx', 'ty', 'welcome', 'how are you', 'what can you do',
      'help', 'test', 'testing', 'who are you', 'what are you', 'how do you work'
    ];
    
    // Split the normalized text into words
    const words = normalizedText.split(/\s+/);
    
    // If the message is just 1-3 words, check if any word is a greeting
    if (words.length <= 3) {
      for (const word of words) {
        if (greetings.includes(word)) {
          console.log("Detected greeting (word match):", word);
          return true;
        }
      }
      
      // Check for common greeting phrases
      if (greetings.some(greeting => normalizedText.includes(greeting))) {
        console.log("Detected greeting (phrase match):", normalizedText);
        return true;
      }
    }
    
    // For longer messages, check if they start with greetings
    for (const greeting of greetings) {
      if (normalizedText.startsWith(greeting + ' ')) {
        console.log("Detected greeting (starts with):", greeting);
        return true;
      }
    }
    
    // Check for exact matches with greetings
    if (greetings.includes(normalizedText)) {
      console.log("Detected greeting (exact match):", normalizedText);
      return true;
    }
    
    return false;
  };

  // Handle sending message
  const handleSendMessage = async () => {
    console.log("handleSendMessage called with dataset type:", selectedDatasetType);
    
    // Allow empty messages for schema generation
    if (loading) return
    
    if (!selectedSource) {
      toast({
        title: "Error",
        description: "Please select a data source first",
        variant: "destructive",
      })
      return
    }

    if (!domain) {
      toast({
        title: "Error",
        description: "Please select a data domain",
        variant: "destructive",
      })
      return
    }

    // Create a new user message
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: message,
      timestamp: new Date()
    }
    
    // Update messages with user message
    setMessages((prevMessages) => [...prevMessages, userMessage])
    
    // Check if the message is a greeting or farewell
    if (isGreetingOrFarewell(message)) {
      console.log("Detected greeting/farewell, blocking backend call:", message);
      
      // Add assistant response without sending to backend
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: "I'm your Schema Generation Assistant. To help you create an effective knowledge graph schema, please describe your dataset and what you want to model. For example, you could say 'I have customer transaction data and want to model relationships between customers and products' or 'I need a schema for my healthcare dataset that connects patients, treatments, and outcomes.' The more details you provide about your data and goals, the better schema I can generate.",
        timestamp: new Date()
      }
      
      // Update messages with assistant response
      setMessages((prevMessages) => [...prevMessages, assistantMessage])
      
      // Reset loading state
      setLoading(false)
      return
    }
    
    // Clear the input
    setMessage("")
    
    // Show loading state
    setLoading(true)
    
    try {
      // First, fetch the detailed source information to get the file path based on dataset type
      let sourceResponse;
      
      // Critical debugging for API selection
      console.log("BEFORE API CALL - Dataset type check:", {
        selectedDatasetType,
        isTransformed: selectedDatasetType === "transformed",
        typeOfVar: typeof selectedDatasetType,
        selectedSource
      });
      
      if (selectedDatasetType === "transformed") {
        // For transformed datasets, use the transformed dataset API
        console.log("Using transformed dataset API for ID:", selectedSource);
        sourceResponse = await fetch(`/api/datapuur-ai/transformed-datasets/${selectedSource}`, {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        });
      } else {
        // For source datasets, use the new source file API
        console.log("Using source file API for ID:", selectedSource);
        sourceResponse = await fetch(`/api/datapuur/source-file/${selectedSource}`, {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        });
      }
      
      if (!sourceResponse.ok) {
        if (sourceResponse.status === 403) {
          const msg = `Permission denied: You don't have sufficient permissions to access ${selectedDatasetType} details.`;
          setErrorMessage(msg);
          setShowError(true);
          setTimeout(() => setShowError(false), 5000); // Hide after 5 seconds
          throw new Error(msg);
        }
        throw new Error(`Failed to fetch ${selectedDatasetType} details: ${sourceResponse.status}`);
      }
      
      const sourceData = await sourceResponse.json();
      
      // Handle different response formats based on dataset type
      let filePath;
      if (selectedDatasetType === "transformed") {
        filePath = sourceData.transformed_file_path;
      } else {
        filePath = sourceData.full_path || sourceData.file_path || sourceData.filepath;
      }
      
      setFilePath(filePath);
      // Extract file type and name based on dataset type
      let fileType;
      let fileName;
      
      if (selectedDatasetType === "transformed") {
        fileType = "parquet";
        fileName = sourceData.name || "transformed-dataset";
      } else {
        fileType = sourceData.file_type || sourceData.type;
        fileName = sourceData.filename;
      }
      
      // Any pre-existing schema information
      const fileMetadata = selectedDatasetType === "transformed" ? 
        sourceData.column_metadata : 
        (sourceData.schema || {})
      
      // Enhanced metadata for schema generation
      const enhancedMetadata = {
        userPrompt: message,
        fileName: fileName,
        fileType: fileType,
        sourceId: selectedSource,
        sourceName: selectedSourceName,
        domain: domain,
        existingSchema: fileMetadata
      };
      
      // Store the file path for reuse during refinement
      setFilePath(filePath);
      
      // Now, send request to build schema API with the file path and enhanced metadata
      console.log("Calling schema generation API with:", {
        source_id: selectedSource,
        dataset_type: selectedDatasetType,
        file_path: filePath
      });
      
      // Check if the domain is a custom domain with a file path
      const customDomainFilePath = customDomainFiles[domain];
      console.log("Custom domain check:", { domain, customDomainFilePath, customDomainFiles });
      
      const response = await fetch("/api/graphschema/build-schema-from-source", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({
          source_id: selectedSource,
          metadata: JSON.stringify(enhancedMetadata),
          file_path: filePath,
          dataset_type: selectedDatasetType,
          domain: domain,
          custom_domain_file: customDomainFilePath // Add custom domain file path if available
        }),
      })
      
      if (!response.ok) {
        if (response.status === 403) {
          const msg = "Permission denied: You don't have sufficient permissions to generate schemas.";
          setErrorMessage(msg);
          setShowError(true);
          setTimeout(() => setShowError(false), 5000); // Hide after 5 seconds
          throw new Error(msg);
        } 
        throw new Error(`Failed to generate schema: ${response.status}`)
      }
      
      const data = await response.json()
      
      // Create assistant message from response
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: `Based on your data, I recommend a schema for ${selectedSourceName}. You can see the visualization and details on the right.`,
        timestamp: new Date(),
        metadata: {
          schema: data.schema,
          cypher: data.cypher
        }
      }
      
      // Update messages with assistant response
      setMessages((prevMessages) => [...prevMessages, assistantMessage])
      
      // Add the file path to the schema
      const schemaWithFilePath = {
        ...data.schema,
        csv_file_path: filePath
      };
      
      // Call the callback to update the parent component with the enhanced schema
      onSchemaGenerated(schemaWithFilePath, data.cypher)
      
      // Store the current schema for refinement (with file path)
      setCurrentSchema(schemaWithFilePath)
      
      toast({
        title: "Success",
        description: "Schema generated successfully!",
      })
    } catch (error) {
      console.error("Error generating schema:", error)
      
      // Add error message
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        role: "system",
        content: "Sorry, I encountered an error generating the schema. Please try again.",
        timestamp: new Date(),
      }
      
      setMessages((prevMessages) => [...prevMessages, errorMessage])
      
      toast({
        title: "Error",
        description: "Failed to generate schema. Please try again.",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  // Expose methods to parent component via ref
  useImperativeHandle(ref, () => ({
    handleSendMessage: async () => {
      return handleSendMessage();
    },
    setMessage: (newMessage: string) => {
      setMessage(newMessage);
    }
  }), [handleSendMessage]);

  // Handle sending message for schema refinement
  const handleRefinement = async () => {
    if (!message.trim() || loading) return
    
    if (!selectedSource) {
      toast({
        title: "Error",
        description: "Please select a data source first",
        variant: "destructive",
      })
      return
    }

    if (!domain) {
      toast({
        title: "Error",
        description: "Please select a data domain",
        variant: "destructive",
      })
      return
    }

    if (!currentSchema) {
      toast({
        title: "Error",
        description: "No schema to refine. Please generate a schema first.",
        variant: "destructive",
      })
      return
    }

    // Create a new user message
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: message,
      timestamp: new Date()
    }
    
    // Update messages with user message
    setMessages((prevMessages) => [...prevMessages, userMessage])
    
    // Clear the input
    setMessage("")
    
    // Show loading state
    setLoading(true)
    
    try {
      // Send request to API for schema refinement with file path
      const response = await fetch("/api/graphschema/refine-schema", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({
          source_id: selectedSource,
          current_schema: currentSchema,
          feedback: message,
          file_path: filePath, // Reuse stored file path
          domain: domain, // Include domain information
          custom_domain_file: customDomainFiles?.[domain], // Include custom domain file if available
          dataset_type: selectedDatasetType, // Include dataset type for proper path handling
        }),
      })
      
      if (!response.ok) {
        throw new Error(`Failed to refine schema: ${response.status}`)
      }
      
      const data = await response.json()
      
      // Create assistant message from response
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: `I've refined the schema based on your feedback. The changes are now visible in the visualization.`,
        timestamp: new Date(),
        metadata: {
          schema: data.schema,
          cypher: data.cypher,
          changes: data.schema.changes || []
        }
      }
      
      // Update messages with assistant response
      setMessages((prevMessages) => [...prevMessages, assistantMessage])
      
      // Remove the changes array from the schema before updating the visualization
      // This is necessary because the visualization component doesn't expect this property
      if (data.schema.changes) {
        const schemaForVisualization = { ...data.schema };
        delete schemaForVisualization.changes;
        
        // Ensure the CSV file path is preserved
        schemaForVisualization.csv_file_path = filePath;
        
        // Call the callback to update the parent component with the cleaned schema
        onSchemaGenerated(schemaForVisualization, data.cypher);
        
        // Update the current schema for future refinements
        setCurrentSchema(schemaForVisualization);
      } else {
        // Ensure the CSV file path is preserved
        const schemaWithFilePath = {
          ...data.schema,
          csv_file_path: filePath
        };
        
        // Call the callback to update the parent component
        onSchemaGenerated(schemaWithFilePath, data.cypher);
        
        // Update the current schema for future refinements
        setCurrentSchema(schemaWithFilePath);
      }
      
      toast({
        title: "Success",
        description: "Schema refined successfully!",
      })
    } catch (error) {
      console.error("Error refining schema:", error)
      
      // Add error message
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        role: "system",
        content: "Sorry, I encountered an error refining the schema. Please try again.",
        timestamp: new Date(),
      }
      
      setMessages((prevMessages) => [...prevMessages, errorMessage])
      
      toast({
        title: "Error",
        description: "Failed to refine schema. Please try again.",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }
  
  // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Log key events for debugging
    console.log("Key pressed:", e.key, "Shift:", e.shiftKey)
    
    // If Enter key is pressed without Shift key and not on iOS
    if (e.key === "Enter" && !e.shiftKey && !/(iPad|iPhone|iPod)/.test(navigator.userAgent)) {
      e.preventDefault()
      
      // Check if we can send a message
      const canSend = !loading && message.trim() && selectedSource
      console.log("Can send message:", canSend, { loading, hasMessage: !!message.trim(), hasSource: !!selectedSource })
      
      if (canSend) {
        if (currentSchema) {
          handleRefinement()
        } else {
          handleSendMessage()
        }
      } else {
        // Show toast if button is disabled but user tries to send
        if (!selectedSource) {
          toast({
            title: "No dataset selected",
            description: "Please select a dataset first before sending a message.",
            variant: "destructive",
          })
        } else if (loading) {
          toast({
            title: "Processing",
            description: "Please wait while we process your current request.",
          })
        }
      }
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Error message alert */}
      {showError && errorMessage && (
        <div className="bg-destructive/15 border border-destructive text-destructive px-4 py-3 rounded-md mb-4 flex items-center justify-between animate-in slide-in-from-top duration-300">
          <div className="flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <span>{errorMessage}</span>
          </div>
          <button 
            onClick={() => setShowError(false)}
            className="text-destructive hover:text-destructive/80"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
      )}
      
      {/* Chat messages */}
      <ScrollArea className="flex-grow pr-4 min-h-0">
        <div className="space-y-3 p-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                "flex flex-col",
                message.role === "user" ? "items-end" : "items-start"
              )}
            >
              <div className="flex items-end gap-2">
                {message.role !== "user" && (
                  <div className="rounded-full bg-primary/10 p-2 flex items-center justify-center">
                    {message.role === "assistant" ? (
                      <BotMessageSquare className="h-4 w-4 text-primary" />
                    ) : (
                      <BotMessageSquare className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                )}
                
                <Card
                  className={cn(
                    "px-4 py-3 max-w-[80%] break-words",
                    message.role === "user" 
                      ? "bg-primary text-primary-foreground" 
                      : message.role === "system"
                      ? "bg-secondary/50"
                      : "bg-card"
                  )}
                >
                  <div className="space-y-2">
                    <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap">
                      {message.content}
                    </div>
                    
                    {message.metadata?.changes && message.metadata.changes.length > 0 && (
                      <div className="mt-3 p-3 bg-muted/30 rounded-md">
                        <h4 className="text-sm font-medium mb-1">Changes Made:</h4>
                        <ul className="list-disc pl-5 text-xs space-y-1">
                          {message.metadata.changes.map((change, idx) => (
                            <li key={idx} className={
                              change.type === 'added' 
                                ? 'text-green-600 dark:text-green-400' 
                                : change.type === 'removed' 
                                  ? 'text-red-600 dark:text-red-400'
                                  : 'text-blue-600 dark:text-blue-400'
                            }>
                              {change.type === 'added' ? 'Added' : change.type === 'removed' ? 'Removed' : 'Modified'} {change.entity}: {change.details}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </Card>
                
                {message.role === "user" && (
                  <div className="rounded-full bg-primary p-2 flex items-center justify-center">
                    <User className="h-4 w-4 text-primary-foreground" />
                  </div>
                )}
              </div>
              
              <span className="text-xs text-muted-foreground mt-1 px-2">
                {formatTime(message.timestamp)}
              </span>
            </div>
          ))}
          
          {/* Loading indicator */}
          {loading && (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          )}
          
          {/* Reference for auto-scrolling */}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>
      
      {/* Chat input */}
      <div className="p-4 border-t mt-auto">
        <div className="flex items-end gap-2">
          <Textarea
            id="schema-chat-input"
            ref={textareaRef}
            value={message}
            onChange={(e) => {
              console.log("Setting message to:", e.target.value);
              setMessage(e.target.value);
              // Force update the message state immediately
              e.target.dispatchEvent(new Event('input', { bubbles: true }));
            }}
            onKeyDown={handleKeyDown}
            placeholder="Ask about schema..."
            className="flex-grow resize-none min-h-[60px] max-h-[200px] overflow-y-auto"
            disabled={loading || !selectedSource}
          />
          <Button
            className="flex-shrink-0"
            onClick={() => {
              console.log("Button clicked. Current state:", {
                message: message,
                messageEmpty: !message.trim(),
                loading: loading,
                selectedSource: selectedSource,
                currentSchema: currentSchema !== null
              });
              if (currentSchema) {
                handleRefinement();
              } else {
                handleSendMessage();
              }
            }}
            disabled={loading || !selectedSource}
            // Remove the message.trim() check to allow the button to be enabled regardless of message content
            // This fixes the issue where the button remains disabled even after typing
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            <span className="ml-2 hidden md:inline">{currentSchema ? "Refine" : "Generate"}</span>
          </Button>
        </div>
      </div>
    </div>
  )
})
