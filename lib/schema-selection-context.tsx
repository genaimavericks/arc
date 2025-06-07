"use client"

import { createContext, useContext, useState, useEffect, ReactNode } from "react"
import { useToast } from "@/components/ui/use-toast"

// Define the schema type
export interface Schema {
  id: number
  name: string
  created_at: string
  updated_at?: string
  schema_json: string
  csv_path?: string
  cypher?: string
}

// Context state type
interface SchemaSelectionContextType {
  // State
  schemas: Schema[]
  selectedSchemaId: number | null
  isLoading: boolean
  error: string | null
  
  // Actions
  selectSchema: (id: number | null) => void
  refreshSchemas: () => Promise<void>
  getSchemaById: (id: number) => Schema | undefined
}

// Create context
const SchemaSelectionContext = createContext<SchemaSelectionContextType | undefined>(undefined)

// Provider component
export function SchemaSelectionProvider({ children }: { children: ReactNode }) {
  const [schemas, setSchemas] = useState<Schema[]>([])
  const [selectedSchemaId, setSelectedSchemaId] = useState<number | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { toast } = useToast()

  // Fetch schemas on component mount
  useEffect(() => {
    refreshSchemas()
  }, [])

  // Load schemas from API
  const refreshSchemas = async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      const token = localStorage.getItem('token') // Get token
      if (!token) {
        throw new Error('Authentication token not found.')
      }
      
      const response = await fetch('/api/graphschema/schemas', {
        headers: { // Add headers
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json' // Optional, but good practice
        }
      })
      
      if (!response.ok) {
        throw new Error(`Failed to fetch schemas: ${response.statusText}`)
      }
      
      const data = await response.json()
      setSchemas(data)
      
      // If we have schemas but none selected, select the first one
      if (data.length > 0 && selectedSchemaId === null) {
        setSelectedSchemaId(data[0].id)
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error fetching schemas'
      setError(errorMessage)
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  // Select a schema by ID
  const selectSchema = (id: number | null) => {
    setSelectedSchemaId(id)
  }

  // Get a schema by ID
  const getSchemaById = (id: number) => {
    return schemas.find(schema => schema.id === id)
  }

  // Context value
  const value = {
    schemas,
    selectedSchemaId,
    isLoading,
    error,
    selectSchema,
    refreshSchemas,
    getSchemaById
  }

  return (
    <SchemaSelectionContext.Provider value={value}>
      {children}
    </SchemaSelectionContext.Provider>
  )
}

// Custom hook to use the schema selection context
export function useSchemaSelection() {
  const context = useContext(SchemaSelectionContext)
  
  if (context === undefined) {
    throw new Error("useSchemaSelection must be used within a SchemaSelectionProvider")
  }
  
  return context
}
