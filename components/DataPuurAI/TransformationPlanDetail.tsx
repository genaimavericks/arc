"use client"

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { 
  Tabs, 
  TabsContent, 
  TabsList, 
  TabsTrigger 
} from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/components/ui/use-toast'
import { formatDate } from '@/lib/utils'
import { 
  Loader2, 
  Play, 
  RefreshCw, 
  ArrowDown, 
  FileSpreadsheet, 
  ArrowBigDown, 
  CheckCircle, 
  XCircle 
} from 'lucide-react'
import { TransformationPlan, TransformationStep } from '@/lib/datapuur-types'

interface TransformationPlanDetailProps {
  planId: string
}

export function TransformationPlanDetail({ planId }: TransformationPlanDetailProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [plan, setPlan] = useState<TransformationPlan | null>(null)
  const [executionLogs, setExecutionLogs] = useState<string[]>([])
  const [activeTab, setActiveTab] = useState('steps')
  const router = useRouter()
  const { toast } = useToast()

  const fetchPlanDetails = async () => {
    try {
      setIsLoading(true)
      const response = await fetch(`/api/datapuur-ai/transformation-plans/${planId}`)
      if (!response.ok) {
        throw new Error('Failed to fetch transformation plan')
      }
      
      const data = await response.json()
      setPlan(data)
      
      // Get execution logs if available from job
      if (data.job_id && data.status === "completed") {
        const jobResponse = await fetch(`/api/datapuur-ai/jobs/${data.job_id}`)
        if (jobResponse.ok) {
          const jobData = await jobResponse.json()
          if (jobData.result && jobData.result.execution_logs) {
            setExecutionLogs(jobData.result.execution_logs)
          }
        }
      }
    } catch (error) {
      console.error('Error fetching plan details:', error)
      toast({
        title: "Error",
        description: "Failed to load transformation plan. Please try again.",
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
    }
  }
  
  useEffect(() => {
    fetchPlanDetails()
  }, [planId])
  
  const handleExecutePlan = async () => {
    try {
      const response = await fetch(`/api/datapuur-ai/transformation-plans/${planId}/execute`, {
        method: 'POST'
      })
      
      if (!response.ok) {
        throw new Error('Failed to execute transformation plan')
      }
      
      toast({
        title: "Transformation Started",
        description: "The transformation job has been started. You can monitor progress here.",
      })
      
      // Refresh the plan details
      fetchPlanDetails()
      
    } catch (error) {
      console.error('Error executing transformation plan:', error)
      toast({
        title: "Error",
        description: "Failed to execute transformation plan. Please try again.",
        variant: "destructive"
      })
    }
  }
  
  const handleViewDataset = () => {
    if (plan && plan.output_file_path) {
      router.push(`/datapuur/data-catalog?datasetId=${encodeURIComponent(plan.output_file_path)}`)
    }
  }
  
  // Helper function to render step badge
  const renderStepBadge = (index: number, totalSteps: number) => {
    return (
      <Badge variant="outline" className="text-xs">
        Step {index + 1} of {totalSteps}
      </Badge>
    )
  }
  
  // Helper function to render status badge
  const renderStatusBadge = (status: string) => {
    let variant: "default" | "secondary" | "outline" | "destructive" = "outline"
    
    switch (status) {
      case "completed":
        variant = "default"
        break
      case "running":
        variant = "secondary"
        break
      case "failed":
        variant = "destructive"
        break
      default:
        variant = "outline"
    }
    
    return <Badge variant={variant}>{status}</Badge>
  }
  
  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-2">Loading plan details...</span>
      </div>
    )
  }
  
  if (!plan) {
    return (
      <div className="text-center p-6">
        <XCircle className="h-12 w-12 mx-auto text-destructive mb-4" />
        <h3 className="text-lg font-medium mb-2">Plan Not Found</h3>
        <p className="text-muted-foreground mb-4">
          The requested transformation plan could not be found.
        </p>
        <Button onClick={() => router.push('/datapuur/ai-transformation')}>
          Back to Transformation Plans
        </Button>
      </div>
    )
  }
  
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">{plan.name}</h2>
          <div className="flex items-center space-x-2 mt-1">
            <p className="text-muted-foreground">
              Created {formatDate(new Date(plan.created_at))}
            </p>
            {renderStatusBadge(plan.status)}
          </div>
        </div>
        
        <div className="flex space-x-2">
          {plan.status !== "running" && (
            <Button
              onClick={handleExecutePlan}
              disabled={plan.status === "running"}
            >
              {plan.status === "completed" ? (
                <RefreshCw className="h-4 w-4 mr-2" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              {plan.status === "completed" ? "Re-execute" : "Execute Plan"}
            </Button>
          )}
          
          {plan.status === "completed" && plan.output_file_path && (
            <Button variant="outline" onClick={handleViewDataset}>
              <FileSpreadsheet className="h-4 w-4 mr-2" />
              View Dataset
            </Button>
          )}
        </div>
      </div>
      
      {plan.description && (
        <Card>
          <CardContent className="pt-6">
            <p>{plan.description}</p>
          </CardContent>
        </Card>
      )}
      
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="steps">Transformation Steps</TabsTrigger>
          <TabsTrigger value="execution">Execution Logs</TabsTrigger>
        </TabsList>
        
        <TabsContent value="steps">
          <div className="space-y-4 mt-4">
            {plan.transformation_steps.map((step, index) => (
              <Card key={index}>
                <CardHeader className="pb-2">
                  <div className="flex justify-between">
                    <CardTitle className="text-lg">{step.operation}</CardTitle>
                    {renderStepBadge(index, plan.transformation_steps.length)}
                  </div>
                  <CardDescription>
                    {step.description}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="bg-slate-100 dark:bg-slate-900 rounded p-3 text-sm font-mono overflow-auto max-h-32">
                    <pre>{JSON.stringify(step.parameters, null, 2)}</pre>
                  </div>
                </CardContent>
              </Card>
            ))}
            
            {plan.transformation_steps.length === 0 && (
              <Card>
                <CardContent className="py-6 text-center">
                  <p className="text-muted-foreground">No transformation steps defined.</p>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>
        
        <TabsContent value="execution">
          <div className="mt-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg">Execution Logs</CardTitle>
                <CardDescription>
                  {plan.status === "completed" 
                    ? "Logs from the last execution" 
                    : "Execute the plan to see logs"}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {executionLogs.length > 0 ? (
                  <div className="bg-black text-green-400 p-4 rounded overflow-auto max-h-96 font-mono text-sm">
                    {executionLogs.map((log, i) => (
                      <div key={i} className="whitespace-pre-wrap pb-1">
                        {log}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-center text-muted-foreground py-4">
                    {plan.status === "completed" 
                      ? "No execution logs available." 
                      : "Execute this plan to see logs."}
                  </p>
                )}
              </CardContent>
            </Card>
            
            {plan.status === "completed" && plan.output_file_path && (
              <Card className="mt-4">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg">Transformation Result</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">Output File</p>
                      <p className="text-muted-foreground">
                        {plan.output_file_path}
                      </p>
                    </div>
                    <CheckCircle className="h-6 w-6 text-green-500" />
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
