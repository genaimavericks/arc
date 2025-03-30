/**
 * Central configuration for the RSW application
 * This file provides a consistent way to access configuration values throughout the application
 */

/**
 * Get the base API URL for backend requests
 * Returns the base URL without the /api suffix
 */
export function getApiBaseUrl(): string {
  // For client-side requests, use NEXT_PUBLIC_API_URL if available
  if (typeof window !== 'undefined') {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || '/api';
    
    // If the API URL is a relative path, prepend the origin
    if (apiUrl.startsWith('/')) {
      return `${window.location.origin}`;
    }
    
    // If the apiUrl ends with /api, remove it to get the base URL
    if (apiUrl.endsWith('/api')) {
      return apiUrl.substring(0, apiUrl.length - 4);
    }
    
    return apiUrl;
  }
  
  // For server-side rendering, default to base URL
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || '/api';
  if (apiUrl.endsWith('/api')) {
    return apiUrl.substring(0, apiUrl.length - 4);
  }
  return apiUrl;
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
