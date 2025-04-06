"use client"

import { useState, useEffect, useMemo } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useToast } from "@/components/ui/use-toast"
import { format } from "date-fns"
import {
  BarChart2,
  FileText,
  AlertTriangle,
  CheckCircle,
  Info,
  Database,
  Calendar,
  PieChart,
  BarChart,
  LineChart,
  Clock,
  Percent,
  Hash,
  ListFilter,
  Fingerprint,
  Activity,
  ToggleLeft,
  Braces,
  FileQuestion,
} from "lucide-react"
import LoadingSpinner from "@/components/loading-spinner"

interface ProfileDetailsProps {
  profileId: string;
}

interface ColumnProfile {
  name: string
  column_name?: string
  data_type: string
  count: number
  unique_count: number
  null_count: number
  missing_count: number
  quality_score: number
  completeness: number
  uniqueness: number
  validity: number
  min_value: any
  max_value: any
  mean?: number
  median?: number
  std_dev?: number
  histogram?: {
    bins: any[]
    counts: number[]
  }
  top_values?: {
    value: any
    count: number
  }[]
  distribution?: {
    category: string
    count: number
  }[]
}

interface ProfileData {
  id: string
  file_id: string
  file_name: string
  total_rows: number
  total_columns: number
  data_quality_score: number
  columns: Record<string, ColumnProfile> | ColumnProfile[]
  created_at: string
  column_names?: Record<string, string>
  original_headers?: string[]
}

