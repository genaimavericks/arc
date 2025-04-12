"use client"

import { useState, useEffect } from "react"
import { X, XCircle, CheckCircle, Clock, RefreshCw } from "lucide-react"
import { useKGInsightsJobs } from "@/lib/kginsights-job-context"
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { formatDistanceToNow } from "date-fns"

export default function FloatingKGJobCard() {
  const { 
    jobs, 
    isLoading, 
    refreshJobs, 
    cancelJob,
    clearCompletedJobs
  } = useKGInsightsJobs()
  
  const [minimized, setMinimized] = useState(false)
  const [visible, setVisible] = useState(false)
  const [showCardTimeout, setShowCardTimeout] = useState<NodeJS.Timeout | null>(null)

  // Determine if there are any active jobs
  const activeJobs = jobs.filter(job => job.status === "pending" || job.status === "running")
  const completedJobs = jobs.filter(job => job.status === "completed")
  const failedJobs = jobs.filter(job => job.status === "failed" || job.status === "cancelled")
  
  // Handle visibility based on jobs
  useEffect(() => {
    // Only show card if there are active jobs or recently completed/failed jobs
    if (activeJobs.length > 0) {
      // Always show if there are active jobs
      setVisible(true)
      
      // Clear any existing timeout
      if (showCardTimeout) {
        clearTimeout(showCardTimeout)
        setShowCardTimeout(null)
      }
    } else if (completedJobs.length > 0 || failedJobs.length > 0) {
      // Show for completed/failed jobs, but set a timeout to hide
      setVisible(true)
      
      // Clear any existing timeout
      if (showCardTimeout) {
        clearTimeout(showCardTimeout)
      }
      
      // Set a new timeout to hide the card after 5 seconds
      const timeout = setTimeout(() => {
        setVisible(false)
        clearCompletedJobs()
      }, 5000) // 5 seconds per requirements
      
      setShowCardTimeout(timeout)
    } else {
      // No jobs or only old completed jobs - don't show
      setVisible(false)
    }
    
    // Cleanup on unmount
    return () => {
      if (showCardTimeout) {
        clearTimeout(showCardTimeout)
      }
    }
  }, [jobs, activeJobs.length, completedJobs.length, failedJobs.length])

  // Force refresh jobs periodically when there are active jobs
  useEffect(() => {
    if (activeJobs.length > 0) {
      // Set up a timer to refresh jobs every second
      const refreshTimer = setInterval(() => {
        refreshJobs();
      }, 1000);
      
      // Clean up timer
      return () => {
        clearInterval(refreshTimer);
      };
    }
  }, [activeJobs.length, refreshJobs]);

  // Handle job status icons and colors
  const getJobStatusInfo = (status: string) => {
    switch (status) {
      case "pending":
        return { 
          icon: <Clock className="h-4 w-4" />, 
          color: "bg-yellow-200 text-yellow-800",
          label: "Pending"
        }
      case "running":
        return { 
          icon: <RefreshCw className="h-4 w-4 animate-spin" />, 
          color: "bg-blue-200 text-blue-800",
          label: "Running"
        }
      case "completed":
        return { 
          icon: <CheckCircle className="h-4 w-4" />, 
          color: "bg-green-200 text-green-800",
          label: "Completed"
        }
      case "failed":
        return { 
          icon: <XCircle className="h-4 w-4" />, 
          color: "bg-red-200 text-red-800",
          label: "Failed"
        }
      case "cancelled":
        return { 
          icon: <XCircle className="h-4 w-4" />, 
          color: "bg-gray-200 text-gray-800",
          label: "Cancelled"
        }
      default:
        return { 
          icon: <Clock className="h-4 w-4" />, 
          color: "bg-gray-200 text-gray-800",
          label: "Unknown"
        }
    }
  }

  // Format job type for display
  const formatJobType = (type: string) => {
    switch (type) {
      case "load_data":
        return "Load Data"
      case "clean_data":
        return "Clean Data"
      default:
        return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
    }
  }

  // Get the time ago from a timestamp
  const getTimeAgo = (timestamp: string) => {
    try {
      return formatDistanceToNow(new Date(timestamp), { addSuffix: true })
    } catch (err) {
      return "unknown time"
    }
  }

  if (!visible) {
    return null
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 max-w-md">
      <Card className="shadow-lg border-2 overflow-hidden max-h-[80vh]">
        <CardHeader className="py-2 px-4 bg-gray-100 flex flex-row items-center justify-between space-y-0">
          <CardTitle className="font-medium text-sm flex gap-2 items-center">
            <RefreshCw className={`h-4 w-4 ${activeJobs.length > 0 ? 'animate-spin' : ''}`} />
            KG Processing Jobs {activeJobs.length > 0 ? `(${activeJobs.length} active)` : ''}
          </CardTitle>
          <div className="flex items-center gap-1">
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-6 w-6 p-0" 
              onClick={() => setMinimized(!minimized)}
            >
              {minimized ? "+" : "-"}
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              className="h-6 px-2 flex items-center gap-1 text-xs" 
              onClick={() => {
                setVisible(false)
                clearCompletedJobs()
              }}
            >
              <X className="h-3 w-3" /> Close
            </Button>
          </div>
        </CardHeader>
        
        {!minimized && (
          <>
            <CardContent className="p-4 max-h-[500px] overflow-y-auto">
              {jobs.length === 0 ? (
                <p className="text-sm text-gray-500">No active jobs</p>
              ) : (
                <ul className="space-y-3">
                  {jobs.map(job => {
                    const { icon, color, label } = getJobStatusInfo(job.status)
                    
                    return (
                      <li key={job.id} className="bg-gray-50 rounded-md p-3">
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <Badge className={color}>
                                <span className="flex items-center gap-1">
                                  {icon} {label}
                                </span>
                              </Badge>
                              <span className="text-xs text-gray-500">
                                {getTimeAgo(job.created_at)}
                              </span>
                            </div>
                            
                            <h4 className="font-medium text-sm mt-1">
                              {formatJobType(job.job_type)} - Schema #{job.schema_id}
                            </h4>
                            
                            <p className="text-xs text-gray-700 mt-1 break-words">
                              {job.message || 'Processing...'}
                            </p>
                            
                            {job.status === "running" && (
                              <div className="mt-2">
                                <Progress value={job.progress || 0} max={100} className="h-1" />
                                <p className="text-xs text-right mt-0.5 text-gray-500">
                                  {job.progress || 0}%
                                </p>
                              </div>
                            )}
                            
                            {job.error && (
                              <p className="text-xs text-red-600 mt-1">
                                Error: {job.error}
                              </p>
                            )}
                          </div>
                          
                          {(job.status === "pending" || job.status === "running") && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 px-1.5 text-xs ml-2"
                              onClick={() => cancelJob(job.id)}
                            >
                              Cancel
                            </Button>
                          )}
                        </div>
                      </li>
                    )
                  })}
                </ul>
              )}
            </CardContent>
            
            <CardFooter className="p-2 bg-gray-50 flex justify-between">
              <Button 
                variant="ghost" 
                size="sm" 
                className="text-xs"
                onClick={refreshJobs}
                disabled={isLoading}
              >
                <RefreshCw className={`h-3 w-3 mr-1 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              
              {jobs.some(job => job.status === "completed" || job.status === "failed" || job.status === "cancelled") && (
                <Button 
                  variant="ghost" 
                  size="sm"
                  className="text-xs"
                  onClick={clearCompletedJobs}
                >
                  Clear Completed
                </Button>
              )}
            </CardFooter>
          </>
        )}
      </Card>
    </div>
  )
}
