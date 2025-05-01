"use client"

import { useState, useEffect } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { AlertCircle, CheckCircle, Clock, RefreshCw, XCircle, FileText, Database, FolderOpen, BarChart } from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import { getApiBaseUrl } from "@/lib/config"
import { useIngestion, Job } from "@/lib/ingestion-context"
import { motion } from "framer-motion"

// Define component props
interface IngestionMonitorProps {
  jobs?: Job[]
  onJobUpdated?: (job: Job) => void
  errors?: { id: string; message: string; timestamp: string }[]
  isPolling?: boolean
  processingStatus?: string
}

export function IngestionMonitor({ jobs: propJobs, onJobUpdated, errors: propErrors = [], isPolling: propIsPolling, processingStatus }: IngestionMonitorProps) {
  const [activeTab, setActiveTab] = useState("active")
  
  // Use the global ingestion context
  const { jobs: contextJobs, errors: contextErrors, updateJob, isPolling: contextIsPolling, setIsPolling, cancelAllActiveJobs } = useIngestion()
  
  // Use either the props or the context values
  const jobs = propJobs || contextJobs
  const errors = propErrors.length > 0 ? propErrors : contextErrors
  const localIsPolling = propIsPolling !== undefined ? propIsPolling : contextIsPolling

  // Helper function to get the group key for a job
  const getGroupKey = (job: Job) => {
    // Safely handle undefined or null startTime
    if (!job.startTime) {
      return "unknown-date"
    }
    return job.startTime.split("T")[0]
  }

  // Filter jobs based on status
  const activeJobs = jobs.filter((job) => job.status === "running" || job.status === "queued")
  const completedJobs = jobs.filter((job) => job.status === "completed")
  const failedJobs = jobs.filter((job) => job.status === "failed")

  // Poll for job updates
  useEffect(() => {
    if (!localIsPolling) return

    // Function to check job status
    const checkJobs = async () => {
      try {
        const apiBaseUrl = getApiBaseUrl()
        const token = localStorage.getItem("token")

        if (!token) return

        // Only check running or queued jobs
        const jobsToCheck = jobs.filter(job => 
          job.status === "running" || job.status === "queued"
        )

        if (jobsToCheck.length === 0) return

        for (const job of jobsToCheck) {
          try {
            const response = await fetch(`${apiBaseUrl}/api/datapuur/job-status/${job.id}`, {
              headers: {
                Authorization: `Bearer ${token}`
              }
            })
            
            // Handle 404 responses - job no longer exists
            if (response.status === 404) {
              console.log(`Job ${job.id} no longer exists (404), removing from tracking`)
              
              // Mark job as removed
              updateJob({
                ...job,
                status: "removed",
                markedForRemoval: true,
                details: "Job no longer exists on server"
              })
              
              continue
            }
            
            if (!response.ok) {
              console.error(`Error checking job ${job.id}: ${response.statusText}`)
              continue
            }
            
            const data = await response.json()
            
            // Update job with new status
            if (data) {
              if (onJobUpdated) {
                onJobUpdated(data)
              } else {
                updateJob(data)
              }
            }
          } catch (error) {
            console.error(`Error checking job ${job.id}:`, error)
          }
        }
      } catch (error) {
        console.error("Error polling job status:", error)
      }
    }

    // Run immediately when jobs change
    checkJobs()
    
    // Then set up the polling interval
    const pollInterval = setInterval(checkJobs, 10000) // Poll every 10 seconds instead of 3

    return () => clearInterval(pollInterval)
  }, [jobs, localIsPolling, onJobUpdated, updateJob])

  const [cancellingJobs, setCancellingJobs] = useState<string[]>([])
  const [cancellingProcessing, setCancellingProcessing] = useState(false)

  const getJobIcon = (type: string) => {
    switch (type) {
      case "file":
        return <FileText className="h-4 w-4" />
      case "database":
        return <Database className="h-4 w-4" />
      case "profile":
        return <BarChart className="h-4 w-4" />
      default:
        return <FileText className="h-4 w-4" />
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "running":
        return (
          <Badge className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300 flex items-center gap-1">
            <RefreshCw className="h-3 w-3 animate-spin" />
            Running
          </Badge>
        )
      case "queued":
        return (
          <Badge className="bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300 flex items-center gap-1">
            <Clock className="h-3 w-3" />
            Queued
          </Badge>
        )
      case "completed":
        return (
          <Badge className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300 flex items-center gap-1">
            <CheckCircle className="h-3 w-3" />
            Completed
          </Badge>
        )
      case "failed":
        return (
          <Badge className="bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300 flex items-center gap-1">
            <XCircle className="h-3 w-3" />
            Failed
          </Badge>
        )
      case "cancelled":
        return (
          <Badge className="bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300 flex items-center gap-1">
            <XCircle className="h-3 w-3" />
            Cancelled
          </Badge>
        )
      default:
        return <Badge className="bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300">{status}</Badge>
    }
  }

  const formatTime = (timeString: string) => {
    if (!timeString) return "N/A"
    try {
      return formatDistanceToNow(new Date(timeString), { addSuffix: true })
    } catch (error) {
      return timeString
    }
  }

  const cancelJob = async (jobId: string) => {
    try {
      // Add job to cancelling list to show loading state
      setCancellingJobs(prev => [...prev, jobId])
      
      // Immediately update UI to show job is being cancelled
      const jobToUpdate = jobs.find(job => job.id === jobId)
      if (jobToUpdate && (onJobUpdated || updateJob)) {
        const updatingJob = {
          ...jobToUpdate,
          status: "cancelling", // Temporary status for UI feedback
        }
        
        if (onJobUpdated) {
          onJobUpdated(updatingJob)
        } else if (updateJob) {
          updateJob(updatingJob)
        }
      }
      
      const apiBaseUrl = getApiBaseUrl();
      const response = await fetch(`${apiBaseUrl}/api/datapuur/cancel-job/${jobId}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      })

      if (response.ok) {
        const updatedJob = await response.json()
        if (onJobUpdated) {
          onJobUpdated(updatedJob)
        } else if (updateJob) {
          updateJob(updatedJob)
        }
      }
    } catch (error) {
      console.error("Error canceling job:", error)
    } finally {
      // Remove job from cancelling list
      setCancellingJobs(prev => prev.filter(id => id !== jobId))
    }
  }

  // Add a function to group jobs by batch or source
  const groupJobs = (jobs: Job[]) => {
    // Group jobs by their creation time (within a 30-second window)
    const groupedJobs: Record<string, Job[]> = {}

    jobs.forEach((job) => {
      const timeKey = getGroupKey(job)
      if (!groupedJobs[timeKey]) {
        groupedJobs[timeKey] = []
      }
      groupedJobs[timeKey].push(job)
    })

    // Sort groups by most recent first
    return Object.entries(groupedJobs)
      .sort(([keyA], [keyB]) => {
        return keyB.localeCompare(keyA)
      })
      .map(([key, jobs]) => ({
        key,
        jobs,
      }))
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsPolling(!localIsPolling)}
            className={localIsPolling ? "border-primary text-primary" : ""}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${localIsPolling ? "animate-spin" : ""}`} />
            {localIsPolling ? "Auto-refreshing" : "Auto-refresh paused"}
          </Button>
        </div>
        <div className="text-sm text-muted-foreground">
          {activeJobs.length} active, {completedJobs.length} completed, {failedJobs.length} failed
        </div>
      </div>

      <Tabs defaultValue="active" value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid grid-cols-3">
          <TabsTrigger value="active">Active Jobs {activeJobs.length > 0 && `(${activeJobs.length})`}</TabsTrigger>
          <TabsTrigger value="completed">
            Completed {completedJobs.length > 0 && `(${completedJobs.length})`}
          </TabsTrigger>
          <TabsTrigger value="failed">Failed {failedJobs.length > 0 && `(${failedJobs.length})`}</TabsTrigger>
        </TabsList>

        <TabsContent value="active" className="space-y-4 mt-4">
          {activeJobs.length === 0 && !processingStatus ? (
            activeTab === "active" ? (
              <div className="text-center py-8 text-muted-foreground">No active jobs</div>
            ) : null
          ) : (
            <>
              {/* Display processing status if available */}
              {processingStatus && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-card border border-primary/20 rounded-lg p-4 mb-4"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex items-center">
                      <div className="mr-2 p-1 rounded-full bg-background">
                        <FileText className="h-4 w-4 text-blue-500" />
                      </div>
                      <div>
                        <h4 className="font-medium text-foreground">File Processing</h4>
                        <p className="text-sm text-muted-foreground">{processingStatus}</p>
                      </div>
                    </div>
                    {/* Only show cancel button if processing status doesn't include "Ingestion job started" */}
                    {!processingStatus.includes("Ingestion job started") && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          // Set cancelling state for this job
                          setCancellingProcessing(true);
                          
                          // Use the context function to cancel all active jobs
                          cancelAllActiveJobs()
                            .then(() => {
                              console.log("Successfully cancelled all jobs from ingestion monitor");
                            })
                            .catch((error: Error) => {
                              console.error("Error cancelling jobs from ingestion monitor:", error);
                            })
                            .finally(() => {
                              // Reset cancelling state after a short delay
                              setTimeout(() => {
                                setCancellingProcessing(false);
                              }, 1000);
                            });
                        }}
                        disabled={cancellingProcessing}
                        className={`h-7 px-2 ${cancellingProcessing ? 'text-muted-foreground' : 'text-destructive hover:bg-destructive/10'} text-xs`}
                        title="Cancel processing"
                      >
                        {cancellingProcessing ? (
                          <>
                            <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
                            Cancelling...
                          </>
                        ) : (
                          "Cancel"
                        )}
                      </Button>
                    )}
                  </div>
                </motion.div>
              )}
              
              {/* Group jobs that were likely uploaded together */}
              {groupJobs(activeJobs).map(({ key, jobs }) => (
                <div key={key} className="mb-6">
                  {jobs.length > 1 && (
                    <div className="flex items-center mb-2 text-sm text-muted-foreground">
                      <FolderOpen className="h-4 w-4 mr-1" />
                      <span>Batch upload ({jobs.length} files)</span>
                    </div>
                  )}

                  <div className="space-y-3">
                    {jobs.map((job) => (
                      <div key={job.id} className="border border-border rounded-lg p-4 bg-card/50">
                        <div className="flex justify-between items-start mb-2">
                          <div className="flex items-center">
                            <div className="mr-2">{getJobIcon(job.type)}</div>
                            <div>
                              <h4 className="font-medium text-foreground">{job.name}</h4>
                              <p className="text-xs text-muted-foreground">{job.details}</p>
                            </div>
                          </div>
                          <div className="flex items-center space-x-2">
                            {getStatusBadge(job.status)}
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => cancelJob(job.id)}
                              disabled={cancellingJobs.includes(job.id)}
                              className="h-7 px-2 text-destructive hover:bg-destructive/10"
                            >
                              {cancellingJobs.includes(job.id) ? (
                                <>
                                  <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
                                  Cancelling...
                                </>
                              ) : (
                                "Cancel"
                              )}
                            </Button>
                          </div>
                        </div>
                        <div className="space-y-2">
                          <div className="flex justify-between text-xs text-muted-foreground">
                            <span>Progress: {job.progress}%</span>
                            <span>Started {formatTime(job.startTime)}</span>
                          </div>
                          <Progress value={job.progress} className="h-2" />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </>
          )}
        </TabsContent>

        <TabsContent value="completed" className="space-y-4 mt-4">
          {completedJobs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">No completed jobs</div>
          ) : (
            completedJobs.map((job) => (
              <div key={job.id} className="border border-border rounded-lg p-4 bg-card/50">
                <div className="flex justify-between items-start">
                  <div className="flex items-center">
                    <div className="mr-2">{getJobIcon(job.type)}</div>
                    <div>
                      <h4 className="font-medium text-foreground">{job.name}</h4>
                      <p className="text-xs text-muted-foreground">{job.details}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">{getStatusBadge(job.status)}</div>
                </div>
                <div className="mt-2 text-xs text-muted-foreground flex justify-between">
                  <span>Completed {formatTime(job.endTime || '')}</span>
                  <span>Duration: {job.duration || "N/A"}</span>
                </div>
              </div>
            ))
          )}
        </TabsContent>

        <TabsContent value="failed" className="space-y-4 mt-4">
          {failedJobs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">No failed jobs</div>
          ) : (
            failedJobs.map((job) => (
              <div key={job.id} className="border border-border rounded-lg p-4 bg-card/50">
                <div className="flex justify-between items-start">
                  <div className="flex items-center">
                    <div className="mr-2">{getJobIcon(job.type)}</div>
                    <div>
                      <h4 className="font-medium text-foreground">{job.name}</h4>
                      <p className="text-xs text-muted-foreground">{job.details}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">{getStatusBadge(job.status)}</div>
                </div>
                <div className="mt-2 text-xs text-destructive">Error: {job.error || "Unknown error occurred"}</div>
                <div className="mt-1 text-xs text-muted-foreground">Failed {formatTime(job.endTime || '')}</div>
              </div>
            ))
          )}
        </TabsContent>
      </Tabs>

      {/* Error Log Section */}
      {errors.length > 0 && (
        <div className="mt-6 border-t border-border pt-4">
          <h4 className="font-medium text-foreground mb-2 flex items-center">
            <AlertCircle className="h-4 w-4 mr-2 text-destructive" />
            Error Log
          </h4>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {errors.map((error) => (
              <div key={error.id} className="bg-destructive/10 border border-destructive/20 rounded-md p-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-destructive font-medium">{error.message}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
