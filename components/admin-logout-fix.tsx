"use client"

import { useAuth } from "@/lib/auth-context"
import { useRouter } from "next/navigation"
import { handleAuthFailure } from "@/lib/auth-utils"

// This is a utility component to ensure proper logout behavior
export function useAdminLogout() {
  const { logout: authLogout } = useAuth()
  const router = useRouter()

  const logout = () => {
    // Use the centralized auth failure handler which will:
    // 1. Clear tokens from localStorage
    // 2. Set the authExpired flag in sessionStorage
    // 3. Redirect to the login page
    handleAuthFailure()
    
    // Then call the original logout (which will also clear user state)
    setTimeout(() => {
      authLogout()
    }, 100)
  }

  return logout
}

