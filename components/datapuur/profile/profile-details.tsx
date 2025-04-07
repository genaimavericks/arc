"use client"

import { useState, useEffect, useMemo } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useToast } from "@/components/ui/use-toast"
import { format } from "date-fns"
import {
  BarChart2,
  Calendar,
  Database,
  FileBarChart,
  FileLineChart,
  FileSpreadsheet,
  Filter,
  ListFilter,
  MoreHorizontal,
  Percent,
  PieChart,
  SquareCode,
  Table as TableIcon,
  Search,
  AlertTriangle,
  Fingerprint,
  MapPin,
  Mail,
  Phone,
  FileText,
  Hash,
  ToggleLeft,
  Key,
  Clock,
  Activity,
  Info,
  Braces,
  FileQuestion,
  CheckCircle,
  BarChart,
  LineChart,
  Download
} from "lucide-react"
import LoadingSpinner from "@/components/loading-spinner"
import { 
  BarChart as RechartsBarChart, 
  Bar, 
  PieChart as RechartsPieChart, 
  Pie,
  Cell,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer 
} from "recharts"

// Register Chart.js components
// ChartJS.register(
//   CategoryScale,
//   LinearScale,
//   BarElement,
//   Title,
//   Tooltip,
//   Legend,
//   ArcElement
// )

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
  mean_value?: number
  median_value?: number
  mode_value?: string
  std_dev?: number
  frequent_values?: { [key: string]: number }
  invalid_values?: { [key: string]: number }
  outliers?: {
    z_score: { [key: string]: number }
    iqr: { [key: string]: number }
  }
  patterns?: {
    has_nulls: boolean
    completeness: number
  }
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
  exact_duplicates_count: number
  fuzzy_duplicates_count: number
  duplicate_groups?: {
    exact: any[]
    fuzzy: any[]
  }
}

