"use client"

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { format } from 'date-fns'
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Loader2, ArrowRight, ArrowDown, ArrowUp, PlusCircle, Trash2 } from 'lucide-react'
import { useToast } from "@/components/ui/use-toast"
import { TransformationPlan } from '@/lib/datapuur-types'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"

export function TransformationPlansList() {
  const [plans, setPlans] = useState<TransformationPlan[]>([])
  const [page, setPage] = useState(1)
  const [isLoading, setIsLoading] = useState(false)
  const [isDeleting, setIsDeleting] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [permissionError, setPermissionError] = useState<string | null>(null)
  const [hasMore, setHasMore] = useState(true)
  const itemsPerPage = 10 // Number of items per page
  const router = useRouter()
  const { toast } = useToast()
  
  // Define table columns for transformation plans
  const columns = [
    { header: "Name", accessor: "name" },
    { header: "Description", accessor: "description" },
    { header: "Status", accessor: "status" },
    { header: "Created", accessor: "created_at" },
    { header: "Actions", accessor: "actions" }
  ]

  // Function to fetch transformation plans from backend API
  const fetchTransformationPlans = async (currentPage: number) => {
    try {
      setIsLoading(true)
      setError(null)

      // Get token from localStorage for authentication
      const token = localStorage.getItem('token')
      if (!token) {
        throw new Error('Authentication token not found')
      }

      // Fetch data from backend API
      const response = await fetch(
        `/api/datapuur-ai/transformations?page=${currentPage}&limit=${itemsPerPage}`, 
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )

      if (!response.ok) {
        throw new Error(`Error fetching transformation plans: ${response.status}`)
      }

      const data = await response.json()
      
      // Handle both response formats: { plans: [...] } or direct array
      // Ensure we have an array even if the API returns null or undefined
      const newPlans = Array.isArray(data) ? data : Array.isArray(data?.plans) ? data.plans : []
      
      // Validate each plan to ensure it has required fields
      const validatedPlans = newPlans.filter((plan: any) => {
        return plan && typeof plan === 'object' && plan.id && plan.name;
      });
      
      if (currentPage === 1) {
        setPlans(validatedPlans)
      } else {
        setPlans(prevPlans => [...prevPlans, ...validatedPlans])
      }
      
      // Update hasMore based on if we got fewer items than requested
      setHasMore(validatedPlans.length === itemsPerPage)
      setPage(currentPage)
    } catch (err) {
      console.error('Error fetching transformation plans:', err)
      setError(err instanceof Error ? err.message : 'An unknown error occurred')
    } finally {
      setIsLoading(false)
    }
  }

  // Fetch transformation plans when component mounts or page changes
  useEffect(() => {
    fetchTransformationPlans(page)
  }, [page]);

  // Navigate to plan details page
  const handleViewPlan = (planId: string | number) => {
    // Store the plan ID in localStorage for access in the Create Transformation tab
    localStorage.setItem('current_transformation_id', planId.toString())
    
    // Redirect to the Create Transformation tab with the plan ID as a query parameter
    router.push(`/datapuur/ai-transformation?tab=create&draft_plan_id=${planId}`)
    
    // After navigation, wait a moment and force page reload to ensure tab changes
    setTimeout(() => {
      window.location.reload()
    }, 100)
  }

  // Handle creating a new plan
  const handleCreatePlan = () => {
    // Use tab-based navigation to the create tab within the main AI transformation page
    router.push('/datapuur/ai-transformation?tab=create')
  }

  // Format date to readable string with additional validation
  const formatDate = (dateString: string | null | undefined) => {
    try {
      // Return early if date is null/undefined/empty
      if (!dateString) {
        return 'No date';
      }
      
      // Validate the date string before attempting to format
      const date = new Date(dateString);
      
      // Check if the date is valid (not Invalid Date)
      if (isNaN(date.getTime())) {
        return 'Invalid date';
      }
      
      // Format the valid date
      return format(date, 'PPP');
    } catch (e) {
      console.error('Date formatting error:', e);
      return 'Unknown date';
    }
  }

  // Handle load more button click
  const handleLoadMore = () => {
    setPage(prevPage => prevPage + 1)
    // fetchTransformationPlans will be called by the useEffect that depends on page
  }
  
  // Handle deleting a transformation plan
  const handleDeletePlan = async (planId: string, planName: string) => {
    try {
      setIsDeleting(planId)
      
      // Get token from localStorage for authentication
      const token = localStorage.getItem('token')
      if (!token) {
        throw new Error('Authentication token not found')
      }
      
      // Call API to delete the plan
      const response = await fetch(`/api/datapuur-ai/transformations/${planId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      
      // Handle permission denied errors
      if (response.status === 403) {
        setPermissionError("Permission denied: You don't have access to delete transformation plans")
        return
      }
      
      if (!response.ok) {
        throw new Error(`Failed to delete transformation plan: ${response.status}`)
      }
      
      // Remove the deleted plan from the state
      setPlans(prevPlans => prevPlans.filter(plan => plan.id !== planId))
      
      // Show success message
      toast({
        title: "Plan deleted",
        description: `${planName} has been deleted successfully.`,
      })
    } catch (err) {
      console.error('Error deleting transformation plan:', err)
      setError(err instanceof Error ? err.message : 'Failed to delete transformation plan')
    } finally {
      setIsDeleting(null)
    }
  }

  // Display appropriate message when no data or loading
  if (isLoading && plans.length === 0) {
    return (
      <div className="flex justify-center items-center p-8">
        <Loader2 className="h-8 w-8 animate-spin mr-2" />
        <span>Loading transformation plans...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center p-8 space-y-4">
        <div className="p-4 bg-red-50 border border-red-200 rounded-md text-red-800">
          <p className="font-medium mb-2">Error loading transformation plans</p>
          <p className="text-sm">{error}</p>
        </div>
        <Button onClick={() => {
          setError(null)
          fetchTransformationPlans(1)
        }}>
          <ArrowUp className="h-4 w-4 mr-2" />
          Try Again
        </Button>
      </div>
    )
  }

  if (!isLoading && plans.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 space-y-4">
        <p className="text-center text-gray-500">
          No transformation plans found.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4 w-full">
      {permissionError && (
        <div className="bg-destructive text-white p-4 mb-4 rounded-md flex items-center justify-between">
          <span>{permissionError}</span>
        </div>
      )}
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold">Transformation Plans</h2>
      </div>
      
      <Table className="border rounded-md">
        <TableHeader>
          <TableRow>
            {columns.map((column) => (
              <TableHead key={column.accessor}>{column.header}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {plans.map((plan) => (
            <TableRow key={plan.id}>
              <TableCell className="font-medium">{plan.name}</TableCell>
              <TableCell>{plan.description}</TableCell>
              <TableCell>
                <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${plan.status === 'completed' ? 'bg-green-100 text-green-800' : plan.status === 'error' ? 'bg-red-100 text-red-800' : 'bg-blue-100 text-blue-800'}`}>
                  {plan.status}
                </span>
              </TableCell>
              <TableCell>{plan.created_at ? formatDate(plan.created_at) : 'N/A'}</TableCell>
              <TableCell className="space-x-2">
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => handleViewPlan(plan.id)}
                >
                  <ArrowRight className="h-4 w-4 mr-1" /> Edit
                </Button>
                
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button 
                      variant="ghost" 
                      size="sm"
                      className="text-red-600 hover:bg-red-50 hover:text-red-700"
                      disabled={isDeleting === plan.id}
                    >
                      {isDeleting === plan.id ? (
                        <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4 mr-1" />
                      )} 
                      Delete
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Delete Transformation Plan</AlertDialogTitle>
                      <AlertDialogDescription>
                        Are you sure you want to delete the transformation plan "{plan.name}"?
                        This action cannot be undone.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction 
                        className="bg-red-600 hover:bg-red-700"
                        onClick={() => handleDeletePlan(plan.id, plan.name)}
                      >
                        Delete
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
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
