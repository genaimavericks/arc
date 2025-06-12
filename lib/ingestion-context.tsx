"use client"

import { createContext, useContext, useState, useEffect, type ReactNode } from "react"
import { getApiBaseUrl } from "@/lib/config"
import { fetchWithAuth } from "@/lib/auth-utils"

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
function saveJobsToStorage(jobs: Job[]) {
  try {
    // Filter out any jobs with status 'removed', 'deleted', or 'cancelled'
    // before saving to localStorage to prevent orphaned jobs
    const validJobsToSave = jobs.filter(job => 
      !['removed', 'deleted', 'cancelled'].includes(job.status) &&
      !job.markedForRemoval
    );
    
    console.log('Saving valid jobs to localStorage:', validJobsToSave.length);
    localStorage.setItem('ingestionJobs', JSON.stringify(validJobsToSave))
  } catch (error) {
    console.error('Error saving jobs to localStorage:', error)
  }
}

// Helper function to get jobs from localStorage
function getJobsFromStorage(): Job[] {
  try {
    const jobsData = localStorage.getItem('ingestionJobs')
    if (!jobsData) return []
    
    const parsedJobs = JSON.parse(jobsData)
    
    // Filter out any stale jobs that may have been left in localStorage
    const validJobs = parsedJobs.filter((job: Job) => 
      !['removed', 'deleted', 'cancelled'].includes(job.status) &&
      !job.markedForRemoval
    )
    
    console.log('Retrieved valid jobs from localStorage:', validJobs.length);
    return validJobs
  } catch (error) {
    console.error('Error retrieving jobs from localStorage:', error)
    return []
  }
}

