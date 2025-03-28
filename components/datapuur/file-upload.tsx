"use client"

import { useState, useRef } from "react"
import { FileUp, X, FileText, Upload, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { motion } from "framer-motion"

// Define job interface for type safety
interface Job {
  id: string
  name: string
  type: string
  status: string
  progress: number
  startTime: string
  endTime: string | null
  details: string
}

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
  // Update the component to handle multiple files
  // Change the file state from a single file to an array of files
  const [files, setFiles] = useState<File[]>([])
  // Replace the single file state with files array
  // const [file, setFile] = useState(null)
  const [dragActive, setDragActive] = useState(false)
  // Update the uploadProgress state to track multiple files
  const [uploadProgress, setUploadProgress] = useState<Record<number, number>>({})
  const [error, setError] = useState("")
  const fileInputRef = useRef(null)

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  // Update the drag and drop handler to accept multiple files
  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      // Process all dropped files
      const droppedFiles = Array.from(e.dataTransfer.files)
      handleFiles(droppedFiles)
    }
  }

  // Update the file input change handler to accept multiple files
  const handleChange = (e) => {
    e.preventDefault()
    if (e.target.files && e.target.files.length > 0) {
      // Process all selected files
      const selectedFiles = Array.from(e.target.files)
      handleFiles(selectedFiles)
    }
  }

  // Create a new function to handle multiple files
  const handleFiles = (newFiles: File[]) => {
    // Filter out unsupported file types
    const validFiles = newFiles.filter((file) => {
      const fileType = file.name.split(".").pop().toLowerCase()
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
    setFiles((prevFiles) => prevFiles.filter((_, i) => i !== index))
    setUploadProgress({})
    setError("")
  }

  // Update the handleUpload function to handle multiple files
  const handleUpload = async () => {
    if (files.length === 0) return

    setIsProcessing(true)
    setUploadProgress({})
    setError("")
    onStatusChange(`Preparing to upload ${files.length} file${files.length > 1 ? "s" : ""}...`)

    // Process each file sequentially
    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      try {
        // Update status for current file
        onStatusChange(`Uploading file ${i + 1} of ${files.length}: ${file.name}...`)

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
        
        // Notify about the job immediately - ensure this is called
        if (onJobCreated) {
          console.log("Creating initial job:", initialJob)
          onJobCreated(initialJob)
        }

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
          
          for (let start = 0; start < file.size; start += CHUNK_SIZE) {
            const chunk = file.slice(start, start + CHUNK_SIZE);
            const chunkFormData = new FormData();
            chunkFormData.append('file', chunk, file.name);
            chunkFormData.append('chunkSize', chunkSize.toString());
            chunkFormData.append('chunkIndex', String(uploadedChunks));
            chunkFormData.append('totalChunks', String(totalChunks));
            chunkFormData.append('uploadId', uploadId);
            
            try {
              // Send the chunk
              const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "/api"}/datapuur/upload-chunk`, {
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
                onJobUpdated(progressJob);
              }
              
              // Update status
              onStatusChange(`Uploading file ${i + 1} of ${files.length}: ${file.name} (${percentComplete}%)...`);
            } catch (error) {
              console.error("Error uploading chunk:", error);
              throw error;
            }
          }
          
          // Complete the chunked upload
          const completeResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "/api"}/datapuur/complete-chunked-upload`, {
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
            throw new Error("Failed to complete chunked upload");
          }
          
          const data = await completeResponse.json();
          onStatusChange(`File ${i + 1} uploaded successfully! Processing data...`);
          
          // Continue with ingestion as before
          const ingestResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "/api"}/datapuur/ingest-file`, {
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
          
          // Replace the temporary job with the real one - use both callbacks to ensure proper updating
          if (onJobUpdated) {
            onJobUpdated(updatedJob)
          }
          
          // Also notify about job creation to ensure it appears in the jobs list
          if (onJobCreated) {
            onJobCreated(updatedJob)
          }
          
          onStatusChange(`Ingestion job started for ${file.name} with ID: ${ingestData.job_id}`)
        } else {
          // Use XMLHttpRequest for smaller files (existing code)
          const xhr = new XMLHttpRequest()
          
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
                console.log("Updating job progress:", progressJob)
                onJobUpdated(progressJob)
              }
              
              // Update status
              onStatusChange(`Uploading file ${i + 1} of ${files.length}: ${file.name} (${percentComplete}%)...`)
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
          xhr.open("POST", `${process.env.NEXT_PUBLIC_API_URL || "/api"}/datapuur/upload`, true)
          xhr.setRequestHeader("Authorization", `Bearer ${localStorage.getItem("token")}`)
          xhr.send(formData)
          
          // Wait for the upload to complete
          const data = await uploadPromise
          onStatusChange(`File ${i + 1} uploaded successfully! Processing data...`)

          // Create a new ingestion job
          const ingestResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "/api"}/datapuur/ingest-file`, {
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
          
          onStatusChange(`Ingestion job started for ${file.name} with ID: ${ingestData.job_id}`)
        }
      } catch (error) {
        console.error(`Error uploading file ${file.name}:`, error)
        const errorMessage = error instanceof Error ? error.message : "Failed to upload file"
        setError(`Error with file ${file.name}: ${errorMessage}`)
        if (onError) onError({ message: errorMessage })
        // Continue with next file despite error
      }
    }

    onStatusChange(`Completed processing ${files.length} file${files.length > 1 ? "s" : ""}`)
    setIsProcessing(false)
  }

  const removeAllFiles = () => {
    setFiles([])
    setUploadProgress({})
    setError("")
    onStatusChange("")
  }

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
              onClick={() => fileInputRef.current.click()}
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
              <div key={index} className="flex justify-between items-center p-3 border border-border rounded-lg">
                <div className="flex items-center">
                  <FileText className="h-5 w-5 text-primary mr-3" />
                  <div>
                    <p className="font-medium text-foreground">{file.name}</p>
                    <p className="text-sm text-muted-foreground">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                  </div>
                </div>

                {uploadProgress[index] !== undefined && (
                  <div className="w-24 mr-4">
                    <Progress value={uploadProgress[index]} className="h-2" />
                  </div>
                )}

                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => removeFile(index)}
                  disabled={isProcessing}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>

          <Button
            className="w-full bg-primary hover:bg-primary/90 text-primary-foreground"
            onClick={handleUpload}
            disabled={isProcessing}
          >
            {isProcessing ? (
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
                Processing...
              </span>
            ) : (
              <span className="flex items-center">
                <Upload className="mr-2 h-4 w-4" />
                Upload {files.length} File{files.length !== 1 ? "s" : ""}
              </span>
            )}
          </Button>
        </div>
      )}

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