export default function ProfileDetails({ profileId }: ProfileDetailsProps) {
  const [profile, setProfile] = useState<ProfileData | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedColumn, setSelectedColumn] = useState<string | null>(null)
  const { toast } = useToast()

  useEffect(() => {
    const fetchProfileDetails = async () => {
      try {
        setLoading(true)
        const token = localStorage.getItem("token")
        
        if (!token) {
          toast({
            title: "Authentication Error",
            description: "You must be logged in to view profile details",
            variant: "destructive",
          })
          return
        }

        console.log(`Fetching profile details for ID: ${profileId}`)
        const response = await fetch(`/api/profiler/profiles/${profileId}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })

        if (response.status === 401) {
          toast({
            title: "Authentication Error",
            description: "Your session has expired. Please log in again.",
            variant: "destructive",
          })
          return
        }

        if (!response.ok) {
          console.error(`Error response: ${response.status} ${response.statusText}`)
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const data = await response.json()
        console.log("Profile data received:", data)
        
        // Log column structure for debugging
        console.log("Column structure:", {
          columnKeys: Object.keys(data.columns || {}),
          firstColumn: data.columns ? data.columns[Object.keys(data.columns)[0]] : null,
          originalHeaders: data.original_headers || "No original headers found"
        })
        
        // Ensure the data has the expected structure
        if (!data || !data.columns) {
          console.error("Invalid profile data structure:", data)
          toast({
            title: "Error",
            description: "The profile data has an invalid structure. Please try again.",
            variant: "destructive",
          })
          return
        }
        
        setProfile(data)
        
        // Set the first column as selected by default
        if (data.columns && Object.keys(data.columns).length > 0) {
          setSelectedColumn(Object.keys(data.columns)[0])
        }
      } catch (error) {
        console.error("Error fetching profile details:", error)
        toast({
          title: "Error",
          description: "Failed to fetch profile details. Please try again.",
          variant: "destructive",
        })
      } finally {
        setLoading(false)
      }
    }

    if (profileId) {
      fetchProfileDetails()
    } else {
      setLoading(false)
    }
  }, [profileId, toast])

  // Helper functions for quality score display
  const getQualityScoreLabel = (score?: number): string => {
    if (score === undefined) return 'N/A';
    
    // Assuming score is already multiplied by 100 from the backend
    if (score >= 90) return 'Excellent';
    if (score >= 75) return 'Good';
    if (score >= 60) return 'Fair';
    if (score >= 40) return 'Poor';
    return 'Bad';
  };

  const getQualityScoreBadgeVariant = (score?: number): "default" | "destructive" | "secondary" | "outline" => {
    if (score === undefined) return 'default';
    
    // Assuming score is already multiplied by 100 from the backend
    if (score >= 90) return 'default';
    if (score >= 75) return 'secondary';
    if (score >= 60) return 'outline';
    return 'destructive';
  };

  const getQualityBadgeVariant = (score?: number): "default" | "destructive" | "secondary" | "outline" => {
    if (score === undefined) return 'default';
    
    // Assuming score is already multiplied by 100 from the backend
    if (score >= 90) return 'default';
    if (score >= 75) return 'secondary';
    if (score >= 60) return 'outline';
    return 'destructive';
  };

  const getDataTypeIcon = (dataType: string) => {
    switch (dataType?.toLowerCase()) {
      case 'integer':
      case 'int':
      case 'float':
      case 'double':
      case 'decimal':
      case 'numeric':
        return <Hash className="h-4 w-4 text-blue-500" />
      case 'string':
      case 'text':
      case 'varchar':
      case 'char':
        return <FileText className="h-4 w-4 text-green-500" />
      case 'boolean':
      case 'bool':
        return <ToggleLeft className="h-4 w-4 text-purple-500" />
      case 'date':
      case 'datetime':
      case 'timestamp':
        return <Calendar className="h-4 w-4 text-orange-500" />
      case 'object':
      case 'json':
        return <Braces className="h-4 w-4 text-yellow-500" />
      default:
        return <FileQuestion className="h-4 w-4 text-gray-500" />
    }
  }

  // Format column name for display
  const formatColumnName = (columnName: string): string => {
    // Check if the column name is a numeric index
    if (/^\d+$/.test(columnName)) {
      const columnIndex = parseInt(columnName, 10);
      
      // If columns is an array, try to get the column_name property
      if (Array.isArray(profile?.columns)) {
        const column = profile.columns[columnIndex];
        if (column && typeof column === 'object' && 'column_name' in column && typeof column.column_name === 'string') {
          return column.column_name;
        }
      }
      
      // First try to get the name from original_headers if available
      if (profile?.original_headers && profile.original_headers[columnIndex] && typeof profile.original_headers[columnIndex] === 'string') {
        return profile.original_headers[columnIndex];
      }
      
      // Check if the column data itself has a name property
      if (Array.isArray(profile?.columns)) {
        const column = profile.columns[columnIndex];
        if (column && typeof column === 'object' && 'name' in column && typeof column.name === 'string') {
          return column.name;
        }
      } else if (profile?.columns && profile.columns[columnName]) {
        const column = profile.columns[columnName];
        if (typeof column === 'object' && 'name' in column && typeof column.name === 'string') {
          return column.name;
        }
        if (typeof column === 'object' && 'column_name' in column && typeof column.column_name === 'string') {
          return column.column_name;
        }
      }
      
      // Then try to get a more descriptive name from column_names if available
      if (profile?.column_names && profile.column_names[columnName] && typeof profile.column_names[columnName] === 'string') {
        return profile.column_names[columnName];
      }
      
      // Otherwise, format it as "Column X"
      return `Column ${columnName}`;
    }
    return columnName;
  };

  // Format data type for display
  const formatDataType = (dataType: string | undefined): string => {
    if (!dataType) return 'Unknown';
    
    // Capitalize first letter and format nicely
    return dataType.charAt(0).toUpperCase() + dataType.slice(1).toLowerCase();
  };

  // Format value for display
  const formatValue = (value: any): string => {
    // Handle undefined or null values
    if (value === undefined || value === null) return 'N/A'
    
    // Handle numeric values
    if (typeof value === 'number') {
      // Check if it's a valid number
      if (isNaN(value)) return 'N/A'
      
      // Format number with commas for thousands
      return value.toLocaleString()
    }
    
    // Handle boolean values
    if (typeof value === 'boolean') {
      return value ? 'True' : 'False'
    }
    
    // Handle date values
    if (value instanceof Date) {
      return value.toLocaleDateString()
    }
    
    // Handle arrays
    if (Array.isArray(value)) {
      if (value.length === 0) return 'Empty array'
      return `[${value.slice(0, 3).map(v => formatValue(v)).join(', ')}${value.length > 3 ? '...' : ''}]`
    }
    
    // Handle objects
    if (typeof value === 'object') {
      return JSON.stringify(value).slice(0, 50) + (JSON.stringify(value).length > 50 ? '...' : '')
    }
    
    // Convert to string for all other types
    return String(value)
  }

  // Extract column names from profile data
  const columnNames = useMemo(() => {
    if (!profile || !profile.columns) return [];
    
    // Check if columns is an array or object
    if (Array.isArray(profile.columns)) {
      // If it's an array, use indices as keys
      return profile.columns.map((_, index) => String(index));
    } else {
      // If it's an object, use its keys
      return Object.keys(profile.columns);
    }
  }, [profile]);

  // Get selected column data
  const selectedColumnData = useMemo(() => {
    if (!selectedColumn || !profile?.columns) return null;
    
    // Check if columns is an array or object
    if (Array.isArray(profile.columns)) {
      // For array format
      const index = parseInt(selectedColumn, 10);
      const columnData = index >= 0 && index < profile.columns.length ? profile.columns[index] : null;
      
      // Log the column data for debugging
      console.log("Selected column data (array format):", columnData);
      
      // Ensure the column data has all required properties
      if (columnData) {
        // Make sure all required properties exist with appropriate defaults
        return {
          ...columnData,
          name: columnData.name || columnData.column_name || `Column ${index}`,
          data_type: columnData.data_type || 'unknown',
          count: columnData.count || 0,
          unique_count: columnData.unique_count || 0,
          null_count: columnData.null_count || 0,
          missing_count: columnData.missing_count || 0,
          quality_score: columnData.quality_score || 0,
          completeness: columnData.completeness || 0,
          uniqueness: columnData.uniqueness || 0,
          validity: columnData.validity || 0,
          min_value: columnData.min_value,
          max_value: columnData.max_value
        };
      }
      return null;
    } else {
      // For object format
      const columnData = profile.columns[selectedColumn] || null;
      
      // Log the column data for debugging
      console.log("Selected column data (object format):", columnData);
      
      // Ensure the column data has all required properties
      if (columnData) {
        // Make sure all required properties exist with appropriate defaults
        return {
          ...columnData,
          name: columnData.name || columnData.column_name || selectedColumn,
          data_type: columnData.data_type || 'unknown',
          count: columnData.count || 0,
          unique_count: columnData.unique_count || 0,
          null_count: columnData.null_count || 0,
          missing_count: columnData.missing_count || 0,
          quality_score: columnData.quality_score || 0,
          completeness: columnData.completeness || 0,
          uniqueness: columnData.uniqueness || 0,
          validity: columnData.validity || 0,
          min_value: columnData.min_value,
          max_value: columnData.max_value
        };
      }
      return null;
    }
  }, [selectedColumn, profile]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <LoadingSpinner />
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="flex justify-center items-center h-64 text-muted-foreground">
        No profile data available
      </div>
    )
  }

  // Safety check for selectedColumnData
  if (selectedColumn && !selectedColumnData) {
    return (
      <div className="flex justify-center items-center h-64 text-muted-foreground">
        Selected column data not available
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <div className="flex justify-between items-start">
            <div>
              <CardTitle className="text-2xl">{profile.file_name}</CardTitle>
              <CardDescription>
                Profile generated on {format(new Date(profile.created_at), "MMMM d, yyyy 'at' h:mm a")}
              </CardDescription>
            </div>
            <Badge variant={getQualityBadgeVariant(profile?.data_quality_score)}>
              {profile?.data_quality_score !== undefined ? `${Math.round(profile.data_quality_score)}%` : 'N/A'}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Database className="h-5 w-5 mr-2 text-primary" />
                    <span className="font-medium">Rows</span>
                  </div>
                  <span className="text-2xl font-bold">{formatValue(profile?.total_rows)}</span>
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <BarChart2 className="h-5 w-5 mr-2 text-primary" />
                    <span className="font-medium">Columns</span>
                  </div>
                  <span className="text-2xl font-bold">{formatValue(profile?.total_columns)}</span>
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Clock className="h-5 w-5 mr-2 text-primary" />
                    <span className="font-medium">Age</span>
                  </div>
                  <span className="text-2xl font-bold">
                    {profile?.created_at ? format(new Date(profile.created_at), "MMM d, yyyy") : 'N/A'}
                  </span>
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Activity className="h-5 w-5 mr-2 text-primary" />
                    <span className="font-medium">Quality Score</span>
                  </div>
                  <div className="flex items-center">
                    <span className="text-2xl font-bold mr-2">
                      {getQualityScoreLabel(profile?.data_quality_score)}
                    </span>
                    <Badge variant={getQualityBadgeVariant(profile?.data_quality_score)}>
                      {profile?.data_quality_score !== undefined ? `${Math.round(profile.data_quality_score)}%` : 'N/A'}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle>Columns</CardTitle>
            <CardDescription>
              Select a column to view detailed statistics
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[400px]">
              <div className="p-4">
                {columnNames.map((columnName) => {
                  const column = Array.isArray(profile.columns) ? profile.columns[parseInt(columnName, 10)] : profile.columns[columnName]
                  return (
                    <div
                      key={columnName}
                      className={`flex items-center justify-between p-2 rounded-md cursor-pointer mb-2 hover:bg-accent ${
                        selectedColumn === columnName ? "bg-accent" : ""
                      }`}
                      onClick={() => setSelectedColumn(columnName)}
                    >
                      <div className="flex items-center">
                        {getDataTypeIcon(column.data_type)}
                        <span className="ml-2 font-medium">{formatColumnName(columnName)}</span>
                      </div>
                      <Badge variant={getQualityBadgeVariant(profile?.data_quality_score)}>
                        {getQualityScoreLabel(profile?.data_quality_score)}
                      </Badge>
                    </div>
                  )
                })}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        <Card className="md:col-span-3">
          {selectedColumnData ? (
            <>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <div>
                    <CardTitle className="flex items-center">
                      {getDataTypeIcon(selectedColumnData.data_type)}
                      <span className="ml-2">{selectedColumn ? formatColumnName(selectedColumn) : 'No column selected'}</span>
                    </CardTitle>
                    <CardDescription>
                      {formatDataType(selectedColumnData.data_type)} • {formatValue(selectedColumnData.count)} values
                    </CardDescription>
                  </div>
                  <Badge variant={getQualityBadgeVariant(profile?.data_quality_score)}>
                    {getQualityScoreLabel(profile?.data_quality_score)}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="overview">
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="overview">Overview</TabsTrigger>
                    <TabsTrigger value="statistics">Statistics</TabsTrigger>
                    <TabsTrigger value="quality">Quality</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="overview" className="space-y-4 mt-4">
                    <div className="grid grid-cols-2 gap-4">
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm font-medium">Unique Values</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="flex items-center justify-between">
                            <span className="text-2xl font-bold">
                              {formatValue(selectedColumnData.unique_count)}
                            </span>
                            <span className="text-sm text-muted-foreground">
                              {selectedColumnData && selectedColumnData.count > 0 ? 
                                `(${Math.round((selectedColumnData.unique_count / selectedColumnData.count) * 100)}%)` : 
                                '(0%)'}
                            </span>
                          </div>
                        </CardContent>
                      </Card>
                      
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm font-medium">Missing Values</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="flex items-center justify-between">
                            <span className="text-2xl font-bold">
                              {formatValue(selectedColumnData.missing_count)}
                            </span>
                            <span className="text-sm text-muted-foreground">
                              {selectedColumnData && selectedColumnData.count > 0 ? 
                                `(${Math.round((selectedColumnData.missing_count / selectedColumnData.count) * 100)}%)` : 
                                '(0%)'}
                            </span>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                    
                    {selectedColumnData.top_values && selectedColumnData.top_values.length > 0 && (
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm font-medium">Top Values</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-2">
                            {selectedColumnData.top_values.map((item, index) => (
                              <div key={index} className="flex items-center justify-between">
                                <span className="font-medium truncate max-w-[200px]">
                                  {item.value === null ? "<null>" : String(item.value)}
                                </span>
                                <div className="flex items-center">
                                  <span className="text-sm text-muted-foreground mr-2">
                                    {formatValue(item.count)} 
                                    {selectedColumnData && selectedColumnData.count > 0 && item.count !== undefined ? 
                                      `(${Math.round((item.count / selectedColumnData.count) * 100)}%)` : 
                                      '(0%)'}
                                  </span>
                                  <Progress
                                    value={selectedColumnData && selectedColumnData.count > 0 && item.count !== undefined ? 
                                      (item.count / selectedColumnData.count) * 100 : 0}
                                    className="w-24"
                                  />
                                </div>
                              </div>
                            ))}
                          </div>
                        </CardContent>
                      </Card>
                    )}
                    
                    {/* Only show range for numeric data types */}
                    {['integer', 'int', 'float', 'double', 'decimal', 'numeric'].includes(selectedColumnData.data_type?.toLowerCase()) && 
                     selectedColumnData.min_value !== undefined && selectedColumnData.max_value !== undefined && (
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm font-medium">Range</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="flex items-center justify-between">
                            <div>
                              <div className="text-sm text-muted-foreground">Min</div>
                              <div className="font-bold">{formatValue(selectedColumnData.min_value)}</div>
                            </div>
                            <Separator className="w-12" />
                            <div>
                              <div className="text-sm text-muted-foreground">Max</div>
                              <div className="font-bold">{formatValue(selectedColumnData.max_value)}</div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    )}
                  </TabsContent>
                  
                  <TabsContent value="statistics" className="space-y-4 mt-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <h4 className="text-sm font-medium mb-1">Null Count</h4>
                        <p className="text-2xl font-bold">{formatValue(selectedColumnData.null_count)}</p>
                      </div>
                      <div>
                        <h4 className="text-sm font-medium mb-1">Unique Count</h4>
                        <p className="text-2xl font-bold">{formatValue(selectedColumnData.unique_count)}</p>
                      </div>
                      
                      {/* Show min/max/mean/median only for numeric data types */}
                      {['integer', 'int', 'float', 'double', 'decimal', 'numeric'].includes(selectedColumnData.data_type?.toLowerCase()) && (
                        <>
                          <div>
                            <h4 className="text-sm font-medium mb-1">Min Value</h4>
                            <p className="text-2xl font-bold">{formatValue(selectedColumnData.min_value)}</p>
                          </div>
                          <div>
                            <h4 className="text-sm font-medium mb-1">Max Value</h4>
                            <p className="text-2xl font-bold">{formatValue(selectedColumnData.max_value)}</p>
                          </div>
                          {selectedColumnData.mean !== undefined && (
                            <div>
                              <h4 className="text-sm font-medium mb-1">Mean</h4>
                              <p className="text-2xl font-bold">{formatValue(selectedColumnData.mean)}</p>
                            </div>
                          )}
                          {selectedColumnData.median !== undefined && (
                            <div>
                              <h4 className="text-sm font-medium mb-1">Median</h4>
                              <p className="text-2xl font-bold">{formatValue(selectedColumnData.median)}</p>
                            </div>
                          )}
                          {selectedColumnData.std_dev !== undefined && (
                            <div>
                              <h4 className="text-sm font-medium mb-1">Standard Deviation</h4>
                              <p className="text-2xl font-bold">{formatValue(selectedColumnData.std_dev)}</p>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                    
                    {/* Show histogram for numeric data types */}
                    {['integer', 'int', 'float', 'double', 'decimal', 'numeric'].includes(selectedColumnData.data_type?.toLowerCase()) && 
                      selectedColumnData.histogram && selectedColumnData.histogram.bins.length > 0 && (
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm font-medium">Distribution</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="h-[200px] flex items-end justify-between">
                            {selectedColumnData.histogram.counts.map((count, index) => {
                              const maxCount = Math.max(...selectedColumnData.histogram!.counts)
                              const height = (count / maxCount) * 100
                              return (
                                <div key={index} className="flex flex-col items-center">
                                  <div
                                    className="w-6 bg-primary rounded-t"
                                    style={{ height: `${Math.max(5, height)}%` }}
                                  ></div>
                                  <span className="text-xs text-muted-foreground mt-1 rotate-45 origin-left">
                                    {selectedColumnData.histogram!.bins[index].toFixed(1)}
                                  </span>
                                </div>
                              )
                            })}
                          </div>
                        </CardContent>
                      </Card>
                    )}
                    
                    {/* Show pie chart visualization for string/categorical data types */}
                    {!['integer', 'int', 'float', 'double', 'decimal', 'numeric'].includes(selectedColumnData.data_type?.toLowerCase()) && 
                      selectedColumnData.top_values && selectedColumnData.top_values.length > 0 && (
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm font-medium">Value Distribution</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-4">
                            {selectedColumnData.top_values.map((item, index) => {
                              const percentage = selectedColumnData.count > 0 ? (item.count / selectedColumnData.count) * 100 : 0
                              const colors = ['bg-blue-500', 'bg-green-500', 'bg-yellow-500', 'bg-purple-500', 'bg-pink-500', 'bg-indigo-500', 'bg-red-500', 'bg-orange-500', 'bg-teal-500', 'bg-cyan-500']
                              const color = colors[index % colors.length]
                              
                              return (
                                <div key={index} className="flex items-center space-x-2">
                                  <div className={`w-3 h-3 rounded-full ${color}`}></div>
                                  <div className="flex-1 min-w-0">
                                    <div className="flex justify-between">
                                      <span className="text-sm font-medium truncate max-w-[200px]">
                                        {item.value === null ? '<null>' : String(item.value)}
                                      </span>
                                      <span className="text-sm text-muted-foreground">
                                        {formatValue(item.count)} ({percentage.toFixed(1)}%)
                                      </span>
                                    </div>
                                    <Progress value={percentage} className="h-2" />
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        </CardContent>
                      </Card>
                    )}
                  </TabsContent>
                  
                  <TabsContent value="quality" className="space-y-4 mt-4">
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">Quality Metrics</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-4">
                          <div>
                            <div className="flex justify-between mb-1">
                              <span className="text-sm font-medium">Completeness</span>
                              <span className="text-sm font-medium">
                                {Math.round(selectedColumnData.completeness)}%
                              </span>
                            </div>
                            <Progress value={selectedColumnData.completeness} />
                          </div>
                          
                          <div>
                            <div className="flex justify-between mb-1">
                              <span className="text-sm font-medium">Uniqueness</span>
                              <span className="text-sm font-medium">
                                {Math.round(selectedColumnData.uniqueness)}%
                              </span>
                            </div>
                            <Progress value={selectedColumnData.uniqueness} />
                          </div>
                          
                          <div>
                            <div className="flex justify-between mb-1">
                              <span className="text-sm font-medium">Validity</span>
                              <span className="text-sm font-medium">
                                {Math.round(selectedColumnData.validity)}%
                              </span>
                            </div>
                            <Progress value={selectedColumnData.validity} />
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                    
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">Quality Score</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="flex items-center justify-center">
                          <div className="relative h-32 w-32">
                            <div className="absolute inset-0 flex items-center justify-center">
                              <span className={`text-3xl font-bold ${getQualityBadgeVariant(profile?.data_quality_score)}`}>
                                {profile?.data_quality_score !== undefined ? `${Math.round(profile.data_quality_score)}%` : 'N/A'}
                              </span>
                            </div>
                            <svg className="h-full w-full" viewBox="0 0 100 100">
                              <circle
                                cx="50"
                                cy="50"
                                r="40"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="10"
                                className="text-muted"
                              />
                              <circle
                                cx="50"
                                cy="50"
                                r="40"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="10"
                                strokeDasharray={`${profile?.data_quality_score} 100`}
                                strokeLinecap="round"
                                className={getQualityBadgeVariant(profile?.data_quality_score)}
                                transform="rotate(-90 50 50)"
                              />
                            </svg>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </>
          ) : (
            <CardContent className="flex flex-col items-center justify-center h-[400px] text-center">
              <Info className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium">No column selected</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Select a column from the list to view detailed statistics
              </p>
            </CardContent>
          )}
        </Card>
      </div>
    </div>
  )
}
