"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { 
  ArrowLeft, 
  ArrowRight, 
  Calendar, 
  ChevronDown, 
  ChevronLeft, 
  ChevronRight, 
  Download, 
  Eye, 
  FileDown, 
  FileText, 
  Filter, 
  HardDrive, 
  RefreshCw,
  Search
} from "lucide-react"
import { motion } from "framer-motion"
import { formatDistanceToNow, format } from "date-fns"
import { getApiBaseUrl } from "@/lib/config"
import { fetchWithAuth, handleAuthFailure } from "@/lib/auth-utils"
import { toast } from "@/hooks/use-toast"
import { DataPuurLayout } from "@/components/datapuur/datapuur-layout"

// Define dataset interface
interface Dataset {
  id: string
  name: string    // Original filename with extension or connection string for DB
  dataset?: string // Filename without extension for files, or table name for DB
  type: string
  size: number
  uploaded_at: string
  uploaded_by: string
  source_type: string
  row_count?: number
}

// Constant for maximum preview rows
<<<<<<< HEAD
const MAX_PREVIEW_ROWS = 500;
=======
const MAX_PREVIEW_ROWS = 2000;
>>>>>>> 7f05c0c (Update Datapuur Export page: Add 2000 row preview limit, update pagination display text, and change filter message styling to blue (#0569d9))

export default function ExportPage() {
  // Helper function to strip file extensions
  const stripFileExtension = (filename: string): string => {
    return filename.split('.').slice(0, -1).join('.');
  }

  // State for datasets
  const [isLoading, setIsLoading] = useState(true)
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [filteredDatasets, setFilteredDatasets] = useState<Dataset[]>([])
  const [searchQuery, setSearchQuery] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [itemsPerPage] = useState(10)
  
  // State for sorting
  const [sortField, setSortField] = useState<"name" | "size" | "uploaded_at">("uploaded_at")
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc")
  
  // Track expanded items
  const [expandedItems, setExpandedItems] = useState<Record<string, boolean>>({})
  // Track which tab is active for each expanded item
  const [activeTabs, setActiveTabs] = useState<Record<string, string>>({})
  
  // Add state for storing fetched data and loading states
  const [itemData, setItemData] = useState<Record<string, { preview: any; filter: any }>>({})  
  const [tabLoadingStates, setTabLoadingStates] = useState<
    Record<string, { preview: boolean; filter: boolean }>
  >({})
  
  // Add state for preview pagination
  const [previewPage, setPreviewPage] = useState<Record<string, number>>({})
  const [previewPageSize] = useState(15) // Fixed at 15 rows per page as per requirements
  
  // Add state for filters
  const [activeFilters, setActiveFilters] = useState<Record<string, { column: string; operator: string; value: string }>>({})
  
  // Animation variants
  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.05,
      },
    },
  }

  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 },
  }
  
  // Format file size for display
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
  }

  // Function to handle sorting
  const handleSort = (field: "name" | "size" | "uploaded_at") => {
    // If clicking the same field, toggle direction
    if (field === sortField) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc")
    } else {
      // If clicking a new field, set it as the sort field and default to descending
      setSortField(field)
      setSortDirection("desc")
    }
  }

  // Function to sort datasets
  const sortDatasets = (data: Dataset[]) => {
    return [...data].sort((a, b) => {
      let comparison = 0
      
      if (sortField === "name") {
        comparison = a.name.localeCompare(b.name)
      } else if (sortField === "size") {
        comparison = a.size - b.size
      } else if (sortField === "uploaded_at") {
        comparison = new Date(a.uploaded_at).getTime() - new Date(b.uploaded_at).getTime()
      }
      
      return sortDirection === "asc" ? comparison : -comparison
    })
  }

  // Function to fetch datasets
  const fetchDatasets = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const apiBaseUrl = getApiBaseUrl()
      const data = await fetchWithAuth(
        `/api/export/datasets?page=${page}&limit=${itemsPerPage}&search=${encodeURIComponent(searchQuery)}`
      )
      const sortedData = sortDatasets(data.datasets)
      setDatasets(data.datasets)
      setFilteredDatasets(sortedData)
      setTotalPages(Math.ceil(data.total / itemsPerPage))
    } catch (err) {
      console.error("Error fetching datasets:", err)
      setError("Failed to load datasets. Please try again later.")
      
      // Use mock data for demonstration if API fails
      const mockData = generateMockData()
      const sortedMockData = sortDatasets(mockData)
      setDatasets(mockData)
      setFilteredDatasets(sortedMockData)
      setTotalPages(Math.ceil(mockData.length / itemsPerPage))
    } finally {
      setIsLoading(false)
    }
  }

  // Function to toggle expanded state
  const toggleExpand = (id: string) => {
    setExpandedItems((prev) => {
      const newState = { ...prev, [id]: !prev[id] }
      
      // If expanding, set default active tab and fetch preview data
      if (newState[id] && !activeTabs[id]) {
        setActiveTabs((prevTabs) => ({ ...prevTabs, [id]: "preview" }))
        fetchPreviewData(id)
      }
      
      return newState
    })
  }

  // Function to set active tab for an item
  const setActiveTab = (id: string, tab: string) => {
    setActiveTabs((prev) => ({ ...prev, [id]: tab }))
    
    // Fetch data based on tab type if not already loaded
    if (tab === "preview" && (!itemData[id]?.preview || activeFilters[id])) {
      fetchPreviewData(id)
    } else if (tab === "filter" && !itemData[id]?.filter) {
      // For filter tab, we just need to ensure preview data is loaded
      if (!itemData[id]?.preview) {
        fetchPreviewData(id)
      }
    }
  }

  // Function to fetch preview data
  const fetchPreviewData = async (id: string) => {
    // Set loading state
    setTabLoadingStates((prev) => ({
      ...prev,
      [id]: { ...prev[id], preview: true },
    }))
    
    try {
      const apiBaseUrl = getApiBaseUrl()
      const currentPage = previewPage[id] || 1
      
      // Apply filters if they exist
      let endpoint = `/api/export/datasets/${id}/preview?page=${currentPage}&page_size=${previewPageSize}&max_rows=${MAX_PREVIEW_ROWS}`
      
      if (activeFilters[id]) {
        const { column, operator, value } = activeFilters[id]
        endpoint = `/api/export/datasets/${id}/filter?column=${column}&operator=${operator}&value=${encodeURIComponent(value)}&page=${currentPage}&page_size=${previewPageSize}&max_rows=${MAX_PREVIEW_ROWS}`
      }
      
      // Use fetchWithAuth for authenticated requests
      const data = await fetchWithAuth(endpoint)
      
      // Update item data
      setItemData((prev) => ({
        ...prev,
        [id]: { ...prev[id], preview: data },
      }))
    } catch (err) {
      console.error(`Error fetching preview for dataset ${id}:`, err)
      toast({
        title: "Error",
        description: "Failed to load preview data. Please try again.",
        variant: "destructive",
      })
      
      // Use mock data for demonstration
      const mockPreviewData = generateMockPreviewData(id)
      setItemData((prev) => ({
        ...prev,
        [id]: { ...prev[id], preview: mockPreviewData },
      }))
    } finally {
      // Clear loading state
      setTabLoadingStates((prev) => ({
        ...prev,
        [id]: { ...prev[id], preview: false },
      }))
    }
  }

  // Function to handle preview pagination
  const handlePreviewPageChange = (id: string, newPage: number) => {
    setPreviewPage((prev) => ({ ...prev, [id]: newPage }))
    
    // Refetch data with new page
    setTimeout(() => {
      fetchPreviewData(id)
    }, 0)
  }

  // Function to apply filter
  const applyFilter = (id: string, column: string, operator: string, value: string) => {
    // Validate inputs to prevent errors
    if (!id || !column || !operator || !value.trim()) {
      toast({
        title: "Invalid filter",
        description: "Please provide all filter values",
        variant: "destructive"
      })
      return
    }

    try {
      // Update active filters and reset to page 1 in a single batch update
      const newFilter = { column, operator, value }
      setActiveFilters((prev) => ({
        ...prev,
        [id]: newFilter,
      }))
      
      // Reset to page 1 when applying a filter
      setPreviewPage((prev) => ({ ...prev, [id]: 1 }))
      
      // Directly fetch filtered data with the new filter values
      // This ensures we're using the new filter values directly rather than depending on state update
      const apiBaseUrl = getApiBaseUrl()
      const currentPage = 1 // Always start at page 1 when applying a filter
      
      // Set loading state
      setTabLoadingStates((prev) => ({
        ...prev,
        [id]: { ...prev[id], preview: true },
      }))
      
      // Construct URL with the new filter values directly (not from state)
      const url = `${apiBaseUrl}/api/export/datasets/${id}/filter?column=${column}&operator=${operator}&value=${encodeURIComponent(value)}&page=${currentPage}&page_size=${previewPageSize}&max_rows=${MAX_PREVIEW_ROWS}`
      
      fetch(url, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      })
      .then(response => {
        if (!response.ok) {
          throw new Error("Failed to fetch preview data")
        }
        return response.json()
      })
      .then(data => {
        // Update item data
        setItemData((prev) => ({
          ...prev,
          [id]: { ...prev[id], preview: data },
        }))
      })
      .catch(err => {
        console.error(`Error fetching preview for dataset ${id}:`, err)
        toast({
          title: "Error",
          description: "Failed to load preview data. Please try again.",
          variant: "destructive",
        })
        
        // Use mock data for demonstration
        const mockPreviewData = generateMockPreviewData(id)
        setItemData((prev) => ({
          ...prev,
          [id]: { ...prev[id], preview: mockPreviewData },
        }))
      })
      .finally(() => {
        // Clear loading state
        setTabLoadingStates((prev) => ({
          ...prev,
          [id]: { ...prev[id], preview: false },
        }))
      })
    } catch (error) {
      console.error("Error applying filter:", error)
      toast({
        title: "Error",
        description: "Failed to apply filter. Please try again.",
        variant: "destructive"
      })
    }
  }

  // Function to clear filter
  const clearFilter = (id: string) => {
    try {
      // Remove the active filter
      setActiveFilters((prev) => {
        const newFilters = { ...prev }
        delete newFilters[id]
        return newFilters
      })
      
      // Reset filter form values
      setFilterColumns((prev) => {
        const newValues = { ...prev }
        delete newValues[id]
        return newValues
      })
      
      setFilterOperators((prev) => {
        const newValues = { ...prev }
        delete newValues[id]
        return newValues
      })
      
      setFilterValues((prev) => {
        const newValues = { ...prev }
        delete newValues[id]
        return newValues
      })
      
      // Reset to page 1
      setPreviewPage((prev) => ({ ...prev, [id]: 1 }))
      
      // Directly fetch unfiltered data without waiting for state updates
      const apiBaseUrl = getApiBaseUrl()
      const currentPage = 1 // Always start at page 1 when clearing a filter
      
      // Set loading state
      setTabLoadingStates((prev) => ({
        ...prev,
        [id]: { ...prev[id], preview: true },
      }))
      
      // Use the unfiltered endpoint directly
      const url = `${apiBaseUrl}/api/export/datasets/${id}/preview?page=${currentPage}&page_size=${previewPageSize}&max_rows=${MAX_PREVIEW_ROWS}`
      
      fetch(url, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      })
      .then(response => {
        if (!response.ok) {
          throw new Error("Failed to fetch preview data")
        }
        return response.json()
      })
      .then(data => {
        // Update item data
        setItemData((prev) => ({
          ...prev,
          [id]: { ...prev[id], preview: data },
        }))
      })
      .catch(err => {
        console.error(`Error fetching preview for dataset ${id}:`, err)
        toast({
          title: "Error",
          description: "Failed to load preview data. Please try again.",
          variant: "destructive",
        })
        
        // Use mock data for demonstration
        const mockPreviewData = generateMockPreviewData(id)
        setItemData((prev) => ({
          ...prev,
          [id]: { ...prev[id], preview: mockPreviewData },
        }))
      })
      .finally(() => {
        // Clear loading state
        setTabLoadingStates((prev) => ({
          ...prev,
          [id]: { ...prev[id], preview: false },
        }))
      })
    } catch (error) {
      console.error("Error clearing filter:", error)
      toast({
        title: "Error",
        description: "Failed to clear filter. Please try again.",
        variant: "destructive"
      })
    }
  }

  // Function to download dataset as CSV
  // Generate mock data for demonstration
  const generateMockData = (): Dataset[] => {
    return [
      {
        id: "1",
        name: "customer_data_2023.csv",
        type: "csv",
        size: 1024 * 1024 * 2.5, // 2.5 MB
        uploaded_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(), // 2 days ago
        uploaded_by: "admin",
        source_type: "file",
        row_count: 5243
      },
      {
        id: "2",
        name: "product_catalog.json",
        type: "json",
        size: 1024 * 1024 * 1.2, // 1.2 MB
        uploaded_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 5).toISOString(), // 5 days ago
        uploaded_by: "admin",
        source_type: "file",
        row_count: 1250
      },
      {
        id: "3",
        name: "telecom_churn_data.csv",
        type: "csv",
        size: 1024 * 1024 * 18.6, // 18.6 MB
        uploaded_at: new Date(Date.now() - 1000 * 60 * 7).toISOString(), // 7 minutes ago
        uploaded_by: "admin",
        source_type: "file",
        row_count: 27000
      },
      {
        id: "4",
        name: "user_feedback.json",
        type: "json",
        size: 1024 * 512, // 512 KB
        uploaded_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(), // 30 minutes ago
        uploaded_by: "admin",
        source_type: "file",
        row_count: 850
      },
      {
        id: "5",
        name: "inventory_data.csv",
        type: "csv",
        size: 1024 * 1024 * 5.1, // 5.1 MB
        uploaded_at: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(), // 2 hours ago
        uploaded_by: "admin",
        source_type: "file",
        row_count: 12500
      }
    ]
  }

  // Generate mock preview data
  const generateMockPreviewData = (id: string) => {
    if (id === "1") {
      // Mock data for customer_data_2023.csv
      return {
        columns: ["customer_id", "name", "email", "age", "signup_date"],
        data: [
          { customer_id: 1, name: "John Doe", email: "john@example.com", age: 34, signup_date: "2023-01-15" },
          { customer_id: 2, name: "Jane Smith", email: "jane@example.com", age: 28, signup_date: "2023-01-16" },
          { customer_id: 3, name: "Robert Johnson", email: "robert@example.com", age: 45, signup_date: "2023-01-17" },
          { customer_id: 4, name: "Emily Davis", email: "emily@example.com", age: 31, signup_date: "2023-01-18" },
          { customer_id: 5, name: "Michael Wilson", email: "michael@example.com", age: 29, signup_date: "2023-01-19" },
          { customer_id: 6, name: "Sarah Brown", email: "sarah@example.com", age: 37, signup_date: "2023-01-20" },
          { customer_id: 7, name: "David Miller", email: "david@example.com", age: 42, signup_date: "2023-01-21" },
          { customer_id: 8, name: "Jennifer Taylor", email: "jennifer@example.com", age: 33, signup_date: "2023-01-22" },
          { customer_id: 9, name: "James Anderson", email: "james@example.com", age: 39, signup_date: "2023-01-23" },
          { customer_id: 10, name: "Lisa Thomas", email: "lisa@example.com", age: 27, signup_date: "2023-01-24" },
          { customer_id: 11, name: "Richard Jackson", email: "richard@example.com", age: 48, signup_date: "2023-01-25" },
          { customer_id: 12, name: "Mary White", email: "mary@example.com", age: 36, signup_date: "2023-01-26" },
          { customer_id: 13, name: "Charles Harris", email: "charles@example.com", age: 41, signup_date: "2023-01-27" },
          { customer_id: 14, name: "Patricia Martin", email: "patricia@example.com", age: 30, signup_date: "2023-01-28" },
          { customer_id: 15, name: "Thomas Thompson", email: "thomas@example.com", age: 44, signup_date: "2023-01-29" }
        ],
        page: 1,
        page_size: 15,
        total_rows: 5243,
        total_pages: 350
      }
    } else if (id === "3") {
      // Mock data for telecom_churn_data.csv
      return {
        columns: ["customerID", "gender", "SeniorCitizen", "Partner", "Dependents", "tenure", "PhoneService", "MultipleLines", "InternetService", "OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies", "Contract", "PaperlessBilling", "PaymentMethod", "MonthlyCharges", "TotalCharges", "Churn"],
        data: [
          { customerID: "7590-VHVEG", gender: "Female", SeniorCitizen: 0, Partner: "Yes", Dependents: "No", tenure: 1, PhoneService: "No", MultipleLines: "No phone service", InternetService: "DSL", OnlineSecurity: "No", OnlineBackup: "Yes", DeviceProtection: "No", TechSupport: "No", StreamingTV: "No", StreamingMovies: "No", Contract: "Month-to-month", PaperlessBilling: "Yes", PaymentMethod: "Electronic check", MonthlyCharges: 29.85, TotalCharges: 29.85, Churn: "No" },
          { customerID: "5575-GNVDE", gender: "Male", SeniorCitizen: 0, Partner: "No", Dependents: "No", tenure: 34, PhoneService: "Yes", MultipleLines: "No", InternetService: "DSL", OnlineSecurity: "Yes", OnlineBackup: "No", DeviceProtection: "Yes", TechSupport: "No", StreamingTV: "No", StreamingMovies: "No", Contract: "One year", PaperlessBilling: "No", PaymentMethod: "Mailed check", MonthlyCharges: 56.95, TotalCharges: 1889.5, Churn: "No" },
          { customerID: "3668-QPYBK", gender: "Male", SeniorCitizen: 0, Partner: "No", Dependents: "No", tenure: 2, PhoneService: "Yes", MultipleLines: "No", InternetService: "DSL", OnlineSecurity: "Yes", OnlineBackup: "Yes", DeviceProtection: "No", TechSupport: "No", StreamingTV: "No", StreamingMovies: "No", Contract: "Month-to-month", PaperlessBilling: "Yes", PaymentMethod: "Mailed check", MonthlyCharges: 53.85, TotalCharges: 108.15, Churn: "Yes" },
          { customerID: "7795-CFOCW", gender: "Male", SeniorCitizen: 0, Partner: "No", Dependents: "No", tenure: 45, PhoneService: "Yes", MultipleLines: "No", InternetService: "DSL", OnlineSecurity: "Yes", OnlineBackup: "No", DeviceProtection: "Yes", TechSupport: "Yes", StreamingTV: "No", StreamingMovies: "No", Contract: "One year", PaperlessBilling: "No", PaymentMethod: "Bank transfer (automatic)", MonthlyCharges: 42.3, TotalCharges: 1840.75, Churn: "No" },
          { customerID: "9237-HQITU", gender: "Female", SeniorCitizen: 0, Partner: "No", Dependents: "No", tenure: 2, PhoneService: "Yes", MultipleLines: "No", InternetService: "Fiber optic", OnlineSecurity: "No", OnlineBackup: "No", DeviceProtection: "No", TechSupport: "No", StreamingTV: "No", StreamingMovies: "No", Contract: "Month-to-month", PaperlessBilling: "Yes", PaymentMethod: "Electronic check", MonthlyCharges: 70.7, TotalCharges: 151.65, Churn: "Yes" },
          { customerID: "9305-CDSKC", gender: "Female", SeniorCitizen: 0, Partner: "No", Dependents: "No", tenure: 8, PhoneService: "Yes", MultipleLines: "Yes", InternetService: "Fiber optic", OnlineSecurity: "No", OnlineBackup: "No", DeviceProtection: "Yes", TechSupport: "No", StreamingTV: "Yes", StreamingMovies: "Yes", Contract: "Month-to-month", PaperlessBilling: "Yes", PaymentMethod: "Electronic check", MonthlyCharges: 99.65, TotalCharges: 820.5, Churn: "Yes" },
          { customerID: "1452-KIOVK", gender: "Male", SeniorCitizen: 0, Partner: "No", Dependents: "Yes", tenure: 22, PhoneService: "Yes", MultipleLines: "Yes", InternetService: "Fiber optic", OnlineSecurity: "No", OnlineBackup: "Yes", DeviceProtection: "No", TechSupport: "No", StreamingTV: "Yes", StreamingMovies: "No", Contract: "Month-to-month", PaperlessBilling: "Yes", PaymentMethod: "Credit card (automatic)", MonthlyCharges: 89.1, TotalCharges: 1949.4, Churn: "No" },
          { customerID: "6713-OKOMC", gender: "Female", SeniorCitizen: 0, Partner: "No", Dependents: "No", tenure: 10, PhoneService: "No", MultipleLines: "No phone service", InternetService: "DSL", OnlineSecurity: "No", OnlineBackup: "No", DeviceProtection: "No", TechSupport: "No", StreamingTV: "No", StreamingMovies: "No", Contract: "Month-to-month", PaperlessBilling: "No", PaymentMethod: "Mailed check", MonthlyCharges: 29.75, TotalCharges: 301.9, Churn: "No" },
          { customerID: "7892-POOKP", gender: "Female", SeniorCitizen: 0, Partner: "Yes", Dependents: "No", tenure: 28, PhoneService: "Yes", MultipleLines: "Yes", InternetService: "Fiber optic", OnlineSecurity: "No", OnlineBackup: "No", DeviceProtection: "Yes", TechSupport: "Yes", StreamingTV: "Yes", StreamingMovies: "Yes", Contract: "Month-to-month", PaperlessBilling: "Yes", PaymentMethod: "Electronic check", MonthlyCharges: 104.8, TotalCharges: 3046.05, Churn: "Yes" },
          { customerID: "6388-TABGU", gender: "Male", SeniorCitizen: 0, Partner: "No", Dependents: "No", tenure: 62, PhoneService: "Yes", MultipleLines: "No", InternetService: "DSL", OnlineSecurity: "Yes", OnlineBackup: "Yes", DeviceProtection: "Yes", TechSupport: "No", StreamingTV: "No", StreamingMovies: "No", Contract: "One year", PaperlessBilling: "Yes", PaymentMethod: "Bank transfer (automatic)", MonthlyCharges: 56.15, TotalCharges: 3487.95, Churn: "No" },
          { customerID: "9763-PDTKK", gender: "Female", SeniorCitizen: 0, Partner: "Yes", Dependents: "Yes", tenure: 13, PhoneService: "Yes", MultipleLines: "No", InternetService: "DSL", OnlineSecurity: "Yes", OnlineBackup: "No", DeviceProtection: "No", TechSupport: "No", StreamingTV: "No", StreamingMovies: "No", Contract: "Month-to-month", PaperlessBilling: "Yes", PaymentMethod: "Electronic check", MonthlyCharges: 49.95, TotalCharges: 587.45, Churn: "No" },
          { customerID: "7469-LKBCI", gender: "Male", SeniorCitizen: 0, Partner: "No", Dependents: "No", tenure: 16, PhoneService: "Yes", MultipleLines: "No", InternetService: "Fiber optic", OnlineSecurity: "No", OnlineBackup: "No", DeviceProtection: "No", TechSupport: "No", StreamingTV: "No", StreamingMovies: "No", Contract: "Month-to-month", PaperlessBilling: "Yes", PaymentMethod: "Electronic check", MonthlyCharges: 74.4, TotalCharges: 1192.35, Churn: "Yes" },
          { customerID: "8091-TTVAX", gender: "Male", SeniorCitizen: 0, Partner: "Yes", Dependents: "No", tenure: 58, PhoneService: "Yes", MultipleLines: "Yes", InternetService: "Fiber optic", OnlineSecurity: "No", OnlineBackup: "No", DeviceProtection: "Yes", TechSupport: "No", StreamingTV: "Yes", StreamingMovies: "Yes", Contract: "One year", PaperlessBilling: "Yes", PaymentMethod: "Credit card (automatic)", MonthlyCharges: 100.35, TotalCharges: 5681.1, Churn: "No" },
          { customerID: "0280-XJGEX", gender: "Male", SeniorCitizen: 0, Partner: "No", Dependents: "No", tenure: 49, PhoneService: "Yes", MultipleLines: "Yes", InternetService: "Fiber optic", OnlineSecurity: "No", OnlineBackup: "Yes", DeviceProtection: "Yes", TechSupport: "No", StreamingTV: "Yes", StreamingMovies: "Yes", Contract: "Month-to-month", PaperlessBilling: "Yes", PaymentMethod: "Bank transfer (automatic)", MonthlyCharges: 103.7, TotalCharges: 5036.3, Churn: "Yes" },
          { customerID: "5129-JLPIS", gender: "Male", SeniorCitizen: 0, Partner: "No", Dependents: "No", tenure: 25, PhoneService: "Yes", MultipleLines: "Yes", InternetService: "Fiber optic", OnlineSecurity: "No", OnlineBackup: "No", DeviceProtection: "Yes", TechSupport: "Yes", StreamingTV: "Yes", StreamingMovies: "Yes", Contract: "Month-to-month", PaperlessBilling: "Yes", PaymentMethod: "Electronic check", MonthlyCharges: 106.7, TotalCharges: 2686.05, Churn: "Yes" },
          { customerID: "3655-SNQYZ", gender: "Female", SeniorCitizen: 0, Partner: "Yes", Dependents: "Yes", tenure: 69, PhoneService: "Yes", MultipleLines: "Yes", InternetService: "Fiber optic", OnlineSecurity: "Yes", OnlineBackup: "Yes", DeviceProtection: "Yes", TechSupport: "Yes", StreamingTV: "Yes", StreamingMovies: "Yes", Contract: "Two year", PaperlessBilling: "Yes", PaymentMethod: "Credit card (automatic)", MonthlyCharges: 113.25, TotalCharges: 7895.15, Churn: "No" }
        ],
        page: 1,
        page_size: 15,
        total_rows: 27000,
        total_pages: 1800
      }
    } else {
      // Default mock data for other datasets
      return {
        columns: ["id", "name", "value", "date"],
        data: [
          { id: 1, name: "Item 1", value: 100, date: "2023-01-01" },
          { id: 2, name: "Item 2", value: 200, date: "2023-01-02" },
          { id: 3, name: "Item 3", value: 300, date: "2023-01-03" },
          { id: 4, name: "Item 4", value: 400, date: "2023-01-04" },
          { id: 5, name: "Item 5", value: 500, date: "2023-01-05" },
          { id: 6, name: "Item 6", value: 600, date: "2023-01-06" },
          { id: 7, name: "Item 7", value: 700, date: "2023-01-07" },
          { id: 8, name: "Item 8", value: 800, date: "2023-01-08" },
          { id: 9, name: "Item 9", value: 900, date: "2023-01-09" },
          { id: 10, name: "Item 10", value: 1000, date: "2023-01-10" },
          { id: 11, name: "Item 11", value: 1100, date: "2023-01-11" },
          { id: 12, name: "Item 12", value: 1200, date: "2023-01-12" },
          { id: 13, name: "Item 13", value: 1300, date: "2023-01-13" },
          { id: 14, name: "Item 14", value: 1400, date: "2023-01-14" },
          { id: 15, name: "Item 15", value: 1500, date: "2023-01-15" }
        ],
        page: 1,
        page_size: 15,
        total_rows: 1000,
        total_pages: 67
      }
    }
  }

  // Function to download dataset as CSV
  const downloadDataset = (id: string, name: string) => {
    const apiBaseUrl = getApiBaseUrl()
    let url = `${apiBaseUrl}/api/export/datasets/${id}/download?format=csv`
    
    // Apply filters if they exist
    if (activeFilters[id]) {
      const { column, operator, value } = activeFilters[id]
      url += `&column=${column}&operator=${operator}&value=${encodeURIComponent(value)}`
    }
    
    // Create a link and trigger download
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `${name.split('.')[0]}_export.csv`)
    link.setAttribute('target', '_blank')
    
    // Add token to download request
    const token = localStorage.getItem("token")
    if (token) {
      // For simple cases, you can use this approach
      // For production, consider using a more secure method
      link.setAttribute('data-token', token)
      
      // This is a simple way to add the token to the request
      // A better approach would be to use a proper download service
      link.onclick = function() {
        fetch(url, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })
        .then(response => response.blob())
        .then(blob => {
          const url = window.URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.style.display = 'none'
          a.href = url
          a.download = `${name.split('.')[0]}_export.csv`
          document.body.appendChild(a)
          a.click()
          window.URL.revokeObjectURL(url)
        })
        .catch(error => {
          console.error('Error downloading file:', error)
          toast({
            title: "Download Error",
            description: "Failed to download the file. Please try again.",
            variant: "destructive",
          })
        })
        return false
      }
    }
    
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  // Apply sorting when datasets change or sort parameters change
  useEffect(() => {
    if (datasets.length > 0) {
      const sortedData = sortDatasets(datasets)
      setFilteredDatasets(sortedData)
    }
  }, [sortField, sortDirection, datasets])

  // useEffect for data fetching
  useEffect(() => {
    fetchDatasets()
    
    // No auto-refresh - only fetch when page or search query changes
  }, [page, searchQuery])

  // Function to render the preview tab content
  const renderPreviewContent = (dataset: Dataset) => {
    const id = dataset.id
    const isLoading = tabLoadingStates[id]?.preview
    const previewData = itemData[id]?.preview
    const currentPage = previewPage[id] || 1

    if (isLoading) {
      return (
        <div className="flex justify-center items-center h-40">
          <RefreshCw className="h-8 w-8 animate-spin text-primary" />
        </div>
      )
    }

    if (!previewData || !previewData.columns || !previewData.data) {
      return (
        <div className="p-4 bg-muted/30 rounded-md text-muted-foreground">
          No preview data available for this dataset.
        </div>
      )
    }

    // Calculate total pages based on the maximum preview rows limit
    const effectiveRowCount = Math.min(previewData.total_rows || 0, MAX_PREVIEW_ROWS);
    const totalPages = Math.max(1, Math.ceil(effectiveRowCount / previewPageSize));

    return (
      <div className="space-y-4 w-full overflow-hidden" style={{ maxWidth: 1170 }}>
         {/* Preview table */}
        <div className="bg-card shadow-sm border border-border rounded-md overflow-hidden">
          <div className="overflow-x-auto" style={{ maxWidth: '100%' }}>
            <table className="w-full border-collapse whitespace-nowrap">
              <thead className="bg-muted/50">
                <tr>
                  {previewData.columns.map((column: string, index: number) => (
                    <th key={index} className="px-4 py-2 text-left text-sm font-medium text-muted-foreground border-b whitespace-nowrap">
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewData.data.map((row: any, rowIndex: number) => (
                  <tr key={rowIndex} className={rowIndex % 2 === 0 ? "bg-background" : "bg-muted/20"}>
                    {previewData.columns.map((column: string, colIndex: number) => (
                      <td key={colIndex} className="px-4 py-2 text-sm border-b border-border whitespace-nowrap overflow-hidden text-ellipsis">
                        {row[column] !== null && row[column] !== undefined ? (
                          typeof row[column] === "object" ? (
                            JSON.stringify(row[column])
                          ) : (
                            String(row[column])
                          )
                        ) : (
                          <span className="text-muted-foreground italic">NULL</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pagination controls */}
        <div className="flex justify-between items-center text-sm text-muted-foreground">
          <div>
            Showing {(currentPage - 1) * previewPageSize + 1} to{" "}
            {Math.min(currentPage * previewPageSize, Math.min(MAX_PREVIEW_ROWS, previewData.total_rows))}{" "}
            of {Math.min(MAX_PREVIEW_ROWS, previewData.total_rows)} rows available for preview
            {previewData.total_rows > MAX_PREVIEW_ROWS && (
              <span> (Total Rows - {previewData.total_rows})</span>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePreviewPageChange(id, 1)}
              disabled={currentPage === 1}
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePreviewPageChange(id, currentPage - 1)}
              disabled={currentPage === 1}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-sm">
              Page {currentPage} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePreviewPageChange(id, currentPage + 1)}
              disabled={currentPage === totalPages}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePreviewPageChange(id, totalPages)}
              disabled={currentPage === totalPages}
            >
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // State for filter forms - moved outside of render function to avoid React hooks errors
  const [filterColumns, setFilterColumns] = useState<Record<string, string>>({})
  const [filterOperators, setFilterOperators] = useState<Record<string, string>>({})
  const [filterValues, setFilterValues] = useState<Record<string, string>>({})
  const [rowLimits, setRowLimits] = useState<Record<string, number>>({})
  
  // Helper function to initialize filter form values
  const initializeFilterValues = (id: string, previewData: any) => {
    if (!filterColumns[id] && previewData?.columns?.length > 0) {
      setFilterColumns(prev => ({
        ...prev,
        [id]: activeFilters[id]?.column || previewData.columns[0]
      }))
    }
    
    if (!filterOperators[id]) {
      setFilterOperators(prev => ({
        ...prev,
        [id]: activeFilters[id]?.operator || "eq"
      }))
    }
    
    if (!filterValues[id]) {
      setFilterValues(prev => ({
        ...prev,
        [id]: activeFilters[id]?.value || ""
      }))
    }
  }
  
  // Global useEffect to initialize filter values whenever preview data changes
  useEffect(() => {
    // Check all datasets with preview data and initialize their filter values
    Object.entries(itemData).forEach(([id, data]) => {
      if (data?.preview?.columns?.length > 0) {
        initializeFilterValues(id, data.preview)
      }
    })
  }, [itemData])

  // Function to download filtered dataset
  const downloadFilteredDataset = async (id: string, format: 'csv' | 'json' = 'csv', maxRows?: number) => {
    try {
      // Get the API base URL
      const apiBaseUrl = getApiBaseUrl()
      
      // Construct the base download URL
      const baseUrl = `${apiBaseUrl}/api/export/download?dataset_id=${id}&file_format=${format}`
      
      // Add filter parameters if a filter is applied
      const filter = activeFilters[id]
      const filterParams = filter ? 
        `&column=${encodeURIComponent(filter.column)}&operator=${encodeURIComponent(filter.operator)}&value=${encodeURIComponent(filter.value)}` : 
        ''
      
      // Add row limit parameter if specified
      const rowLimitParam = maxRows ? `&max_rows=${maxRows}` : ''
      
      const downloadUrl = baseUrl + filterParams + rowLimitParam
      
      // Get the authentication token
      const token = localStorage.getItem("token")
      if (!token) {
        toast({
          title: "Authentication error",
          description: "You must be logged in to download data.",
          variant: "destructive"
        })
        handleAuthFailure()
        return
      }
      
      // Use fetchWithAuth for authenticated requests
      // We need to extract the endpoint from the full URL
      const endpoint = downloadUrl.replace(apiBaseUrl, '')
      const response = await fetch(`${apiBaseUrl}${endpoint}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      // Check for authentication errors
      if (response.status === 401 || response.status === 403) {
        handleAuthFailure()
        return
      }
      
      if (!response.ok) {
        throw new Error(`Download failed with status: ${response.status}`)
      }
      
      // Get the blob from the response
      const blob = await response.blob()
      
      // Create a download link for the blob
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      
      // Get filename from the Content-Disposition header or create a default one
      const contentDisposition = response.headers.get('Content-Disposition')
      let filename = `filtered_data.${format}`
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename=([^;]+)/)
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].trim()
        }
      }
      
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      
      toast({
        title: "Download complete",
        description: `Dataset has been downloaded as ${format.toUpperCase()}`,
      })
    } catch (error) {
      console.error("Error downloading filtered dataset:", error)
      toast({
        title: "Download failed",
        description: "An error occurred while downloading the filtered dataset.",
        variant: "destructive"
      })
    }
  }

  // Function to render the filter tab content
  const renderFilterContent = (dataset: Dataset) => {
    const id = dataset.id
    const previewData = itemData[id]?.preview
    const hasActiveFilter = !!activeFilters[id]

    if (!previewData || !previewData.columns) {
      return (
        <div className="p-4 bg-muted/30 rounded-md text-muted-foreground">
          Preview data must be loaded before filtering. Please check the Preview tab first.
        </div>
      )
    }
    
    // Use the state from our global filter state objects with safe fallbacks
    const filterColumn = filterColumns[id] || (previewData.columns[0] || "")
    const filterOperator = filterOperators[id] || "eq"
    const filterValue = filterValues[id] || ""

    return (
      <div className="space-y-6 w-full overflow-hidden">
        {/* Filter form */}
        <div className="bg-card shadow-sm border border-border rounded-md p-4">
          <h4 className="text-sm font-medium mb-4">Filter Dataset</h4>
          
          {/* Filter controls */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-sm text-muted-foreground mb-1 block">Column</label>
              <Select 
                value={filterColumn} 
                onValueChange={(value) => setFilterColumns(prev => ({ ...prev, [id]: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select column" />
                </SelectTrigger>
                <SelectContent>
                  {previewData.columns.map((column: string) => (
                    <SelectItem key={column} value={column}>
                      {column}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm text-muted-foreground mb-1 block">Operator</label>
              <Select 
                value={filterOperator} 
                onValueChange={(value) => setFilterOperators(prev => ({ ...prev, [id]: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select operator" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="eq">Equals</SelectItem>
                  <SelectItem value="neq">Not Equals</SelectItem>
                  <SelectItem value="gt">Greater Than</SelectItem>
                  <SelectItem value="lt">Less Than</SelectItem>
                  <SelectItem value="gte">Greater Than or Equal</SelectItem>
                  <SelectItem value="lte">Less Than or Equal</SelectItem>
                  <SelectItem value="contains">Contains</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm text-muted-foreground mb-1 block">Value</label>
              <Input
                type="text"
                value={filterValue}
                onChange={(e) => setFilterValues(prev => ({ ...prev, [id]: e.target.value }))}
                placeholder="Enter filter value"
              />
            </div>
          </div>
          
          {/* Filter action buttons */}
          <div className="flex justify-end mt-6 space-x-2">
            {hasActiveFilter && (
              <Button variant="outline" onClick={() => clearFilter(id)}>
                Clear Filter
              </Button>
            )}
            <Button
              onClick={() => {
                try {
                  // Safely get the current filter values
                  const column = filterColumns[id] || previewData.columns[0]
                  const operator = filterOperators[id] || "eq"
                  const value = filterValues[id] || ""
                  
                  // Apply the filter with error handling
                  applyFilter(id, column, operator, value)
                } catch (error) {
                  console.error("Error in filter button click:", error)
                  toast({
                    title: "Error",
                    description: "Something went wrong. Please try again.",
                    variant: "destructive"
                  })
                }
              }}
              disabled={!filterValue.trim()}
            >
              Apply Filter
            </Button>
          </div>
          
          {/* Custom row download section */}
          <div className="mt-6 pt-4 border-t border-border bg-background shadow-sm p-4 rounded-md">
            <h5 className="text-sm font-medium mb-3 flex items-center gap-2 text-foreground">
              <Download className="h-4 w-4 text-primary" />
              Download Custom Rows
            </h5>
            
            {hasActiveFilter && (
              <div className="mb-4 pb-3 border-b border-border/50">
                <div className="flex items-center mb-2">
                  <span className="text-xs font-medium text-primary mr-1">Active Filter:</span>
                  <span className="text-xs text-foreground">
                    {activeFilters[id].column}{' '}
                    {activeFilters[id].operator === "eq" ? "equals" : 
                     activeFilters[id].operator === "neq" ? "not equals" : 
                     activeFilters[id].operator === "gt" ? "greater than" : 
                     activeFilters[id].operator === "lt" ? "less than" : 
                     activeFilters[id].operator === "gte" ? "greater than or equal to" : 
                     activeFilters[id].operator === "lte" ? "less than or equal to" : 
                     "contains"}{" "}
                    <span className="font-medium">{activeFilters[id].value}</span>
                  </span>
                  <Button variant="ghost" size="sm" className="ml-2 h-6 px-2 py-0" onClick={() => clearFilter(id)}>
                    <span className="text-xs">Clear</span>
                  </Button>
                </div>
                <p className="text-xs font-medium" style={{ color: "#0569d9" }}>
                  Your download will include only the rows that match this filter*
                </p>
              </div>
            )}
            
            <div className="flex items-center gap-4">
              <div className="w-64">
                <label className="text-sm text-foreground mb-1 block">Number of Rows</label>
                <Input
                  type="number"
                  min="1"
                  placeholder="Enter row limit"
                  value={rowLimits[id] || ''}
                  onChange={(e) => {
                    const value = e.target.value ? parseInt(e.target.value) : undefined;
                    setRowLimits(prev => ({
                      ...prev,
                      [id]: value as number
                    }));
                  }}
                  className="h-10 bg-background border-border"
                />
                <p className="text-xs font-medium mt-1" style={{ color: "#0569d9" }}>
                  {rowLimits[id] ? `Will download first ${rowLimits[id]} rows` : 'Leave empty to download all rows'}
                  {hasActiveFilter && ' matching your filter'}{hasActiveFilter ? '*' : '*'}
                </p>
              </div>
              
              <Button 
                variant="default" 
                size="default" 
                className="flex items-center gap-1 h-10 mt-7 bg-primary hover:bg-primary/90 text-primary-foreground"
                onClick={() => downloadFilteredDataset(id, 'csv', rowLimits[id])}
              >
                <Download className="h-4 w-4" />
                Download Custom (CSV)
              </Button>
            </div>
          </div>
        </div>

        {/* Removed active filter indicator with download buttons section */}

        {/* Preview of filtered data */}
        <div className="w-full overflow-hidden">
          <h4 className="text-sm font-medium mb-2">Preview with{hasActiveFilter ? " Applied Filter" : "out Filters"}</h4>
          {renderPreviewContent(dataset)}
        </div>
      </div>
    )
  }

  return (
    <DataPuurLayout>
      <div className="flex-1 space-y-2 p-4 md:p-8 pt-6 overflow-hidden" style={{ maxWidth: '1170px', margin: '0 auto' }}>
        <div className="flex w-full items-center justify-between pb-2">
          <h2 className="text-2xl font-bold tracking-tight">Export</h2>
          <div className="flex items-center space-x-2">
            <div className="flex items-center">
              <Search className="h-4 w-4 text-muted-foreground absolute ml-2" />
              <Input 
                type="search" 
                placeholder="Search datasets..." 
                className="max-w-sm pl-8" 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <Button 
              variant="outline" 
              size="icon"
              onClick={() => {
                setPage(1)
                fetchDatasets()
              }}
              title="Refresh datasets"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
            <div className="space-y-2">

              {error && (
                <div className="bg-destructive/10 border border-destructive text-destructive p-3 rounded-md mb-6">
                  {error}
                </div>
              )}

              {/* Dataset header */}
              <div className="mb-4 text-sm">
                <div className="bg-muted/50 rounded-t-lg grid grid-cols-12 gap-4 p-4 font-medium text-muted-foreground">
                  <div 
                    className="col-span-6 flex items-center gap-1 cursor-pointer hover:text-foreground transition-colors"
                    onClick={() => handleSort("name")}
                  >
                    Name
                    {sortField === "name" && (
                      <span className="ml-1">
                        {sortDirection === "asc" ? "↑" : "↓"}
                      </span>
                    )}
                  </div>
                  <div 
                    className="col-span-3 flex items-center gap-1 cursor-pointer hover:text-foreground transition-colors"
                    onClick={() => handleSort("size")}
                  >
                    Size
                    {sortField === "size" && (
                      <span className="ml-1">
                        {sortDirection === "asc" ? "↑" : "↓"}
                      </span>
                    )}
                  </div>
                  <div 
                    className="col-span-2 flex items-center gap-1 cursor-pointer hover:text-foreground transition-colors"
                    onClick={() => handleSort("uploaded_at")}
                  >
                    Last Updated
                    {sortField === "uploaded_at" && (
                      <span className="ml-1">
                        {sortDirection === "asc" ? "↑" : "↓"}
                      </span>
                    )}
                  </div>
                  <div className="col-span-1 text-right">
                    Actions
                  </div>
                </div>
              </div>

              {/* Dataset list */}
              {isLoading ? (
                <div className="flex justify-center items-center h-64">
                  <RefreshCw className="h-8 w-8 animate-spin text-primary" />
                </div>
              ) : filteredDatasets.length === 0 ? (
                <div className="text-center p-12 border border-dashed border-border rounded-lg">
                  <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <h3 className="text-lg font-medium text-foreground mb-2">No datasets found</h3>
                  <p className="text-muted-foreground">
                    {searchQuery
                      ? "Try adjusting your search"
                      : "Import data through the ingestion page to see datasets here"}
                  </p>
                </div>
              ) : (
                <motion.div variants={container} initial="hidden" animate="show" className="space-y-4">
                  {filteredDatasets.map((dataset) => (
                    <motion.div
                      key={dataset.id}
                      variants={item}
                      className="border rounded-lg overflow-hidden bg-card/50 hover:bg-card/80 transition-colors"
                    >
                      {/* Header row */}
                      <div
                        className="grid grid-cols-12 gap-4 p-4 cursor-pointer"
                        onClick={() => toggleExpand(dataset.id)}
                      >
                        <div className="col-span-6 flex items-center gap-2">
                          <FileText className="h-5 w-5 text-primary flex-shrink-0" />
                          <div>
                            <div className="font-medium text-foreground truncate">{dataset.dataset || stripFileExtension(dataset.name)}</div>
                            <div className="text-xs text-muted-foreground flex items-center gap-1">
                              <Badge className="text-xs">{dataset.type.toUpperCase()}</Badge>
                              <span>•</span>
                              <span>Uploaded by {dataset.uploaded_by}</span>
                            </div>
                          </div>
                        </div>

                        <div className="col-span-3 flex items-center text-muted-foreground">
                          <HardDrive className="h-3 w-3 mr-1 flex-shrink-0" />
                          {formatFileSize(dataset.size)}
                        </div>

                        <div className="col-span-2 flex items-center text-muted-foreground">
                          <Calendar className="h-3 w-3 mr-1 flex-shrink-0" />
                          <div>
                            <div>
                              {(() => {
                                try {
                                  // Parse the UTC date from the ISO string
                                  const utcDate = new Date(dataset.uploaded_at);
                                  
                                  // Get the client's timezone offset in minutes
                                  const timezoneOffset = new Date().getTimezoneOffset();
                                  
                                  // Convert from UTC to client's local time by adjusting for timezone offset
                                  // Note: getTimezoneOffset() returns minutes WEST of UTC, so we negate it
                                  const localDate = new Date(utcDate.getTime() - (timezoneOffset * 60 * 1000));
                                  
                                  // For relative time display
                                  return formatDistanceToNow(localDate, { addSuffix: true });
                                } catch (error) {
                                  console.error("Error formatting relative time:", error, dataset.uploaded_at);
                                  return "Unknown";
                                }
                              })()}
                            </div>
                            <div className="text-xs">
                              {(() => {
                                try {
                                  // Parse the UTC date from the ISO string
                                  const utcDate = new Date(dataset.uploaded_at);
                                  
                                  // Get the client's timezone offset in minutes
                                  const timezoneOffset = new Date().getTimezoneOffset();
                                  
                                  // Convert from UTC to client's local time by adjusting for timezone offset
                                  // Note: getTimezoneOffset() returns minutes WEST of UTC, so we negate it
                                  const localDate = new Date(utcDate.getTime() - (timezoneOffset * 60 * 1000));
                                  
                                  // Format the local date
                                  // This uses ISO string and then removes the 'T' and timezone part
                                  return localDate.toISOString().replace('T', ' ').substring(0, 19);
                                } catch (error) {
                                  console.error("Error formatting date:", error, dataset.uploaded_at);
                                  return dataset.uploaded_at || "Unknown";
                                }
                              })()}
                            </div>
                          </div>
                        </div>

                        <div className="col-span-1 flex items-center justify-end gap-1">
                          <Button
                            variant="outline"
                            size="sm"
                            className="flex items-center gap-1 text-xs h-8"
                            title="Download CSV"
                            onClick={(e) => {
                              e.stopPropagation()
                              downloadDataset(dataset.id, dataset.dataset || dataset.name)
                            }}
                          >
                            <FileDown className="h-3 w-3" />
                            CSV
                          </Button>
                          
                          <ChevronDown
                            className={`h-4 w-4 transition-transform ${expandedItems[dataset.id] ? "rotate-180" : ""}`}
                          />
                        </div>
                      </div>

                      {/* Expanded content */}
                      {expandedItems[dataset.id] && (
                        <div className="border-t border-border p-4 w-full overflow-hidden">
                          {/* Tabs for different views */}
                          <Tabs value={activeTabs[dataset.id] || "preview"} className="w-full">
                            <TabsList className="bg-muted/30 mb-4">
                              <TabsTrigger 
                                value="preview" 
                                onClick={() => setActiveTab(dataset.id, "preview")}
                              >
                                <Eye className="h-4 w-4 mr-1" />
                                Preview
                              </TabsTrigger>
                              <TabsTrigger 
                                value="filter" 
                                onClick={() => setActiveTab(dataset.id, "filter")}
                              >
                                <Filter className="h-4 w-4 mr-1" />
                                Filter
                              </TabsTrigger>
                            </TabsList>

                            {/* Tab content */}
                            <TabsContent value="preview" className="w-full overflow-hidden">
                              {renderPreviewContent(dataset)}
                            </TabsContent>
                            <TabsContent value="filter" className="w-full overflow-hidden">
                              {renderFilterContent(dataset)}
                            </TabsContent>
                          </Tabs>
                        </div>
                      )}
                    </motion.div>
                  ))}
                </motion.div>
              )}

              {/* Pagination */}
              {!isLoading && filteredDatasets.length > 0 && totalPages > 1 && (
                <div className="flex justify-center mt-6">
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(1)}
                      disabled={page === 1}
                    >
                      <ArrowLeft className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(page - 1)}
                      disabled={page === 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <span className="text-sm">
                      Page {page} of {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(page + 1)}
                      disabled={page === totalPages}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(totalPages)}
                      disabled={page === totalPages}
                    >
                      <ArrowRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </div>
      </div>
    </DataPuurLayout>
  )
}

