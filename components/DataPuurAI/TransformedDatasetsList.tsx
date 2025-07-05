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
import { Loader2, Database, Eye, FileSpreadsheet, Trash2 } from 'lucide-react'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog'
import { useAuth } from '@/lib/auth-context'
import { fetchWithAuth } from '@/lib/auth-utils'
import { TransformedDataset } from '@/lib/datapuur-types'

interface TransformedDatasetsListProps {
  onSelectDataset: React.Dispatch<React.SetStateAction<TransformedDataset | null>>
}

export function TransformedDatasetsList({ onSelectDataset }: TransformedDatasetsListProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [datasets, setDatasets] = useState<TransformedDataset[]>([])
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [datasetToDelete, setDatasetToDelete] = useState<TransformedDataset | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const { toast } = useToast()
  const { user } = useAuth()
  
  const fetchDatasets = async () => {
    try {
      setIsLoading(true)
      
      try {
        const data = await fetchWithAuth(`/api/datapuur-ai/transformed-datasets?page=${page}&limit=10`)
        setDatasets(data)
        setHasMore(data.length === 10)
      } catch (apiError) {
        throw new Error('Failed to fetch transformed datasets')
      }
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
  
  const handleDeleteDataset = async () => {
    if (!datasetToDelete) return
    
    try {
      setIsDeleting(true)
      
      const response = await fetch(`/api/datapuur-ai/transformed-datasets/${datasetToDelete.id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        }
      })
      
      if (!response.ok) {
        throw new Error('Failed to delete dataset')
      }
      
      toast({
        title: "Success",
        description: `Dataset "${datasetToDelete.name}" has been deleted successfully.`,
      })
      
      // Refresh the dataset list
      fetchDatasets()
    } catch (error) {
      console.error('Error deleting dataset:', error)
      toast({
        title: "Error",
        description: "Failed to delete dataset. Please try again.",
        variant: "destructive"
      })
    } finally {
      setIsDeleting(false)
      setDatasetToDelete(null)
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
                <div className="flex space-x-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onSelectDataset(dataset)}
                  >
                    <Eye className="h-4 w-4 mr-1" /> View Details
                  </Button>
                  {user?.permissions && (user.permissions.includes('datapuur:write') || user.permissions.includes('datapuur:manage')) && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="text-destructive hover:bg-destructive hover:text-destructive-foreground"
                      onClick={() => setDatasetToDelete(dataset)}
                      disabled={isDeleting}
                    >
                      <Trash2 className="h-4 w-4 mr-1" /> Delete
                    </Button>
                  )}
                </div>
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
      
      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!datasetToDelete} onOpenChange={(open) => !open && setDatasetToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure you want to delete this dataset?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete the dataset "{datasetToDelete?.name}".
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteDataset}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  Deleting...
                </>
              ) : (
                'Delete'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