export default function ProfileDetails({ profileId }: ProfileDetailsProps) {
  const [profile, setProfile] = useState<ProfileData | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedColumn, setSelectedColumn] = useState<string | null>(null)
  const [exporting, setExporting] = useState(false)
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
    if (score === undefined) return 'Unknown';
    if (score >= 90) return 'Excellent';
    if (score >= 80) return 'Good';
    if (score >= 70) return 'Fair';
    if (score >= 60) return 'Poor';
    return 'Critical';
  };

  // Badge variant for quality score
  const getQualityBadgeVariant = (score?: number): "default" | "destructive" | "secondary" | "outline" => {
    if (score === undefined) return 'secondary';
    if (score >= 90) return 'default';
    if (score >= 75) return 'default';
    if (score >= 60) return 'secondary';
    if (score >= 40) return 'secondary';
    return 'destructive';
  };

  const formatValue = (value?: number | string): string => {
    if (value === undefined || value === null) return '0';
    return typeof value === 'number' ? value.toLocaleString() : value;
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
      case 'email':
        return <Mail className="h-4 w-4 text-amber-500" />
      case 'phone':
        return <Phone className="h-4 w-4 text-indigo-500" />
      case 'uuid':
        return <Key className="h-4 w-4 text-sky-500" />
      case 'postal_code':
        return <MapPin className="h-4 w-4 text-rose-500" />
      default:
        return <Database className="h-4 w-4 text-gray-500" />
    }
  }

  const formatDataType = (dataType: string): string => {
    switch (dataType?.toLowerCase()) {
      case 'integer':
      case 'int':
        return 'Integer'
      case 'float':
      case 'double':
      case 'decimal':
      case 'numeric':
        return 'Float'
      case 'string':
      case 'text':
      case 'varchar':
      case 'char':
        return 'Text'
      case 'boolean':
      case 'bool':
        return 'Boolean'
      case 'date':
      case 'datetime':
      case 'timestamp':
        return 'Date'
      case 'email':
        return 'Email'
      case 'phone':
        return 'Phone'
      case 'uuid':
        return 'UUID'
      case 'postal_code':
        return 'Postal Code'
      default:
        return dataType || 'Unknown'
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

  // Format value for display
  const formatValueForDisplay = (value: any): string => {
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
      return `[${value.slice(0, 3).map(v => formatValueForDisplay(v)).join(', ')}${value.length > 3 ? '...' : ''}]`
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
        // Calculate missing values by combining null_count with empty string count from frequent_values
        let emptyStringCount = 0;
        if (columnData.frequent_values && '' in columnData.frequent_values) {
          emptyStringCount = columnData.frequent_values[''];
        }
        
        const missingCount = (columnData.null_count || 0) + emptyStringCount;
        
        // Make sure all required properties exist with appropriate defaults
        return {
          ...columnData,
          name: columnData.name || columnData.column_name || `Column ${index}`,
          data_type: columnData.data_type || 'unknown',
          count: columnData.count || 0,
          unique_count: columnData.unique_count || 0,
          null_count: columnData.null_count || 0,
          missing_count: missingCount,
          quality_score: columnData.quality_score || 0,
          completeness: columnData.completeness || 0,
          uniqueness: columnData.uniqueness || 0,
          validity: columnData.validity || 0,
          min_value: columnData.min_value,
          max_value: columnData.max_value,
          mode_value: columnData.mode_value
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
        // Calculate missing values by combining null_count with empty string count from frequent_values
        let emptyStringCount = 0;
        if (columnData.frequent_values && '' in columnData.frequent_values) {
          emptyStringCount = columnData.frequent_values[''];
        }
        
        const missingCount = (columnData.null_count || 0) + emptyStringCount;
        
        // Make sure all required properties exist with appropriate defaults
        return {
          ...columnData,
          name: columnData.name || columnData.column_name || selectedColumn,
          data_type: columnData.data_type || 'unknown',
          count: columnData.count || 0,
          unique_count: columnData.unique_count || 0,
          null_count: columnData.null_count || 0,
          missing_count: missingCount,
          quality_score: columnData.quality_score || 0,
          completeness: columnData.completeness || 0,
          uniqueness: columnData.uniqueness || 0,
          validity: columnData.validity || 0,
          min_value: columnData.min_value,
          max_value: columnData.max_value,
          mode_value: columnData.mode_value
        };
      }
      return null;
    }
  }, [selectedColumn, profile]);

  // Handle export functionality
  const handleExport = async (format: 'csv' | 'json') => {
    if (!profile || exporting) return;
    
    try {
      setExporting(true);
      
      if (format === 'json') {
        // Create a JSON string with proper formatting
        const jsonString = JSON.stringify(profile, null, 2);
        
        // Create a blob of the data
        const blob = new Blob([jsonString], { type: 'application/json' });
        
        // Create a temporary URL for the blob
        const url = window.URL.createObjectURL(blob);
        
        // Create and trigger download
        downloadFile(url, `${profile.file_name.replace(/\s+/g, '_')}_profile.json`);
        
        toast({
          title: "Export Successful",
          description: "Profile data has been exported as JSON",
        });
      } else {
        // Create CSV content
        const csvContent = generateCSV(profile);
        
        // Create a blob of the data
        const blob = new Blob([csvContent], { type: 'text/csv' });
        
        // Create a temporary URL for the blob
        const url = window.URL.createObjectURL(blob);
        
        // Create and trigger download
        downloadFile(url, `${profile.file_name.replace(/\s+/g, '_')}_profile.csv`);
        
        toast({
          title: "Export Successful",
          description: "Profile data has been exported as CSV",
        });
      }
    } catch (error) {
      console.error(`Error exporting profile as ${format}:`, error);
      toast({
        title: "Export Failed",
        description: `Failed to export profile data as ${format}. Please try again.`,
        variant: "destructive",
      });
    } finally {
      setExporting(false);
    }
  };
  
  // Helper function to trigger file download
  const downloadFile = (url: string, fileName: string) => {
    // Create a temporary link element
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = fileName;
    
    // Append to the DOM, trigger click, and clean up
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };
  
  // Generate CSV content from profile data
  const generateCSV = (profileData: ProfileData): string => {
    let csvRows: string[] = [];
    
    // Add header information
    csvRows.push('Profile Summary');
    csvRows.push(`ID,${profileData.id}`);
    csvRows.push(`File Name,${profileData.file_name}`);
    csvRows.push(`Total Rows,${profileData.total_rows}`);
    csvRows.push(`Total Columns,${profileData.total_columns}`);
    csvRows.push(`Data Quality Score,${profileData.data_quality_score?.toFixed(2)}%`);
    csvRows.push(`Created At,${profileData.created_at}`);
    csvRows.push(`Exact Duplicates,${profileData.exact_duplicates_count || 0}`);
    csvRows.push(`Fuzzy Duplicates,${profileData.fuzzy_duplicates_count || 0}`);
    csvRows.push(''); // Empty row for separation
    
    // Add column profiles section
    csvRows.push('Column Profiles');
    
    // Create header row for column data
    const columnHeaders = [
      "Column Name", "Data Type", "Count", "Null Count", "Unique Count",
      "Quality Score", "Completeness", "Uniqueness", "Validity",
      "Min Value", "Max Value", "Mean", "Median", "Mode", "Std Dev"
    ];
    csvRows.push(columnHeaders.join(','));
    
    // Process columns
    const columnsData = profileData.columns;
    if (Array.isArray(columnsData)) {
      // Handle array format
      columnsData.forEach((colData, i) => {
        const colName = colData.column_name || colData.name || `Column ${i}`;
        const rowData = extractColumnData(colName, colData);
        csvRows.push(rowData.join(','));
      });
    } else if (typeof columnsData === 'object' && columnsData !== null) {
      // Handle dictionary format
      Object.entries(columnsData).forEach(([colName, colData]) => {
        const rowData = extractColumnData(colName, colData);
        csvRows.push(rowData.join(','));
      });
    }
    
    // Join rows with newlines
    return csvRows.join('\n');
  };
  
  // Extract column data for CSV export
  const extractColumnData = (colName: string, colData: ColumnProfile): string[] => {
    // Escape any commas in the column name or values
    const escapeCSV = (value: any): string => {
      if (value === null || value === undefined) return '';
      const strValue = String(value);
      return strValue.includes(',') ? `"${strValue}"` : strValue;
    };
    
    return [
      escapeCSV(colName),
      escapeCSV(colData.data_type || ''),
      escapeCSV(colData.count || 0),
      escapeCSV(colData.null_count || 0),
      escapeCSV(colData.unique_count || 0),
      escapeCSV(colData.quality_score ? `${(colData.quality_score * 100).toFixed(2)}%` : '0%'),
      escapeCSV(colData.completeness?.toFixed(2) || 0),
      escapeCSV(colData.uniqueness?.toFixed(2) || 0),
      escapeCSV(colData.validity?.toFixed(2) || 0),
      escapeCSV(colData.min_value || ''),
      escapeCSV(colData.max_value || ''),
      escapeCSV(colData.mean_value || ''),
      escapeCSV(colData.median_value || ''),
      escapeCSV(colData.mode_value || ''),
      escapeCSV(colData.std_dev || '')
    ];
  };

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
            <div className="flex space-x-2 items-center">
              <button
                onClick={() => handleExport('csv')}
                className="flex items-center space-x-1 px-3 py-1 bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200 transition"
                title="Export as CSV"
              >
                <FileSpreadsheet className="h-4 w-4" />
                <span>CSV</span>
              </button>
              <button
                onClick={() => handleExport('json')}
                className="flex items-center space-x-1 px-3 py-1 bg-green-100 text-green-700 rounded-md hover:bg-green-200 transition"
                title="Export as JSON"
              >
                <Braces className="h-4 w-4" />
                <span>JSON</span>
              </button>
              <Badge variant={getQualityBadgeVariant(profile?.data_quality_score)}>
                {profile?.data_quality_score !== undefined ? `${Math.round(profile.data_quality_score)}%` : 'N/A'}
              </Badge>
            </div>
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
            
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Fingerprint className="h-5 w-5 mr-2 text-primary" />
                    <span className="font-medium">Exact Duplicates</span>
                  </div>
                  <span className="text-2xl font-bold">{formatValue(profile?.exact_duplicates_count)}</span>
                </div>
                {profile?.duplicate_groups?.exact && profile.duplicate_groups.exact.length > 0 && (
                  <div className="mt-4">
                    <div className="text-sm text-muted-foreground mb-2">Sample duplicate records:</div>
                    <div className="max-h-[200px] overflow-auto rounded border text-xs">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            {/* Display headers for first 3-4 columns */}
                            {Object.keys(profile.duplicate_groups.exact[0]).slice(0, 4).map((key, index) => (
                              <TableHead key={index} className="p-2">{key}</TableHead>
                            ))}
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {/* Show up to 5 duplicate records */}
                          {profile.duplicate_groups.exact.slice(0, 5).map((record: any, index: number) => (
                            <TableRow key={index}>
                              {Object.keys(record).slice(0, 4).map((key, keyIndex) => (
                                <TableCell key={keyIndex} className="p-2 truncate">
                                  {typeof record[key] === 'object' ? 
                                    JSON.stringify(record[key]).substring(0, 30) : 
                                    String(record[key]).substring(0, 30)}
                                </TableCell>
                              ))}
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Fingerprint className="h-5 w-5 mr-2 text-primary" />
                    <span className="font-medium">Fuzzy Duplicates</span>
                  </div>
                  <span className="text-2xl font-bold">{formatValue(profile?.fuzzy_duplicates_count)}</span>
                </div>
                {profile?.duplicate_groups?.fuzzy && profile.duplicate_groups.fuzzy.length > 0 && (
                  <div className="mt-4">
                    <div className="text-sm text-muted-foreground mb-2">Sample similar records:</div>
                    <div className="max-h-[200px] overflow-auto rounded border text-xs">
                      {profile.duplicate_groups.fuzzy.slice(0, 3).map((group, groupIndex) => (
                        <div key={groupIndex} className="mb-3 border-b pb-2">
                          <div className="font-semibold p-2 bg-muted">
                            Group {groupIndex + 1} - {group.count} similar records
                          </div>
                          {group.sample && group.sample.length > 0 && (
                            <Table>
                              <TableHeader>
                                <TableRow>
                                  {/* Display headers for first 3-4 columns */}
                                  {Object.keys(group.sample[0]).slice(0, 4).map((key, index) => (
                                    <TableHead key={index} className="p-2">{key}</TableHead>
                                  ))}
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {/* Show samples from this group */}
                                {group.sample.map((record: any, index: number) => (
                                  <TableRow key={index}>
                                    {Object.keys(record).slice(0, 4).map((key, keyIndex) => (
                                      <TableCell key={keyIndex} className="p-2 truncate">
                                        {typeof record[key] === 'object' ? 
                                          JSON.stringify(record[key]).substring(0, 30) : 
                                          String(record[key]).substring(0, 30)}
                                      </TableCell>
                                    ))}
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
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
                      <Badge variant={getQualityBadgeVariant(column.quality_score * 100)}>
                        {getQualityScoreLabel(column.quality_score * 100)}
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
                  <Badge variant={getQualityBadgeVariant(selectedColumnData.quality_score * 100)}>
                    {selectedColumnData.quality_score !== undefined ? `${Math.round(selectedColumnData.quality_score * 100)}%` : 'N/A'}
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
                                `(${((selectedColumnData.unique_count / selectedColumnData.count) * 100).toFixed(1)}%)` : 
                                '(0.0%)'}
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
                                `(${((selectedColumnData.missing_count / selectedColumnData.count) * 100).toFixed(1)}%)` : 
                                '(0.0%)'}
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
                    
                    {/* Add histogram for numeric columns */}
                    {['integer', 'int', 'float', 'double', 'decimal', 'numeric'].includes(selectedColumnData.data_type?.toLowerCase()) && (
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm font-medium">Value Distribution</CardTitle>
                        </CardHeader>
                        <CardContent>
                          {selectedColumnData.frequent_values && Object.keys(selectedColumnData.frequent_values).length > 0 ? (
                            <ResponsiveContainer width="100%" height={250}>
                              <RechartsBarChart 
                                data={Object.entries(selectedColumnData.frequent_values)
                                  .filter(([key]) => key !== '' && key !== 'null')
                                  .map(([key, value]) => ({
                                    name: key === 'null' ? '<null>' : key,
                                    value: value
                                  }))
                                  .sort((a, b) => {
                                    // Try to convert to numbers for numeric sorting if possible
                                    const numA = parseFloat(a.name);
                                    const numB = parseFloat(b.name);
                                    return !isNaN(numA) && !isNaN(numB) ? numA - numB : 0;
                                  })
                                  .slice(0, 10)
                                }
                              >
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis 
                                  dataKey="name" 
                                  tick={{ fontSize: 10 }}
                                  angle={-45}
                                  textAnchor="end"
                                  interval={0}
                                />
                                <YAxis />
                                <Tooltip 
                                  formatter={(value) => [`${value} occurrences`, 'Count']} 
                                  labelFormatter={(label) => `Value: ${label}`}
                                />
                                <Bar dataKey="value" fill="#6366f1" />
                              </RechartsBarChart>
                            </ResponsiveContainer>
                          ) : (
                            <div className="h-[250px] flex items-center justify-center">
                              <p className="text-muted-foreground">No distribution data available</p>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    )}
                    
                    {/* Add invalid values section for special data types in Overview tab */}
                    {['email', 'phone', 'uuid', 'postal_code'].includes(selectedColumnData.data_type?.toLowerCase()) && 
                      selectedColumnData.invalid_values && Object.keys(selectedColumnData.invalid_values).length > 0 && (
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm font-medium">
                            <div className="flex items-center">
                              <AlertTriangle className="h-4 w-4 text-amber-500 mr-2" />
                              Invalid Values
                            </div>
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-3">
                            <div className="text-sm text-muted-foreground mb-2">
                              The following values do not match the expected format for {formatDataType(selectedColumnData.data_type)}:
                            </div>
                            {Object.entries(selectedColumnData.invalid_values)
                              .slice(0, 5)
                              .map(([key, value], index) => (
                                <div key={index} className="flex items-center justify-between border-b pb-2">
                                  <div className="font-medium truncate max-w-[200px] text-red-600">{key}</div>
                                  <div className="text-sm">{formatValue(value)} occurrences</div>
                                </div>
                              ))}
                            {Object.keys(selectedColumnData.invalid_values).length > 5 && (
                              <div className="text-sm text-muted-foreground text-center italic">
                                + {Object.keys(selectedColumnData.invalid_values).length - 5} more invalid values
                              </div>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    )}
                    
                    {/* Add visualization for string/categorical data */}
                    {!['integer', 'int', 'float', 'double', 'decimal', 'numeric'].includes(selectedColumnData.data_type?.toLowerCase()) && (
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm font-medium">Value Distribution</CardTitle>
                        </CardHeader>
                        <CardContent>
                          {selectedColumnData.frequent_values && Object.keys(selectedColumnData.frequent_values).length > 0 ? (
                            <ResponsiveContainer width="100%" height={250}>
                              <RechartsPieChart>
                                <Pie
                                  data={Object.entries(selectedColumnData.frequent_values)
                                    .map(([key, value]) => ({
                                      name: key === 'null' ? '<null>' : key === '' ? '<empty>' : key,
                                      value: value
                                    }))
                                    .sort((a, b) => b.value - a.value)
                                    .slice(0, 5)
                                  }
                                  cx="50%"
                                  cy="50%"
                                  outerRadius={80}
                                  fill="#8884d8"
                                  dataKey="value"
                                  nameKey="name"
                                  label={({name, percent}) => `${name}: ${(percent * 100).toFixed(0)}%`}
                                >
                                  {
                                    Object.entries(selectedColumnData.frequent_values)
                                      .map(([key, value], index) => (
                                        <Cell 
                                          key={`cell-${index}`} 
                                          fill={['#6366f1', '#8b5cf6', '#ec4899', '#f43f5e', '#f97316'][index % 5]} 
                                        />
                                      ))
                                  }
                                </Pie>
                                <Tooltip formatter={(value) => [`${value} occurrences`, 'Count']} />
                                <Legend />
                              </RechartsPieChart>
                            </ResponsiveContainer>
                          ) : (
                            <div className="h-[250px] flex items-center justify-center">
                              <p className="text-muted-foreground">No distribution data available</p>
                            </div>
                          )}
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
                            <p className="text-2xl font-bold">{formatValueForDisplay(selectedColumnData.min_value)}</p>
                          </div>
                          <div>
                            <h4 className="text-sm font-medium mb-1">Max Value</h4>
                            <p className="text-2xl font-bold">{formatValueForDisplay(selectedColumnData.max_value)}</p>
                          </div>
                          {selectedColumnData.mean_value !== undefined && (
                            <div>
                              <h4 className="text-sm font-medium mb-1">Mean</h4>
                              <p className="text-2xl font-bold">{formatValueForDisplay(selectedColumnData.mean_value)}</p>
                            </div>
                          )}
                          {selectedColumnData.median_value !== undefined && (
                            <div>
                              <h4 className="text-sm font-medium mb-1">Median</h4>
                              <p className="text-2xl font-bold">{formatValueForDisplay(selectedColumnData.median_value)}</p>
                            </div>
                          )}
                          {selectedColumnData.mode_value !== undefined && (
                            <div>
                              <h4 className="text-sm font-medium mb-1">Mode</h4>
                              <p className="text-2xl font-bold">{formatValueForDisplay(selectedColumnData.mode_value)}</p>
                            </div>
                          )}
                          {selectedColumnData.std_dev !== undefined && (
                            <div>
                              <h4 className="text-sm font-medium mb-1">Standard Deviation</h4>
                              <p className="text-2xl font-bold">{formatValueForDisplay(selectedColumnData.std_dev)}</p>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                    
                    {/* Add outliers section */}
                    {['integer', 'int', 'float', 'double', 'decimal', 'numeric'].includes(selectedColumnData.data_type?.toLowerCase()) && 
                      selectedColumnData.outliers && 
                      (Object.keys(selectedColumnData.outliers.z_score).length > 0 || 
                       Object.keys(selectedColumnData.outliers.iqr).length > 0) && (
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm font-medium">
                            <div className="flex items-center">
                              <AlertTriangle className="h-4 w-4 text-amber-500 mr-2" />
                              Outliers Detected
                            </div>
                          </CardTitle>
                          <CardDescription>
                            Values that significantly deviate from the normal distribution
                          </CardDescription>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-4">
                            {/* Z-Score based outliers */}
                            {Object.keys(selectedColumnData.outliers.z_score).length > 0 && (
                              <div>
                                <h4 className="text-sm font-medium mb-2">Z-Score Method (±3σ)</h4>
                                <div className="space-y-2 pl-2">
                                  {Object.entries(selectedColumnData.outliers.z_score).map(([value, count], i) => (
                                    <div key={i} className="flex items-center justify-between border-b pb-1">
                                      <span className="font-medium text-red-600">{value}</span>
                                      <span className="text-sm text-muted-foreground">{formatValue(count)} occurrences</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            
                            {/* IQR based outliers */}
                            {Object.keys(selectedColumnData.outliers.iqr).length > 0 && (
                              <div>
                                <h4 className="text-sm font-medium mb-2">IQR Method (Q1-1.5×IQR, Q3+1.5×IQR)</h4>
                                <div className="space-y-2 pl-2">
                                  {Object.entries(selectedColumnData.outliers.iqr).map(([value, count], i) => (
                                    <div key={i} className="flex items-center justify-between border-b pb-1">
                                      <span className="font-medium text-red-600">{value}</span>
                                      <span className="text-sm text-muted-foreground">{formatValue(count)} occurrences</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            
                            <div className="text-xs text-muted-foreground mt-2">
                              <p>Z-Score: Values beyond 3 standard deviations from the mean</p>
                              <p>IQR: Values beyond 1.5× interquartile range from Q1/Q3</p>
                            </div>
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
                                {Math.round(selectedColumnData.completeness * 100)}%
                              </span>
                            </div>
                            <Progress value={selectedColumnData.completeness * 100} />
                          </div>
                          
                          <div>
                            <div className="flex justify-between mb-1">
                              <span className="text-sm font-medium">Uniqueness</span>
                              <span className="text-sm font-medium">
                                {Math.round(selectedColumnData.uniqueness * 100)}%
                              </span>
                            </div>
                            <Progress value={selectedColumnData.uniqueness * 100} />
                          </div>
                          
                          <div>
                            <div className="flex justify-between mb-1">
                              <span className="text-sm font-medium">Validity</span>
                              <span className="text-sm font-medium">
                                {Math.round(selectedColumnData.validity * 100)}%
                              </span>
                            </div>
                            <Progress value={selectedColumnData.validity * 100} />
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
                              <span className={`text-3xl font-bold ${getQualityBadgeVariant(selectedColumnData.quality_score * 100)}`}>
                                {selectedColumnData.quality_score !== undefined ? `${Math.round(selectedColumnData.quality_score * 100)}%` : 'N/A'}
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
                                strokeDasharray={`${selectedColumnData.quality_score * 100} 100`}
                                strokeLinecap="round"
                                className={getQualityBadgeVariant(selectedColumnData.quality_score * 100)}
                                transform="rotate(-90 50 50)"
                              />
                            </svg>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                    
                    {/* Add new section to display invalid values for special data types */}
                    {['email', 'phone', 'uuid', 'postal_code'].includes(selectedColumnData.data_type?.toLowerCase()) && (
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm font-medium">Invalid Values</CardTitle>
                        </CardHeader>
                        <CardContent>
                          {selectedColumnData.invalid_values && Object.keys(selectedColumnData.invalid_values).length > 0 ? (
                            <div className="space-y-2">
                              {Object.entries(selectedColumnData.invalid_values).map(([key, value], index) => (
                                <div key={index} className="flex items-center justify-between">
                                  <span className="font-medium truncate max-w-[200px]">{key}</span>
                                  <div className="flex items-center">
                                    <span className="text-sm text-muted-foreground mr-2">{formatValue(value)}</span>
                                    <Progress
                                      value={selectedColumnData.count > 0 && value !== undefined ? (value / selectedColumnData.count) * 100 : 0}
                                      className="w-24"
                                    />
                                  </div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="h-[200px] flex items-center justify-center">
                              <p className="text-muted-foreground">No invalid values found</p>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    )}
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
