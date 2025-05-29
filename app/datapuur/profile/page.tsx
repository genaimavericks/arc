"use client"

import { useEffect, useState, Suspense } from "react"
import dynamic from "next/dynamic"
import { useRouter, useSearchParams } from "next/navigation"
import { DataPuurLayout } from "@/components/datapuur/datapuur-layout"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { RefreshCw, Search } from "lucide-react"
import { useToast } from "@/components/ui/use-toast"
import LoadingSpinner from "@/components/loading-spinner"

// Use dynamic imports to avoid SSR issues
const ProfileList = dynamic(() => import("@/components/datapuur/profile/profile-list"), { ssr: false })
const ProfileDetails = dynamic(() => import("@/components/datapuur/profile/profile-details"), { ssr: false })

// Separate component to handle search params
function ProfilePageContent() {
  const [loading, setLoading] = useState(true)
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [activeTab, setActiveTab] = useState<string>("list")
  const router = useRouter()
  const searchParams = useSearchParams()
  const { toast } = useToast()
  const fileId = searchParams.get("fileId")
  const initialTab = searchParams.get("activeTab")

  useEffect(() => {
    // If fileId is provided in URL, we'll load the latest profile for that file
    const fetchLatestProfileForFile = async () => {
      if (!fileId) {
        setLoading(false)
        return
      }
      
      try {
        const token = localStorage.getItem("token")
        if (!token) {
          toast({
            title: "Authentication Error",
            description: "You must be logged in to view profiles",
            variant: "destructive",
          })
          router.push("/login")
          return
        }

        const response = await fetch(`/api/profiler/profiles/file/${fileId}`, {
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
          router.push("/login")
          return
        }

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const data = await response.json()
        setSelectedProfileId(data.id)
      } catch (error) {
        console.error("Error fetching profile for file:", error)
        toast({
          title: "Error",
          description: "Failed to fetch profile for the specified file",
          variant: "destructive",
        })
      } finally {
        setLoading(false)
      }
    }

    fetchLatestProfileForFile()
  }, [fileId, router, toast])

  useEffect(() => {
    // Set initial active tab from URL if provided
    if (initialTab && (initialTab === "list" || initialTab === "details")) {
      setActiveTab(initialTab)
    }
  }, [initialTab])

  const handleRefresh = () => {
    setIsRefreshing(true)
    // Force reload the current page
    router.refresh()
    setTimeout(() => setIsRefreshing(false), 1000)
  }

  const handleProfileSelect = (profileId: string) => {
    setSelectedProfileId(profileId)
    setActiveTab("details") // Switch to details tab when a profile is selected
  }

  return (
    <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold tracking-tight">Profiles</h2>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {loading ? (
          <div className="flex justify-center items-center h-64">
            <LoadingSpinner />
          </div>
        ) : (
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <div className="flex items-center justify-between mb-4">
              <TabsList className="grid w-auto grid-cols-2">
                <TabsTrigger value="list">Profile List</TabsTrigger>
                <TabsTrigger value="details" disabled={!selectedProfileId}>Profile Details</TabsTrigger>
              </TabsList>
              
              {activeTab === "list" && (
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
              )}
            </div>
            
            <TabsContent value="list" className="mt-4">
              <ProfileList 
                onProfileSelect={handleProfileSelect} 
                selectedProfileId={selectedProfileId}
                fileIdFilter={fileId || undefined}
              />
            </TabsContent>
            
            <TabsContent value="details" className="mt-4">
              {selectedProfileId ? (
                // @ts-ignore - Ignore TypeScript error for dynamic component
                <ProfileDetails profileId={selectedProfileId} />
              ) : (
                <div className="flex justify-center items-center h-64 text-muted-foreground">
                  Select a profile from the list to view details
                </div>
              )}
            </TabsContent>
          </Tabs>
        )}
      </div>
    </div>
  )
}

export default function DataProfilePage() {
  return (
    <DataPuurLayout>
      <Suspense fallback={<div className="flex justify-center items-center h-64"><LoadingSpinner /></div>}>
        <ProfilePageContent />
      </Suspense>
    </DataPuurLayout>
  )
}
