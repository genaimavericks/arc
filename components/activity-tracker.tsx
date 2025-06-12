"use client"

import { useEffect } from "react"
import { usePathname } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import { getApiBaseUrl } from "@/lib/config"
import { fetchWithAuth } from "@/lib/auth-utils"

export function ActivityTracker() {
  const pathname = usePathname()
  const { user } = useAuth()

  useEffect(() => {
    // Only track if user is logged in
    if (!user) return

    const logPageVisit = async () => {
      try {
        // Use fetchWithAuth for proper token expiration handling
        await fetchWithAuth("/api/admin/activity/log", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            action: "Page visit",
            details: `Visited ${pathname}`,
            page_url: pathname,
            username: user.username, // Explicitly include username
          }),
        })
      } catch (error) {
        // Silent fail - don't interrupt user experience for logging
        console.error("Failed to log page visit:", error)
      }
    }

    // Add a small delay to avoid too many logs during rapid navigation
    const timeoutId = setTimeout(() => {
      logPageVisit()
    }, 300)

    return () => clearTimeout(timeoutId)
  }, [pathname, user])

  // This is a utility component that doesn't render anything
  return null
}
