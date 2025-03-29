"use client"

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { RefreshCw } from "lucide-react"
import { useState, useEffect } from "react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"

interface SchemaViewerModalProps {
  isOpen: boolean
  onClose: () => void
  datasetId: string
  datasetName: string
}

interface SchemaField {
  name: string
  type: string
  nullable: boolean
  description?: string
}

export function SchemaViewerModal({ isOpen, onClose, datasetId, datasetName }: SchemaViewerModalProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [schema, setSchema] = useState<SchemaField[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen) {
      fetchSchemaData()
    }
  }, [isOpen, datasetId])

  const fetchSchemaData = async () => {
    try {
      setIsLoading(true)
      setError(null)

      // Use the correct schema endpoint instead of the ingestion endpoint
      const response = await fetch(`/api/datapuur/ingestion-schema/${datasetId}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch schema data: ${response.status}`)
      }

      const data = await response.json()

      // Extract schema from the response
      if (data && data.fields) {
        setSchema(data.fields || [])
      } else if (data && data.schema && data.schema.fields) {
        // Alternative location where schema might be stored
        setSchema(data.schema.fields || [])
      } else {
        // If no schema is found, set an empty array
        setSchema([])
      }
    } catch (error) {
      console.error("Error fetching schema data:", error)
      setError("Failed to load schema data. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  const getTypeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case "string":
        return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300"
      case "integer":
      case "number":
      case "float":
      case "double":
        return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300"
      case "boolean":
        return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300"
      case "date":
      case "datetime":
      case "timestamp":
        return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300"
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300"
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Schema: {datasetName}</DialogTitle>
        </DialogHeader>
        {isLoading ? (
          <div className="flex justify-center items-center h-64">
            <RefreshCw className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : error ? (
          <div className="text-center text-red-500 py-4">{error}</div>
        ) : schema.length === 0 ? (
          <div className="text-center py-4 text-muted-foreground">No schema information available</div>
        ) : (
          <ScrollArea className="h-[400px] pr-4">
            <div className="space-y-3">
              {schema.map((field, index) => (
                <Card key={index} className="border border-border">
                  <CardContent className="p-4">
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="font-medium text-foreground">{field.name}</h3>
                        {field.description && <p className="text-sm text-muted-foreground mt-1">{field.description}</p>}
                      </div>
                      <div className="flex gap-2">
                        <Badge className={getTypeColor(field.type)}>{field.type}</Badge>
                        {field.nullable && <Badge variant="outline">Nullable</Badge>}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </ScrollArea>
        )}
      </DialogContent>
    </Dialog>
  )
}
