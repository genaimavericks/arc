"use client"

import { useState, useEffect, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { PlusCircle, Search, Eye, BarChart2, Wand2, RefreshCw, Trash2, ChevronLeft, ChevronRight, FileDown } from "lucide-react"
import { useRouter } from "next/navigation"
import { DatasetPreviewModal } from "@/components/datapuur/dataset-preview-modal"
import { format, formatDistanceToNow } from "date-fns"
import { useToast } from "@/components/ui/use-toast"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"

// Define types based on the API response structure from datapuur.py
interface DataSource {
  id: string
  name: string
  dataset?: string  // New property: filename without extension or table name for DB
  type: string
  last_updated: string
  status: string
  uploaded_by: string
}

interface DataMetrics {
  total_datasets: number
  total_records: number
  storage_used: string
  active_jobs: number
}

interface Activity {
  id: string
  user: string
  action: string
  timestamp: string
  details?: string
}

interface DashboardData {
  recent_datasets: DataSource[]
  data_growth: any[]
  usage_statistics: any
}

export function DataDashboard() {
  const [searchQuery, setSearchQuery] = useState("")
  const [datasets, setDatasets] = useState<DataSource[]>([])
  const [dataMetrics, setDataMetrics] = useState<DataMetrics | null>(null)
  const [activities, setActivities] = useState<Activity[]>([])
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [previewModalOpen, setPreviewModalOpen] = useState(false)
  const [selectedDataset, setSelectedDataset] = useState<{ id: string; name: string } | null>(null)
  const [previewData, setPreviewData] = useState<any>(null)
  const [authError, setAuthError] = useState<string | null>(null)
  const [sortColumn, setSortColumn] = useState<string>("last_updated")
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc")
  // Add state for delete confirmation dialog
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [datasetToDelete, setDatasetToDelete] = useState<{ id: string; name: string } | null>(null)
  const [userRole, setUserRole] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  // Add pagination state
  const [currentPage, setCurrentPage] = useState(1)
  const [itemsPerPage] = useState(10)
  const router = useRouter()
  const { toast } = useToast()

  // Helper function to make authenticated API requests
  const fetchWithAuth = useCallback(async (url: string, options?: RequestInit) => {
    const token = localStorage.getItem("token")

    if (!token) {
      setAuthError("Authentication token not found. Please log in again.")
      throw new Error("Authentication token not found")
    }

    const response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
      ...options,
    })

    if (response.status === 401) {
      setAuthError("Your session has expired. Please log in again.")
      throw new Error("Authentication failed")
    }

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    return response.json()
  }, [])

  // Function to fetch all data from the API
  const fetchData = useCallback(async () => {
    try {
      setIsRefreshing(true)
      setAuthError(null)

      // Fetch data sources
      const dataSources = await fetchWithAuth("/api/datapuur/sources")
      setDatasets(dataSources)

      // Fetch metrics
      try {
        const metrics = await fetchWithAuth("/api/datapuur/metrics")
        console.log("API Response - Metrics:", metrics)
        setDataMetrics(metrics)
      } catch (error) {
        console.error("Error fetching metrics:", error)
      }

      // Fetch activities
      try {
        const activitiesData = await fetchWithAuth("/api/datapuur/activities")
        console.log("API Response - Activities:", activitiesData)
        setActivities(activitiesData)
      } catch (error) {
        console.error("Error fetching activities:", error)
      }

      // Fetch dashboard data
      try {
        const dashboardData = await fetchWithAuth("/api/datapuur/dashboard")
        console.log("API Response - Dashboard:", dashboardData)
        setDashboardData(dashboardData)
        
        // Log specific parts of the dashboard data for easier comparison
        console.log("Dashboard - metrics:", dashboardData.metrics)
        console.log("Dashboard - chart_data:", dashboardData.chart_data)
        console.log("Dashboard - recent_activities:", dashboardData.recent_activities)
        console.log("Dashboard - userRole:", dashboardData.userRole)
      } catch (error) {
        console.error("Error fetching dashboard data:", error)
      }
    } catch (error) {
      console.error("Error fetching data:", error)
      if (!authError) {
        toast({
          title: "Error",
          description: "Failed to fetch datasets. Please try again.",
          variant: "destructive",
        })
      }
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }, [fetchWithAuth, toast, authError])

  // Fetch data on component mount
  useEffect(() => {
    fetchData()

    // Set up auto-refresh every 30 seconds
    const intervalId = setInterval(() => {
      fetchData()
    }, 30000)

    // Clean up interval on component unmount
    return () => clearInterval(intervalId)
  }, [fetchData])

  // Handle authentication errors
  useEffect(() => {
    if (authError) {
      toast({
        title: "Authentication Error",
        description: authError,
        variant: "destructive",
      })

      // Redirect to login page after a short delay
      const timeoutId = setTimeout(() => {
        router.push("/login")
      }, 2000)

      return () => clearTimeout(timeoutId)
    }
  }, [authError, toast, router])

  useEffect(() => {
    // Get user role from localStorage
    const role = localStorage.getItem("userRole")
    console.log("User role from localStorage:", role)
    setUserRole(role)
    
    // If role is null or undefined, default to admin for testing
    if (!role) {
      console.log("Setting default role to admin for testing")
      setUserRole("admin")
    }
  }, [])

  // Add a function to handle sorting
  const handleSort = (column: string) => {
    if (sortColumn === column) {
      // Toggle direction if clicking the same column
      setSortDirection(sortDirection === "asc" ? "desc" : "asc")
    } else {
      // Set new column and default to descending
      setSortColumn(column)
      setSortDirection("desc")
    }
  }

  // Add a function to get sorted datasets
  const getSortedDatasets = useCallback(() => {
    if (!datasets || datasets.length === 0) return []

    // Filter datasets based on search query
    const filtered = datasets.filter((dataset) =>
      dataset.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (dataset.dataset && dataset.dataset.toLowerCase().includes(searchQuery.toLowerCase())) ||
      dataset.type.toLowerCase().includes(searchQuery.toLowerCase()) ||
      dataset.status.toLowerCase().includes(searchQuery.toLowerCase()) ||
      dataset.uploaded_by.toLowerCase().includes(searchQuery.toLowerCase())
    )

    // Sort the filtered datasets
    return [...filtered].sort((a, b) => {
      let valueA: any = a[sortColumn as keyof DataSource]
      let valueB: any = b[sortColumn as keyof DataSource]

      // Special handling for dates
      if (sortColumn === "last_updated") {
        valueA = new Date(valueA).getTime()
        valueB = new Date(valueB).getTime()
      }

      // Handle string comparison
      if (typeof valueA === "string" && typeof valueB === "string") {
        return sortDirection === "asc" 
          ? valueA.localeCompare(valueB) 
          : valueB.localeCompare(valueA)
      }

      // Handle numeric comparison
      return sortDirection === "asc" ? valueA - valueB : valueB - valueA
    })
  }, [datasets, searchQuery, sortColumn, sortDirection])

  // Replace filteredDatasets with the sorted version
  const filteredDatasets = getSortedDatasets()

  // Add pagination logic
  const indexOfLastItem = currentPage * itemsPerPage
  const indexOfFirstItem = indexOfLastItem - itemsPerPage
  const currentItems = filteredDatasets.slice(indexOfFirstItem, indexOfLastItem)
  const totalPages = Math.ceil(filteredDatasets.length / itemsPerPage)

  // Add pagination control functions
  const goToNextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1)
    }
  }

  const goToPreviousPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1)
    }
  }

  const goToPage = (pageNumber: number) => {
    setCurrentPage(pageNumber)
  }

  const getStatusClass = (status: string) => {
    switch (status.toLowerCase()) {
      case "active":
      case "completed":
      case "exported":
        return "text-green-600"
      case "profiled":
        return "text-blue-600"
      case "ingested":
      case "processing":
        return "text-amber-600"
      case "transform":
      case "transforming":
        return "text-purple-600"
      case "failed":
        return "text-red-600"
      default:
        return "text-gray-600"
    }
  }

  const handleNewDataset = () => {
    router.push("/datapuur/ingestion")
  }

  const handleRefresh = () => {
    fetchData()
  }

  const handleDeleteClick = (dataset: DataSource) => {
    setDatasetToDelete({ id: dataset.id, name: dataset.dataset || dataset.name })
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = async () => {
    if (!datasetToDelete) return

    try {
      setIsDeleting(true)
      
      // Use the new delete-file endpoint with fetchWithAuth
      const response = await fetchWithAuth(`/api/datapuur/delete-file/${datasetToDelete.id}`, {
        method: "DELETE",
      })

      if (response.success) {
        // Remove the dataset from the state
        setDatasets((prevDatasets) => prevDatasets.filter((d) => d.id !== datasetToDelete.id))
        
        toast({
          title: "Dataset deleted",
          description: `${datasetToDelete.name} has been successfully deleted.`,
        })
      }
    } catch (error) {
      console.error("Error deleting dataset:", error)
      toast({
        title: "Error",
        description: "Failed to delete dataset. Please try again.",
        variant: "destructive",
      })
    } finally {
      setIsDeleting(false)
      setDeleteDialogOpen(false)
      setDatasetToDelete(null)
    }
  }

  const handlePreview = async (datasetId: string, datasetName: string) => {
    try {
      setSelectedDataset({ id: datasetId, name: datasetName })

      // Fetch preview data from the API using the new file-preview endpoint with fetchWithAuth helper
      const previewData = await fetchWithAuth(`/api/datapuur/file-preview/${datasetId}`)
      setPreviewData(previewData)
      setPreviewModalOpen(true)
    } catch (error) {
      console.error("Error fetching preview data:", error)
      if (!authError) {
        toast({
          title: "Error",
          description: "Failed to load preview data. Please try again.",
          variant: "destructive",
        })
      }
    }
  }

  const handleProfile = (datasetId: string, e: React.MouseEvent) => {
    // Navigate to the profile page with the dataset ID as a query parameter
    // and set the active tab to "details" to show profile details directly
    e.preventDefault();
    router.push(`/datapuur/profile?fileId=${datasetId}&activeTab=details`);
  }

  const handleTransform = (datasetId: string) => {
    router.push(`/datapuur/transformation/${datasetId}`)
  }

  const handleExport = (datasetId: string) => {
    router.push(`/datapuur/export?id=${datasetId}`)
  }

  const formatDate = (dateString: string) => {
    if (!dateString) return "N/A"
    try {
      // Remove debugging logs in production
      // console.log("Original date string:", dateString);
      
      // Create current time for reference
      const now = new Date();
      
      // Parse the date with proper timezone handling
      let date: Date;
      
      // First, normalize the date string format
      if (dateString.includes('Z')) {
        // Already has UTC marker - parse directly
        date = new Date(dateString);
      } else if (
        (dateString.includes('+') && dateString.indexOf('T') < dateString.indexOf('+')) ||
        (dateString.includes('-') && dateString.indexOf('T') < dateString.lastIndexOf('-'))
      ) {
        // Has timezone offset like +05:30 - parse directly
        date = new Date(dateString);
      } else if (dateString.includes('T')) {
        // Handle database records: has T separator but no timezone
        // Always treat these as UTC time by adding the Z marker
        date = new Date(dateString + 'Z');
      } else {
        // Plain date string without time - parse as local time
        date = new Date(dateString);
      }
      
      // Force conversion to local time by creating a new Date object
      // This ensures consistent handling for both file and database records
      const localDate = new Date(date.getTime());
      // console.log("Date converted to local:", localDate.toString());
      date = localDate;
      
      // Calculate time difference in minutes for debugging
      const diffMs = now.getTime() - date.getTime();
      const diffMinutes = Math.floor(diffMs / (1000 * 60));
      console.log(`Time difference: ${diffMinutes} minutes ago`);
      
      // Format for relative time display - using addSuffix ensures we get "X time ago"
      const relativeTime = formatDistanceToNow(date, { addSuffix: true });
      
      // Format the date in local time with seconds
      const formattedDate = format(date, 'yyyy-MM-dd HH:mm:ss');
      
      return (
        <div>
          <div>{relativeTime}</div>
          <div className="text-xs">{formattedDate}</div>
        </div>
      )
    } catch (error) {
      console.error("Error formatting date:", error, dateString);
      return dateString;
    }
  }

  const canDeleteDataset = (dataset: DataSource) => {
    console.log("Current user role:", userRole)
    // For testing, always return true to make the button visible
    return true
    // Uncomment this when testing is complete:
    // return userRole === "admin"
  }

  return (
    <div className="w-full space-y-2 mx-6 max-w-[calc(100%-3rem)]">
      <div className="flex w-full items-center justify-between pb-2 pt-2">
        <h2 className="text-2xl font-bold tracking-tight ml-3">Dashboard</h2>
        <div className="flex items-center space-x-2 mr-3">
          <div className="flex items-center">
            <Search className="h-4 w-4 text-muted-foreground absolute ml-2" />
            <Input 
              placeholder="Search Datasets..." 
              className="max-w-sm pl-8" 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <Button 
            variant="outline" 
            size="icon"
            onClick={handleRefresh} 
            disabled={isRefreshing} 
            title="Refresh datasets"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      <div className="bg-card/80 backdrop-blur-sm p-4 rounded-lg border border-border shadow-md mb-4 overflow-x-auto">
        <div className="flex flex-row items-center justify-between mb-4">
          <div className="flex items-center">
            <h3 className="text-xl font-semibold text-foreground flex items-center">
              <Table className="w-5 h-5 mr-2 text-primary" />
              Datasets
            </h3>
            <Button onClick={handleNewDataset} className="flex items-center gap-2 ml-4" size="sm">
              <PlusCircle className="h-4 w-4" />
            </Button>
          </div>
          <div className="text-sm text-muted-foreground">Auto-refreshes every 30 seconds</div>
        </div>
        <div>
          {isLoading ? (
            <div className="flex justify-center items-center h-64">
              <RefreshCw className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : (
            <>
              <Table className="w-full">
                <TableHeader>
                  <TableRow className="border-t border-b border-border">
                    <TableHead 
                      className="cursor-pointer hover:text-primary transition-colors px-4 py-3"
                      onClick={() => handleSort("name")}
                    >
                      Name
                      {sortColumn === "name" && (
                        <span className="ml-1">
                          {sortDirection === "asc" ? "↑" : "↓"}
                        </span>
                      )}
                    </TableHead>
                    <TableHead 
                      className="cursor-pointer hover:text-primary transition-colors px-4 py-3"
                      onClick={() => handleSort("type")}
                    >
                      Type
                      {sortColumn === "type" && (
                        <span className="ml-1">
                          {sortDirection === "asc" ? "↑" : "↓"}
                        </span>
                      )}
                    </TableHead>
                    <TableHead 
                      className="cursor-pointer hover:text-primary transition-colors px-4 py-3"
                      onClick={() => handleSort("last_updated")}
                    >
                      Last Updated
                      {sortColumn === "last_updated" && (
                        <span className="ml-1">
                          {sortDirection === "asc" ? "↑" : "↓"}
                        </span>
                      )}
                    </TableHead>
                    <TableHead 
                      className="cursor-pointer hover:text-primary transition-colors px-4 py-3"
                      onClick={() => handleSort("status")}
                    >
                      Status
                      {sortColumn === "status" && (
                        <span className="ml-1">
                          {sortDirection === "asc" ? "↑" : "↓"}
                        </span>
                      )}
                    </TableHead>
                    <TableHead 
                      className="cursor-pointer hover:text-primary transition-colors px-4 py-3"
                      onClick={() => handleSort("uploaded_by")}
                    >
                      Uploaded By
                      {sortColumn === "uploaded_by" && (
                        <span className="ml-1">
                          {sortDirection === "asc" ? "↑" : "↓"}
                        </span>
                      )}
                    </TableHead>
                    <TableHead className="w-[180px] text-center px-4 py-3">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {currentItems.length > 0 ? (
                    currentItems.map((dataset) => (
                      <TableRow key={dataset.id}>
                        <TableCell className="font-medium px-4 py-3">{dataset.dataset || dataset.name}</TableCell>
                        <TableCell className="px-4 py-3">{dataset.type}</TableCell>
                        <TableCell className="px-4 py-3">{formatDate(dataset.last_updated)}</TableCell>
                        <TableCell className={`${getStatusClass(dataset.status)} px-4 py-3`}>{dataset.status}</TableCell>
                        <TableCell className="px-4 py-3">{dataset.uploaded_by}</TableCell>
                        <TableCell className="px-4 py-3">
                          <div className="flex justify-center space-x-2">
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handlePreview(dataset.id, dataset.dataset || dataset.name)}
                              title="Preview"
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={(e) => handleProfile(dataset.id, e)}
                              title="Profile"
                              disabled={dataset.status.toLowerCase() !== "active"}
                            >
                              <BarChart2 className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleTransform(dataset.id)}
                              title="Transform"
                              disabled={dataset.status.toLowerCase() !== "active"}
                            >
                              <Wand2 className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleExport(dataset.id)}
                              title="Export"
                              disabled={dataset.status.toLowerCase() !== "active"}
                            >
                              <FileDown className="h-4 w-4" />
                            </Button>

                            {canDeleteDataset(dataset) && (
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleDeleteClick(dataset)}
                                title="Delete"
                                className="text-destructive hover:bg-destructive/10"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={6} className="h-24 text-center">
                        {searchQuery
                          ? "No matching datasets found."
                          : "No datasets available. Create one by clicking 'New Dataset'."}
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
              {filteredDatasets.length > 0 && (
                <div className="flex items-center justify-between mt-4 px-2">
                  <div className="text-sm text-muted-foreground">
                    Showing {indexOfFirstItem + 1} to {Math.min(indexOfLastItem, filteredDatasets.length)} of {filteredDatasets.length} datasets
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={goToPreviousPage}
                      disabled={currentPage === 1}
                      className="h-8 w-8 p-0"
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      // Show pages around current page
                      let pageNum = 0;
                      if (totalPages <= 5) {
                        // If we have 5 or fewer pages, show all
                        pageNum = i + 1;
                      } else if (currentPage <= 3) {
                        // If we're near the start
                        pageNum = i + 1;
                      } else if (currentPage >= totalPages - 2) {
                        // If we're near the end
                        pageNum = totalPages - 4 + i;
                      } else {
                        // We're in the middle
                        pageNum = currentPage - 2 + i;
                      }
                      
                      return (
                        <Button
                          key={pageNum}
                          variant={currentPage === pageNum ? "default" : "outline"}
                          size="sm"
                          onClick={() => goToPage(pageNum)}
                          className="h-8 w-8 p-0"
                        >
                          {pageNum}
                        </Button>
                      );
                    })}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={goToNextPage}
                      disabled={currentPage === totalPages}
                      className="h-8 w-8 p-0"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
      {selectedDataset && (
        <DatasetPreviewModal
          isOpen={previewModalOpen}
          onClose={() => setPreviewModalOpen(false)}
          datasetId={selectedDataset.id}
          datasetName={selectedDataset.name}
          previewData={previewData}
        />
      )}
      
      {/* Delete confirmation dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure you want to delete this dataset?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete the dataset
              {datasetToDelete ? ` "${datasetToDelete.name}"` : ""} and all associated data.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleDeleteConfirm} 
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
