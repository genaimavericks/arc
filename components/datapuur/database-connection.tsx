"use client"

import { useState, useEffect } from "react"
import { Database, Play, Save, Trash, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { getApiBaseUrl } from "@/lib/config"
import { useIngestion, Job } from "@/lib/ingestion-context"
import { useToast } from "@/hooks/use-toast"

export function DatabaseConnection({
  onSchemaDetected,
  isProcessing,
  setIsProcessing,
  chunkSize,
  onStatusChange,
  onJobCreated,
  onError,
}: {
  onSchemaDetected: (schema: any) => void;
  isProcessing: boolean;
  setIsProcessing: (isProcessing: boolean) => void;
  chunkSize: number;
  onStatusChange: (status: string) => void;
  onJobCreated: (job: Job) => void;
  onError?: (error: { message: string }) => void;
}) {
  // Use toast notifications for database-specific messages
  const { toast } = useToast();
  
  // Function to show toast notifications for database operations
  const showDatabaseToast = (title: string, message: string, type: "default" | "destructive" = "default") => {
    toast({
      title: title,
      description: message,
      variant: type,
      duration: 5000 // Auto-dismiss after 5 seconds
    });
  };
  // Use the global ingestion context
  const { addJob, updateJob, addError, setProcessingStatus } = useIngestion()
  
  const [connectionType, setConnectionType] = useState("mysql")
  const [connectionConfig, setConnectionConfig] = useState({
    host: "",
    port: "",
    database: "",
    username: "",
    password: "",
    table: "",
  })
  const [savedConnections, setSavedConnections] = useState<Array<{
    id: string;
    name: string;
    type: string;
    config: {
      host: string;
      port: string;
      database: string;
      username: string;
      password: string;
      table: string;
    };
  }>>([])
  const [error, setError] = useState("")
  const [connectionName, setConnectionName] = useState("")
  
  // Load saved connections on component mount
  useEffect(() => {
    fetchSavedConnections()
  }, [])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setConnectionConfig({
      ...connectionConfig,
      [name]: value,
    })
  }

  const handleTypeChange = (value: string) => {
    setConnectionType(value)

    // Set default port based on database type
    let defaultPort = ""
    switch (value) {
      case "mysql":
        defaultPort = "3306"
        break
      case "postgresql":
        defaultPort = "5432"
        break
      case "mssql":
        defaultPort = "1433"
        break
    }

    setConnectionConfig({
      ...connectionConfig,
      port: defaultPort,
    })
  }

  const validateConnection = () => {
    if (!connectionConfig.host) return "Host is required"
    if (!connectionConfig.port) return "Port is required"
    if (!connectionConfig.database) return "Database name is required"
    if (!connectionConfig.username) return "Username is required"
    if (!connectionConfig.table) return "Table name is required"
    return ""
  }

  const testConnection = async () => {
    const validationError = validateConnection()
    if (validationError) {
      setError(validationError)
      // Show error toast
      showDatabaseToast("Connection Validation Error", validationError, "destructive")
      if (onError) onError({ message: validationError })
      return
    }

    setIsProcessing(true)
    setError("")
    // Show testing toast
    showDatabaseToast("Database Connection", "Testing database connection...")
    // Clear any existing processing status
    setProcessingStatus("")

    try {
      const apiBaseUrl = getApiBaseUrl()
      const response = await fetch(`${apiBaseUrl}/api/datapuur/test-connection`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({
          type: connectionType,
          config: connectionConfig,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || "Failed to connect to database")
      }

      // Show success toast
      showDatabaseToast("Connection Successful", "Database is accessible.")
      // Clear any existing processing status
      setProcessingStatus("")
    } catch (error: any) {
      console.error("Error testing connection:", error)
      setError(error.message || "Failed to connect to database")
      // Show error toast
      showDatabaseToast("Connection Failed", error.message || "Failed to connect to database", "destructive")
      if (onError) onError({ message: error.message || "Failed to connect to database" })
      
      // Also add to global error context
      addError(`Error connecting to ${connectionType} database at ${connectionConfig.host}:${connectionConfig.port}: ${error.message || "Failed to connect to database"}`)
    } finally {
      setIsProcessing(false)
    }
  }

  const fetchSchema = async () => {
    const validationError = validateConnection()
    if (validationError) {
      setError(validationError)
      // Show error toast
      showDatabaseToast("Schema Validation Error", validationError, "destructive")
      if (onError) onError({ message: validationError })
      return
    }

    setIsProcessing(true)
    setError("")
    // Show fetching toast
    showDatabaseToast("Database Schema", "Fetching database schema...")
    // Clear any existing processing status
    setProcessingStatus("")

    try {
      const apiBaseUrl = getApiBaseUrl()
      const response = await fetch(`${apiBaseUrl}/api/datapuur/db-schema`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({
          type: connectionType,
          config: connectionConfig,
          chunkSize,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || "Failed to fetch schema")
      }

      const data = await response.json()
      onSchemaDetected(data.schema)
      // Show success toast
      showDatabaseToast("Schema Loaded", "Database schema fetched successfully!")
      // Clear any existing processing status
      setProcessingStatus("")
    } catch (error: any) {
      console.error("Error fetching schema:", error)
      setError(error.message || "Failed to fetch schema")
      // Show error toast
      showDatabaseToast("Schema Fetch Failed", error.message || "Failed to fetch schema", "destructive")
      if (onError) onError({ message: error.message || "Failed to fetch schema" })
      
      // Also add to global error context
      addError(`Error fetching schema from ${connectionType} database at ${connectionConfig.host}:${connectionConfig.port}: ${error.message || "Failed to fetch schema"}`)
    } finally {
      setIsProcessing(false)
    }
  }

  const startIngestion = async () => {
    const validationError = validateConnection()
    if (validationError) {
      setError(validationError)
      if (onError) onError({ message: validationError })
      return
    }

    setIsProcessing(true)
    setError("")
    
    // Show toast notification for starting ingestion
    showDatabaseToast("Database Ingestion", `Starting ingestion from ${connectionType} database ${connectionConfig.database}.${connectionConfig.table}`)
    
    // Clear any existing processing status
    setProcessingStatus("")

    try {
      // Log attempt with details for debugging
      console.log(`Attempting to ingest data from ${connectionType} database: ${connectionConfig.host}:${connectionConfig.port}/${connectionConfig.database}.${connectionConfig.table}`)

      const apiBaseUrl = getApiBaseUrl()
      const response = await fetch(`${apiBaseUrl}/api/datapuur/ingest-db`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({
          type: connectionType,
          config: connectionConfig,
          chunk_size: chunkSize,
          connection_name: connectionName || `${connectionType}-${connectionConfig.database}-${connectionConfig.table}`,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        let errorMessage = errorData.detail || "Failed to start database ingestion"
        
        // Provide more specific error messages based on common database errors
        if (errorMessage.includes("access denied") || errorMessage.includes("permission")) {
          errorMessage = `Database access denied. Please check your credentials and ensure your user has SELECT permissions on table ${connectionConfig.table}.`
        } else if (errorMessage.includes("table") && errorMessage.includes("not found")) {
          errorMessage = `Table '${connectionConfig.table}' not found in database '${connectionConfig.database}'. Please verify the table name.`
        } else if (errorMessage.includes("connection refused") || errorMessage.includes("could not connect")) {
          errorMessage = `Could not connect to ${connectionType} server at ${connectionConfig.host}:${connectionConfig.port}. Please check that the server is running and accessible.`
        }
        
        throw new Error(errorMessage)
      }

      const data = await response.json()

      // Create a job object for the UI - use running status to match file ingestion behavior
      const job: Job = {
        id: data.job_id,
        name: `${connectionType.toUpperCase()}: ${connectionConfig.database}.${connectionConfig.table}`,
        type: "database",
        status: "running",
        progress: 1, // Start with 1% progress to make the progress bar visible immediately
        startTime: new Date().toISOString(),
        endTime: null,
        details: `Ingesting from ${connectionType} database: ${connectionConfig.host}:${connectionConfig.port}/${connectionConfig.database}.${connectionConfig.table}`,
      }
      
      // Add the job to the UI
      onJobCreated(job)
      
      // Also add to global context
      addJob(job)
      
      
      // Show toast notification for job creation
      showDatabaseToast("Ingestion Started", `Job ID: ${data.job_id} - Processing ${connectionType} database ${connectionConfig.database}.${connectionConfig.table}`)
      
      // Clear any existing processing status
      setProcessingStatus("")
    } catch (error: any) {
      console.error("Error starting ingestion:", error)
      setError(error.message || "Failed to start database ingestion")
      showDatabaseToast("Ingestion Failed", error.message || "Failed to start database ingestion", "destructive")
      if (onError) onError({ message: error.message || "Failed to start database ingestion" })
      
      // Add to global error context with more detailed information
      addError(`Error ingesting from ${connectionType} database at ${connectionConfig.host}:${connectionConfig.port}/${connectionConfig.database}.${connectionConfig.table}: ${error.message}`)
    } finally {
      setIsProcessing(false)
    }
  }

  const fetchSavedConnections = async () => {
    try {
      const apiBaseUrl = getApiBaseUrl()
      const response = await fetch(`${apiBaseUrl}/api/datapuur/db-connections`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      })

      if (!response.ok) {
        const errorData = await response.json()
        console.error("Error fetching saved connections:", errorData)
        return
      }

      const connections = await response.json()
      setSavedConnections(connections)
    } catch (error) {
      console.error("Error fetching saved connections:", error)
    }
  }

  const saveConnection = async () => {
    if (!connectionName) {
      setError("Please provide a name for this connection")
      // Show error toast
      showDatabaseToast("Save Error", "Please provide a name for this connection", "destructive")
      return
    }

    const validationError = validateConnection()
    if (validationError) {
      setError(validationError)
      // Show error toast
      showDatabaseToast("Validation Error", validationError, "destructive")
      return
    }

    setIsProcessing(true)
    // Show saving toast
    showDatabaseToast("Saving Connection", `Saving connection "${connectionName}"...`)
  
    try {
      const apiBaseUrl = getApiBaseUrl()
      const response = await fetch(`${apiBaseUrl}/api/datapuur/db-connections`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({
          name: connectionName,
          type: connectionType,
          config: connectionConfig, // Backend will store actual password securely
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || "Failed to save connection")
      }

      // Refresh the connections list
      fetchSavedConnections()
    
      setConnectionName("")
      // Show success toast
      showDatabaseToast("Connection Saved", `Connection "${connectionName}" saved successfully!`)
    } catch (error: any) {
      console.error("Error saving connection:", error)
      setError(error.message || "Failed to save connection")
      // Show error toast
      showDatabaseToast("Save Failed", error.message || "Failed to save connection", "destructive")
      addError(`Error saving database connection: ${error.message || "Unknown error"}`)
    } finally {
      setIsProcessing(false)
    }
  }

  const loadConnection = (connection: {
    id: string;
    name: string;
    type: string;
    config: {
      host: string;
      port: string;
      database: string;
      username: string;
      password: string;
      table: string;
    };
  }) => {
    setConnectionType(connection.type)
    setConnectionConfig({
      ...connection.config,
      password: "", // Clear password for security
    })
    setConnectionName(connection.name) // Set the connection name for reference
    
    // Show toast notification for loaded connection
    showDatabaseToast("Connection Loaded", `Loaded connection "${connection.name}"`)
    
    // IMPORTANT: Force clear any processing status to prevent "File Processing" display
    setProcessingStatus("")
    
    // Also directly clear from localStorage to ensure no persistence
    if (typeof window !== 'undefined') {
      localStorage.removeItem('processingStatus')
      console.log("Forcibly cleared processing status when loading connection")
    }
  }

  const deleteConnection = async (id: string) => {
    setIsProcessing(true)
    // Show deleting toast
    showDatabaseToast("Deleting Connection", "Deleting connection...")
    
    try {
      const apiBaseUrl = getApiBaseUrl()
      const response = await fetch(`${apiBaseUrl}/api/datapuur/db-connections/${id}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || "Failed to delete connection")
      }

      // Refresh the connections list
      fetchSavedConnections()
      // Show success toast
      showDatabaseToast("Connection Deleted", "Connection deleted successfully")
    } catch (error: any) {
      console.error("Error deleting connection:", error)
      setError(error.message || "Failed to delete connection")
      // Show error toast
      showDatabaseToast("Delete Failed", error.message || "Failed to delete connection", "destructive")
      addError(`Error deleting database connection: ${error.message || "Unknown error"}`)
    } finally {
      setIsProcessing(false)
    }
  }

  return (
    <div className="space-y-6">
      <h3 className="text-xl font-semibold text-foreground mb-4 flex items-center">
        <Database className="w-5 h-5 mr-2 text-primary" />
        Database Connection
      </h3>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="connectionName">Connection Name</Label>
            <Input
              id="connectionName"
              value={connectionName}
              onChange={(e) => setConnectionName(e.target.value)}
              placeholder="e.g., Production MySQL"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="connectionType">Database Type</Label>
            <Select value={connectionType} onValueChange={handleTypeChange}>
              <SelectTrigger id="connectionType">
                <SelectValue placeholder="Select database type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="mysql">MySQL</SelectItem>
                <SelectItem value="postgresql">PostgreSQL</SelectItem>
                <SelectItem value="mssql">SQL Server</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="host">Host</Label>
            <Input
              id="host"
              name="host"
              value={connectionConfig.host}
              onChange={handleInputChange}
              placeholder="e.g., 172.104.129.10 or 192.168.1.1"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="port">Port</Label>
            <Input
              id="port"
              name="port"
              value={connectionConfig.port}
              onChange={handleInputChange}
              placeholder="e.g., 3306 for MySQL"
            />
          </div>
        </div>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="database">Database Name</Label>
            <Input
              id="database"
              name="database"
              value={connectionConfig.database}
              onChange={handleInputChange}
              placeholder="e.g., my_database"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="username">Username</Label>
            <Input
              id="username"
              name="username"
              value={connectionConfig.username}
              onChange={handleInputChange}
              placeholder="e.g., root"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              name="password"
              type="password"
              value={connectionConfig.password}
              onChange={handleInputChange}
              placeholder="Enter password"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="table">Table Name</Label>
            <Input
              id="table"
              name="table"
              value={connectionConfig.table}
              onChange={handleInputChange}
              placeholder="e.g., customers"
            />
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-3 pt-4">
        <Button
          variant="outline"
          className="border-primary text-primary hover:bg-primary/10"
          onClick={testConnection}
          disabled={isProcessing}
        >
          Test Connection
        </Button>
        <Button
          variant="outline"
          className="border-secondary text-secondary hover:bg-secondary/10"
          onClick={fetchSchema}
          disabled={isProcessing}
        >
          <Play className="mr-2 h-4 w-4" />
          Fetch Schema
        </Button>
        <Button
          className="bg-primary hover:bg-primary/90 text-primary-foreground"
          onClick={startIngestion}
          disabled={isProcessing}
        >
          <Play className="mr-2 h-4 w-4" />
          Start Ingestion
        </Button>
      </div>

      {/* Save Connection Section */}
      <div className="border-t border-border pt-4 mt-4">
        <h4 className="font-medium text-foreground mb-4">Save Connection</h4>
        <div className="flex space-x-2">
          <Button
            variant="outline"
            className="border-primary text-primary hover:bg-primary/10"
            onClick={saveConnection}
            disabled={isProcessing}
          >
            <Save className="mr-2 h-4 w-4" />
            Save
          </Button>
        </div>
      </div>

      {/* Saved Connections */}
      {savedConnections.length > 0 && (
        <div className="border-t border-border pt-4">
          <h4 className="font-medium text-foreground mb-4">Saved Connections</h4>
          <div className="space-y-2">
            {savedConnections.map((conn) => (
              <div
                key={conn.id}
                className="flex justify-between items-center p-3 border border-border rounded-md bg-card/50 hover:bg-card"
              >
                <div>
                  <p className="font-medium text-foreground">{conn.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {conn.type} • {conn.config.host}:{conn.config.port} • {conn.config.database}
                  </p>
                </div>
                <div className="flex space-x-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => loadConnection(conn)}
                    className="h-8 px-2 text-primary"
                  >
                    Load
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteConnection(conn.id)}
                    className="h-8 px-2 text-destructive"
                  >
                    <Trash className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mt-4 p-4 bg-card/50 rounded-lg border border-border">
        <h4 className="font-medium text-foreground mb-2">Instructions:</h4>
        <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1">
          <li>Configure database connection details to ingest data from SQL databases</li>
          <li>Supported databases: MySQL, PostgreSQL, and SQL Server</li>
          <li>Test your connection before starting ingestion</li>
          <li>Fetch schema to preview the table structure</li>
          <li>Save connections for future use</li>
          <li>Monitor ingestion progress in the Ingestion Jobs section</li>
        </ul>
      </div>
    </div>
  )
}
