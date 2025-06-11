"use client"

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { useToast } from '@/hooks/use-toast'
import { formatBytes, formatDate } from '@/lib/utils'
import { Loader2, Brain, Zap, FileSpreadsheet } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'

// Define the data source type
interface DataSource {
  id: string
  name: string
  file_path: string
  file_size: number
  row_count: number | null
  column_count: number | null
  created_at: string
  updated_at: string | null
  data_type: string
  has_profile: boolean
  dataset: string
}

export function DataSourcesList() {
  const [isLoading, setIsLoading] = useState(true)
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [transformingSourceId, setTransformingSourceId] = useState<string | null>(null)
  const router = useRouter()
  const { toast } = useToast()
  
  // Fetch data sources from the API
  const fetchDataSources = async () => {
    try {
      setIsLoading(true)
      
      // Get token from localStorage
      const token = localStorage.getItem('token')
      
      // Use the standard datapuur sources endpoint instead of the AI endpoint
      const response = await fetch(`/api/datapuur/sources?page=${page}&limit=10`, {
        headers: {
          'Authorization': token ? `Bearer ${token}` : ''
        }
      })
      
      if (!response.ok) {
        throw new Error('Failed to fetch data sources')
      }
      
      const data = await response.json()
      setDataSources(data)
      setHasMore(data.length === 10) // Assume there's more if we got a full page
      
    } catch (error) {
      console.error('Error fetching data sources:', error)
      toast({
        title: "Error",
        description: "Failed to load data sources. Please try again.",
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
    }
  }
  
  useEffect(() => {
    fetchDataSources()
  }, [page])
  
  // Navigate to AI Profile or AI Transformation
  const handleCreateProfile = (dataSource: DataSource) => {
    router.push(`/datapuur/ai-profile?file_id=${dataSource.id}&file_name=${encodeURIComponent(dataSource.name)}&file_path=${encodeURIComponent(dataSource.file_path)}`)
  }
  
  const handleCreateTransformation = async (dataSource: DataSource) => {
    // Show a warning if no profile exists, but continue anyway
    if (!dataSource.has_profile) {
      toast({
        title: "No AI Profile",
        description: "Proceeding without an AI profile. Some advanced features may be limited.",
        variant: "default"
      })
    }

    try {
      const token = localStorage.getItem('token')
      if (!token) {
        throw new Error('Authentication token not found')
      }

      // Set the current source being transformed to show spinner on button
      setTransformingSourceId(dataSource.id)
      
      // Show toast notification that transformation is being created
      toast({
        title: "Creating Transformation",
        description: "Please wait while we prepare your transformation plan..."
      })
      
      // First, check if transformation plans exist for this source
      let existingPlanId = undefined
      
      try {
        // Get the filename without extension to match source_id format
        const filenameNoExt = dataSource.id;
        
        // Use the dedicated endpoint to find transformation plans directly by source_id
        const plansResponse = await fetch(`/api/datapuur-ai/transformations/by-source/${filenameNoExt}`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        if (plansResponse.ok) {
          const plansData = await plansResponse.json()
          
          // Check if response contains transformation plans
          if (plansData.transformation_plans && plansData.transformation_plans.length > 0) {
            // Use the ID of the first plan associated with this source
            existingPlanId = plansData.transformation_plans[0].id
            console.log(`Found existing plan ID: ${existingPlanId} for source ${filenameNoExt}`)
          } else {
            console.log(`No existing transformation plans found for source ${filenameNoExt}`)
          }
        }
      } catch (error) {
        console.error('Error checking for existing plans:', error)
        // Continue with creating a new plan if the check fails
      }
      
      let planId = existingPlanId;
      
      // Only create a new draft plan if we didn't find an existing one
      if (!existingPlanId) {
        console.log("No existing plan found, creating a new draft plan")
        
        // Create a draft transformation plan using the dedicated draft endpoint
        const response = await fetch('/api/datapuur-ai/transformations/draft', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            name: `${dataSource.name} - Transformation`,
            description: "AI-powered data transformation plan",
            source_id: dataSource.id,  // Use source_id for data source reference
            profile_session_id: dataSource.has_profile ? dataSource.id : undefined,
            input_instructions: "",
            is_draft: true  // Mark as draft
          })
        })
  
        if (!response.ok) {
          throw new Error(`Failed to create transformation plan: ${response.statusText}`)
        }
  
        const data = await response.json()
        planId = data.id;
        
        toast({
          title: "Success",
          description: "Created new transformation plan. Redirecting..."
        })
      } else {
        toast({
          title: "Success",
          description: "Using existing transformation plan. Redirecting..."
        })
      }

      router.push(`/datapuur/ai-transformation?tab=create&file_id=${dataSource.id}&file_name=${encodeURIComponent(dataSource.name)}&file_path=${encodeURIComponent(dataSource.file_path)}&draft_plan_id=${planId}`)
      
      // After navigation, wait a moment and force page reload to ensure tab changes
      setTimeout(() => {
        window.location.reload()
      }, 100)
      
    } catch (error: any) {
      console.error('Error creating transformation draft:', error)
      toast({
        title: "Error",
        description: error.message || "Failed to create transformation plan",
        variant: "destructive"
      })
      
      // Don't redirect when there's an error creating the plan
      // Stay on the current page so the user can try again or choose a different action
    } finally {
      setIsLoading(false)
      setTransformingSourceId(null) // Reset the transforming source ID when operation completes
    }
  }
  
  if (isLoading && dataSources.length === 0) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-2">Loading data sources...</span>
      </div>
    )
  }
  
  if (!isLoading && dataSources.length === 0) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center p-6">
            <FileSpreadsheet className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No Data Sources Found</h3>
            <p className="text-muted-foreground mb-4">
              Upload a file in the Ingestion section to get started.
            </p>
            <Button onClick={() => router.push('/datapuur/ingestion')}>
              Go to Ingestion
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }
  
  return (
    <div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Size</TableHead>
            <TableHead>Rows</TableHead>
            <TableHead>Created</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {dataSources.map((source) => (
            <TableRow key={source.id}>
              <TableCell className="font-medium">{source.dataset}</TableCell>
              <TableCell>{formatBytes(source.file_size)}</TableCell>
              <TableCell>{source.row_count?.toLocaleString() || 'Unknown'}</TableCell>
              <TableCell>{formatDate(source.created_at)}</TableCell>
              <TableCell className="space-x-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleCreateProfile(source)}
                >
                  <Brain className="h-4 w-4 mr-1" /> AI Profile
                </Button>
                <Button 
                  size="sm"
                  variant={source.has_profile ? "default" : "secondary"}
                  onClick={() => handleCreateTransformation(source)}
                  disabled={transformingSourceId !== null} // Disable all buttons while any transformation is in progress
                >
                  {transformingSourceId === source.id ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-1 animate-spin" /> Creating...
                    </>
                  ) : (
                    <>
                      <Zap className="h-4 w-4 mr-1" /> Transform
                    </>
                  )}
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      
      <div className="flex justify-between mt-4">
        <Button 
          variant="outline" 
          onClick={() => setPage(p => Math.max(1, p - 1))}
          disabled={page === 1}
        >
          Previous
        </Button>
        <Button 
          variant="outline" 
          onClick={() => setPage(p => p + 1)}
          disabled={!hasMore}
        >
          Next
        </Button>
      </div>
    </div>
  )
}
