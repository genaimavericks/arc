"use client"

import { useState, useEffect } from "react"
import { ReloadIcon, TrashIcon, StopIcon, PlayIcon } from "@radix-ui/react-icons"
import { Button } from "@/components/ui/button"
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { toast } from "@/components/ui/use-toast"
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
import { Input } from "@/components/ui/input"
import { getApiBaseUrl } from "@/lib/config"

// Define job type
interface Job {
  id: string
  name: string
  type: string
  status: string
  createdAt: string
  updatedAt: string
  progress: number
  details: string
  error?: string
}

export function JobControlTab() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState("")
  const [jobToDelete, setJobToDelete] = useState<Job | null>(null)
  const [jobToStop, setJobToStop] = useState<Job | null>(null)
  
  // Fetch all jobs from the system
  const fetchJobs = async () => {
    setIsLoading(true)
    try {
      const apiBaseUrl = getApiBaseUrl()
      const token = localStorage.getItem("token")
      
      if (!token) {
        throw new Error("No authentication token found")
      }

      const response = await fetch(`${apiBaseUrl}/api/datapuur/admin/jobs`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      if (!response.ok) {
        throw new Error(`Error fetching jobs: ${response.statusText}`)
      }

      const data = await response.json()
      setJobs(data)
    } catch (error) {
      console.error("Failed to fetch jobs:", error)
      toast({
        title: "Error",
        description: "Failed to load jobs. Please try again.",
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
    }
  }

  // Stop a job
  const stopJob = async (jobId: string) => {
    try {
      const apiBaseUrl = getApiBaseUrl()
      const token = localStorage.getItem("token")
      
      if (!token) {
        throw new Error("No authentication token found")
      }

      const response = await fetch(`${apiBaseUrl}/api/datapuur/admin/jobs/${jobId}/stop`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        }
      })

      if (!response.ok) {
        throw new Error(`Error stopping job: ${response.statusText}`)
      }
      
      // Mark job as cancelled in localStorage
      const ingestionJobsData = localStorage.getItem("ingestionJobs");
      if (ingestionJobsData) {
        try {
          const ingestionJobs = JSON.parse(ingestionJobsData);
          const updatedJobs = ingestionJobs.map((job: any) => 
            job.id === jobId 
              ? { ...job, status: "cancelled", markedForRemoval: true } 
              : job
          );
          localStorage.setItem("ingestionJobs", JSON.stringify(updatedJobs));
          console.log(`Marked job ${jobId} as cancelled in localStorage`);
        } catch (error) {
          console.error("Error updating localStorage:", error);
        }
      }

      toast({
        title: "Success",
        description: "Job stopped successfully"
      })
      
      // Refresh the job list
      fetchJobs()
    } catch (error) {
      console.error("Failed to stop job:", error)
      toast({
        title: "Error",
        description: "Failed to stop job. Please try again.",
        variant: "destructive"
      })
    }
  }

  // Delete a job
  const deleteJob = async (jobId: string) => {
    try {
      const apiBaseUrl = getApiBaseUrl()
      const token = localStorage.getItem("token")
      
      if (!token) {
        throw new Error("No authentication token found")
      }

      const response = await fetch(`${apiBaseUrl}/api/datapuur/admin/jobs/${jobId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      if (!response.ok) {
        throw new Error(`Error deleting job: ${response.statusText}`)
      }

      // Clean up job from localStorage
      const ingestionJobsData = localStorage.getItem("ingestionJobs");
      if (ingestionJobsData) {
        try {
          const ingestionJobs = JSON.parse(ingestionJobsData);
          const updatedJobs = ingestionJobs.filter((job: any) => job.id !== jobId);
          localStorage.setItem("ingestionJobs", JSON.stringify(updatedJobs));
          console.log(`Removed job ${jobId} from localStorage`);
        } catch (error) {
          console.error("Error updating localStorage:", error);
        }
      }

      toast({
        title: "Success",
        description: "Job deleted successfully"
      })
      
      // Refresh the job list
      fetchJobs()
    } catch (error) {
      console.error("Failed to delete job:", error)
      toast({
        title: "Error",
        description: "Failed to delete job. Please try again.",
        variant: "destructive"
      })
    }
  }

  // Load data on component mount
  useEffect(() => {
    fetchJobs()
    
    // Set up polling for job updates (every 15 seconds)
    const interval = setInterval(fetchJobs, 15000)
    
    return () => clearInterval(interval)
  }, [])

  // Filter jobs based on search term
  const filteredJobs = jobs.filter(job => 
    job.id.toLowerCase().includes(searchTerm.toLowerCase()) || 
    job.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    job.type.toLowerCase().includes(searchTerm.toLowerCase()) ||
    job.status.toLowerCase().includes(searchTerm.toLowerCase())
  )

  // Get status badge color
  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "completed":
        return "bg-green-500 hover:bg-green-600"
      case "running":
      case "queued":
        return "bg-blue-500 hover:bg-blue-600"
      case "failed":
        return "bg-red-500 hover:bg-red-600"
      case "cancelled":
        return "bg-orange-500 hover:bg-orange-600"
      default:
        return "bg-gray-500 hover:bg-gray-600"
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold mb-1">Job Control</h2>
          <p className="text-muted-foreground text-sm">
            Manage all system jobs from one place (admin only)
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Input
            placeholder="Search jobs..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="max-w-[250px]"
          />
          <Button 
            onClick={fetchJobs} 
            variant="outline" 
            size="icon"
            disabled={isLoading}
          >
            <ReloadIcon className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      <div className="border rounded-md">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Progress</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8">
                  <ReloadIcon className="h-5 w-5 animate-spin mx-auto mb-2" />
                  <span className="text-sm text-muted-foreground">Loading jobs...</span>
                </TableCell>
              </TableRow>
            ) : filteredJobs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8">
                  <p className="text-muted-foreground">No jobs found</p>
                </TableCell>
              </TableRow>
            ) : (
              filteredJobs.map((job) => (
                <TableRow key={job.id}>
                  <TableCell className="font-mono text-xs">{job.id}</TableCell>
                  <TableCell>{job.name}</TableCell>
                  <TableCell>{job.type}</TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(job.status)}>
                      {job.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
                      <div 
                        className="bg-primary h-2.5 rounded-full" 
                        style={{ width: `${job.progress}%` }}
                      ></div>
                    </div>
                    <span className="text-xs text-muted-foreground mt-1">
                      {job.progress}%
                    </span>
                  </TableCell>
                  <TableCell>{new Date(job.createdAt).toLocaleString()}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {/* Stop job button (only for running/queued jobs) */}
                      {(job.status === "running" || job.status === "queued") && (
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button 
                              variant="outline" 
                              size="icon"
                              onClick={() => setJobToStop(job)}
                            >
                              <StopIcon className="h-4 w-4" />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Stop Job</AlertDialogTitle>
                              <AlertDialogDescription>
                                Are you sure you want to stop this job? This action cannot be undone.
                                <div className="mt-2 p-2 bg-muted rounded-md">
                                  <p><strong>ID:</strong> {jobToStop?.id}</p>
                                  <p><strong>Name:</strong> {jobToStop?.name}</p>
                                  <p><strong>Type:</strong> {jobToStop?.type}</p>
                                </div>
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancel</AlertDialogCancel>
                              <AlertDialogAction 
                                onClick={() => {
                                  if (jobToStop) {
                                    stopJob(jobToStop.id)
                                  }
                                }}
                              >
                                Stop Job
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      )}
                      
                      {/* Delete job button */}
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button 
                            variant="outline" 
                            size="icon"
                            onClick={() => setJobToDelete(job)}
                          >
                            <TrashIcon className="h-4 w-4" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Delete Job</AlertDialogTitle>
                            <AlertDialogDescription>
                              Are you sure you want to delete this job? This action cannot be undone.
                              <div className="mt-2 p-2 bg-muted rounded-md">
                                <p><strong>ID:</strong> {jobToDelete?.id}</p>
                                <p><strong>Name:</strong> {jobToDelete?.name}</p>
                                <p><strong>Type:</strong> {jobToDelete?.type}</p>
                              </div>
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction 
                              onClick={() => {
                                if (jobToDelete) {
                                  deleteJob(jobToDelete.id)
                                }
                              }}
                            >
                              Delete Job
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
