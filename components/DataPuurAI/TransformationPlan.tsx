"use client"

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { 
  Loader2, Send, Bot, User, AlertCircle, CheckCircle2, 
  Play, Pause, Download, RefreshCw, FileCode
} from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { CodeBlock } from '@/components/ui/code-block'

interface TransformationPlanProps {
  sessionId: string
  onClose?: () => void
  transformationPlan?: TransformationPlanData
}

interface TransformationStep {
  order: number
  operation: string
  description: string
  parameters: Record<string, any>
}

interface TransformationPlanData {
  id: string
  profile_session_id: string
  name: string
  description: string
  status: string
  transformation_steps: TransformationStep[]
  expected_improvements: Record<string, any> // Changed from string to any to handle nested objects
  transformation_script?: string
  created_at: string
  updated_at: string
}

interface JobStatus {
  id: string
  job_type: string
  status: string
  progress: number
  message?: string
  result?: Record<string, any>
  error?: string
  created_at: string
  started_at?: string
  completed_at?: string
}

export function TransformationPlan({ sessionId, onClose, transformationPlan }: TransformationPlanProps) {
  const router = useRouter()
  const [plan, setPlan] = useState<TransformationPlanData | null>(transformationPlan || null)
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [planName, setPlanName] = useState('Data Quality Improvement Plan')
  const [planDescription, setPlanDescription] = useState('')
  const [message, setMessage] = useState('')
  const [sending, setSending] = useState(false)
  const [currentJob, setCurrentJob] = useState<JobStatus | null>(null)
  const [polling, setPolling] = useState(false)
  const { toast } = useToast()

  const createPlan = async () => {
    setCreating(true)
    try {
      const response = await fetch('/api/datapuur-ai/transformations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          profile_session_id: sessionId,
          name: planName,
          description: planDescription
        })
      })

      if (!response.ok) throw new Error('Failed to create transformation plan')
      
      const data = await response.json()
      setPlan(data)
      
      toast({
        title: "Success",
        description: "Transformation plan created successfully"
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to create transformation plan",
        variant: "destructive"
      })
    } finally {
      setCreating(false)
    }
  }

  const executeScript = async () => {
    if (!plan || !plan.transformation_script) return

    try {
      const response = await fetch('/api/datapuur-ai/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          script: plan.transformation_script,
          job_type: 'transformation',
          plan_id: plan.id
        })
      })

      // Handle permission denied errors
      if (response.status === 403) {
        toast({
          title: "Permission Denied",
          description: "You don't have access to execute transformation scripts.",
          variant: "destructive"
        })
        return
      }
      
      if (!response.ok) throw new Error('Failed to execute script')
      
      const data = await response.json()
      console.log('Job execution response:', data)
      
      // Ensure we have a valid job_id before setting current job
      if (data && data.job_id) {
        setCurrentJob({
          id: data.job_id,
          job_type: 'transformation',
          status: data.status || 'pending',
          progress: 0,
          message: data.message || 'Script execution started',
          created_at: new Date().toISOString()
        })
        setPolling(true)
        
        toast({
          title: "Execution Started",
          description: "Transformation script is running..."
        })
      } else {
        throw new Error('Invalid job response: missing job_id')
      }
    } catch (error) {
      console.error('Script execution error:', error)
      toast({
        title: "Error",
        description: "Failed to execute transformation script",
        variant: "destructive"
      })
    }
  }

  const checkJobStatus = async (jobId: string) => {
    try {
      const response = await fetch(`/api/datapuur-ai/jobs/${jobId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })

      if (!response.ok) throw new Error('Failed to check job status')
      
      const data = await response.json()
      setCurrentJob(data)

      if (data.status === 'completed' || data.status === 'failed') {
        setPolling(false)
        
        if (data.status === 'completed') {
          toast({
            title: "Transformation Complete",
            description: "Your data has been successfully transformed"
          })
        } else {
          toast({
            title: "Transformation Failed",
            description: data.error || "An error occurred during transformation",
            variant: "destructive"
          })
        }
      }
    } catch (error) {
      console.error('Error checking job status:', error)
    }
  }

  useEffect(() => {
    if (polling && currentJob) {
      const interval = setInterval(() => {
        checkJobStatus(currentJob.id)
      }, 2000)

      return () => clearInterval(interval)
    }
  }, [polling, currentJob])

  const downloadScript = () => {
    if (!plan || !plan.transformation_script) return

    const blob = new Blob([plan.transformation_script], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `transformation_${plan.id}.py`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  if (!plan) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle>Create Transformation Plan</CardTitle>
          <CardDescription>
            Generate an AI-powered transformation plan for your data
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Plan Name</label>
            <Input
              value={planName}
              onChange={(e) => setPlanName(e.target.value)}
              placeholder="Enter plan name"
            />
          </div>
          
          <div className="space-y-2">
            <label className="text-sm font-medium">Description (Optional)</label>
            <Textarea
              value={planDescription}
              onChange={(e) => setPlanDescription(e.target.value)}
              placeholder="Describe your transformation goals..."
              rows={3}
            />
          </div>

          <Button 
            onClick={createPlan} 
            disabled={creating || !planName.trim()}
            className="w-full"
          >
            {creating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating Plan...
              </>
            ) : (
              'Create Transformation Plan'
            )}
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>{plan.name}</CardTitle>
            <CardDescription>{plan.description}</CardDescription>
          </div>
          <div className="flex items-center gap-3">
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => router.push('/datapuur/data-catalog')}
            >
              View Catalog
            </Button>
            <Badge variant={plan.status === 'completed' ? 'default' : 'secondary'}>
              {plan.status}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col space-y-4">
        <Tabs defaultValue="steps" className="flex-1 flex flex-col">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="steps">Steps</TabsTrigger>
            <TabsTrigger value="script">Script</TabsTrigger>
            <TabsTrigger value="execution">Execution</TabsTrigger>
            <TabsTrigger value="results">Results</TabsTrigger>
          </TabsList>
          
          <TabsContent value="steps" className="space-y-4">
            <div className="space-y-3">
              {plan.transformation_steps.map((step) => (
                <Card key={step.order}>
                  <CardContent className="pt-4">
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-sm font-medium">
                        {step.order}
                      </div>
                      <div className="flex-1 space-y-1">
                        <h4 className="font-medium">{step.description}</h4>
                        <p className="text-sm text-muted-foreground">
                          Operation: {step.operation}
                        </p>
                        {Object.keys(step.parameters).length > 0 && (
                          <div className="mt-2">
                            <p className="text-xs font-medium mb-1">Parameters:</p>
                            <pre className="text-xs bg-muted p-2 rounded">
                              {JSON.stringify(step.parameters, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Expected Improvements</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {Object.entries(plan.expected_improvements).map(([key, value]) => {
                    // Check if value is a nested object with current/post_transformation keys
                    const isNestedObject = 
                      typeof value === 'object' && 
                      value !== null &&
                      ('current' in value || 'post_transformation' in value);
                    
                    if (isNestedObject) {
                      return (
                        <div key={key} className="border rounded-md p-3">
                          <div className="font-medium mb-2">{key.replace(/_/g, ' ')}</div>
                          <div className="grid grid-cols-2 gap-2 text-sm">
                            {value.current && (
                              <div className="space-y-1">
                                <div className="text-muted-foreground">Current:</div>
                                <div>{String(value.current)}</div>
                              </div>
                            )}
                            {value.post_transformation && (
                              <div className="space-y-1">
                                <div className="text-muted-foreground">After Transformation:</div>
                                <div>{String(value.post_transformation)}</div>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    } else {
                      // Handle simple string values
                      return (
                        <div key={key} className="flex justify-between border-b pb-2">
                          <span className="text-sm text-muted-foreground">
                            {key.replace(/_/g, ' ')}:
                          </span>
                          <span className="text-sm font-medium">{String(value)}</span>
                        </div>
                      );
                    }
                  })}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="script" className="flex-1 flex flex-col space-y-4">
            {plan.transformation_script ? (
              <>
                <div className="flex justify-end gap-2">
                  <Button size="sm" variant="outline" onClick={downloadScript}>
                    <Download className="mr-2 h-4 w-4" />
                    Download Script
                  </Button>
                  <Button size="sm" onClick={executeScript} disabled={polling}>
                    <Play className="mr-2 h-4 w-4" />
                    Execute Script
                  </Button>
                </div>
                <ScrollArea className="flex-1">
                  <CodeBlock code={plan.transformation_script} language="python" />
                </ScrollArea>
              </>
            ) : (
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>No transformation script generated yet</AlertDescription>
              </Alert>
            )}
          </TabsContent>

          <TabsContent value="execution" className="space-y-4">
            {currentJob ? (
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm">Job Status</CardTitle>
                    <Badge variant={
                      currentJob.status === 'completed' ? 'default' :
                      currentJob.status === 'failed' ? 'destructive' :
                      'secondary'
                    }>
                      {currentJob.status}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {currentJob.status === 'running' && (
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>Progress</span>
                        <span>{currentJob.progress}%</span>
                      </div>
                      <Progress value={currentJob.progress} />
                    </div>
                  )}
                  
                  {currentJob.message && (
                    <Alert>
                      <AlertDescription>{currentJob.message}</AlertDescription>
                    </Alert>
                  )}
                  
                  {currentJob.error && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>{currentJob.error}</AlertDescription>
                    </Alert>
                  )}
                  
                  <div className="text-xs text-muted-foreground space-y-1">
                    <p>Created: {new Date(currentJob.created_at).toLocaleString()}</p>
                    {currentJob.started_at && (
                      <p>Started: {new Date(currentJob.started_at).toLocaleString()}</p>
                    )}
                    {currentJob.completed_at && (
                      <p>Completed: {new Date(currentJob.completed_at).toLocaleString()}</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Alert>
                <AlertDescription>
                  No execution job running. Execute the script to start transformation.
                </AlertDescription>
              </Alert>
            )}
          </TabsContent>

          <TabsContent value="results" className="space-y-4">
            {currentJob && currentJob.status === 'completed' && currentJob.result ? (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Transformation Results</CardTitle>
                </CardHeader>
                <CardContent>
                  <pre className="text-sm bg-muted p-4 rounded overflow-auto">
                    {JSON.stringify(currentJob.result, null, 2)}
                  </pre>
                </CardContent>
              </Card>
            ) : (
              <Alert>
                <AlertDescription>
                  No results available yet. Execute the transformation to see results.
                </AlertDescription>
              </Alert>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
