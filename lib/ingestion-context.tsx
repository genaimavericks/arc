"use client"

import { createContext, useContext, useState, useEffect, type ReactNode } from "react"
import { getApiBaseUrl } from "@/lib/config"

// Define job interface
export interface Job {
  id: string
  name: string
  type: string
  status: string
  progress: number
  startTime: string
  endTime: string | null
  details: string
  error?: string
  duration?: string
}

// Define context type
interface IngestionContextType {
  jobs: Job[]
  errors: string[]
  processingStatus: string
  addJob: (job: Job) => void
  updateJob: (updatedJob: Job) => void
  removeJob: (jobId: string) => void
  addError: (error: string) => void
  clearErrors: () => void
  setProcessingStatus: (status: string) => void
  isPolling: boolean
  setIsPolling: (isPolling: boolean) => void
}

// Create context
const IngestionContext = createContext<IngestionContextType | undefined>(undefined)

// Helper functions for localStorage
const saveJobsToStorage = (jobs: Job[]) => {
  try {
    localStorage.setItem('ingestionJobs', JSON.stringify(jobs))
  } catch (error) {
    console.error('Error saving jobs to localStorage:', error)
  }
}

// Helper function to get jobs from localStorage
const getJobsFromStorage = (): Job[] => {
  try {
    const storedJobs = localStorage.getItem("ingestionJobs")
    if (storedJobs) {
      const parsedJobs = JSON.parse(storedJobs)
      // Filter out completed and failed jobs when retrieving from storage
      // This ensures completed jobs don't persist after a page refresh
      return parsedJobs.filter((job: Job) => 
        job.status === "running" || job.status === "queued"
      )
    }
  } catch (error) {
    console.error("Error retrieving jobs from localStorage:", error)
  }
  return []
}

// Provider component
export function IngestionProvider({ children }: { children: ReactNode }) {
  // Initialize state from localStorage if available
  const [jobs, setJobs] = useState<Job[]>(() => getJobsFromStorage())
  const [errors, setErrors] = useState<string[]>([])
  const [processingStatus, setProcessingStatus] = useState<string>("")
  const [isPolling, setIsPolling] = useState(true)

  // Add a new job
  const addJob = (job: Job) => {
    setJobs((prevJobs) => {
      const newJobs = [job, ...prevJobs]
      saveJobsToStorage(newJobs)
      return newJobs
    })
  }

  // Update an existing job
  const updateJob = (updatedJob: Job) => {
    setJobs((prevJobs) => {
      // First update the job in the state
      const updatedJobs = prevJobs.map((job) => (job.id === updatedJob.id ? updatedJob : job))
      
      // If the job has just completed or failed, set a timeout to remove it
      if ((updatedJob.status === "completed" || updatedJob.status === "failed") && 
          updatedJobs.find(job => job.id === updatedJob.id)?.status !== updatedJob.status) {
        
        // Remove the job after 30 seconds (30000ms) to give user time to see the completion
        setTimeout(() => {
          setJobs(currentJobs => {
            const filteredJobs = currentJobs.filter(job => job.id !== updatedJob.id)
            saveJobsToStorage(filteredJobs)
            return filteredJobs
          })
        }, 30000)
      }
      
      saveJobsToStorage(updatedJobs)
      return updatedJobs
    })
  }

  // Remove a job
  const removeJob = (jobId: string) => {
    setJobs((prevJobs) => {
      const filteredJobs = prevJobs.filter((job) => job.id !== jobId)
      saveJobsToStorage(filteredJobs)
      return filteredJobs
    })
  }

  // Add an error
  const addError = (error: string) => {
    setErrors((prevErrors) => [error, ...prevErrors])
  }

  // Clear all errors
  const clearErrors = () => {
    setErrors([])
  }

  // Check for active jobs on initial load or when user returns to the app
  useEffect(() => {
    const checkInitialJobStatus = async () => {
      // Get jobs from localStorage
      const storedJobs = getJobsFromStorage();
      
      // If there are no stored jobs, no need to continue
      if (storedJobs.length === 0) return;
      
      // Find active jobs (running or queued)
      const activeJobs = storedJobs.filter(job => 
        (job.status === "running" || job.status === "queued") && 
        !job.id.startsWith("temp-")
      );
      
      if (activeJobs.length === 0) return;
      
      try {
        // Check the status of each active job
        for (const job of activeJobs) {
          const apiBaseUrl = getApiBaseUrl();
          const response = await fetch(`${apiBaseUrl}/api/datapuur/job-status/${job.id}`, {
            headers: {
              Authorization: `Bearer ${localStorage.getItem("token")}`,
            },
          });
          
          if (response.ok) {
            const updatedJob = await response.json();
            // Update the job with the latest status
            updateJob(updatedJob);
          }
        }
      } catch (error) {
        console.error("Error checking initial job status:", error);
      }
    };
    
    // Run the check when the component mounts
    checkInitialJobStatus();
    
    // Also run the check when the user returns to the tab/window
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        checkInitialJobStatus();
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    // Clean up the event listener
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [updateJob]);

  // Poll for job updates
  useEffect(() => {
    if (!isPolling) return

    // Initial check immediately when a new job is added
    const checkJobs = async () => {
      // Only poll for active jobs
      const jobsToUpdate = jobs.filter((job) => 
        (job.status === "running" || job.status === "queued") && 
        // Skip temporary jobs (they start with "temp-")
        !job.id.startsWith("temp-")
      )

      if (jobsToUpdate.length === 0) {
        return
      }

      try {
        for (const job of jobsToUpdate) {
          const apiBaseUrl = getApiBaseUrl()
          const response = await fetch(`${apiBaseUrl}/api/datapuur/job-status/${job.id}`, {
            headers: {
              Authorization: `Bearer ${localStorage.getItem("token")}`,
            },
          })

          if (response.ok) {
            const updatedJob = await response.json()
            updateJob(updatedJob)
          }
        }
      } catch (error) {
        console.error("Error polling job status:", error)
      }
    }

    // Run immediately when jobs change or component mounts
    checkJobs()
    
    // Then set up the polling interval
    const pollInterval = setInterval(checkJobs, 3000) // Poll every 3 seconds

    return () => clearInterval(pollInterval)
  }, [jobs, isPolling, updateJob])

  // Provide the context value
  const contextValue: IngestionContextType = {
    jobs,
    errors,
    processingStatus,
    addJob,
    updateJob,
    removeJob,
    addError,
    clearErrors,
    setProcessingStatus,
    isPolling,
    setIsPolling,
  }

  return (
    <IngestionContext.Provider value={contextValue}>
      {children}
    </IngestionContext.Provider>
  )
}

// Custom hook to use the ingestion context
export function useIngestion() {
  const context = useContext(IngestionContext)
  if (context === undefined) {
    throw new Error("useIngestion must be used within an IngestionProvider")
  }
  return context
}