// Provider component
export function IngestionProvider({ children }: { children: ReactNode }) {
  // Initialize state with empty array, load from storage client-side
  const [jobs, setJobs] = useState<Job[]>([])
  const [errors, setErrors] = useState<{ id: string; message: string; timestamp: string }[]>([])
  // Initialize processing status from localStorage if available, but filter out database-related messages
  const [processingStatus, setProcessingStatus] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      const storedStatus = localStorage.getItem('processingStatus');
      if (storedStatus && (
          storedStatus.toLowerCase().includes('database') ||
          storedStatus.includes('will be extracted from') ||
          storedStatus.includes('stored in parquet format'))) {
        // Don't restore database-related messages
        console.log("Filtering out database-related processing status:", storedStatus);
        localStorage.removeItem('processingStatus');
        return "";
      }
      return storedStatus || "";
    }
    return "";
  })
  const [isPolling, setIsPolling] = useState(true)

  // Create a custom setter for processing status that also updates localStorage
  const updateProcessingStatus = (status: string) => {
    // Update the state
    setProcessingStatus(status);
    
    // Also update localStorage if needed
    if (typeof window !== 'undefined') {
      if (status === "") {
        // Clear the status from localStorage
        localStorage.removeItem('processingStatus');
      } else if (!status.toLowerCase().includes('database')) {
        // Only store non-database related messages
        localStorage.setItem('processingStatus', status);
      }
    }
  };
  
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
      
      // If the job is now completed, failed, cancelled or removed, mark it for removal
      if (
        (updatedJob.status === "completed" || 
         updatedJob.status === "failed" || 
         updatedJob.status === "cancelled" ||
         updatedJob.status === "removed") && 
        !newJobs[index].markedForRemoval
      ) {
        // Mark the job for removal
        newJobs[index] = {
          ...newJobs[index],
          markedForRemoval: true,
        }
        
        // Clear processing status if this was a cancelled/removed job
        if (updatedJob.status === "cancelled" || updatedJob.status === "removed") {
          updateProcessingStatus("");
          
          // For removed jobs, immediately remove from the jobs array and localStorage
          if (updatedJob.status === "removed") {
            console.log(`Immediately removing job ${updatedJob.id} from tracking (status: removed)`);
            
            // Remove from localStorage
            if (typeof window !== 'undefined') {
              try {
                const jobsData = localStorage.getItem('ingestionJobs');
                if (jobsData) {
                  const parsedJobs = JSON.parse(jobsData);
                  const cleanedJobs = parsedJobs.filter((job: Job) => job.id !== updatedJob.id);
                  localStorage.setItem('ingestionJobs', JSON.stringify(cleanedJobs));
                  console.log(`Removed job ${updatedJob.id} from localStorage`);
                }
              } catch (error) {
                console.error('Error removing job from localStorage:', error);
              }
            }
            
            // Return a new array without this job
            return prevJobs.filter(job => job.id !== updatedJob.id);
          }
          
          // For cancelled jobs, just remove from localStorage but keep in memory briefly
          const filteredJobs = prevJobs.filter(job => job.id !== updatedJob.id);
          saveJobsToStorage(filteredJobs);
        }
        
        // Remove the job after a delay
        const removalDelay = (updatedJob.status === "cancelled" ) ? 3000 : 5000;
        setTimeout(() => {
          setJobs((currentJobs) => {
            const filteredJobs = currentJobs.filter((job) => job.id !== updatedJob.id);
            // Update localStorage when removing jobs
            saveJobsToStorage(filteredJobs);
            return filteredJobs;
          })
        }, removalDelay) // Remove after delay (shorter for cancelled/removed jobs)
      }
      
      // For any status update, persist to localStorage
      if (typeof window !== 'undefined') {
        saveJobsToStorage(newJobs);
      }
      
      return newJobs
    })
  }

  // Remove a job
  const removeJob = (jobId: string) => {
    setJobs((prevJobs) => {
      // First, find the job and mark it as removed
      const updatedJobs = prevJobs.map(job => {
        if (job.id === jobId) {
          return {
            ...job,
            status: "removed",
            markedForRemoval: true,
            details: "Job removed from tracking"
          };
        }
        return job;
      });
      
      // Then filter it out completely
      const filteredJobs = updatedJobs.filter((job) => job.id !== jobId);
      
      if (typeof window !== 'undefined') {
        // Save the updated jobs to localStorage
        saveJobsToStorage(filteredJobs);
        
        // Also explicitly remove this job ID from any tracking in localStorage
        try {
          const jobsData = localStorage.getItem('ingestionJobs');
          if (jobsData) {
            const parsedJobs = JSON.parse(jobsData);
            const cleanedJobs = parsedJobs.filter((job: Job) => job.id !== jobId);
            localStorage.setItem('ingestionJobs', JSON.stringify(cleanedJobs));
          }
        } catch (error) {
          console.error('Error cleaning job from localStorage:', error);
        }
      }
      
      return filteredJobs;
    });
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
    updateProcessingStatus("");
    
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
        
        // Use fetchWithAuth for proper token expiration handling
        const response = await fetchWithAuth(`/api/datapuur/cancel-job/${job.id}`, {
          method: "POST",
        });
        
        console.log(`API response status: ${response.status}`);
        
        // Handle 404 Not Found responses - job no longer exists
        if (response.status === 404) {
          console.log(`Job ${job.id} no longer exists (404), marking as removed`);
          
          // Mark the job as removed since it no longer exists on the server
          updateJob({
            ...job,
            status: "removed",
            markedForRemoval: true,
            endTime: new Date().toISOString(),
            details: "Job no longer exists on server"
          });
          continue;
        }
        
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
      
      // Find active jobs (running or queued), but skip any that are marked for removal
      const activeJobs = storedJobs.filter(job => {
        // First check if the job is running or queued (this implicitly means it's not removed)
        const isActiveStatus = job.status === "running" || job.status === "queued";
        // Then check other conditions
        return isActiveStatus && 
               !job.id.startsWith("temp-") &&
               !job.markedForRemoval;
      });
      
      if (activeJobs.length === 0) return;
      
      try {
        // Check the status of each active job
        for (const job of activeJobs) {
          const apiBaseUrl = getApiBaseUrl();
          const response = await fetchWithAuth(`/api/datapuur/job-status/${job.id}`, {
            headers: {
              // Ensure token is accessed client-side
              Authorization: `Bearer ${typeof window !== 'undefined' ? localStorage.getItem("token") : ''}`,
            },
          });
          
          // Handle 404 Not Found responses - job no longer exists
          if (response.status === 404) {
            console.log(`Job ${job.id} no longer exists (404), removing from tracking`);
            
            // Mark the job as removed
            updateJob({
              ...job,
              status: "removed" as Job["status"],  // Type assertion to fix lint error
              markedForRemoval: true,
              details: "Job no longer exists on server"
            });
            
            continue;
          }
          
          if (response.ok) {
            const updatedJob = await response.json();
            // Update the job with the latest status
            updateJob(updatedJob);
            
            // Clear the processing status for any job that has completed, failed, or been cancelled
            if (updatedJob.status === "completed" || updatedJob.status === "failed" || updatedJob.status === "cancelled") {
              // Clear the processing status to remove the "File Processing" message
              updateProcessingStatus("");
              console.log(`Job ${updatedJob.id} (${updatedJob.type}) ${updatedJob.status} - clearing processing status on initial check`);
            }
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

    // Function to check status of all jobs
    const checkJobs = async () => {
      try {
        const apiBaseUrl = getApiBaseUrl()
        const token = localStorage.getItem("token")
        
        if (!token) return // Skip if no token
        
        // Check each running or queued job, but skip any that are marked for removal
        const jobsToCheck = jobs.filter(job => {
          // First check if the job is running or queued (this implicitly means it's not removed)
          const isActiveStatus = job.status === "running" || job.status === "queued";
          // Then check if it's not marked for removal
          return isActiveStatus && !job.markedForRemoval;
        })
        
        if (jobsToCheck.length === 0) return // Skip if no jobs to check
        
        for (const job of jobsToCheck) {
          try {
            const response = await fetchWithAuth(`/api/datapuur/job-status/${job.id}`, {
              headers: {
                Authorization: `Bearer ${token}`
              }
            })
            
            // Handle 404 Not Found responses - job no longer exists
            if (response.status === 404) {
              console.log(`Job ${job.id} no longer exists (404), removing from tracking`)
              
              // Remove the job from localStorage
              updateJob({
                ...job,
                status: "removed" as Job["status"],  // Type assertion to fix lint error
                markedForRemoval: true,
                details: "Job no longer exists on server"
              })
              
              // Continue to next job
              continue
            }
            
            if (!response.ok) {
              console.error(`Error checking job ${job.id}: ${response.statusText}`)
              continue
            }
            
            const data = await response.json()
            
            // Update job status
            updateJob({
              ...job,
              status: data.status,
              progress: data.progress,
              details: data.details || job.details,
              error: data.error,
              endTime: data.end_time || job.endTime
            })
            
            // Clear the processing status for any job that has completed, failed, or been cancelled
            if (data.status === "completed" || data.status === "failed" || data.status === "cancelled") {
              // Clear the processing status to remove the "File Processing" message
              updateProcessingStatus("");
              console.log(`Job ${job.id} (${job.type}) ${data.status} - clearing processing status`);
            }
          } catch (error) {
            console.error(`Error polling job status for job ${job.id}:`, error)
          }
        }
      } catch (error) {
        console.error("Error polling job status:", error)
      }
    }

    // Run immediately when jobs change or component mounts
    checkJobs()
    
    // Then set up the polling interval - poll more frequently to show progress updates better
    const pollInterval = setInterval(checkJobs, 5000) // Poll every 3 seconds for more responsive progress updates

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
    setProcessingStatus: updateProcessingStatus, // Use our custom function that handles localStorage
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
