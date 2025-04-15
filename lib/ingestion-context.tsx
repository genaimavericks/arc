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
  markedForRemoval?: boolean
}

// Define context type
interface IngestionContextType {
  jobs: Job[]
  errors: { id: string; message: string; timestamp: string }[]
  processingStatus: string
  addJob: (job: Job) => void
  updateJob: (updatedJob: Job) => void
  removeJob: (jobId: string) => void
  addError: (error: string) => void
  clearErrors: () => void
  setProcessingStatus: (status: string) => void
  cancelAllActiveJobs: () => Promise<void>
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
  // Initialize state with empty array, load from storage client-side
  const [jobs, setJobs] = useState<Job[]>([])
  const [errors, setErrors] = useState<{ id: string; message: string; timestamp: string }[]>([])
  const [processingStatus, setProcessingStatus] = useState<string>("")
  const [isPolling, setIsPolling] = useState(true)

  // Load initial jobs from localStorage on client-side mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      setJobs(getJobsFromStorage());
    }
  }, []);

  // Add a new job
  const addJob = (job: Job) => {
    setJobs((prevJobs) => {
      const newJobs = [job, ...prevJobs]
      if (typeof window !== 'undefined') {
        saveJobsToStorage(newJobs)
      }
      return newJobs
    })
  }

  // Update a job in the jobs array
  const updateJob = (updatedJob: Job) => {
    setJobs((prevJobs) => {
      // Find the job to update
      const index = prevJobs.findIndex((job) => job.id === updatedJob.id)
      
      // If job not found, return unchanged array
      if (index === -1) return prevJobs
      
      // Create a new array with the updated job
      const newJobs = [...prevJobs]
      newJobs[index] = updatedJob
      
      // If the job is now completed, failed, or cancelled, mark it for removal after a delay
      if (
        (updatedJob.status === "completed" || 
         updatedJob.status === "failed" || 
         updatedJob.status === "cancelled") && 
        !newJobs[index].markedForRemoval
      ) {
        // Mark the job for removal
        newJobs[index] = {
          ...newJobs[index],
          markedForRemoval: true,
        }
        
        // Clear processing status if this was a cancelled job
        if (updatedJob.status === "cancelled") {
          setProcessingStatus("");
        }
        
        // Remove the job after a delay
        const removalDelay = updatedJob.status === "cancelled" ? 3000 : 5000;
        setTimeout(() => {
          setJobs((currentJobs) =>
            currentJobs.filter((job) => job.id !== updatedJob.id)
          )
        }, removalDelay) // Remove after delay (shorter for cancelled jobs)
      }
      
      return newJobs
    })
  }

  // Remove a job
  const removeJob = (jobId: string) => {
    setJobs((prevJobs) => {
      const filteredJobs = prevJobs.filter((job) => job.id !== jobId)
      if (typeof window !== 'undefined') {
        saveJobsToStorage(filteredJobs)
      }
      return filteredJobs
    })
  }

  // Add an error
  const addError = (error: string) => {
    // Generate a unique ID for this error to track it for removal
    const errorId = `error-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    
    // Add the error with its ID to the errors array
    setErrors((prevErrors) => [{
      id: errorId,
      message: error,
      timestamp: new Date().toISOString()
    }, ...prevErrors]);
    
    // Automatically remove the error after 5 seconds
    setTimeout(() => {
      setErrors((currentErrors) => 
        currentErrors.filter((err) => err.id !== errorId)
      );
    }, 5000); // 5 seconds timeout
  }

  // Clear all errors
  const clearErrors = () => {
    setErrors([]);
  }

  // Cancel all active jobs
  const cancelAllActiveJobs = async (): Promise<void> => {
    console.log("Attempting to cancel all active jobs...");
    
    // First, clear the processing status immediately to stop file processing
    // This ensures the notification is removed and signals to the FileUpload component
    // that processing should stop
    setProcessingStatus("");
    
    // If there's an active upload in progress, mark it as cancelled in localStorage
    // Do this early in the function to ensure file processing is cancelled immediately
    if (typeof window !== 'undefined') {
      const activeUploads = Object.keys(localStorage)
        .filter(key => key.startsWith('upload_'))
        .map(key => key.replace('upload_', ''));
      
      for (const uploadId of activeUploads) {
        console.log(`Marking upload ${uploadId} as cancelled in localStorage`);
        localStorage.setItem(`cancelled_upload_${uploadId}`, "true");
      }
    }
    
    // Find all active jobs
    const activeJobs = jobs.filter(
      job => job.status === "running" || job.status === "queued"
    );
    
    console.log(`Found ${activeJobs.length} active jobs to cancel:`, activeJobs);
    
    if (activeJobs.length === 0) {
      console.log("No active jobs found to cancel");
      return;
    }
    
    // Cancel each job
    for (const job of activeJobs) {
      try {
        console.log(`Attempting to cancel job ${job.id}...`);
        
        // Update the job status to "cancelling" immediately for better UX
        updateJob({
          ...job,
          status: "cancelling",
          details: `${job.details} (Cancelling...)`,
        });
        
        const apiBaseUrl = getApiBaseUrl();
        console.log(`Making API call to ${apiBaseUrl}/api/datapuur/cancel-job/${job.id}`);
        
        const response = await fetch(`${apiBaseUrl}/api/datapuur/cancel-job/${job.id}`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${typeof window !== 'undefined' ? localStorage.getItem("token") : ''}`,
          },
        });
        
        console.log(`API response status: ${response.status}`);
        
        if (response.ok) {
          console.log(`Successfully cancelled job ${job.id}`);
          
          // Update the job in the UI
          updateJob({
            ...job,
            status: "cancelled",
            endTime: new Date().toISOString(),
            details: `${job.details} (Cancelled by user)`,
          });
        } else {
          console.error(`Failed to cancel job ${job.id}: ${response.statusText}`);
          
          // Even if the API call fails, update the UI to reflect cancellation
          // This ensures the user gets feedback even if there's a backend issue
          updateJob({
            ...job,
            status: "cancelled",
            endTime: new Date().toISOString(),
            details: `${job.details} (Cancellation attempted)`,
          });
          
          addError(`Failed to cancel job ${job.id}: ${response.statusText}`);
        }
      } catch (error) {
        console.error(`Error cancelling job ${job.id}:`, error);
        
        // Update the UI even if there's an exception
        updateJob({
          ...job,
          status: "cancelled",
          endTime: new Date().toISOString(),
          details: `${job.details} (Cancellation attempted)`,
        });
        
        addError(`Failed to cancel job ${job.id}: ${error}`);
      }
    }
  };

  // Check for active jobs on initial load or when user returns to the app
  useEffect(() => {
    // Ensure this runs client-side only
    if (typeof window === 'undefined') return;
    
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
              // Ensure token is accessed client-side
              Authorization: `Bearer ${typeof window !== 'undefined' ? localStorage.getItem("token") : ''}`,
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
    
    // Run the check when the component mounts (client-side)
    checkInitialJobStatus();
    
    // Also run the check when the user returns to the tab/window
    const handleVisibilityChange = () => {
      if (typeof window !== 'undefined' && document.visibilityState === 'visible') {
        checkInitialJobStatus();
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    // Clean up the event listener
    return () => {
      if (typeof window !== 'undefined') {
        document.removeEventListener('visibilitychange', handleVisibilityChange);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [updateJob]); // updateJob dependency might cause re-runs, consider if needed

  // Poll for job updates
  useEffect(() => {
    // Ensure this runs client-side only
    if (typeof window === 'undefined' || !isPolling) return

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
        // Use Promise.all to fetch all job statuses concurrently instead of sequentially
        // This ensures all jobs get updated at the same time
        const apiBaseUrl = getApiBaseUrl()
        const jobPromises = jobsToUpdate.map(job => 
          fetch(`${apiBaseUrl}/api/datapuur/job-status/${job.id}`, {
            method: "GET",
            headers: {
              Authorization: `Bearer ${typeof window !== 'undefined' ? localStorage.getItem("token") : ''}`,
            },
          })
          .then(response => {
            if (response.ok) {
              return response.json()
            }
            return null
          })
          .catch(error => {
            console.error(`Error polling job status for job ${job.id}:`, error)
            return null
          })
        )
        
        const updatedJobs = await Promise.all(jobPromises)
        
        // Update all jobs that returned valid data
        updatedJobs.forEach(updatedJob => {
          if (updatedJob) {
            updateJob(updatedJob)
          }
        })
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
    cancelAllActiveJobs,
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
