"use client"

import React, { useState, useEffect } from 'react'
import { DataPuurLayout } from '@/components/datapuur/datapuur-layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { fetchWithAuth } from '@/lib/auth-utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { 
  Search, 
  Database, 
  FileText, 
  Brain, 
  Loader2, 
  AlertCircle, 
  Plus,
  History,
  Trash2,
  ChevronRight,
  FileQuestion,
  CheckCircle,
  Clock,
  Play,
  FileJson,
  RefreshCw,
  BarChart2
} from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { ProfileSession } from '@/components/DataPuurAI/ProfileSession'
import { TransformationPlan } from '@/components/DataPuurAI/TransformationPlan'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Progress } from '@/components/ui/progress'
import dynamic from "next/dynamic"

// Use dynamic imports to avoid SSR issues
const ProfileList = dynamic(() => import("@/components/datapuur/profile/profile-list"), { ssr: false })
const ProfileDetails = dynamic(() => import("@/components/datapuur/profile/profile-details"), { ssr: false })

interface DataSource {
  id: string
  name: string
  type: string
  last_updated: string
  status: string
  uploaded_by: string
  dataset?: string
  path?: string
}

interface Profile {
  id: string
  file_id: string
  file_name: string
  total_rows: number
  total_columns: number
  data_quality_score: number
  created_at: string
  status: string
}

interface ProfileSummary {
  text: string;
}

interface Session {
  id: string;
  profile_id: string;
  file_id: string;
  file_name: string;
  status: string;
  created_at: string;
  updated_at: string;
  session_type: string;
  profile_summary?: ProfileSummary | string | null;
  data_quality_issues?: any[];
  improvement_suggestions?: any[];
  messages?: any[];
}

interface SessionDebugInfo {
  rawResponse: string;
  parsedData: string | null;
  error: string | null;
  sessionsFound: number;
}

declare global {
  interface Window {
    _sessionDebug?: {
      originalData: any;
      cleanSessions: Session[];
    };
    _sessionDebugInfo?: SessionDebugInfo;
  }
}

