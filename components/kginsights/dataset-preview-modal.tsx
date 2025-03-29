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
      // Ensure data.data is an array
      const dataArray = Array.isArray(data.data) ? data.data : [data.data];
      
      // Format: { headers: string[], data: any[][] }
      return (
        <ScrollArea className="h-[400px]">
          <Table>
            <TableHeader>
              <TableRow>
                {data.headers.map((header: string, index: number) => (
                  <TableHead key={index}>{header}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {dataArray.map((row: any[], rowIndex: number) => (
                <TableRow key={rowIndex}>
                  {Array.isArray(row) ? row.map((cell, cellIndex) => (
                    <TableCell key={cellIndex}>{cell !== null && cell !== undefined ? String(cell) : ""}</TableCell>
                  )) : (
                    <TableCell>{row !== null && row !== undefined ? String(row) : ""}</TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </ScrollArea>
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
                      {row[header] !== null && row[header] !== undefined ? String(row[header]) : ""}
                    </TableCell>
                  )) : (
                    <TableCell>
                      {row !== null && row !== undefined ? String(row) : ""}
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

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-4xl">
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
          renderPreviewTable()
        )}
      </DialogContent>
    </Dialog>
  )
}
