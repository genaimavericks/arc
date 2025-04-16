"use client"

import { useState, useRef, useEffect } from "react"
import { FileUp, X, FileText, Upload, AlertCircle, Eye, BarChart } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { motion } from "framer-motion"
import { getApiBaseUrl } from "@/lib/config"
import { useIngestion, Job } from "@/lib/ingestion-context"

// Define component props interface
interface FileUploadProps {
  onSchemaDetected: (schema: any) => void
  isProcessing: boolean
  setIsProcessing: (isProcessing: boolean) => void
  chunkSize: number
  onStatusChange: (status: string) => void
  onJobCreated: (job: Job) => void
  onJobUpdated?: (job: Job) => void
  onError: (error: { message: string }) => void
}

export function FileUpload({
  onSchemaDetected,
  isProcessing,
  setIsProcessing,
  chunkSize,
  onStatusChange,
  onJobCreated,
  onJobUpdated,
  onError,
}: FileUploadProps) {
  // Use the global ingestion context
  const { 
    addJob, 
    updateJob, 
    addError, 
    setProcessingStatus, 
    processingStatus, 
    jobs, 
    removeJob 
  } = useIngestion()
  
  // Add references for cancellation
  const [isCancelling, setIsCancelling] = useState(false)
  const xhrRef = useRef<XMLHttpRequest | null>(null)
  const uploadIdRef = useRef<string | null>(null)
  
  // Update the component to handle multiple files
  // Change the file state from a single file to an array of files
  const [files, setFiles] = useState<File[]>([])
  // Add state to track files that are currently being processed
  const [processingFiles, setProcessingFiles] = useState<File[]>([])
  // Replace the single file state with files array
  // const [file, setFile] = useState(null)
  const [dragActive, setDragActive] = useState(false)
  // Update the uploadProgress state to track multiple files
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({})
  const [error, setError] = useState("")
  const [previewData, setPreviewData] = useState<{ headers: string[], rows: any[][], fileName: string } | null>(null)
  const [isPreviewLoading, setIsPreviewLoading] = useState(false)
  const [generateProfile, setGenerateProfile] = useState(true)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDrag = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  // Update the drag and drop handler to accept multiple files
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      // Process all dropped files
      const droppedFiles = Array.from(e.dataTransfer.files) as File[]
      handleFiles(droppedFiles)
    }
  }

  // Update the file input change handler to accept multiple files
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault()
    if (e.target.files && e.target.files.length > 0) {
      // Process all selected files
      const selectedFiles = Array.from(e.target.files) as File[]
      handleFiles(selectedFiles)
    }
  }

  // Create a new function to handle multiple files
  const handleFiles = (newFiles: File[]) => {
    // Filter out unsupported file types
    const validFiles = newFiles.filter((file) => {
      const fileType = file.name.split(".").pop()?.toLowerCase() || "";
      if (fileType !== "csv" && fileType !== "json") {
        setError(`File ${file.name} is not supported. Only CSV and JSON files are allowed.`)
        return false
      }

      // Check file size (limit to 2GB for browser processing)
      if (file.size > 2048 * 1024 * 1024) {
        setError(`File ${file.name} exceeds 2GB limit.`)
        return false
      }

      return true
    })

    // Add valid files to the state
    if (validFiles.length > 0) {
      setFiles((prevFiles) => [...prevFiles, ...validFiles])
      setError("")
    }
  }

  // Update the removeFile function to remove a specific file
  const removeFile = (index: number) => {
    setFiles((prevFiles) => {
      const updatedFiles = prevFiles.filter((_, i) => i !== index);
      // Clear preview data if the previewed file is removed
      if (previewData && files[index] && previewData.fileName === files[index].name) {
        setPreviewData(null);
      }
      return updatedFiles;
    });
    setUploadProgress({});
    setError("");
  }

  // Update the handleUpload function to handle multiple files
  const handleUpload = async () => {
    if (files.length === 0) return
    
    // Instead of blocking the entire UI, just mark these files as processing
    // and move them to the processingFiles array
    const filesToProcess = [...files]
    setProcessingFiles(prev => [...prev, ...filesToProcess])
    
    // Clear the main files array to allow new files to be added
    setFiles([])
    
    setIsProcessing(true)
    setError("")
    setUploadProgress({})
    onStatusChange("Starting upload...")
    setProcessingStatus("Starting upload...")
    
    // Process each file sequentially
    for (let i = 0; i < filesToProcess.length; i++) {
      // Check if we should stop processing (files array might have been cleared by cancelUpload)
      if (isCancelling) {
        console.log("Upload cancelled, stopping file processing")
        break
      }
      
      const file = filesToProcess[i]
      const fileId = `${file.name}-${file.size}-${Date.now()}`
      
      try {
        // Check file type
        const fileExtension = file.name.split('.').pop()?.toLowerCase() || ''
        const isCSV = fileExtension === 'csv'
        const isJSON = fileExtension === 'json'
        const isParquet = fileExtension === 'parquet'
        
        if (!isCSV && !isJSON && !isParquet) {
          throw new Error(`Unsupported file type: ${fileExtension}. Only CSV, JSON, and Parquet files are supported.`)
        }
        
        // Set processing status with file type information for better user feedback
        onStatusChange(`Preparing to upload ${file.name} (${fileExtension.toUpperCase()} file)...`)
        setProcessingStatus(`Preparing to upload ${file.name} (${fileExtension.toUpperCase()} file)...`)
        
        // Create a job object immediately to show in the UI, even before the upload completes
        // This ensures the job card appears right away for large files
        const tempJobId = `temp-${Date.now()}-${i}`
        const initialJob: Job = {
          id: tempJobId,
          name: file.name,
          type: "file",
          status: "uploading", // Changed from "queued" to "uploading" for better user feedback
          progress: 0,
          startTime: new Date().toISOString(),
          endTime: null,
          details: `File: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`,
        }
        
        // Notify about the job immediately - use both local and global state
        if (onJobCreated) {
          console.log("Creating initial job:", initialJob)
          onJobCreated(initialJob)
        }
        // Also add to global context
        addJob(initialJob)

        const formData = new FormData()
        formData.append("file", file)
        formData.append("chunkSize", chunkSize.toString())
        
        // For large files, use a streaming approach with chunked upload
        const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB chunks for better performance
        
        if (file.size > 50 * 1024 * 1024) { // Only use chunked upload for files > 50MB
          // Use chunked upload for large files
          const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
          let uploadedChunks = 0;
          
          // Create a unique upload ID for this file
          const uploadId = `upload-${Date.now()}-${Math.random().toString(36).substring(2, 15)}`;
          uploadIdRef.current = uploadId;
          
          for (let start = 0; start < file.size; start += CHUNK_SIZE) {
            // Check for cancellation before each chunk
            if (isCancelling || localStorage.getItem(`cancelled_upload_${uploadId}`) === "true") {
              console.log("Upload cancelled during chunking, stopping chunk upload")
              throw new Error("Upload cancelled by user")
            }
            
            const chunk = file.slice(start, start + CHUNK_SIZE);
            const chunkFormData = new FormData();
            chunkFormData.append('file', chunk, file.name);
            chunkFormData.append('chunkSize', chunkSize.toString());
            chunkFormData.append('chunkIndex', String(uploadedChunks));
            chunkFormData.append('totalChunks', String(totalChunks));
            chunkFormData.append('uploadId', uploadId);
            
            try {
              // Send the chunk
              const apiBaseUrl = getApiBaseUrl();
              const response = await fetch(`${apiBaseUrl}/api/datapuur/upload-chunk`, {
                method: 'POST',
                headers: {
                  Authorization: `Bearer ${localStorage.getItem("token")}`,
                },
                body: chunkFormData,
              });
              
              if (!response.ok) {
                throw new Error(`Failed to upload chunk ${uploadedChunks + 1} of ${totalChunks}`);
              }
              
              uploadedChunks++;
              
              // Update progress based on chunks
              const percentComplete = Math.round((uploadedChunks / totalChunks) * 100);
              
              // Update the job progress
              const progressJob: Job = {
                ...initialJob,
                progress: percentComplete,
                details: `Uploading: ${percentComplete}% of ${(file.size / 1024 / 1024).toFixed(2)} MB`,
              };
              
              // Update the job in the UI
              if (onJobUpdated) {
                onJobUpdated(progressJob)
              }
              // Also update in global context
              updateJob(progressJob)
              
              // Update status
              onStatusChange(`Uploading file ${i + 1} of ${filesToProcess.length}: ${file.name} (${percentComplete}%)...`)
              setProcessingStatus(`Uploading file ${i + 1} of ${filesToProcess.length}: ${file.name} (${percentComplete}%)...`)
            } catch (error) {
              console.error("Error uploading chunk:", error);
              throw error;
            }
          }
          
          // Check for cancellation before completing the upload
          if (isCancelling || localStorage.getItem(`cancelled_upload_${uploadId}`) === "true") {
            console.log("Upload cancelled before completion, stopping upload process")
            throw new Error("Upload cancelled by user")
          }
          
          // Complete the chunked upload
          const apiBaseUrl = getApiBaseUrl();
          const completeResponse = await fetch(`${apiBaseUrl}/api/datapuur/complete-chunked-upload`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${localStorage.getItem("token")}`,
            },
            body: JSON.stringify({
              uploadId,
              fileName: file.name,
              totalChunks,
              chunkSize: CHUNK_SIZE,
              totalSize: file.size,
              originalChunkSize: chunkSize
            }),
          });
          
          if (!completeResponse.ok) {
            const errorText = await completeResponse.text();
            let errorMessage = "Failed to complete chunked upload";
            try {
              const errorData = JSON.parse(errorText);
              errorMessage = errorData.detail || errorMessage;
            } catch (e) {
              // If JSON parsing fails, use the raw error text if available
              if (errorText) {
                errorMessage = errorText;
              }
            }
            console.error("Chunked upload completion error:", errorMessage);
            throw new Error(errorMessage);
          }
          
          const data = await completeResponse.json();
          
          // Check if the upload was cancelled by the server
          if (data.cancelled) {
            console.log("Server reported upload was cancelled")
            throw new Error("Upload cancelled by user")
          }
          
          onStatusChange(`File ${i + 1} uploaded successfully! Processing data...`)
          setProcessingStatus(`File ${i + 1} uploaded successfully! Processing data...`)
          
          // Continue with ingestion as before
          const ingestResponse = await fetch(`${apiBaseUrl}/api/datapuur/ingest-file`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${localStorage.getItem("token")}`,
            },
            body: JSON.stringify({
              file_id: data.file_id,
              file_name: file.name,
              chunk_size: chunkSize,
            }),
          });
          
          if (!ingestResponse.ok) {
            const errorData = await ingestResponse.json();
            throw new Error(errorData.detail || `Failed to start ingestion for ${file.name}`);
          }
          
          const ingestData = await ingestResponse.json();
          
          // Check if the ingestion was cancelled by the server
          if (ingestData.cancelled) {
            console.log("Server reported ingestion was cancelled")
            throw new Error("Upload cancelled by user")
          }
          
          // Update the job with the real job ID
          const updatedJob: Job = {
            id: ingestData.job_id,
            name: file.name,
            type: "file",
            status: "running",
            progress: 0,
            startTime: new Date().toISOString(),
            endTime: null,
            details: `File: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`,
          };
          
          // Replace the temporary job with the real one - use both local and global state
          if (onJobUpdated) {
            onJobUpdated(updatedJob)
          }
          // Also notify about job creation to ensure it appears in the jobs list
          if (onJobCreated) {
            onJobCreated(updatedJob)
          }
          
          onStatusChange(`Ingestion job started for ${file.name} with ID: ${ingestData.job_id}`)
          setProcessingStatus(`Ingestion job started for ${file.name} with ID: ${ingestData.job_id}`)
          
          // Update progress - ingestion started
          setUploadProgress((prev) => ({ ...prev, [fileId]: 90 }))
          
          // If profile generation is enabled, request a profile for this file
          if (generateProfile && !isCancelling && localStorage.getItem(`cancelled_upload_${uploadIdRef.current}`) !== "true") {
            try {
              // First, get file details to get the file path
              const fileDetailsResponse = await fetch(`${apiBaseUrl}/api/datapuur/ingestion-preview/${ingestData.job_id}`, {
                method: "GET",
                headers: {
                  Authorization: `Bearer ${localStorage.getItem("token")}`,
                },
              });

              // Check for cancellation before proceeding
              if (isCancelling) {
                console.log("Upload cancelled before profile generation, skipping profile")
                throw new Error("Upload cancelled by user")
              }
              
              if (!fileDetailsResponse.ok) {
                console.error("Error fetching file details for profiling, but continuing with ingestion");
              } else {
                const fileDetails = await fileDetailsResponse.json();
                console.log("$$$$$$$$$$$$$$$$$$$Preview generation started:", fileDetails);
                
                // Check for cancellation again before proceeding with profile generation
                if (isCancelling) {
                  console.log("Upload cancelled before profile API call, skipping profile")
                  throw new Error("Upload cancelled by user")
                }
                
                // Now call profile API with the file details
                const profileResponse = await fetch(`${apiBaseUrl}/api/profiler/profile-data`, {
                  method: "POST",
                  headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${localStorage.getItem("token")}`,
                  },
                  body: JSON.stringify({
                    file_id: ingestData.file_id,
                    file_name: file.name,
                    // The key fix: use the ingestion job id to create the correct file path
                    // The backend stores the processed data as a parquet file with the job_id as the filename
                    file_path: `${ingestData.job_id}.parquet`,
                  }),
                });
                
                if (!profileResponse.ok) {
                  console.error("Error generating profile, but continuing with ingestion");
                } else {
                  const profileData = await profileResponse.json();
                  console.log("Profile generation started:", profileData);
                  
                  // Create a job entry in the datapuur system for tracking
                  const createJobResponse = await fetch(`${apiBaseUrl}/api/datapuur/create-job`, {
                    method: "POST",
                    headers: {
                      "Content-Type": "application/json",
                      Authorization: `Bearer ${localStorage.getItem("token")}`,
                    },
                    body: JSON.stringify({
                      job_id: profileData.id,
                      job_type: "profile",
                      status: "completed", // Since profiling is synchronous, it's already completed
                      details: {
                        file_id: ingestData.file_id,
                        file_name: file.name,
                        profile_id: profileData.id
                      }
                    }),
                  });
                  
                  if (!createJobResponse.ok) {
                    console.error("Failed to create job entry for profile, but profile was generated successfully");
                  }
                  
                  // Create a job for profile generation in the UI
                  onJobCreated({
                    id: profileData.id, // Using profile ID as job ID
                    name: `Profile: ${file.name}`,
                    type: "profile",
                    status: "completed", // Since profiling is synchronous, it's already completed
                    progress: 100,
                    startTime: new Date().toISOString(),
                    endTime: new Date().toISOString(), // Set end time since it's completed
                    details: `Profile generated for: ${file.name}`,
                  });
                  
                  // Also add to global context
                  addJob({
                    id: profileData.id, // Using profile ID as job ID
                    name: `Profile: ${file.name}`,
                    type: "profile",
                    status: "completed", // Since profiling is synchronous, it's already completed
                    progress: 100,
                    startTime: new Date().toISOString(),
                    endTime: new Date().toISOString(), // Set end time since it's completed
                    details: `Profile generated for: ${file.name}`,
                  });
                }
              }
            } catch (profileError) {
              console.error("Profile generation error:", profileError);
              // Don't throw error here - we still want to complete the main process
            }
          }
          
          // Update progress - complete
          setUploadProgress((prev) => ({ ...prev, [fileId]: 100 }))
        } else {
          // Use XMLHttpRequest for smaller files (existing code)
          const xhr = new XMLHttpRequest()
          xhrRef.current = xhr;
          
          // Set up progress tracking
          xhr.upload.addEventListener("progress", (event) => {
            if (event.lengthComputable) {
              const percentComplete = Math.round((event.loaded / event.total) * 100)
              
              // Update the job progress
              const progressJob: Job = {
                ...initialJob,
                progress: percentComplete,
                details: `Uploading: ${percentComplete}% of ${(file.size / 1024 / 1024).toFixed(2)} MB`,
              }
              
              // Update the job in the UI - use onJobUpdated instead of onJobCreated for progress updates
              if (onJobUpdated) {
                onJobUpdated(progressJob)
              }
              // Also update in global context
              updateJob(progressJob)
              
              // Update status
              onStatusChange(`Uploading file ${i + 1} of ${filesToProcess.length}: ${file.name} (${percentComplete}%)...`)
              setProcessingStatus(`Uploading file ${i + 1} of ${filesToProcess.length}: ${file.name} (${percentComplete}%)...`)
            }
          })
          
          // Create a promise to handle the XHR response
          const uploadPromise = new Promise<any>((resolve, reject) => {
            xhr.onload = function() {
              if (xhr.status >= 200 && xhr.status < 300) {
                try {
                  const data = JSON.parse(xhr.responseText)
                  resolve(data)
                } catch (e) {
                  reject(new Error("Invalid JSON response"))
                }
              } else {
                try {
                  const errorData = JSON.parse(xhr.responseText)
                  reject(new Error(errorData.detail || `Failed to upload file ${file.name}`))
                } catch (e) {
                  reject(new Error(`Failed to upload file ${file.name}`))
                }
              }
            }
            
            xhr.onerror = function() {
              reject(new Error(`Network error during upload of ${file.name}`))
            }
          })
          
          // Open and send the request
          const apiBaseUrl = getApiBaseUrl();
          xhr.open("POST", `${apiBaseUrl}/api/datapuur/upload`, true)
          xhr.setRequestHeader("Authorization", `Bearer ${localStorage.getItem("token")}`)
          xhr.send(formData)
          
          // Wait for the upload to complete
          const data = await uploadPromise
          onStatusChange(`File ${i + 1} uploaded successfully! Processing data...`)
          setProcessingStatus(`File ${i + 1} uploaded successfully! Processing data...`)

          // Create a new ingestion job
          const ingestResponse = await fetch(`${apiBaseUrl}/api/datapuur/ingest-file`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${localStorage.getItem("token")}`,
            },
            body: JSON.stringify({
              file_id: data.file_id,
              file_name: file.name,
              chunk_size: chunkSize,
            }),
          })

          if (!ingestResponse.ok) {
            const errorData = await ingestResponse.json()
            throw new Error(errorData.detail || `Failed to start ingestion for ${file.name}`)
          }

          const ingestData = await ingestResponse.json()

          // Check if the ingestion was cancelled by the server
          if (ingestData.cancelled) {
            console.log("Server reported ingestion was cancelled")
            throw new Error("Upload cancelled by user")
          }

          // Update the job with the real job ID
          const updatedJob: Job = {
            id: ingestData.job_id,
            name: file.name,
            type: "file",
            status: "running",
            progress: 0,
            startTime: new Date().toISOString(),
            endTime: null,
            details: `File: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`,
          }

          // Replace the temporary job with the real one - use both callbacks to ensure proper updating
          if (onJobUpdated) {
            onJobUpdated(updatedJob)
          }
          
          // Also notify about job creation to ensure it appears in the jobs list
          if (onJobCreated) {
            onJobCreated(updatedJob)
          }
          
          // Update in global context - this will replace the temp job
          updateJob(updatedJob)
          
          // Always set processing status regardless of file type
          const fileType = file.name.split('.').pop()?.toUpperCase() || 'FILE';
          onStatusChange(`Ingestion job started for ${file.name} with ID: ${ingestData.job_id}`)
          setProcessingStatus(`Ingestion job started for ${file.name} (${fileType}) with ID: ${ingestData.job_id}`)
          
          // Update progress - ingestion started
          setUploadProgress((prev) => ({ ...prev, [fileId]: 90 }))
          
          // If profile generation is enabled, request a profile for this file
          if (generateProfile && !isCancelling) {
            try {
              // First, get file details to get the file path
              const fileDetailsResponse = await fetch(`${apiBaseUrl}/api/datapuur/sources/${ingestData.job_id}`, {
                method: "GET",
                headers: {
                  Authorization: `Bearer ${localStorage.getItem("token")}`,
                },
              });

              // Check for cancellation before proceeding
              if (isCancelling) {
                console.log("Upload cancelled before profile generation, skipping profile")
                throw new Error("Upload cancelled by user")
              }

              if (!fileDetailsResponse.ok) {
                console.error("Error fetching file details for profiling, but continuing with ingestion");
              } else {
                const fileDetails = await fileDetailsResponse.json();
                console.log("$$$$$$$$$$$$$$$$$$$ Sources File details:", fileDetails);
                
                // Check for cancellation again before proceeding with profile generation
                if (isCancelling) {
                  console.log("Upload cancelled before profile API call, skipping profile")
                  throw new Error("Upload cancelled by user")
                }
                
                // Now call profile API with the file details
                const profileResponse = await fetch(`${apiBaseUrl}/api/profiler/profile-data`, {
                  method: "POST",
                  headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${localStorage.getItem("token")}`,
                  },
                  body: JSON.stringify({
                    file_id: fileDetails.id,
                    file_name: file.name,
                    // The key fix: use the ingestion job id to create the correct file path
                    // The backend stores the processed data as a parquet file with the job_id as the filename
                    file_path: `${ingestData.job_id}.parquet`,
                  }),
                });
                
                if (!profileResponse.ok) {
                  console.error("Error generating profile, but continuing with ingestion");
                } else {
                  const profileData = await profileResponse.json();
                  console.log("Profile generation started:", profileData);
                  
                  // Create a job entry in the datapuur system for tracking
                  const createJobResponse = await fetch(`${apiBaseUrl}/api/datapuur/create-job`, {
                    method: "POST",
                    headers: {
                      "Content-Type": "application/json",
                      Authorization: `Bearer ${localStorage.getItem("token")}`,
                    },
                    body: JSON.stringify({
                      job_id: profileData.id,
                      job_type: "profile",
                      status: "completed", // Since profiling is synchronous, it's already completed
                      details: {
                        file_id: ingestData.file_id,
                        file_name: file.name,
                        profile_id: profileData.id
                      }
                    }),
                  });
                  
                  if (!createJobResponse.ok) {
                    console.error("Failed to create job entry for profile, but profile was generated successfully");
                  }
                  
                  // Create a job for profile generation in the UI
                  onJobCreated({
                    id: profileData.id, // Using profile ID as job ID
                    name: `Profile: ${file.name}`,
                    type: "profile",
                    status: "completed", // Since profiling is synchronous, it's already completed
                    progress: 100,
                    startTime: new Date().toISOString(),
                    endTime: new Date().toISOString(), // Set end time since it's completed
                    details: `Profile generated for: ${file.name}`,
                  });
                  
                  // Also add to global context
                  addJob({
                    id: profileData.id, // Using profile ID as job ID
                    name: `Profile: ${file.name}`,
                    type: "profile",
                    status: "completed", // Since profiling is synchronous, it's already completed
                    progress: 100,
                    startTime: new Date().toISOString(),
                    endTime: new Date().toISOString(), // Set end time since it's completed
                    details: `Profile generated for: ${file.name}`,
                  });
                }
              }
            } catch (profileError) {
              console.error("Profile generation error:", profileError);
              // Don't throw error here - we still want to complete the main process
            }
          }
          
          // Update progress - complete
          setUploadProgress((prev) => ({ ...prev, [fileId]: 100 }))
        }
      } catch (error: any) {
        console.error(`Error processing file ${file.name}:`, error)
        
        // Update error state
        const errorMessage = error.message || "Unknown error occurred during upload"
        setError(errorMessage)
        onError({ message: errorMessage })
        
        // Remove the temporary job if it exists
        const tempJobId = `temp-${Date.now()}-${i}`
        removeJob(tempJobId)
        
        // Add error to global context
        addError(`Error uploading ${file.name}: ${errorMessage}`)
        
        // Break the loop on error
        break
      } finally {
        // Remove this file from the processing files array
        setProcessingFiles(prev => prev.filter(f => f !== file))
      }
    }
    
    // Only reset processing state if there are no more files being processed
    if (processingFiles.length === 0) {
      setIsProcessing(false)
      onStatusChange("")
      setProcessingStatus("")
    }
  }

  const removeAllFiles = () => {
    setFiles([])
    setUploadProgress({})
    setError("")
    onStatusChange("")
  }

  // Cancel the upload process
  const cancelUpload = () => {
    console.log("Cancelling upload...")
    setIsCancelling(true)
    
    // If there's an active XHR request, abort it
    if (xhrRef.current) {
      xhrRef.current.abort()
      xhrRef.current = null
    }
    
    // If there's an upload ID, mark it as cancelled in localStorage
    if (uploadIdRef.current) {
      localStorage.setItem(`cancelled_upload_${uploadIdRef.current}`, "true")
    }
    
    // Cancel any active ingestion jobs
    const activeJobs = jobs.filter(job => 
      (job.status === "running" || job.status === "queued") && 
      !job.id.startsWith("temp-")
    )
    
    // Cancel each active job via the API
    activeJobs.forEach(async (job) => {
      try {
        const apiBaseUrl = getApiBaseUrl()
        const response = await fetch(`${apiBaseUrl}/api/datapuur/cancel-job/${job.id}`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        })
        
        if (response.ok) {
          console.log(`Successfully cancelled job ${job.id}`)
          // Update the job status in the UI immediately
          updateJob({
            ...job,
            status: "cancelled",
            endTime: new Date().toISOString(),
            details: `${job.details} (Cancelled by user)`,
          })
        }
      } catch (error) {
        console.error(`Error cancelling job ${job.id}:`, error)
      }
    })
    
    // Clear processing files
    setProcessingFiles([])
    
    // Reset state
    setFiles([])
    setUploadProgress({})
    setIsProcessing(false)
    setError("")
    onStatusChange("")
    setProcessingStatus("")
    
    // Reset cancellation flag after a short delay
    setTimeout(() => {
      setIsCancelling(false)
    }, 500)
  }

  // Function to preview file contents
  const handlePreview = async (fileIndex: number) => {
    if (!files[fileIndex]) return
    
    setIsPreviewLoading(true)
    setError("")
    
    try {
      const file = files[fileIndex]
      const fileType = file.name.split(".").pop()?.toLowerCase()
      
      // Update status - but DON'T set processing status for preview operations
      const previewStatus = `Generating preview for ${file.name}...`
      onStatusChange(previewStatus)
      
      // For large files (over 50MB), use the server-side preview API instead of client-side parsing
      if (file.size > 50 * 1024 * 1024) {
        try {
          const apiBaseUrl = getApiBaseUrl();
          const formData = new FormData();
          
          // Only send the first 10MB of the file for preview
          const previewChunk = file.slice(0, 10 * 1024 * 1024);
          formData.append('file', previewChunk, file.name);
          
          const response = await fetch(`${apiBaseUrl}/api/datapuur/preview-file`, {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${localStorage.getItem("token")}`,
            },
            body: formData,
          });
          
          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Failed to preview file");
          }
          
          const data = await response.json();
          
          setPreviewData({
            headers: data.headers || [],
            rows: data.rows || [],
            fileName: file.name,
          });
          
          onStatusChange("");
          setIsPreviewLoading(false);
          
        } catch (error) {
          console.error("Server preview error:", error);
          setError(error instanceof Error ? error.message : "Failed to preview large file");
          addError(error instanceof Error ? error.message : "Failed to preview large file");
          onStatusChange("");
          setIsPreviewLoading(false);
        }
        
        return;
      }
      
      // Process the file locally instead of uploading to the server (for smaller files)
      if (fileType === 'csv') {
        // Read CSV file locally
        const reader = new FileReader()
        
        reader.onload = (e) => {
          try {
            const text = e.target?.result as string
            if (!text) {
              throw new Error("Failed to read file content")
            }
            
            // Parse CSV content
            const lines = text.split('\n')
            if (lines.length === 0) {
              throw new Error("CSV file is empty")
            }
            
            // Extract headers (first line)
            const headers = lines[0].split(',').map(header => header.trim().replace(/^"|"$/g, ''))
            
            // Extract rows (up to 50 rows for preview)
            const rows = []
            const maxRows = Math.min(lines.length - 1, 50)
            
            for (let i = 1; i <= maxRows; i++) {
              if (lines[i].trim() === '') continue
              
              // Handle quoted values correctly
              const row = []
              let currentValue = ''
              let insideQuotes = false
              
              for (let char of lines[i]) {
                if (char === '"') {
                  insideQuotes = !insideQuotes
                } else if (char === ',' && !insideQuotes) {
                  row.push(currentValue.trim().replace(/^"|"$/g, ''))
                  currentValue = ''
                } else {
                  currentValue += char
                }
              }
              
              // Add the last value
              row.push(currentValue.trim().replace(/^"|"$/g, ''))
              rows.push(row)
            }
            
            // Update the preview data state
            setPreviewData({
              headers,
              rows,
              fileName: file.name,
            })
            
            // Clear status after preview is generated
            onStatusChange("")
            setIsPreviewLoading(false)
          } catch (error) {
            console.error("CSV parsing error:", error)
            setError(error instanceof Error ? error.message : "Failed to parse CSV file")
            addError(error instanceof Error ? error.message : "Failed to parse CSV file")
            onStatusChange("")
            setIsPreviewLoading(false)
          }
        }
        
        reader.onerror = () => {
          setError("Failed to read file")
          addError("Failed to read file")
          onStatusChange("")
          setIsPreviewLoading(false)
        }
        
        // Start reading the file
        reader.readAsText(file)
      } else if (fileType === 'json') {
        // Read JSON file locally
        const reader = new FileReader()
        
        reader.onload = (e) => {
          try {
            const text = e.target?.result as string
            if (!text) {
              throw new Error("Failed to read file content")
            }
            
            // Parse JSON content
            const data = JSON.parse(text)
            
            // Ensure data is an array
            if (!Array.isArray(data)) {
              throw new Error("JSON file must contain an array of objects")
            }
            
            if (data.length === 0) {
              setPreviewData({
                headers: [],
                rows: [],
                fileName: file.name,
              })
              onStatusChange("")
              setIsPreviewLoading(false)
              return
            }
            
            // Extract headers from the first object
            const headers = Object.keys(data[0])
            
            // Extract rows (up to 50 rows for preview)
            const rows = []
            const maxRows = Math.min(data.length, 50)
            
            for (let i = 0; i < maxRows; i++) {
              const row = []
              for (const header of headers) {
                row.push(data[i][header])
              }
              rows.push(row)
            }
            
            // Update the preview data state
            setPreviewData({
              headers,
              rows,
              fileName: file.name,
            })
            
            // Clear status after preview is generated
            onStatusChange("")
            setIsPreviewLoading(false)
          } catch (error) {
            console.error("JSON parsing error:", error)
            setError(error instanceof Error ? error.message : "Failed to parse JSON file")
            addError(error instanceof Error ? error.message : "Failed to parse JSON file")
            onStatusChange("")
            setIsPreviewLoading(false)
          }
        }
        
        reader.onerror = () => {
          setError("Failed to read file")
          addError("Failed to read file")
          onStatusChange("")
          setIsPreviewLoading(false)
        }
        
        // Start reading the file
        reader.readAsText(file)
      } else {
        throw new Error(`Unsupported file type: ${fileType}. Only CSV and JSON files are supported.`)
      }
      
    } catch (error) {
      console.error("Preview error:", error)
      setError(error instanceof Error ? error.message : "Failed to generate preview")
      addError(error instanceof Error ? error.message : "Failed to generate preview")
      
      // Clear status on error
      onStatusChange("")
      setIsPreviewLoading(false)
    }
  }

  const openFileDialog = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click()
    }
  }

  // Handle successful upload completion
  const handleUploadSuccess = (file: File, response: any, jobId: string) => {
    console.log("Upload completed successfully:", file.name)
    
    // Clear the processing status since the job is now visible in the jobs list
    setProcessingStatus("")
    onStatusChange("")
    
    // Update the job with the real ID from the server and mark as running
    if (response.job) {
      updateJob({
        ...response.job,
        status: "running",
        progress: 0,
      })
    }
    
    // If schema was detected, notify the parent component
    if (response.schema) {
      onSchemaDetected(response.schema)
    }
    
    // Remove the file from the list after successful upload
    setFiles((prevFiles) => prevFiles.filter((f) => f !== file))
    
    // If all files are processed, reset the processing state
    if (files.length <= 1) {
      setIsProcessing(false)
    }
  }
  
  // Handle upload error
  const handleUploadError = (file: File, error: any, jobId: string) => {
    console.error("Upload error:", error)
    
    // Clear the processing status
    setProcessingStatus("")
    onStatusChange("")
    
    // Set the error message
    const errorMessage = error instanceof Error ? error.message : "Upload failed"
    setError(errorMessage)
    addError(errorMessage)
    
    // Update the job status to failed
    updateJob({
      id: jobId,
      name: file.name,
      type: "file",
      status: "failed",
      progress: 0,
      startTime: new Date().toISOString(),
      endTime: new Date().toISOString(),
      details: `Failed to upload ${file.name}`,
      error: errorMessage,
    })
    
    // Reset the processing state
    setIsProcessing(false)
  }

  // Add an effect to monitor processingStatus changes from the context
  // This will help detect when a cancel is triggered from the floating job card
  useEffect(() => {
    // If processingStatus is cleared while we're still processing, it might be due to cancellation
    if (isProcessing && !processingStatus) {
      console.log("Processing status was cleared while still processing, likely due to cancellation");
      cancelUpload();
    }
  }, [processingStatus, isProcessing]);

  // Update the existing effect to also check for processingStatus changes
  useEffect(() => {
    // If processing status is cleared and we were processing, it might be due to cancellation
    if (isProcessing) {
      // Check if we should cancel the upload (e.g., if the cancel button was clicked in the floating job card)
      const anyJobCancelled = jobs.some(job => job.status === "cancelled");
      if (anyJobCancelled || !processingStatus) {
        console.log("Detected job cancellation from floating job card, cancelling upload");
        cancelUpload();
      }
    }
  }, [isProcessing, jobs, processingStatus]);

  // Add an effect to automatically clear error messages after 5 seconds
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => {
        setError("");
      }, 5000); // 5 seconds
      
      return () => clearTimeout(timer);
    }
  }, [error]);

  return (
    <div className="space-y-4">
      <h3 className="text-xl font-semibold text-foreground mb-4 flex items-center">
        <FileUp className="w-5 h-5 mr-2 text-primary" />
        Upload Data Files
      </h3>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {files.length === 0 ? (
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            dragActive ? "border-primary bg-primary/5" : "border-border bg-background/50"
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={handleChange}
            accept=".csv,.json"
            multiple
          />
          <motion.div whileHover={{ scale: 1.05 }} className="inline-block">
            <FileUp className="w-16 h-16 text-primary mx-auto mb-4" />
          </motion.div>
          <p className="text-muted-foreground mb-4">Drag and drop files here, or click to browse</p>
          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <Button
              className="bg-primary hover:bg-primary/90 text-primary-foreground"
              onClick={openFileDialog}
            >
              Select Files
            </Button>
            <div className="text-sm text-muted-foreground mt-2 sm:mt-0 sm:ml-2 flex items-center">
              Supported formats: CSV, JSON
            </div>
          </div>
        </div>
      ) : (
        <div className="border rounded-lg p-6 bg-card">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-foreground">Selected Files ({files.length})</h3>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setFiles([])}
              disabled={isProcessing}
              className="text-muted-foreground hover:text-foreground"
            >
              Clear All
            </Button>
          </div>

          <div className="space-y-3 max-h-60 overflow-y-auto mb-4">
            {files.map((file, index) => (
              <div key={`file-${index}`} className="flex justify-between items-center p-3 border border-border rounded-lg">
                <div className="flex items-center">
                  <FileText className="h-5 w-5 text-primary mr-3" />
                  <div>
                    <p className="font-medium text-foreground">{file.name}</p>
                    <p className="text-sm text-muted-foreground">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                  </div>
                </div>

                {uploadProgress[`${file.name}-${file.size}-${Date.now()}`] !== undefined && (
                  <div className="w-24 mr-4">
                    <Progress value={uploadProgress[`${file.name}-${file.size}-${Date.now()}`]} className="h-2" />
                  </div>
                )}

                <div className="flex items-center">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handlePreview(index)}
                    disabled={isPreviewLoading}
                    className="text-muted-foreground hover:text-foreground mr-1"
                    title="Preview file"
                  >
                    <Eye className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => removeFile(index)}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
            
            {/* Show processing files with a different style */}
            {processingFiles.map((file, index) => (
              <div key={`processing-${index}`} className="flex justify-between items-center p-3 border border-primary/30 bg-primary/5 rounded-lg">
                <div className="flex items-center">
                  <FileText className="h-5 w-5 text-primary mr-3" />
                  <div>
                    <p className="font-medium text-foreground">{file.name}</p>
                    <p className="text-sm text-muted-foreground">{(file.size / 1024 / 1024).toFixed(2)} MB (Processing)</p>
                  </div>
                </div>

                {uploadProgress[`${file.name}-${file.size}-${Date.now()}`] !== undefined && (
                  <div className="w-24 mr-4">
                    <Progress value={uploadProgress[`${file.name}-${file.size}-${Date.now()}`]} className="h-2" />
                  </div>
                )}

                <div className="flex items-center">
                  <span className="text-xs text-muted-foreground">Processing...</span>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-4 flex flex-col gap-2 mb-4">
            <div className="flex items-center space-x-2">
              <Checkbox 
                id="generateProfile" 
                checked={generateProfile} 
                onCheckedChange={(value) => setGenerateProfile(value === true)}
              />
              <Label htmlFor="generateProfile" className="cursor-pointer flex items-center">
                <BarChart className="w-4 h-4 mr-2 text-muted-foreground" />
                Generate data profile during ingestion
              </Label>
            </div>
            <p className="text-xs text-muted-foreground ml-6">
              Creates statistical analysis including data types, distributions, and quality metrics
            </p>
          </div>

          <Button
            className="w-full bg-primary hover:bg-primary/90 text-primary-foreground"
            onClick={handleUpload}
            disabled={files.length === 0}
          >
            {files.length > 0 ? (
              <span className="flex items-center">
                <Upload className="mr-2 h-4 w-4" />
                Upload {files.length} File{files.length !== 1 ? "s" : ""}
              </span>
            ) : processingFiles.length > 0 ? (
              <span className="flex items-center">
                <svg
                  className="animate-spin -ml-1 mr-3 h-4 w-4 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Processing {processingFiles.length} file{processingFiles.length !== 1 ? "s" : ""}...
              </span>
            ) : (
              <span className="flex items-center">
                <Upload className="mr-2 h-4 w-4" />
                Select files to upload
              </span>
            )}
          </Button>

          {/* Preview section restored */}
          {previewData && (
            <div className="border rounded-lg p-4 mb-4 bg-card/50 overflow-x-auto">
              <div className="flex justify-between items-center mb-3">
                <h4 className="font-medium text-foreground">
                  Preview: {previewData.fileName} ({previewData.rows.length} rows)
                </h4>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setPreviewData(null)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
              
              {previewData.headers.length > 0 ? (
                <div className="max-h-[400px] overflow-auto">
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="bg-muted/50">
                        {previewData.headers.map((header, i) => (
                          <th key={i} className="p-2 text-left border text-sm font-medium text-foreground">
                            {header}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {previewData.rows.map((row, i) => (
                        <tr key={i} className={i % 2 === 0 ? "bg-background" : "bg-muted/20"}>
                          {row.map((cell, j) => (
                            <td key={j} className="p-2 border text-sm text-muted-foreground">
                              {typeof cell === 'object' ? JSON.stringify(cell) : String(cell)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-muted-foreground text-sm">No data available for preview</p>
              )}
            </div>
          )}

          {isPreviewLoading && (
            <div className="flex justify-center items-center p-4 mb-4">
              <svg
                className="animate-spin h-5 w-5 text-primary mr-3"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
              <span>Loading preview...</span>
            </div>
          )}
        </div>
      )}
      
      {/* Instructions section moved outside the conditional rendering to ensure it's always visible */}
      <div className="mt-4 p-4 bg-card/50 rounded-lg border border-border">
        <h4 className="font-medium text-foreground mb-2">Instructions:</h4>
        <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1">
          <li>Upload CSV or JSON files up to 2GB</li>
          <li>CSV files should use comma as delimiter and include a header row</li>
          <li>JSON files should contain an array of objects with consistent structure</li>
          <li>The system will automatically detect the schema of your data</li>
          <li>Adjust chunk size in the Processing Configuration section for large files</li>
          <li>Monitor ingestion progress in the Ingestion Jobs section</li>
        </ul>
      </div>
    </div>
  )
}
