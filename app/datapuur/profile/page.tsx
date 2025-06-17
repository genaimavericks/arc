"use client"

import { useEffect } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { DataPuurLayout } from "@/components/datapuur/datapuur-layout"
import LoadingSpinner from "@/components/loading-spinner"

/**
 * Redirect component that sends users from the old Profile page to the new location
 * in the AI Profile Analysis page with the profile-list tab active
 */
function ProfileRedirect() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const fileId = searchParams.get("fileId")
  const activeTab = searchParams.get("activeTab")
  
  useEffect(() => {
    // Construct the redirect URL
    let redirectUrl = "/datapuur/ai-profile?activeTab=profile-list"
    
    // If there's a fileId, pass it along to the new page
    if (fileId) {
      redirectUrl += `&fileId=${fileId}`
    }
    
    // If the user was viewing profile details, redirect to that tab
    if (activeTab === "details" && fileId) {
      redirectUrl = `/datapuur/ai-profile?activeTab=profile-details&fileId=${fileId}`
    }
    
    // Redirect to the new location
    router.replace(redirectUrl)
  }, [router, fileId, activeTab])

  return (
    <div className="flex justify-center items-center h-64">
      <LoadingSpinner />
      <p className="ml-4 text-muted-foreground">Redirecting to AI Profile Analysis...</p>
    </div>
  )
}

export default function DataProfilePage() {
  return (
    <DataPuurLayout>
      <ProfileRedirect />
    </DataPuurLayout>
  )
}
