"use client"

import { createContext, useContext, useState, useEffect, ReactNode } from "react"
import { useToast } from "@/components/ui/use-toast"

// Define job types
export type JobType = "load_data" | "clean_data"

// Define job status types
export type JobStatus = "pending" | "running" | "completed" | "failed" | "cancelled"

// Define job interface
export interface KGJob {
  id: string
  schema_id: number
  job_type: JobType
  status: JobStatus
  progress: number
  message: string
  created_at: string
  updated_at: string
  result?: Record<string, any>
  error?: string
}

// Context state type
interface KGInsightsJobContextType {
  // State
  jobs: KGJob[]
  isLoading: boolean
  error: string | null
  
  // Actions
  refreshJobs: () => Promise<void>
  startLoadDataJob: (schemaId: number, options?: Record<string, any>) => Promise<KGJob | null>
  startCleanDataJob: (schemaId: number, options?: Record<string, any>) => Promise<KGJob | null>
  cancelJob: (jobId: string) => Promise<boolean>
  getJobsForSchema: (schemaId: number) => KGJob[]
  getActiveJobsForSchema: (schemaId: number) => KGJob[]
  clearCompletedJobs: () => void
}

// Local storage key
const STORAGE_KEY = 'kginsights-jobs';

// Function to safely handle localStorage
const safeLocalStorage = {
  getItem: (key: string) => {
    if (typeof window === 'undefined') return null;
    try {
      return localStorage.getItem(key);
    } catch (err) {
      console.error("Error retrieving from localStorage:", err);
      return null;
    }
  },
  setItem: (key: string, value: string) => {
    if (typeof window === 'undefined') return;
    try {
      localStorage.setItem(key, value);
    } catch (err) {
      console.error("Error saving to localStorage:", err);
    }
  }
};

// Create context
const KGInsightsJobContext = createContext<KGInsightsJobContextType | undefined>(undefined)

