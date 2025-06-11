"use client"

import { useState, useEffect } from 'react'
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { useToast } from '@/components/ui/use-toast'
import { formatBytes, formatDate } from '@/lib/utils'
import { Loader2, Database, Eye, FileSpreadsheet } from 'lucide-react'
import { TransformedDataset } from '@/lib/datapuur-types'

interface TransformedDatasetsListProps {
  onSelectDataset: React.Dispatch<React.SetStateAction<TransformedDataset | null>>
}

export function TransformedDatasetsList({ onSelectDataset }: TransformedDatasetsListProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [datasets, setDatasets] = useState<TransformedDataset[]>([])
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const { toast } = useToast()
  
  const fetchDatasets = async () => {
    try {
      setIsLoading(true)
      // Get authentication token from localStorage
      const token = localStorage.getItem('token')
      if (!token) {
        throw new Error('Authentication token not found')
      }
      
      const response = await fetch(`/api/datapuur-ai/transformed-datasets?page=${page}&limit=10`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (!response.ok) {
        throw new Error('Failed to fetch transformed datasets')
      }
      
      const data = await response.json()
      setDatasets(data)
      setHasMore(data.length === 10)
    } catch (error) {
      console.error('Error fetching transformed datasets:', error)
      toast({
        title: "Error",
        description: "Failed to load transformed datasets. Please try again.",
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
    }
  }
  
  useEffect(() => {
    fetchDatasets()
  }, [page])
  
  if (isLoading && datasets.length === 0) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-2">Loading datasets...</span>
      </div>
    )
  }
  
  if (!isLoading && datasets.length === 0) {
    return (
      <div className="text-center p-6">
        <FileSpreadsheet className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <h3 className="text-lg font-medium mb-2">No Transformed Datasets Found</h3>
        <p className="text-muted-foreground mb-4">
          Create a transformation plan and execute it to generate transformed datasets.
        </p>
        <Button onClick={() => window.location.href = '/datapuur/ai-transformation'}>
          Go to AI Transformation
        </Button>
      </div>
    )
  }
  
  return (
    <div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Rows</TableHead>
            <TableHead>Columns</TableHead>
            <TableHead>Size</TableHead>
            <TableHead>Created</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {datasets.map((dataset) => (
            <TableRow key={dataset.id}>
              <TableCell className="font-medium">{dataset.name}</TableCell>
              <TableCell>{dataset.row_count?.toLocaleString() || 'Unknown'}</TableCell>
              <TableCell>{dataset.column_count || 'Unknown'}</TableCell>
              <TableCell>{dataset.file_size_bytes ? formatBytes(dataset.file_size_bytes) : 'Unknown'}</TableCell>
              <TableCell>{formatDate(new Date(dataset.created_at))}</TableCell>
              <TableCell>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onSelectDataset(dataset)}
                >
                  <Eye className="h-4 w-4 mr-1" /> View Details
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      
      <div className="flex justify-between mt-4">
        <Button 
          variant="outline" 
          onClick={() => setPage(p => Math.max(1, p - 1))}
          disabled={page === 1}
        >
          Previous
        </Button>
        <Button 
          variant="outline" 
          onClick={() => setPage(p => p + 1)}
          disabled={!hasMore}
        >
          Next
        </Button>
      </div>
    </div>
  )
}
