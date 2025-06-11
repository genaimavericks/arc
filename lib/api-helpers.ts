// Helper functions for API routes in static export mode

/**
 * This helper allows API routes to work in both development mode and static export.
 * In static export mode, the API routes won't process dynamic requests, so we create
 * a mock response with proper headers to indicate the client should redirect to the real API.
 */
export function createStaticApiHandler(mockResponse: any = null) {
  return {
    GET: async () => {
      // Create a default response for static export builds
      return Response.json(mockResponse || { 
        message: "This is a static API route. In production, this would be served by your actual API server." 
      }, { 
        headers: {
          'X-Static-Export': 'true',
          'Access-Control-Allow-Origin': '*',
          'Content-Type': 'application/json',
        } 
      });
    },
    POST: async () => {
      // Create a default response for static export builds
      return Response.json({ 
        message: "This is a static API route. In production, this would be served by your actual API server." 
      }, { 
        headers: {
          'X-Static-Export': 'true',
          'Access-Control-Allow-Origin': '*',
          'Content-Type': 'application/json',
        } 
      });
    }
  };
}
