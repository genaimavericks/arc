"use client"

import { getApiBaseUrl } from "./config"

/**
 * Utility function to handle authenticated API requests with proper token expiration handling
 * This function will automatically redirect to the login page if the token is expired
 */
export async function fetchWithAuth(url: string, options?: RequestInit): Promise<any> {
  const token = localStorage.getItem("token")
  
  if (!token) {
    console.error("Authentication token not found")
    handleAuthFailure()
    throw new Error("Authentication token not found")
  }

  // Ensure URL has the correct format
  const apiUrl = url.startsWith("http") ? url : `${getApiBaseUrl()}${url}`
  
  // Prepare headers with authentication token
  const headers = {
    ...(options?.headers || {}),
    Authorization: `Bearer ${token}`,
  }

  try {
    const response = await fetch(apiUrl, {
      ...options,
      headers,
    })

    // Handle authentication errors (401 Unauthorized)
    if (response.status === 401) {
      console.error("Authentication token expired or invalid")
      handleAuthFailure()
      throw new Error("Authentication failed")
    }

    // Handle other HTTP errors
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    // Parse and return JSON response
    return await response.json()
  } catch (error) {
    console.error("API request failed:", error)
    
    // If it's an authentication error, it's already handled above
    if ((error as Error).message === "Authentication failed") {
      throw error
    }
    
    // For other errors, just propagate them
    throw error
  }
}

/**
 * Handle authentication failure by clearing tokens and redirecting to login
 */
export function handleAuthFailure(): void {
  // Store the current URL to redirect back after login
  const currentPath = window.location.pathname
  if (currentPath !== "/login") {
    localStorage.setItem("loginRedirectUrl", currentPath)
  }
  
  // Clear authentication data
  localStorage.removeItem("token")
  localStorage.removeItem("user")
  
  // Set a flag to indicate we're logging out due to token expiration
  sessionStorage.setItem("authExpired", "true")
  
  // Redirect to login page
  window.location.href = "/login"
}

/**
 * Check if there was an authentication failure on page load
 * This can be used in the login page to show a message
 */
export function checkAuthFailureOnLoad(): boolean {
  const authExpired = sessionStorage.getItem("authExpired")
  if (authExpired) {
    // Clear the flag so it doesn't persist
    sessionStorage.removeItem("authExpired")
    return true
  }
  return false
}
