"use client"

import { useState, useEffect } from "react"
import { useIngestion } from "@/lib/ingestion-context"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { 
  Activity, 
  ChevronDown, 
  ChevronUp, 
  X, 
  FileText, 
  Database, 
  RefreshCw,
  CheckCircle,
  XCircle,
  Clock,
  Loader2
} from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { formatDistanceToNow } from "date-fns"

export function FloatingJobCard() {
  const { jobs, errors, updateJob, isPolling, setIsPolling, processingStatus } = useIngestion()
  const [isMinimized, setIsMinimized] = useState(() => {
    // Try to retrieve minimized state from localStorage
    try {
      const storedState = localStorage.getItem('jobCardMinimized')
      return storedState ? JSON.parse(storedState) : false
    } catch (error) {
      return false
    }
  })
  const [isVisible, setIsVisible] = useState(true)
  const [recentlyCompletedJobs, setRecentlyCompletedJobs] = useState<string[]>([])
  const [activeTab, setActiveTab] = useState("active")
  
  // Save minimized state to localStorage when it changes
  useEffect(() => {
    try {
      localStorage.setItem('jobCardMinimized', JSON.stringify(isMinimized))
    } catch (error) {
      console.error('Error saving minimized state to localStorage:', error)
    }
  }, [isMinimized])
  
  // Track when jobs complete to show them temporarily
  useEffect(() => {
    const completedJobIds = jobs
      .filter(job => job.status === "completed" || job.status === "failed")
      .map(job => job.id)
    
    // Add newly completed jobs to our tracking array
    setRecentlyCompletedJobs(prev => {
      const newIds = completedJobIds.filter(id => !prev.includes(id))
      
      // For each newly completed job, set a timeout to remove it from our tracking
      newIds.forEach(id => {
        setTimeout(() => {
          setRecentlyCompletedJobs(current => current.filter(jobId => jobId !== id))
        }, 5000) // Show completed jobs for 5 seconds in the card
      })
      
      return [...prev, ...newIds]
    })
  }, [jobs])
  
  // Show active jobs plus recently completed ones
  const activeJobs = jobs.filter(job => 
    job.status === "running" || 
    job.status === "queued" || 
    recentlyCompletedJobs.includes(job.id)
  )
  
  // Only show the card if there are active jobs (running or queued) or there's a processing status
  if ((!activeJobs.some(job => job.status === "running" || job.status === "queued") && !processingStatus) || !isVisible) {
    return null
  }

  // Helper function to get job icon
  const getJobIcon = (type: string) => {
    switch (type) {
      case "file":
        return <FileText className="h-4 w-4 text-blue-500" />
      case "database":
        return <Database className="h-4 w-4 text-green-500" />
      default:
        return <Activity className="h-4 w-4 text-primary" />
    }
  }

  // Helper function to get status badge
  const getStatusBadge = (status: string) => {
    switch (status) {
      case "running":
        return (
          <Badge variant="outline" className="bg-blue-500/10 text-blue-500 border-blue-500/20 flex items-center gap-1">
            <Loader2 className="h-3 w-3 animate-spin" />
            Running
          </Badge>
        )
      case "queued":
        return (
          <Badge variant="outline" className="bg-amber-500/10 text-amber-500 border-amber-500/20 flex items-center gap-1">
            <Clock className="h-3 w-3" />
            Queued
          </Badge>
        )
      case "completed":
        return (
          <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20 flex items-center gap-1">
            <CheckCircle className="h-3 w-3" />
            Completed
          </Badge>
        )
      case "failed":
        return (
          <Badge variant="outline" className="bg-red-500/10 text-red-500 border-red-500/20 flex items-center gap-1">
            <XCircle className="h-3 w-3" />
            Failed
          </Badge>
        )
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  // Helper function to format time
  const formatTime = (timeString: string) => {
    if (!timeString) return "N/A"
    try {
      return formatDistanceToNow(new Date(timeString), { addSuffix: true })
    } catch (error) {
      return timeString
    }
  }

  // Function to cancel a job
  const cancelJob = async (jobId: string) => {
    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || ""
      const response = await fetch(`${apiBaseUrl}/api/datapuur/cancel-job/${jobId}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      })
      
      if (response.ok) {
        // Update the job status in the UI
        updateJob({
          ...jobs.find(job => job.id === jobId)!,
          status: "failed",
          endTime: new Date().toISOString(),
          error: "Job cancelled by user",
        })
      }
    } catch (error) {
      console.error("Error cancelling job:", error)
    }
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 50 }}
        className="fixed bottom-4 right-4 z-50 w-96 bg-card/95 backdrop-blur-sm rounded-lg border border-border shadow-lg"
      >
        <div className="flex justify-between items-center p-3 border-b border-border">
          <div className="flex items-center">
            <Activity className="w-4 h-4 mr-2 text-primary" />
            <h3 className="font-medium text-foreground">
              Ingestion Jobs ({activeJobs.length})
            </h3>
          </div>
          <div className="flex items-center space-x-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => setIsPolling(!isPolling)}
              title={isPolling ? "Auto-refreshing" : "Auto-refresh paused"}
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isPolling ? "animate-spin text-primary" : ""}`} />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => setIsMinimized(!isMinimized)}
              title={isMinimized ? "Expand" : "Minimize"}
            >
              {isMinimized ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => setIsVisible(false)}
              title="Close"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
        
        {!isMinimized && (
          <div className="p-3 max-h-80 overflow-y-auto">
            {/* Display processing status if available */}
            {processingStatus && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-primary/10 border border-primary rounded-lg p-3 text-primary mb-4"
              >
                {processingStatus}
              </motion.div>
            )}
            
            {/* Custom Active Jobs UI */}
            <div className="space-y-3">
              {activeJobs
                .filter(job => job.status === "running" || job.status === "queued")
                .map((job) => (
                  <motion.div 
                    key={job.id} 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="relative bg-card border border-border rounded-lg p-3 overflow-hidden"
                  >
                    {/* Progress bar background for running jobs */}
                    {job.status === "running" && (
                      <div 
                        className="absolute inset-0 bg-blue-500/5 z-0"
                        style={{ 
                          width: `${job.progress}%`,
                          transition: 'width 0.5s ease-in-out'
                        }}
                      />
                    )}
                    
                    {/* Job content */}
                    <div className="relative z-10">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center">
                          <div className="mr-2 p-1 rounded-full bg-background">
                            {getJobIcon(job.type)}
                          </div>
                          <div>
                            <h4 className="font-medium text-foreground text-sm truncate max-w-[150px]">
                              {job.name}
                            </h4>
                            <p className="text-xs text-muted-foreground truncate max-w-[180px]">
                              {job.details}
                            </p>
                          </div>
                        </div>
                        <div className="flex flex-col items-end space-y-1">
                          {getStatusBadge(job.status)}
                          {job.status === "running" && (
                            <span className="text-xs text-muted-foreground">
                              Started {formatTime(job.startTime)}
                            </span>
                          )}
                        </div>
                      </div>
                      
                      {/* Progress indicator for running jobs */}
                      {job.status === "running" && (
                        <div className="mt-2">
                          <div className="flex justify-between text-xs mb-1">
                            <span className="text-muted-foreground">Progress</span>
                            <span className="text-foreground font-medium">{job.progress}%</span>
                          </div>
                          <Progress value={job.progress} className="h-1.5" />
                        </div>
                      )}
                      
                      {/* Action buttons */}
                      <div className="flex justify-end mt-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => cancelJob(job.id)}
                          className="h-7 px-2 text-destructive hover:bg-destructive/10 text-xs"
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  </motion.div>
                ))}
                
              {/* Recently completed jobs */}
              {activeJobs
                .filter(job => recentlyCompletedJobs.includes(job.id))
                .map((job) => (
                  <motion.div 
                    key={job.id} 
                    initial={{ opacity: 1 }}
                    animate={{ opacity: 0.8 }}
                    exit={{ opacity: 0, height: 0, marginBottom: 0 }}
                    className="bg-card border border-border rounded-lg p-3"
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex items-center">
                        <div className="mr-2 p-1 rounded-full bg-background">
                          {getJobIcon(job.type)}
                        </div>
                        <div>
                          <h4 className="font-medium text-foreground text-sm truncate max-w-[150px]">
                            {job.name}
                          </h4>
                          <p className="text-xs text-muted-foreground truncate max-w-[180px]">
                            {job.status === "completed" ? "Completed successfully" : job.error || "Failed"}
                          </p>
                        </div>
                      </div>
                      <div className="flex flex-col items-end">
                        {getStatusBadge(job.status)}
                        <span className="text-xs text-muted-foreground mt-1">
                          {formatTime(job.endTime || '')}
                        </span>
                      </div>
                    </div>
                  </motion.div>
                ))}
                
              {/* Empty state */}
              {activeJobs.filter(job => 
                job.status === "running" || 
                job.status === "queued" || 
                recentlyCompletedJobs.includes(job.id)
              ).length === 0 && !processingStatus && (
                <div className="text-center py-4 text-muted-foreground text-sm">
                  No active jobs
                </div>
              )}
            </div>
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  )
}
