/**
 * Central configuration for the RSW application
 * This file provides a consistent way to access configuration values throughout the application
 */

// This will be replaced at runtime with the actual configuration
declare global {
  interface Window {
    __RSW_CONFIG__?: {
      apiBaseUrl?: string;
    };
  }
}

/**
 * Get the base API URL for backend requests
 * Returns the base URL without the /api suffix
 */
export function getApiBaseUrl(): string {
  // For client-side requests
  if (typeof window !== 'undefined') {
    // First check if we have a runtime config (injected by the server)
    if (window.__RSW_CONFIG__?.apiBaseUrl) {
      return window.__RSW_CONFIG__.apiBaseUrl;
    }
    
    // Then check environment variables
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (apiUrl) {
      // If the apiUrl ends with /api, remove it to get the base URL
      if (apiUrl.endsWith('/api')) {
        return apiUrl.substring(0, apiUrl.length - 4);
      }
      return apiUrl;
    }
    
    // Last resort: use the current window location
    return window.location.origin;
  }
  
  // For server-side rendering
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (apiUrl) {
    if (apiUrl.endsWith('/api')) {
      return apiUrl.substring(0, apiUrl.length - 4);
    }
    return apiUrl;
  }
  
  // Default fallback for server-side rendering
  return '';
}

/**
 * Default configuration used throughout the application
 */
export const config = {
  /**
   * The base URL for all API requests (without the /api suffix)
   */
  apiBaseUrl: getApiBaseUrl(),
};

export default config;
