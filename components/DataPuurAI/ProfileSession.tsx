"use client"

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Send, Bot, User, AlertCircle, CheckCircle2, XCircle, Play, Download, Wand2 } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { CodeBlock } from '../ui/code-block'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Progress } from '@/components/ui/progress'

interface ProfileSessionProps {
  sessionId: string
  onClose?: () => void
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  metadata?: {
    script?: string
    [key: string]: any
  }
}

interface QualityIssue {
  type: string
  column?: string
  severity: 'high' | 'medium' | 'low'
  description: string
  suggestion: string
}

interface Suggestion {
  type?: string
  suggestion: string
  priority?: string | number
}

interface SessionData {
  id: string
  file_id: string
  file_name: string
  profile_id: string
  status: string
  session_type: string
  created_at: string
  updated_at: string
  profile_summary: {
    text: string
  }
  data_quality_issues: QualityIssue[]
  improvement_suggestions: string[]
  messages: Message[]
}

interface ExecutionJob {
  id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  output?: string
  error?: string
  result?: any
  progress?: number
}

// Type guard for suggestion objects
function isSuggestionObject(obj: any): obj is Suggestion {
  return typeof obj === 'object' && obj !== null && typeof obj.suggestion === 'string';
}

export function ProfileSession({ sessionId, onClose }: ProfileSessionProps) {
  const [session, setSession] = useState<SessionData | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [qualityIssues, setQualityIssues] = useState<QualityIssue[]>([])
  const [suggestions, setSuggestions] = useState<(Suggestion | string)[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [activeTab, setActiveTab] = useState('chat')
  const [executingScript, setExecutingScript] = useState(false)
  const [currentJob, setCurrentJob] = useState<ExecutionJob | null>(null)
  const [showJobDialog, setShowJobDialog] = useState(false)
  const [creatingTransformation, setCreatingTransformation] = useState(false)
  const { toast } = useToast()

  useEffect(() => {
    fetchSessionData()
  }, [sessionId])

  const fetchSessionData = async () => {
    try {
      console.log(`===DEBUG=== Fetching token data for sessionId: ${sessionId}`)

      const token = localStorage.getItem('token')
      const response = await fetch(`/api/datapuur-ai/sessions/${sessionId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) throw new Error('Failed to fetch session data')
      
      const data = await response.json()
      setSession(data)
      
      // Fetch messages if any exist
      if (Array.isArray(data.messages)) {
        console.log(`===DEBUG=== Found ${data.messages.length} messages`)
        setMessages(data.messages)
      } else {
        console.log(`===DEBUG=== No messages found or invalid format: ${typeof data.messages}`)
        setMessages([])
      }
      
      // Fetch quality issues and suggestions if available
      if (Array.isArray(data.data_quality_issues)) {
        console.log(`===DEBUG=== Found ${data.data_quality_issues.length} quality issues`)
        setQualityIssues(data.data_quality_issues)
      } else {
        console.log(`===DEBUG=== No quality issues found or invalid format: ${typeof data.data_quality_issues}`)
        setQualityIssues([])
      }
      
      if (Array.isArray(data.improvement_suggestions)) {
        console.log(`===DEBUG=== Found ${data.improvement_suggestions.length} improvement suggestions`)
        setSuggestions(data.improvement_suggestions)
      } else {
        console.log(`===DEBUG=== No improvement suggestions found or invalid format: ${typeof data.improvement_suggestions}`)
        setSuggestions([])
      }
      
      // Debug log the data structure
      console.log('===DEBUG=== Profile session data (truncated):', JSON.stringify(data).substring(0, 1000) + '...')
    } catch (error: any) {
      console.error('===DEBUG=== Error in fetchSessionData:', error)
      toast({
        title: "Error",
        description: error.message || "Failed to load session data",
        variant: "destructive"
      })
    } finally {
      setLoading(false)
    }
  }

  const executeScript = async (script: string, jobType: 'profile' | 'transformation' = 'profile') => {
    setExecutingScript(true)
    setShowJobDialog(true)
    
    try {
      const response = await fetch('/api/datapuur-ai/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          script,
          file_path: session?.file_name || '',
          job_type: jobType
        })
      })

      if (!response.ok) throw new Error('Failed to execute script')
      
      const data = await response.json()
      setCurrentJob({
        id: data.job_id,
        status: 'running',
        progress: 0
      })
      
      // Start polling for job status
      pollJobStatus(data.job_id)
    } catch (error) {
      toast({
        title: "Execution Error",
        description: "Failed to execute script",
        variant: "destructive"
      })
      setShowJobDialog(false)
    } finally {
      setExecutingScript(false)
    }
  }

  const pollJobStatus = async (jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/datapuur-ai/jobs/${jobId}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        
        if (!response.ok) throw new Error('Failed to get job status')
        
        const job = await response.json()
        setCurrentJob(job)
        
        if (job.status === 'completed' || job.status === 'failed') {
          clearInterval(interval)
          
          if (job.status === 'completed') {
            toast({
              title: "Script Executed",
              description: "Script execution completed successfully"
            })
          } else {
            toast({
              title: "Execution Failed",
              description: job.error || "Script execution failed",
              variant: "destructive"
            })
          }
        }
      } catch (error) {
        clearInterval(interval)
        toast({
          title: "Error",
          description: "Failed to get job status",
          variant: "destructive"
        })
      }
    }, 2000) // Poll every 2 seconds
  }

  const createTransformationPlan = async () => {
    if (!session) return
    
    setCreatingTransformation(true)
    
    try {
      const response = await fetch('/api/datapuur-ai/transformations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          profile_session_id: sessionId,
          name: `${session.file_name} - Data Quality Improvements`,
          description: "Automatically generated transformation plan based on profile analysis"
        })
      })

      if (!response.ok) throw new Error('Failed to create transformation plan')
      
      const data = await response.json()
      
      toast({
        title: "Transformation Plan Created",
        description: "Opening transformation workspace..."
      })
      
      // Store the transformation plan ID in localStorage for client-side routing
      localStorage.setItem('current_transformation_id', data.id)
      
      // Use client-side navigation which works better with static exports
      window.location.href = '/datapuur/ai-transformation/dynamic'
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to create transformation plan",
        variant: "destructive"
      })
    } finally {
      setCreatingTransformation(false)
    }
  }

  const downloadTransformedData = async () => {
    if (!currentJob || !currentJob.result?.output_file) return
    
    try {
      const response = await fetch(`/api/datapuur-ai/download/${currentJob.result.output_file}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      
      if (!response.ok) throw new Error('Failed to download file')
      
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = currentJob.result.output_file
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      toast({
        title: "Download Error",
        description: "Failed to download transformed data",
        variant: "destructive"
      })
    }
  }

  const sendMessage = async () => {
    if (!input.trim() || sending) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setSending(true)

    try {
      const response = await fetch(`/api/datapuur-ai/sessions/${sessionId}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ message: input })
      })
      
      if (!response.ok) throw new Error('Failed to send message')
      
      const data = await response.json()
      console.log('Chat response data:', data)
      
      // Handle the message from backend format
      const assistantMessage: Message = {
        id: data.message.id || Date.now().toString() + '-assistant',
        role: 'assistant',
        content: data.message.content,
        timestamp: data.message.timestamp || new Date().toISOString(),
        metadata: data.message.metadata || {}
      }
      
      setMessages(prev => [...prev, assistantMessage])
      
      // Update quality issues and suggestions if provided
      if (data.improvement_suggestions) {
        setSuggestions(data.improvement_suggestions)
      }
      
      // Update quality issues if provided
      if (data.data_quality_issues) {
        setQualityIssues(data.data_quality_issues)
      }
      
      // Log the response data structure for debugging
      console.log('Chat response structure:', JSON.stringify(Object.keys(data), null, 2))
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to send message",
        variant: "destructive"
      })
    } finally {
      setSending(false)
    }
  }

  if (loading) {
    return (
      <Card className="h-full flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </Card>
    )
  }

  if (!session) {
    return (
      <Card className="h-full">
        <CardContent className="flex items-center justify-center h-full">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>Session not found</AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    )
  }

  return (
    <>
      <Card className="h-full flex flex-col max-h-[calc(100vh-200px)] overflow-hidden">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>AI Profile Analysis</CardTitle>
              <CardDescription>
                {session.file_name || 'Unknown file'}
                {/* Quality score has been removed from the interface */}
              </CardDescription>
            </div>
            <Badge variant={session.status === 'active' ? 'default' : 'secondary'}>
              {session.status}
            </Badge>
          </div>
        </CardHeader>
        
        <CardContent className="flex-1 flex flex-col overflow-hidden">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="chat">Chat</TabsTrigger>
              <TabsTrigger value="issues">Quality Issues</TabsTrigger>
              <TabsTrigger value="suggestions">Suggestions</TabsTrigger>
            </TabsList>
            
            <TabsContent value="chat" className="flex-1 flex flex-col overflow-hidden h-full">
              <ScrollArea className="flex-1 pr-4 mb-4 max-h-[calc(100%-60px)] overflow-y-auto">
                <div className="space-y-4">
                  {messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex gap-3 ${
                        message.role === 'user' ? 'justify-end' : 'justify-start'
                      }`}
                    >
                      <div
                        className={`flex gap-3 max-w-[80%] ${
                          message.role === 'user' ? 'flex-row-reverse' : 'flex-row'
                        }`}
                      >
                        <div className="flex-shrink-0">
                          {message.role === 'user' ? (
                            <User className="h-8 w-8 rounded-full bg-primary/10 p-1.5" />
                          ) : (
                            <Bot className="h-8 w-8 rounded-full bg-primary/10 p-1.5" />
                          )}
                        </div>
                        <div className="space-y-2">
                          <Card>
                            <CardContent className="p-3">
                              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                            </CardContent>
                          </Card>
                          {message.metadata?.script && (
                            <Card>
                              <CardHeader className="p-3 pb-2">
                                <div className="flex items-center justify-between">
                                  <CardTitle className="text-sm">Generated Script</CardTitle>
                                  <Button
                                    size="sm"
                                    onClick={() => executeScript(message.metadata!.script!)}
                                    disabled={executingScript}
                                  >
                                    {executingScript ? (
                                      <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : (
                                      <Play className="h-4 w-4" />
                                    )}
                                    Execute
                                  </Button>
                                </div>
                              </CardHeader>
                              <CardContent className="p-3 pt-0">
                                <CodeBlock code={message.metadata.script} language="python" />
                              </CardContent>
                            </Card>
                          )}
                          <p className="text-xs text-muted-foreground">
                            {new Date(message.timestamp).toLocaleTimeString()}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
              
              <div className="flex gap-2">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                  placeholder="Ask about your data or request script generation..."
                  disabled={sending}
                />
                <Button onClick={sendMessage} disabled={sending || !input.trim()}>
                  {sending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </TabsContent>
            
            <TabsContent value="issues" className="flex-1 pt-4">
              {qualityIssues.length > 0 ? (
                <>
                  <div className="flex justify-between items-center">
                    <h3 className="text-lg font-semibold">Detected Quality Issues</h3>
                    <Button
                      onClick={createTransformationPlan}
                      disabled={creatingTransformation}
                      variant="outline"
                    >
                      {creatingTransformation ? (
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      ) : (
                        <Wand2 className="h-4 w-4 mr-2" />
                      )}
                      Create Transformation Plan
                    </Button>
                  </div>
                  <ScrollArea className="flex-1">
                    <div className="space-y-3">
                      {qualityIssues.map((issue, index) => (
                        <Card key={index}>
                          <CardHeader className="pb-3">
                            <div className="flex items-center justify-between">
                              <CardTitle className="text-sm font-medium">
                                {issue.type}
                                {issue.column && (
                                  <span className="text-muted-foreground ml-2">
                                    ({issue.column})
                                  </span>
                                )}
                              </CardTitle>
                              <Badge variant={
                                issue.severity === 'high' ? 'destructive' :
                                issue.severity === 'medium' ? 'default' : 'secondary'
                              }>
                                {issue.severity}
                              </Badge>
                            </div>
                          </CardHeader>
                          <CardContent className="space-y-2">
                            <p className="text-sm text-muted-foreground">{issue.description}</p>
                            <div className="p-3 bg-muted rounded-md">
                              <p className="text-sm font-medium mb-1">Suggestion:</p>
                              <p className="text-sm">{issue.suggestion}</p>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </ScrollArea>
                </>
              ) : (
                <Alert className="mt-0">
                  <CheckCircle2 className="h-4 w-4" />
                  <AlertDescription>No quality issues detected</AlertDescription>
                </Alert>
              )}
            </TabsContent>
            
            <TabsContent value="suggestions" className="flex-1 space-y-2">
              {suggestions.length > 0 ? (
                <>
                  <div className="flex justify-between items-center">
                    <h3 className="text-lg font-semibold">Improvement Suggestions</h3>
                    <Button
                      onClick={createTransformationPlan}
                      disabled={creatingTransformation}
                      variant="outline"
                    >
                      {creatingTransformation ? (
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      ) : (
                        <Wand2 className="h-4 w-4 mr-2" />
                      )}
                      Create Transformation Plan
                    </Button>
                  </div>
                  <ScrollArea className="flex-1">
                    <div className="space-y-3">
                      {suggestions.map((suggestion, index) => (
                        <Card key={index}>
                          <CardContent className="p-4">
                            <div className="space-y-2">
                              {typeof suggestion === 'string' ? (
                                <p className="text-sm">{suggestion}</p>
                              ) : isSuggestionObject(suggestion) ? (
                                <>
                                  {suggestion.type && (
                                    <p className="text-xs text-muted-foreground uppercase">{suggestion.type}</p>
                                  )}
                                  <p className="text-sm">{suggestion.suggestion}</p>
                                  {suggestion.priority && (
                                    <div className="flex items-center mt-1">
                                      <span className="text-xs font-medium bg-muted px-2 py-0.5 rounded-full">
                                        Priority: {suggestion.priority}
                                      </span>
                                    </div>
                                  )}
                                </>
                              ) : (
                                <p className="text-sm">Invalid suggestion format</p>
                              )}
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </ScrollArea>
                </>
              ) : (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>No suggestions available yet</AlertDescription>
                </Alert>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Script Execution Dialog */}
      <Dialog open={showJobDialog} onOpenChange={setShowJobDialog}>
        <DialogContent className="sm:max-w-[625px]">
          <DialogHeader>
            <DialogTitle>Script Execution</DialogTitle>
            <DialogDescription>
              {currentJob?.status === 'running' ? 'Your script is being executed...' :
               currentJob?.status === 'completed' ? 'Script execution completed successfully!' :
               currentJob?.status === 'failed' ? 'Script execution failed' :
               'Preparing to execute script...'}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            {currentJob && (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Status</span>
                  <Badge variant={
                    currentJob.status === 'completed' ? 'default' :
                    currentJob.status === 'failed' ? 'destructive' :
                    'secondary'
                  }>
                    {currentJob.status}
                  </Badge>
                </div>
                
                {currentJob.status === 'running' && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span>Progress</span>
                      <span>{currentJob.progress || 0}%</span>
                    </div>
                    <Progress value={currentJob.progress || 0} />
                  </div>
                )}
                
                {currentJob.output && (
                  <div className="space-y-2">
                    <h4 className="text-sm font-medium">Output</h4>
                    <ScrollArea className="h-[200px] w-full rounded-md border p-3">
                      <pre className="text-xs">{currentJob.output}</pre>
                    </ScrollArea>
                  </div>
                )}
                
                {currentJob.error && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{currentJob.error}</AlertDescription>
                  </Alert>
                )}
                
                {currentJob.result?.output_file && (
                  <Alert>
                    <CheckCircle2 className="h-4 w-4" />
                    <AlertDescription>
                      Transformed data saved as: {currentJob.result.output_file}
                    </AlertDescription>
                  </Alert>
                )}
              </>
            )}
          </div>
          
          <DialogFooter>
            {currentJob?.status === 'completed' && currentJob.result?.output_file && (
              <Button onClick={downloadTransformedData} variant="outline">
                <Download className="h-4 w-4 mr-2" />
                Download Transformed Data
              </Button>
            )}
            <Button onClick={() => setShowJobDialog(false)}>
              {currentJob?.status === 'running' ? 'Run in Background' : 'Close'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
