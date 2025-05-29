"use client"

import { useState } from "react"
import { DataPuurLayout } from "@/components/datapuur/datapuur-layout"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { FileUpload } from "@/components/datapuur/file-upload"
import { DatabaseConnection } from "@/components/datapuur/database-connection"
import { HistoryTab } from "@/components/datapuur/history-tab"
import { SchemaViewer } from "@/components/datapuur/schema-viewer"
import { ChunkSizeConfig } from "@/components/datapuur/chunk-size-config"
import { IngestionMonitor } from "@/components/datapuur/ingestion-monitor"
import { FileUp, Database, Table, Settings, Activity, History } from "lucide-react"
import { motion } from "framer-motion"
import { useIngestion } from "@/lib/ingestion-context"

// Define error interface
interface IngestionError {
  id: number
  message: string
  timestamp: string
}

export default function IngestionPage() {
  const [activeTab, setActiveTab] = useState("file-upload")
  const [detectedSchema, setDetectedSchema] = useState<any>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [processingStatus, setProcessingStatus] = useState("")
  const [chunkSize, setChunkSize] = useState(1000)
  
  // Use the global ingestion context instead of local state
  const { jobs: ingestionJobs, addJob: handleJobCreated, updateJob: handleJobUpdated, addError, errors: contextErrors } = useIngestion()
  
  // Convert context errors to the format expected by the component
  const ingestionErrors = contextErrors.map((message, index) => ({
    id: index,
    message,
    timestamp: new Date().toISOString(),
  }));

  // Animation variants
  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  }

  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 },
  }

  const handleSchemaDetected = (schema: any) => {
    setDetectedSchema(schema)
  }

  const handleChunkSizeChange = (size: number) => {
    setChunkSize(size)
  }

  const handleProcessingStatusChange = (status: string) => {
    setProcessingStatus(status)
  }

  const handleError = (error: { message: string }) => {
    addError(error.message || "An unknown error occurred")
  }

  return (
    <DataPuurLayout>
      <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
        <div className="flex flex-col">
          <h2 className="text-2xl font-bold tracking-tight">Ingestion</h2>
        </div>
        
        <div className="space-y-8">
          {/* Ingestion Jobs - shown on this page for convenience, but also available globally */}
          {(ingestionJobs.some(job => job.status === "running" || job.status === "queued") || processingStatus) && (
            <div className="bg-card p-6 rounded-lg border shadow-md">
              <h3 className="text-xl font-semibold mb-4 flex items-center">
                <Activity className="w-5 h-5 mr-2 text-primary" />
                Ingestion Jobs
              </h3>
              
              <IngestionMonitor
                jobs={ingestionJobs}
                onJobUpdated={handleJobUpdated}
                errors={contextErrors}
                processingStatus={processingStatus}
              />
            </div>
          )}

          <Tabs defaultValue="file-upload" onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid grid-cols-3 mb-8">
              <TabsTrigger value="file-upload" className="flex items-center gap-2">
                <FileUp className="h-4 w-4" />
                File Upload
              </TabsTrigger>
              <TabsTrigger value="database" className="flex items-center gap-2">
                <Database className="h-4 w-4" />
                Database Connection
              </TabsTrigger>
              <TabsTrigger value="history" className="flex items-center gap-2">
                <History className="h-4 w-4" />
                History
              </TabsTrigger>
            </TabsList>

            <TabsContent value="file-upload" className="space-y-6">
              {/* Processing Configuration */}
              <div className="bg-card p-6 rounded-lg border shadow-md">
                <h3 className="text-xl font-semibold mb-4 flex items-center">
                  <Settings className="w-5 h-5 mr-2 text-primary" />
                  Processing Configuration
                </h3>
                <ChunkSizeConfig
                  chunkSize={chunkSize}
                  onChunkSizeChange={handleChunkSizeChange}
                  disabled={isProcessing}
                />
              </div>

              {/* File Upload */}
              <div className="bg-card p-6 rounded-lg border shadow-md">
                <FileUpload
                  onSchemaDetected={handleSchemaDetected}
                  isProcessing={isProcessing}
                  setIsProcessing={setIsProcessing}
                  chunkSize={chunkSize}
                  onStatusChange={handleProcessingStatusChange}
                  onJobCreated={handleJobCreated}
                  onJobUpdated={handleJobUpdated}
                  onError={handleError}
                />
              </div>
            </TabsContent>

            <TabsContent value="database" className="space-y-6">
              <div className="bg-card p-6 rounded-lg border shadow-md">
                <DatabaseConnection
                  onSchemaDetected={handleSchemaDetected}
                  isProcessing={isProcessing}
                  setIsProcessing={setIsProcessing}
                  chunkSize={chunkSize}
                  onStatusChange={handleProcessingStatusChange}
                  onJobCreated={handleJobCreated}
                  onError={handleError}
                />
              </div>
            </TabsContent>

            <TabsContent value="history" className="space-y-6">
              <div className="bg-card p-6 rounded-lg border shadow-md">
                <HistoryTab />
              </div>
            </TabsContent>
          </Tabs>

          {/* Schema Viewer - only show for database tab */}
          {detectedSchema && activeTab === "database" && (
            <div className="bg-card p-6 rounded-lg border shadow-md">
              <h3 className="text-xl font-semibold mb-4 flex items-center">
                <Table className="w-5 h-5 mr-2 text-primary" />
                Detected Schema
              </h3>
              <SchemaViewer schema={detectedSchema} />
            </div>
          )}
        </div>
      </div>
    </DataPuurLayout>
  )
}
