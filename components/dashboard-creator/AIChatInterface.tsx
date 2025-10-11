"use client"

import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Bot, ArrowRight, Lightbulb, Sparkles } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

interface AIChatInterfaceProps {
  onTemplatesGenerated?: (templates: any[]) => void
  selectedDatasets?: {source_ids: string[], transformed_ids: string[]}
  validation?: any
  disabled?: boolean
}

export const AIChatInterface: React.FC<AIChatInterfaceProps> = ({ 
  onTemplatesGenerated,
  selectedDatasets,
  validation,
  disabled = false
}) => {
  const [prompt, setPrompt] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [chatHistory, setChatHistory] = useState<Array<{role: string, content: string}>>([])

  const canProceed = validation?.can_create_dashboard && !disabled

  const suggestedPrompts = [
    "Create an executive dashboard with KPIs and performance metrics",
    "Build a sales analytics dashboard with revenue trends",
    "Design a customer insights dashboard with behavioral analysis", 
    "Generate an operational dashboard with real-time monitoring",
    "Create a financial dashboard with budget vs actual comparisons"
  ]

  const handleGenerateTemplates = async () => {
    if (!prompt.trim() || !canProceed) return
    
    setIsGenerating(true)
    setError(null)
    
    try {
      // Add user message to chat history
      const newChatHistory = [...chatHistory, { role: 'user', content: prompt }]
      setChatHistory(newChatHistory)
      
      // Call the new dashboard API - Robust authentication handling
      const token = localStorage.getItem('token')
      const authToken = localStorage.getItem('authToken') // Alternative token name
      const jwtToken = localStorage.getItem('jwt') // Another alternative
      
      const finalToken = token || authToken || jwtToken
      console.log('Token search results:', {
        token: token ? 'Found' : 'Not found',
        authToken: authToken ? 'Found' : 'Not found', 
        jwtToken: jwtToken ? 'Found' : 'Not found',
        finalToken: finalToken ? 'Using token' : 'No token available'
      })
      
      if (!finalToken) {
        throw new Error('No authentication token found. Please log in again.')
      }
      
      // Also try to get user info to validate token
      const userStr = localStorage.getItem('user')
      const user = userStr ? JSON.parse(userStr) : null
      console.log('User info:', user ? `Logged in as ${user.username || user.email || 'unknown'}` : 'No user info')
      
      // Debug: Log the data being sent
      const requestData = {
        user_prompt: prompt,
        dataset_selection: {
          source_ids: selectedDatasets?.source_ids || [],
          transformed_ids: selectedDatasets?.transformed_ids || []
        },
        user_context: {
          chat_history: newChatHistory
        }
      }
      console.log('Dashboard generation request data:', requestData)
      console.log('Selected datasets:', selectedDatasets)
      
      const response = await fetch('/api/dashboards/generate-templates', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${finalToken}`
        },
        body: JSON.stringify({
          user_prompt: prompt,
          dataset_selection: {
            source_ids: selectedDatasets?.source_ids || [],
            transformed_ids: selectedDatasets?.transformed_ids || []
          },
          user_context: {
            chat_history: newChatHistory
          }
        }),
      })
      
      if (!response.ok) {
        if (response.status === 401) {
          // Handle authentication failure
          console.error('Authentication failed - clearing tokens and redirecting')
          localStorage.removeItem('token')
          localStorage.removeItem('authToken')
          localStorage.removeItem('jwt')
          localStorage.removeItem('user')
          throw new Error('Authentication failed. Please log in again and try dashboard generation.')
        }
        
        // Try to get more detailed error from response
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`
        try {
          const errorData = await response.json()
          if (errorData.detail) {
            errorMessage = errorData.detail
          }
        } catch (e) {
          // Fallback to status text
        }
        throw new Error(errorMessage)
      }
      
      const result = await response.json()
      
      if (result.can_generate) {
        // Add AI response to chat history
        const aiResponse = {
          role: 'assistant',
          content: `I've generated ${result.templates.length} dashboard templates based on your request. Each template is designed with your selected datasets and follows modern design principles.`
        }
        setChatHistory([...newChatHistory, aiResponse])
        
        // Pass templates to parent component
        onTemplatesGenerated?.(result.templates)
        
        // Clear the prompt
        setPrompt('')
      } else {
        // Handle generation failure
        setError(result.message || 'Failed to generate templates')
        const errorResponse = {
          role: 'assistant', 
          content: `I couldn't generate templates: ${result.message}. Please ensure your datasets contain valid data.`
        }
        setChatHistory([...newChatHistory, errorResponse])
      }
      
    } catch (error) {
      console.error('Template generation failed:', error)
      setError(`Generation failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
      
      const errorResponse = {
        role: 'assistant',
        content: 'Sorry, I encountered an error while generating your dashboard templates. Please try again.'
      }
      setChatHistory([...chatHistory, { role: 'user', content: prompt }, errorResponse])
    } finally {
      setIsGenerating(false)
    }
  }

  const handleSuggestedPrompt = (suggestion: string) => {
    setPrompt(suggestion)
  }

  const clearChat = () => {
    setChatHistory([])
    setPrompt('')
    setError(null)
  }

  return (
    <Card className="mt-6">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bot className="w-5 h-5" />
          AI Dashboard Assistant
          <Badge variant="secondary" className="ml-auto">
            Powered by GenAI
          </Badge>
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Describe your ideal dashboard and I'll generate modern, interactive templates using your selected data
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        
        {/* Chat History */}
        {chatHistory.length > 0 && (
          <div className="bg-muted/30 rounded-lg p-4 max-h-60 overflow-y-auto space-y-3">
            {chatHistory.map((message, index) => (
              <div 
                key={index}
                className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                  message.role === 'user' 
                    ? 'bg-primary text-primary-foreground ml-auto' 
                    : 'bg-card border'
                }`}>
                  {message.role === 'assistant' && <Bot className="w-4 h-4 inline mr-2" />}
                  {message.content}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-3">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {/* Suggested Prompts */}
        {chatHistory.length === 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Lightbulb className="w-4 h-4" />
              Try these suggestions:
            </div>
            <div className="flex flex-wrap gap-2">
              {suggestedPrompts.slice(0, 3).map((suggestion, index) => (
                <Button
                  key={index}
                  variant="outline"
                  size="sm"
                  className="text-xs h-auto py-1 px-2"
                  onClick={() => handleSuggestedPrompt(suggestion)}
                  disabled={!canProceed}
                >
                  {suggestion}
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="space-y-3">
          <Textarea
            placeholder={
              canProceed 
                ? "Describe your ideal dashboard... (e.g., 'Create a sales performance dashboard with revenue trends and KPIs')"
                : "Select valid datasets first to enable AI generation"
            }
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={!canProceed || isGenerating}
            className="min-h-[80px] resize-none"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                handleGenerateTemplates()
              }
            }}
          />
          
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {!canProceed && (
                <p className="text-sm text-muted-foreground">
                  {!selectedDatasets || (selectedDatasets.source_ids.length === 0 && selectedDatasets.transformed_ids.length === 0)
                    ? "Select datasets to get started"
                    : "Datasets are being validated..."
                  }
                </p>
              )}
              
              {canProceed && validation && (
                <p className="text-sm text-green-600">
                  Ready with {validation.total_records?.toLocaleString()} records from {validation.results?.length} dataset(s)
                </p>
              )}
            </div>
            
            <div className="flex items-center gap-2">
              {chatHistory.length > 0 && (
                <Button 
                  variant="ghost" 
                  size="sm"
                  onClick={clearChat}
                  disabled={isGenerating}
                >
                  Clear Chat
                </Button>
              )}
              
              <Button 
                onClick={handleGenerateTemplates}
                disabled={!canProceed || !prompt.trim() || isGenerating}
                className="gap-2"
              >
                {isGenerating ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Generate Templates
                  </>
                )}
              </Button>
            </div>
          </div>
          
          {canProceed && (
            <p className="text-xs text-muted-foreground">
              Press Cmd/Ctrl + Enter to generate, or click the button above
            </p>
          )}
        </div>

        {/* AI Capabilities Info */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <Bot className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
            <div className="text-sm">
              <p className="font-medium text-blue-900">AI Assistant Capabilities:</p>
              <ul className="text-blue-700 mt-1 space-y-1 text-xs">
                <li>• Analyzes your dataset schemas to recommend optimal chart types</li>
                <li>• Generates 3-5 modern, interactive dashboard templates</li>
                <li>• Ensures theme consistency with your existing app design</li>
                <li>• Only uses real data fields - no dummy data ever</li>
              </ul>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
