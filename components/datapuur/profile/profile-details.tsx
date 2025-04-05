"use client"

import { useState, useEffect } from "react"
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
} from "lucide-react"
import LoadingSpinner from "@/components/loading-spinner"

interface ProfileDetailsProps {
  profileId: string;
}

interface ColumnProfile {
  name: string
  data_type: string
  count: number
  unique_count: number
  missing_count: number
  min_value?: any
  max_value?: any
  mean?: number
  median?: number
  std_dev?: number
  histogram?: { bins: number[]; counts: number[] }
  top_values?: { value: any; count: number }[]
  distribution?: { category: string; count: number }[]
  quality_score: number
  completeness: number
  uniqueness: number
  validity: number
}

interface ProfileData {
  id: string
  file_id: string
  file_name: string
  total_rows: number
  total_columns: number
  data_quality_score: number
  columns: Record<string, ColumnProfile>
  created_at: string
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
    if (score >= 90) return 'Excellent';
    if (score >= 75) return 'Good';
    if (score >= 60) return 'Fair';
    if (score >= 40) return 'Poor';
    return 'Bad';
  };

  const getQualityScoreBadgeVariant = (score?: number): "default" | "destructive" | "secondary" | "outline" => {
    if (score === undefined) return 'default';
    if (score >= 90) return 'default';
    if (score >= 75) return 'secondary';
    if (score >= 60) return 'outline';
    return 'destructive';
  };

  const getQualityBadgeVariant = (score?: number): "default" | "destructive" | "secondary" | "outline" => {
    if (score === undefined) return 'default';
    if (score >= 90) return 'default';
    if (score >= 75) return 'secondary';
    if (score >= 60) return 'outline';
    return 'destructive';
  };

  const getDataTypeIcon = (dataType: string) => {
    switch (dataType.toLowerCase()) {
      case "numeric":
      case "integer":
      case "float":
      case "double":
        return <Hash className="h-4 w-4" />
      case "string":
      case "text":
        return <FileText className="h-4 w-4" />
      case "boolean":
        return <CheckCircle className="h-4 w-4" />
      case "date":
      case "datetime":
      case "timestamp":
        return <Calendar className="h-4 w-4" />
      case "categorical":
        return <ListFilter className="h-4 w-4" />
      default:
        return <Fingerprint className="h-4 w-4" />
    }
  }

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

  const selectedColumnData = selectedColumn ? profile.columns[selectedColumn] : null;

  // Safety check for selectedColumnData
  if (selectedColumn && !selectedColumnData) {
    return (
      <div className="flex justify-center items-center h-64 text-muted-foreground">
        Selected column data not available
      </div>
    )
  }

  const columnNames = Object.keys(profile.columns)

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
              {getQualityScoreLabel(profile?.data_quality_score)}
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
                  <span className="text-2xl font-bold">{profile?.total_rows !== undefined ? profile.total_rows.toLocaleString() : 'N/A'}</span>
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
                  <span className="text-2xl font-bold">{profile?.total_columns !== undefined ? profile.total_columns.toLocaleString() : 'N/A'}</span>
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
                      {getQualityScoreLabel(profile?.data_quality_score)}
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
                  const column = profile.columns[columnName]
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
                        <span className="ml-2 font-medium">{columnName}</span>
                      </div>
                      <Badge variant={getQualityBadgeVariant(column.quality_score)}>
                        {getQualityScoreLabel(column.quality_score)}
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
                      <span className="ml-2">{selectedColumn}</span>
                    </CardTitle>
                    <CardDescription>
                      {selectedColumnData.data_type} • {selectedColumnData.count !== undefined ? selectedColumnData.count.toLocaleString() : 'N/A'} values
                    </CardDescription>
                  </div>
                  <Badge variant={getQualityBadgeVariant(selectedColumnData.quality_score)}>
                    {getQualityScoreLabel(selectedColumnData.quality_score)}
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
                              {selectedColumnData.unique_count !== undefined ? selectedColumnData.unique_count.toLocaleString() : 'N/A'}
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
                              {selectedColumnData.missing_count !== undefined ? selectedColumnData.missing_count.toLocaleString() : 'N/A'}
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
                                    {item.count !== undefined ? item.count.toLocaleString() : 'N/A'} 
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
                    
                    {selectedColumnData.min_value !== undefined && selectedColumnData.max_value !== undefined && (
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm font-medium">Range</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="flex items-center justify-between">
                            <div>
                              <div className="text-sm text-muted-foreground">Min</div>
                              <div className="font-bold">{selectedColumnData.min_value}</div>
                            </div>
                            <Separator className="w-12" />
                            <div>
                              <div className="text-sm text-muted-foreground">Max</div>
                              <div className="font-bold">{selectedColumnData.max_value}</div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    )}
                  </TabsContent>
                  
                  <TabsContent value="statistics" className="space-y-4 mt-4">
                    {selectedColumnData.mean !== undefined && (
                      <div className="grid grid-cols-2 gap-4">
                        <Card>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium">Mean</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <span className="text-xl font-bold">
                              {typeof selectedColumnData.mean === 'number' 
                                ? selectedColumnData.mean.toFixed(2) 
                                : selectedColumnData.mean}
                            </span>
                          </CardContent>
                        </Card>
                        
                        <Card>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium">Median</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <span className="text-xl font-bold">
                              {typeof selectedColumnData.median === 'number' 
                                ? selectedColumnData.median.toFixed(2) 
                                : selectedColumnData.median}
                            </span>
                          </CardContent>
                        </Card>
                      </div>
                    )}
                    
                    {selectedColumnData.std_dev !== undefined && (
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm font-medium">Standard Deviation</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <span className="text-xl font-bold">
                            {typeof selectedColumnData.std_dev === 'number' 
                              ? selectedColumnData.std_dev.toFixed(2) 
                              : selectedColumnData.std_dev}
                          </span>
                        </CardContent>
                      </Card>
                    )}
                    
                    {selectedColumnData.histogram && selectedColumnData.histogram.bins.length > 0 && (
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
                              <span className={`text-3xl font-bold ${getQualityBadgeVariant(selectedColumnData.quality_score)}`}>
                                {getQualityScoreLabel(selectedColumnData.quality_score)}
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
                                strokeDasharray={`${selectedColumnData.quality_score * 2.51} 251`}
                                strokeLinecap="round"
                                className={getQualityBadgeVariant(selectedColumnData.quality_score)}
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