// Provider component
export function KGInsightsJobProvider({ children }: { children: ReactNode }) {
  const [jobs, setJobs] = useState<KGJob[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pollInterval, setPollInterval] = useState<NodeJS.Timeout | null>(null)
  const { toast } = useToast()

  // Initialize jobs from localStorage
  useEffect(() => {
    // Ensure this only runs on the client
    if (typeof window !== 'undefined') {
      const storedJobsJSON = safeLocalStorage.getItem(STORAGE_KEY);
      if (storedJobsJSON) {
        try {
          const storedJobs = JSON.parse(storedJobsJSON);
          
          // Filter out all completed/failed jobs that are older than 5 minutes
          // This ensures we don't show old completed jobs when just visiting the page
          const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
          const filteredJobs = storedJobs.filter((job: KGJob) => {
            // Keep only active jobs or very recent completed/failed jobs
            if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
              return new Date(job.updated_at) > fiveMinutesAgo;
            }
            return true;
          });
          
          // Only set jobs if there are active ones or very recent completed ones
          setJobs(filteredJobs);
          
          // Update localStorage if we filtered anything out
          if (filteredJobs.length !== storedJobs.length) {
            safeLocalStorage.setItem(STORAGE_KEY, JSON.stringify(filteredJobs));
          }
        } catch (err) {
          console.error("Error parsing stored jobs:", err);
        }
      }
    }
    
    // Only poll for active jobs if we have any
    const hasActiveJobsInStorage = jobs.some(job => 
      job.status === 'pending' || job.status === 'running'
    );
    
    if (hasActiveJobsInStorage) {
      // Start polling only if we have active jobs
      refreshJobs();
      const interval = setInterval(() => {
        // Polling logic only makes sense client-side where jobs might change
        if (typeof window !== 'undefined' && hasActiveJobs()) {
          refreshJobs();
        }
      }, 1000); // Poll every 1 second instead of 3 seconds
      
      setPollInterval(interval);
      
      return () => {
        if (interval) clearInterval(interval);
      };
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  
  // Update localStorage when jobs change
  useEffect(() => {
    // Ensure this only runs on the client
    if (typeof window !== 'undefined' && jobs.length > 0) {
      safeLocalStorage.setItem(STORAGE_KEY, JSON.stringify(jobs));
    }
  }, [jobs]);

  // Check if there are any active jobs
  const hasActiveJobs = () => {
    return jobs.some(job => job.status === "pending" || job.status === "running")
  }

  // Fetch all jobs from API
  const refreshJobs = async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      const token = safeLocalStorage.getItem('token');
      const response = await fetch('/api/processing-jobs', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (!response.ok) {
        throw new Error(`Failed to fetch jobs: ${response.statusText}`)
      }
      
      const data = await response.json()
      
      // Update local state while preserving any jobs not returned by the API
      setJobs(prevJobs => {
        // Create a map of existing jobs by ID for quick lookup
        const existingJobsMap = new Map(prevJobs.map(job => [job.id, job]));
        
        // Process the new jobs from the API
        const updatedJobs = data.map((apiJob: KGJob) => {
          const existingJob = existingJobsMap.get(apiJob.id);
          
          // If this is a temporary job that's been replaced by a real one, use the API data
          if (existingJob && existingJob.id.startsWith('temp-')) {
            return apiJob;
          }
          
          // For existing jobs, always use the API data (server is source of truth)
          return apiJob;
        });
        
        // Keep only the temporary jobs that aren't in the API response yet
        const tempJobs = prevJobs.filter(job => 
          job.id.startsWith('temp-') && 
          !data.some((apiJob: KGJob) => apiJob.schema_id === job.schema_id && apiJob.job_type === job.job_type)
        );
        
        return [...tempJobs, ...updatedJobs];
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error fetching jobs'
      setError(errorMessage)
      console.error(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  // Clear completed jobs
  const clearCompletedJobs = () => {
    setJobs(prevJobs => 
      prevJobs.filter(job => 
        job.status !== 'completed' && job.status !== 'failed' && job.status !== 'cancelled'
      )
    );
  }

  // Start a data loading job
  const startLoadDataJob = async (schemaId: number, options: Record<string, any> = {}) => {
    try {
      // First check if there's already an active job for this schema
      const activeJobs = getActiveJobsForSchema(schemaId)
      if (activeJobs.length > 0) {
        toast({
          title: "Job Already Running",
          description: `There's already an active job for this schema. Please wait for it to complete.`,
          variant: "default",
        })
        return null
      }
      
      // Create a temporary pending job to show immediately
      const tempJobId = `temp-${Date.now()}`
      const tempJob: KGJob = {
        id: tempJobId,
        schema_id: schemaId,
        job_type: "load_data" as JobType,
        status: "pending" as JobStatus,
        progress: 0,
        message: "Initializing data load job...",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
      
      // Add the temporary job to state immediately
      setJobs(prevJobs => [...prevJobs, tempJob])
      
      // Start the job
      const token = safeLocalStorage.getItem('token');
      const response = await fetch('/api/processing-jobs/load-data', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          schema_id: schemaId,
          ...options
        }),
      })
      
      if (!response.ok) {
        // Remove the temporary job if the request failed
        setJobs(prevJobs => prevJobs.filter(job => job.id !== tempJobId))
        throw new Error(`Failed to start load data job: ${response.statusText}`)
      }
      
      const data = await response.json()
      
      // Replace the temporary job with the real one
      setJobs(prevJobs => prevJobs.map(job => 
        job.id === tempJobId ? data : job
      ))
      
      // Refresh jobs to ensure we have the latest data
      await refreshJobs()
      
      toast({
        title: "Data Load Started",
        description: "The data loading process has started and will run in the background.",
        variant: "default",
      })
      
      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error starting data load'
      setError(errorMessage)
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      })
      return null
    }
  }

  // Start a data cleaning job
  const startCleanDataJob = async (schemaId: number, options: Record<string, any> = {}) => {
    try {
      // First check if there's already an active job for this schema
      const activeJobs = getActiveJobsForSchema(schemaId)
      if (activeJobs.length > 0) {
        toast({
          title: "Job Already Running",
          description: `There's already an active job for this schema. Please wait for it to complete.`,
          variant: "default",
        })
        return null
      }
      
      // Create a temporary pending job to show immediately
      const tempJobId = `temp-${Date.now()}`
      const tempJob: KGJob = {
        id: tempJobId,
        schema_id: schemaId,
        job_type: "clean_data" as JobType,
        status: "pending" as JobStatus,
        progress: 0,
        message: "Initializing data cleaning job...",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
      
      // Add the temporary job to state immediately
      setJobs(prevJobs => [...prevJobs, tempJob])
      
      // Start the job
      const token = safeLocalStorage.getItem('token');
      const response = await fetch('/api/processing-jobs/clean-data', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          schema_id: schemaId,
          ...options
        }),
      })
      
      if (!response.ok) {
        // Remove the temporary job if the request failed
        setJobs(prevJobs => prevJobs.filter(job => job.id !== tempJobId))
        throw new Error(`Failed to start clean data job: ${response.statusText}`)
      }
      
      const data = await response.json()
      
      // Replace the temporary job with the real one
      setJobs(prevJobs => prevJobs.map(job => 
        job.id === tempJobId ? data : job
      ))
      
      // Refresh jobs to ensure we have the latest data
      await refreshJobs()
      
      toast({
        title: "Data Clean Started",
        description: "The data cleaning process has started and will run in the background.",
        variant: "default",
      })
      
      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error starting data cleaning'
      setError(errorMessage)
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      })
      return null
    }
  }

  // Cancel a job
  const cancelJob = async (jobId: string) => {
    try {
      const token = safeLocalStorage.getItem('token');
      const response = await fetch(`/api/processing-jobs/${jobId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (!response.ok) {
        throw new Error(`Failed to cancel job: ${response.statusText}`)
      }
      
      // Update local state immediately, then refresh
      setJobs(prevJobs => 
        prevJobs.map(job => 
          job.id === jobId 
            ? { ...job, status: 'cancelled', message: 'Job cancelled by user' } 
            : job
        )
      );
      
      await refreshJobs()
      
      toast({
        title: "Job Cancelled",
        description: "The job has been cancelled successfully.",
        variant: "default",
      })
      
      return true
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error cancelling job'
      setError(errorMessage)
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      })
      return false
    }
  }

  // Get all jobs for a specific schema
  const getJobsForSchema = (schemaId: number) => {
    return jobs.filter(job => job.schema_id === schemaId)
  }

  // Get only active jobs for a specific schema
  const getActiveJobsForSchema = (schemaId: number) => {
    return jobs.filter(
      job => job.schema_id === schemaId && 
      (job.status === "pending" || job.status === "running")
    )
  }

  // Context value
  const value = {
    jobs,
    isLoading,
    error,
    refreshJobs,
    startLoadDataJob,
    startCleanDataJob,
    cancelJob,
    getJobsForSchema,
    getActiveJobsForSchema,
    clearCompletedJobs
  }

  return (
    <KGInsightsJobContext.Provider value={value}>
      {children}
    </KGInsightsJobContext.Provider>
  )
}

// Custom hook to use the KGInsights job context
export function useKGInsightsJobs() {
  const context = useContext(KGInsightsJobContext)
  
  if (context === undefined) {
    throw new Error("useKGInsightsJobs must be used within a KGInsightsJobProvider")
  }
  
  return context
}
