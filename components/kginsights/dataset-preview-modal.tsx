"use client"

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { ScrollArea } from "@/components/ui/scroll-area"
import { RefreshCw } from "lucide-react"
import { useState, useEffect } from "react"

interface DatasetPreviewModalProps {
  isOpen: boolean
  onClose: () => void
  datasetId: string
  datasetName: string
}

export function DatasetPreviewModal({ isOpen, onClose, datasetId, datasetName }: DatasetPreviewModalProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [data, setData] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen) {
      fetchPreviewData()
    }
  }, [isOpen, datasetId])

  const fetchPreviewData = async () => {
    try {
      setIsLoading(true)
      setError(null)

      // Fetch preview data from the API
      const response = await fetch(`/api/datapuur/ingestion-preview/${datasetId}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch preview data: ${response.status}`)
      }

      const data = await response.json()
      console.log("Preview data:", data)
      
      // Ensure we're only showing a limited number of rows (max 100)
      if (data && data.data && Array.isArray(data.data) && data.data.length > 100) {
        data.data = data.data.slice(0, 100)
      }
      
      setData(data)
    } catch (error) {
      console.error("Error fetching preview data:", error)
      setError("Failed to load preview data. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  const renderPreviewTable = () => {
    if (!data) {
      return <div className="text-center py-4">No preview data available</div>
    }

    // Handle different data structures that might come from the API
    if (data.headers && data.data) {
      // For JSON data format - special handling to flatten the view
      if (data.type === "json") {
        // Ensure data.data is an array and limit to 100 rows
        let dataArray = Array.isArray(data.data) ? data.data : [data.data];
        
        // If we have a single object with nested arrays, extract those
        if (dataArray.length === 1 && dataArray[0] && typeof dataArray[0] === 'object') {
          const firstItem = dataArray[0];
          const potentialArray = Object.values(firstItem).find(val => Array.isArray(val));
          if (potentialArray && Array.isArray(potentialArray)) {
            dataArray = potentialArray.slice(0, 100);
          }
        }
        
        // If we still have too many rows, limit to 100
        if (dataArray.length > 100) {
          dataArray = dataArray.slice(0, 100);
        }
        
        // Extract headers if not provided
        const headers = data.headers || (dataArray.length > 0 && typeof dataArray[0] === 'object' 
          ? Object.keys(dataArray[0]) 
          : ['Value']);
        
        return (
          <div className="overflow-x-auto w-full">
            <Table className="min-w-max">
              <TableHeader>
                <TableRow>
                  {headers.map((header: string, index: number) => (
                    <TableHead key={index} className="whitespace-nowrap">{header}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {dataArray.map((row: { [key: string]: any }, rowIndex: number) => (
                  <TableRow key={rowIndex}>
                    {typeof row === 'object' && row !== null ? headers.map((header: string, cellIndex: number) => (
                      <TableCell key={cellIndex} className="whitespace-nowrap">
                        {formatCellValue(row[header])}
                      </TableCell>
                    )) : (
                      <TableCell colSpan={headers.length} className="whitespace-nowrap">
                        {formatCellValue(row)}
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )
      }
      
      // For other tabular data formats (CSV, etc.)
      // Ensure data.data is an array
      const dataArray = Array.isArray(data.data) ? data.data : [data.data];
      
      return (
        <div className="overflow-x-auto w-full">
          <Table className="min-w-max">
            <TableHeader>
              <TableRow>
                {data.headers.map((header: string, index: number) => (
                  <TableHead key={index} className="whitespace-nowrap">{header}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {dataArray.map((row: any[], rowIndex: number) => (
                <TableRow key={rowIndex}>
                  {Array.isArray(row) ? row.map((cell, cellIndex) => (
                    <TableCell key={cellIndex} className="whitespace-nowrap">{formatCellValue(cell)}</TableCell>
                  )) : (
                    <TableCell className="whitespace-nowrap">{formatCellValue(row)}</TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )
    } else if (data.data) {
      // Ensure data.data is an array
      const dataArray = Array.isArray(data.data) ? data.data : [data.data];
      
      // Format: { data: object[] }
      // Only try to get headers if we have array data with objects
      const headers = (Array.isArray(data.data) && data.data.length > 0 && typeof data.data[0] === 'object') 
        ? Object.keys(data.data[0]) 
        : ['Value'];

      return (
        <ScrollArea className="h-[400px]">
          <Table>
            <TableHeader>
              <TableRow>
                {headers.map((header, index) => (
                  <TableHead key={index}>{header}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {dataArray.map((row: any, rowIndex: number) => (
                <TableRow key={rowIndex}>
                  {typeof row === 'object' && row !== null ? headers.map((header, cellIndex) => (
                    <TableCell key={cellIndex}>
                      {formatCellValue(row[header])}
                    </TableCell>
                  )) : (
                    <TableCell>
                      {formatCellValue(row)}
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </ScrollArea>
      )
    } else {
      // Unknown format
      return <div className="text-center py-4">Preview data is in an unsupported format</div>
    }
  }

  // Helper function to format cell values properly
  const formatCellValue = (value: any): React.ReactNode => {
    if (value === null || value === undefined) {
      return "";
    }
    
    if (typeof value === 'object') {
      try {
        // For better readability in the UI, use a pre-formatted display
        return (
          <pre className="text-xs max-w-[200px] overflow-auto">
            {JSON.stringify(value, null, 2)}
          </pre>
        );
      } catch (e) {
        return "[Complex Object]";
      }
    }
    
    return String(value);
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-6xl max-h-[90vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle>Preview: {datasetName}</DialogTitle>
        </DialogHeader>
        {isLoading ? (
          <div className="flex justify-center items-center h-64">
            <RefreshCw className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : error ? (
          <div className="text-center text-red-500 py-4">{error}</div>
        ) : (
          <>
            <div className="text-sm text-muted-foreground mb-2">
              Showing preview data (limited to 100 rows). For full data access, use the data exploration tools.
            </div>
            <div 
              className="overflow-x-auto overflow-y-auto max-h-[70vh]" 
              style={{ 
                scrollbarWidth: 'auto', 
                scrollbarColor: 'rgba(155, 155, 155, 0.7) transparent',
                overflowX: 'scroll',
                paddingBottom: '12px'
              }}
            >
              {renderPreviewTable()}
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