export default function AIProfilePage() {
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [sessions, setSessions] = useState<Session[]>([])
  const [selectedSource, setSelectedSource] = useState<string | null>(null)
  const [selectedProfile, setSelectedProfile] = useState<string | null>(null)
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [activePlanId, setActivePlanId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingProfiles, setLoadingProfiles] = useState(false)
  const [loadingSessions, setLoadingSessions] = useState(false)
  const [permissionError, setPermissionError] = useState<string | null>(null)
  const [creatingSession, setCreatingSession] = useState(false)
  const [activeTab, setActiveTab] = useState('history')
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null)
  const [creatingProfile, setCreatingProfile] = useState(false)
  const [profileProgress, setProfileProgress] = useState(0)
  const [profileStatus, setProfileStatus] = useState<string>('')  
  // For Profile List and Details tabs
  const [profileListSelectedId, setProfileListSelectedId] = useState<string | null>(null)
  const { toast } = useToast()

  // Fetch data sources on mount
  useEffect(() => {
    fetchDataSources()
    fetchSessions()
  }, [])
  
  // Add debug logging whenever sessions change
  useEffect(() => {
    if (sessions) {
      // Make debug info available in global scope
      window._sessionDebug = {
        originalData: sessions,
        cleanSessions: sessions
      }
      
      // Log detailed information about the sessions
      window.console.log('===DEBUG=== Sessions updated, new length:', sessions.length)
      if (sessions.length > 0) {
        window.console.log('===DEBUG=== First session:', sessions[0])
        
        // Check the profile_summary format specifically
        const firstSession = sessions[0]
        if (firstSession.profile_summary) {
          window.console.log(
            '===DEBUG=== profile_summary type:', 
            typeof firstSession.profile_summary,
            'value:', 
            firstSession.profile_summary
          )
        }
      }
    }
  }, [sessions])

  // Fetch profiles when source is selected
  useEffect(() => {
    if (selectedSource) {
      fetchProfiles(selectedSource)
    } else {
      setProfiles([])
      setSelectedProfile(null)
    }
  }, [selectedSource])

  const fetchDataSources = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('token')
      const response = await fetch('/api/datapuur/sources', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        throw new Error('Failed to fetch data sources')
      }

      const data = await response.json()
      setDataSources(data || [])
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load data sources. Please try again.",
        variant: "destructive"
      })
    } finally {
      setLoading(false)
    }
  }

  const fetchProfiles = async (fileId: string) => {
    setLoadingProfiles(true)
    try {
      // Check if AI profile exists for this data source
      // Using try/catch since fetchWithAuth will throw on error status codes
      try {
        // fetchWithAuth automatically parses JSON response
        const data = await fetchWithAuth(`/api/datapuur-ai/profiles?file_id=${fileId}`)
        setProfiles(data.profiles || [])
        
        // Auto-select if only one profile
        if (data.profiles && data.profiles.length === 1) {
          setSelectedProfile(data.profiles[0].id)
        }
      } catch (apiError: any) {
        // Check if it's a 404 error (no profiles exist yet)
        if (apiError.message && apiError.message.includes('404')) {
          setProfiles([])
        } else {
          console.error('Error in API call:', apiError)
          throw apiError
        }
      }
    } catch (error) {
      console.error('Error fetching profiles:', error)
      setProfiles([])
    } finally {
      setLoadingProfiles(false)
    }
  }

  const createProfile = async () => {
    if (!selectedSource) return

    setCreatingProfile(true)
    setProfileProgress(0)
    setProfileStatus('Initializing profile creation...')
    
    // Add notification when profiling starts
    toast({
      title: "Profile Creation Started",
      description: "Creating AI profile for the selected dataset. This may take a few minutes."
    })

    try {
      const sourceData = dataSources.find(s => s.id === selectedSource)
      
      if (!sourceData) {
        throw new Error('Invalid data source')
      }

      // Create or recreate profile
      // fetchWithAuth already parses JSON and handles errors
      const profile = await fetchWithAuth('/api/datapuur-ai/profiles', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          file_id: selectedSource,
          file_name: sourceData.name,
          file_path: sourceData.path || `${selectedSource}.parquet`,
          profile_id: selectedProfile,
          recreate: profiles.length > 0  // Flag to indicate recreation
        })
      })
      
      // fetchWithAuth already throws errors for non-OK responses and returns parsed JSON
      // No need to check profile.ok or profile.status as those are Response object properties
      // that don't exist on the parsed JSON response

      
      
      // If profile already exists and is completed, just update the UI
      if (profile.status === 'completed') {
        setProfiles([profile])
        setSelectedProfile(profile.id)
        toast({
          title: "Success",
          description: profiles.length > 0 ? "Profile recreated successfully" : "Profile created successfully"
        })
        setCreatingProfile(false)
        return
      }
      
      // Poll for profile completion
      let completed = false
      let pollCount = 0
      const maxPolls = 60 // 5 minutes max

      while (!completed && pollCount < maxPolls) {
        await new Promise(resolve => setTimeout(resolve, 5000)) // Poll every 5 seconds
        
        try {
          // fetchWithAuth already parses JSON response
          const statusData = await fetchWithAuth(`/api/datapuur-ai/profiles/${profile.id}`)
          
          if (statusData.status === 'completed') {
            completed = true
            setProfiles([statusData])
            setSelectedProfile(statusData.id)
            toast({
              title: "Success",
              description: profiles.length > 0 ? "Profile recreated successfully" : "Profile created successfully"
            })
          } else if (statusData.status === 'failed') {
            throw new Error(statusData.error || 'Profile creation failed')
          } else {
            // Update progress
            const progress = Math.min(95, (pollCount / maxPolls) * 100)
            setProfileProgress(progress)
            setProfileStatus(statusData.message || 'Processing data...')
          }
        } catch (error) {
          console.error('Error checking profile status:', error)
          // Don't throw here, just continue polling
        }
        
        pollCount++
      }

      if (!completed) {
        throw new Error('Profile creation timed out')
      }
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to create profile",
        variant: "destructive"
      })
    } finally {
      setCreatingProfile(false)
      setProfileProgress(0)
      setProfileStatus('')
    }
  }

  const fetchSessions = async () => {
    setLoadingSessions(true)
    // Create a reference to store debug information
    const debugInfo: SessionDebugInfo = {
      rawResponse: '',
      parsedData: null,
      error: null,
      sessionsFound: 0
    }
    
    try {
      const token = localStorage.getItem('token')
      const response = await fetch('/api/datapuur-ai/sessions?limit=20', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        throw new Error('Failed to fetch sessions')
        }
        
      const data = await response.json()
      setSessions(data.sessions || [])
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load sessions. Please try again.",
        variant: "destructive"
      })
      setSessions([])
    } finally {
      // Expose debug info globally even if there was an error
      window._sessionDebugInfo = debugInfo
      setLoadingSessions(false)
    }
  }

  const startAISession = async () => {
    if (!selectedSource || !selectedProfile) {
      toast({
        title: "Selection Required",
        description: "Please select both a data source and a profile",
        variant: "destructive"
      })
      return
    }

    setCreatingSession(true)
    try {
      const token = localStorage.getItem('token')
      const sourceData = dataSources.find(s => s.id === selectedSource)
      const profileData = profiles.find(p => p.id === selectedProfile)
      
      if (!sourceData || !profileData) {
        throw new Error('Invalid selection')
      }

      const response = await fetch('/api/datapuur-ai/sessions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          file_id: selectedSource,
          file_name: sourceData.name,
          file_path: sourceData.path || `${selectedSource}.parquet`
        })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to create session')
      }

      const session = await response.json()
      setActiveSessionId(session.id)
      setActiveTab('session')
      
      // Refresh sessions list
      fetchSessions()
      
      toast({
        title: "Success",
        description: "AI profiling session started successfully"
      })
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to start AI session",
        variant: "destructive"
      })
    } finally {
      setCreatingSession(false)
    }
  }

  const resumeSession = (sessionId: string) => {
    setActiveSessionId(sessionId)
    setActiveTab('session')
  }

  const deleteSession = async () => {
    if (!sessionToDelete) return

    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`/api/datapuur-ai/sessions/${sessionToDelete}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      // Handle permission denied errors
      if (response.status === 403) {
        setPermissionError("Permission denied: You don't have access to delete profile sessions")
        
        // Auto-dismiss the error after 5 seconds
        setTimeout(() => {
          setPermissionError(null)
        }, 5000)
        return
      }
      
      if (!response.ok) {
        throw new Error('Failed to delete session')
      }

      toast({
        title: "Success",
        description: "Session deleted successfully"
      })

      // Refresh sessions list
      fetchSessions()
      
      // Clear active session if it was deleted
      if (activeSessionId === sessionToDelete) {
        setActiveSessionId(null)
        setActiveTab('new')
      }
    } catch (error) {
      // Only show toast for non-permission errors
      if (!permissionError) {
        toast({
          title: "Error",
          description: "Failed to delete session",
          variant: "destructive"
        })
      }
    } finally {
      setShowDeleteDialog(false)
      setSessionToDelete(null)
    }
  }

  const filteredSources = dataSources.filter(source =>
    source.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const getSourceIcon = (type: string) => {
    switch (type) {
      case 'csv':
      case 'json':
        return <FileText className="h-4 w-4" />
      case 'database':
        return <Database className="h-4 w-4" />
      default:
        return <FileQuestion className="h-4 w-4" />
    }
  }

  const formatFileSize = (bytes: number) => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    if (bytes === 0) return '0 Bytes'
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <DataPuurLayout>
      <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
        {permissionError && (
          <div className="bg-destructive text-white p-4 mb-4 rounded-md flex items-center justify-between">
            <span>{permissionError}</span>
          </div>
        )}
        
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold tracking-tight">AI Profile</h2>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="history">
              <History className="mr-2 h-4 w-4" />
              Profile Sessions 
            </TabsTrigger>
            <TabsTrigger value="new">
              <Brain className="mr-2 h-4 w-4" />
              Analyze Data
            </TabsTrigger>
            <TabsTrigger value="profile-list">
              <BarChart2 className="mr-2 h-4 w-4" />
              Profile List
            </TabsTrigger>
            <TabsTrigger value="profile-details" disabled={!profileListSelectedId}>
              <FileText className="mr-2 h-4 w-4" />
              Profile Details
            </TabsTrigger>
          </TabsList>

          <TabsContent value="new" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Start New AI Profiling Session</CardTitle>
                <CardDescription>
                  Select a data source and profile to begin AI-powered analysis
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Data Source Selection */}
                <div className="space-y-4">
                  <h3 className="text-sm font-medium">1. Select Data Source</h3>
                  
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                      <Input
                        placeholder="Search data sources..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                  </div>

                  {loading ? (
                    <div className="space-y-2">
                      {[1, 2, 3].map((i) => (
                        <Skeleton key={i} className="h-16 w-full" />
                      ))}
                    </div>
                  ) : filteredSources.length === 0 ? (
                    <Alert>
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>
                        {searchQuery ? 'No data sources found matching your search' : 'No data sources available. Upload some data first.'}
                      </AlertDescription>
                    </Alert>
                  ) : (
                    <ScrollArea className="h-64 border rounded-lg">
                      <div className="p-4 space-y-2">
                        {filteredSources.map((source) => (
                          <div
                            key={source.id}
                            className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                              selectedSource === source.id
                                ? 'border-primary bg-primary/5'
                                : 'border-border hover:bg-accent'
                            }`}
                            onClick={() => setSelectedSource(source.id)}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                {getSourceIcon(source.type)}
                                <div>
                                  <p className="font-medium">{source.dataset}</p>
                                  <p className="text-xs text-muted-foreground">{source.type} • {new Date(source.last_updated).toLocaleDateString()}</p>
                                </div>
                              </div>
                              {selectedSource === source.id && (
                                <CheckCircle className="h-5 w-5 text-primary" />
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </ScrollArea>
                  )}
                </div>

                {/* Profile Selection */}
                {selectedSource && (
                  <div className="space-y-4">
                    <h3 className="text-sm font-medium">2. Select Profile</h3>
                    
                    {loadingProfiles ? (
                      <div className="space-y-2">
                        {[1, 2].map((i) => (
                          <Skeleton key={i} className="h-16 w-full" />
                        ))}
                      </div>
                    ) : profiles.length === 0 ? (
                      <div className="space-y-4">
                        <Alert>
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription>
                            No AI profile exists for this data source yet.
                          </AlertDescription>
                        </Alert>
                        
                        {!creatingProfile ? (
                          <Button 
                            onClick={createProfile} 
                            className="w-full"
                            variant="outline"
                          >
                            <Plus className="mr-2 h-4 w-4" />
                            Create Profile
                          </Button>
                        ) : (
                          <div className="space-y-3">
                            <div className="flex items-center gap-2">
                              <Loader2 className="h-4 w-4 animate-spin" />
                              <span className="text-sm font-medium">Creating Profile...</span>
                            </div>
                            <p className="text-xs text-muted-foreground">{profileStatus}</p>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {profiles.map((profile) => (
                          <div
                            key={profile.id}
                            className={`p-4 rounded-lg border cursor-pointer transition-colors ${
                              selectedProfile === profile.id
                                ? 'border-primary bg-primary/5'
                                : 'border-border hover:bg-accent'
                            }`}
                            onClick={() => setSelectedProfile(profile.id)}
                          >
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="font-medium">{profile.file_name}</p>
                                <div className="flex items-center gap-4 mt-1">
                                  <Badge variant="secondary" className="text-xs">
                                    Profile Ready
                                  </Badge>
                                  <span className="text-xs text-muted-foreground">
                                    Created {formatDate(profile.created_at)}
                                  </span>
                                </div>
                              </div>
                              {selectedProfile === profile.id && (
                                <CheckCircle className="h-5 w-5 text-primary" />
                              )}
                            </div>
                          </div>
                        ))}
                        
                        {/* Option to recreate profile */}
                        <div className="pt-2 border-t">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={createProfile}
                            disabled={creatingProfile}
                            className="w-full"
                          >
                            {creatingProfile ? (
                              <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Recreating Profile...
                              </>
                            ) : (
                              <>
                                <RefreshCw className="mr-2 h-4 w-4" />
                                Recreate Profile
                              </>
                            )}
                          </Button>
                        </div>
                        
                        {creatingProfile && (
                          <div className="space-y-2">
                            <p className="text-xs text-muted-foreground text-center">{profileStatus}</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Start Session Button */}
                <div className="flex justify-end">
                  <Button
                    onClick={startAISession}
                    disabled={!selectedSource || !selectedProfile || creatingSession || creatingProfile}
                    size="lg"
                  >
                    {creatingSession ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Starting Session...
                      </>
                    ) : (
                      <>
                        <Brain className="mr-2 h-4 w-4" />
                        Start AI Analysis
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="history" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Session History</CardTitle>
                <CardDescription>
                  View your previous AI profiling sessions.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-end mb-4">
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => {
                      // Force refresh sessions
                      fetchSessions()
                      toast({
                        title: "Refreshing Sessions",
                        description: "Fetching the latest sessions data..."
                      })
                    }}
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Refresh Sessions
                  </Button>
                </div>
                
                {loadingSessions ? (
                  <div className="space-y-2">
                    {[1, 2, 3].map((i) => (
                      <Skeleton key={i} className="h-20 w-full" />
                    ))}
                  </div>
                ) : !sessions || !Array.isArray(sessions) || sessions.length === 0 ? (
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      No sessions found. Start a new AI profiling session to begin.
                    </AlertDescription>
                  </Alert>
                ) : (
                  <div className="space-y-3">
                    {sessions.map((session) => {
                      // Validate session has required fields
                      if (!session || !session.id) {
                        console.error('Invalid session object:', session);
                        return null;
                      }
                      
                      return (
                        <div
                          key={session.id}
                          className="p-4 rounded-lg border hover:bg-accent/50 transition-colors"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <h4 className="font-medium">{session.file_name || 'Unnamed session'}</h4>
                                <Badge variant={session.status === 'active' ? 'default' : 'secondary'}>
                                  {session.status || 'unknown'}
                                </Badge>
                              </div>
                              <p className="text-sm text-muted-foreground mt-1">
                                Created: {session.created_at ? formatDate(session.created_at) : 'Unknown date'}
                              </p>
                              {(() => {
                                // Handle profile_summary rendering in a separate function to avoid React Error #31
                                // Never render an object directly in JSX
                                let summaryText = 'Profile summary available';
                                
                                if (!session.profile_summary) {
                                  return (
                                    <p className="text-sm mt-2 text-muted-foreground italic">
                                      No profile summary available
                                    </p>
                                  );
                                }
                                
                                if (typeof session.profile_summary === 'string') {
                                  summaryText = session.profile_summary;
                                } else if (typeof session.profile_summary === 'object') {
                                  if (session.profile_summary === null) {
                                    summaryText = 'No profile summary';
                                  } else if (session.profile_summary.text && typeof session.profile_summary.text === 'string') {
                                    summaryText = session.profile_summary.text;
                                  } else {
                                    try {
                                      summaryText = 'Summary: ' + JSON.stringify(session.profile_summary).substring(0, 100) + '...';
                                    } catch (e) {
                                      summaryText = 'Summary data available';
                                    }
                                  }
                                }
                                
                                return (
                                  <p className="text-sm mt-2 line-clamp-2">{summaryText}</p>
                                );
                              })()}
                            </div>
                            <div className="flex items-center gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => resumeSession(session.id)}
                              >
                                <ChevronRight className="h-4 w-4 mr-1" />
                                Resume
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setSessionToDelete(session.id)
                                  setShowDeleteDialog(true)
                                }}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Profile List Tab */}
          <TabsContent value="profile-list" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Profile List</CardTitle>
                <CardDescription>
                  View and manage data profiles for your datasets.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-2">
                    <div className="flex items-center">
                      <Search className="h-4 w-4 text-muted-foreground absolute ml-2" />
                      <Input
                        type="text"
                        placeholder="Search profiles..."
                        className="max-w-sm pl-8"
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                          // Pass the search query to the ProfileList component
                          const profileListComponent = document.getElementById('profile-list-component') as any;
                          if (profileListComponent && profileListComponent.setSearchQuery) {
                            profileListComponent.setSearchQuery(e.target.value);
                          }
                        }}
                      />
                    </div>
                    <Button 
                      type="submit" 
                      variant="outline" 
                      size="icon"
                      onClick={() => {
                        // Trigger search in the ProfileList component
                        const profileListComponent = document.getElementById('profile-list-component') as any;
                        if (profileListComponent && profileListComponent.handleSearch) {
                          profileListComponent.handleSearch();
                        }
                      }}
                      title="Search profiles"
                    >
                      <Search className="h-4 w-4" />
                    </Button>
                  </div>
                  <Button 
                    variant="outline" 
                    size="icon"
                    onClick={() => {
                      // Trigger refresh in the ProfileList component
                      const profileListComponent = document.getElementById('profile-list-component') as any;
                      if (profileListComponent && profileListComponent.fetchProfiles) {
                        profileListComponent.fetchProfiles(true);
                      }
                    }}
                    title="Refresh profiles"
                  >
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                </div>
                <ProfileList 
                  onProfileSelect={(profileId) => {
                    setProfileListSelectedId(profileId);
                    setActiveTab("profile-details");
                  }} 
                  selectedProfileId={profileListSelectedId}
                />
              </CardContent>
            </Card>
          </TabsContent>

          {/* Profile Details Tab */}
          <TabsContent value="profile-details" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Profile Details</CardTitle>
                <CardDescription>
                  Detailed information about the selected profile.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {profileListSelectedId ? (
                  <ProfileDetails profileId={profileListSelectedId} />
                ) : (
                  <div className="flex justify-center items-center h-64 text-muted-foreground">
                    Select a profile from the list to view details
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="session" className="h-[calc(100vh-16rem)]">
            {activeSessionId && (
              <ProfileSession 
                sessionId={activeSessionId}
                onClose={() => {
                  setActiveSessionId(null)
                  setActiveTab('new')
                }}
              />
            )}
          </TabsContent>

          <TabsContent value="plan" className="h-[calc(100vh-16rem)]">
            {activePlanId && (
              <TransformationPlan 
                sessionId={activePlanId}
                onClose={() => {
                  setActivePlanId(null)
                  setActiveTab('new')
                }}
              />
            )}
          </TabsContent>
        </Tabs>

        {/* Delete Session Dialog */}
        <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete Session</DialogTitle>
              <DialogDescription>
                Are you sure you want to delete this session? This action cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
                Cancel
              </Button>
              <Button variant="destructive" onClick={deleteSession}>
                Delete
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </DataPuurLayout>
  )
}
