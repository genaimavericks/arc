"use client"

import { useState, useEffect } from "react"
import { X, XCircle, CheckCircle, Clock, RefreshCw, ChevronUp, ChevronDown, Activity, Loader2 } from "lucide-react"
import { useKGInsightsJobs } from "@/lib/kginsights-job-context"
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { formatDistanceToNow } from "date-fns"
import { motion, AnimatePresence } from "framer-motion"
import { createPortal } from "react-dom"

export default function FloatingKGJobCard() {
  const { 
    jobs, 
    isLoading, 
    refreshJobs, 
    cancelJob,
    clearCompletedJobs
  } = useKGInsightsJobs()
  
  const [minimized, setMinimized] = useState(() => {
    // Try to retrieve minimized state from localStorage
    try {
      const storedState = localStorage.getItem('kgJobCardMinimized')
      return storedState ? JSON.parse(storedState) : true
    } catch (error) {
      return true
    }
  })
  const [visible, setVisible] = useState(false)
  const [showCardTimeout, setShowCardTimeout] = useState<NodeJS.Timeout | null>(null)
  const [userDismissed, setUserDismissed] = useState(false)
  const [lastRefreshTime, setLastRefreshTime] = useState(Date.now())
  const [activeTab, setActiveTab] = useState("active")
  const [cancellingJobs, setCancellingJobs] = useState<string[]>([])
  const [mounted, setMounted] = useState(false)

  // Initialize mounted state for portal
  useEffect(() => {
    setMounted(true)
    
    // Add a global click handler to detect clicks on menu items
    const handleGlobalClick = (e: MouseEvent) => {
      // Check if the click is on a menu item or navigation element
      const target = e.target as HTMLElement;
      const isMenuOrNavElement = 
        target.closest('nav') || 
        target.closest('a') || 
        target.closest('button[role="menuitem"]') ||
        target.closest('[data-menu-item]') ||
        target.closest('[role="menu"]') ||
        target.closest('[role="menubar"]') ||
        target.closest('[role="navigation"]') ||
        target.closest('.sidebar') ||
        target.closest('.navbar');
      
      // If clicking on a menu item, ensure the card doesn't interfere
      if (isMenuOrNavElement && visible) {
        // Immediately hide the card when interacting with menus
        setVisible(false);
        setUserDismissed(true);
      }
    };
    
    // Add the global click handler with capture to ensure it runs before other handlers
    document.addEventListener('click', handleGlobalClick, { capture: true });
    
    return () => {
      setMounted(false);
      // Remove the global click handler
      document.removeEventListener('click', handleGlobalClick, { capture: true });
    }
  }, [visible])

  // Save minimized state to localStorage when it changes
  useEffect(() => {
    try {
      localStorage.setItem('kgJobCardMinimized', JSON.stringify(minimized))
    } catch (error) {
      console.error('Error saving minimized state to localStorage:', error)
    }
  }, [minimized])

  const activeJobs = jobs.filter(job => job.status === "pending" || job.status === "running")
  const completedJobs = jobs.filter(job => job.status === "completed")
  const failedJobs = jobs.filter(job => job.status === "failed" || job.status === "cancelled")
  
  // Handle visibility based on jobs
  useEffect(() => {
    // If a new job starts, make the card visible again
    if (activeJobs.length > 0) {
      setVisible(true);
      setMinimized(false); // Expand when active jobs are present
      setUserDismissed(false); // Reset dismissed state when new jobs appear
      
      if (showCardTimeout) {
        clearTimeout(showCardTimeout);
        setShowCardTimeout(null);
      }
    } else if ((completedJobs.length > 0 || failedJobs.length > 0) && !userDismissed) {
      setVisible(true);
      
      // Instead of hiding the card after timeout, minimize it
      if (showCardTimeout) {
        clearTimeout(showCardTimeout);
      }
      
      const timeout = setTimeout(() => {
        // After a job completes, minimize the card
        setMinimized(true);
        
        // Then hide it completely after another delay
        const hideTimeout = setTimeout(() => {
          setVisible(false);
        }, 5000);
        
        return () => clearTimeout(hideTimeout);
      }, 3000);
      
      setShowCardTimeout(timeout);
    } else if (!userDismissed) {
      // Only hide if not explicitly dismissed by user and no jobs
      setVisible(false);
    }
    
    return () => {
      if (showCardTimeout) {
        clearTimeout(showCardTimeout);
      }
    };
  }, [jobs, activeJobs.length, completedJobs.length, failedJobs.length, userDismissed, showCardTimeout]);

  // Force refresh jobs periodically when there are active jobs, but with reduced frequency
  useEffect(() => {
    if (activeJobs.length > 0) {
      const refreshTimer = setInterval(() => {
        const currentTime = Date.now();
        if (currentTime - lastRefreshTime >= 3000) {
          refreshJobs();
          setLastRefreshTime(currentTime);
        }
      }, 3000);
      
      return () => {
        clearInterval(refreshTimer);
      };
    }
  }, [activeJobs.length, refreshJobs, lastRefreshTime]);

  // Handle job status icons and colors
  const getStatusBadge = (status: string) => {
    switch (status) {
      case "pending":
        return (
          <Badge variant="outline" className="bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/20 flex items-center gap-1">
            <Clock className="h-3 w-3" />
            Pending
          </Badge>
        )
      case "running":
        return (
          <Badge variant="outline" className="bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20 flex items-center gap-1">
            <Loader2 className="h-3 w-3 animate-spin" />
            Running
          </Badge>
        )
      case "completed":
        return (
          <Badge variant="outline" className="bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20 flex items-center gap-1">
            <CheckCircle className="h-3 w-3" />
            Completed
          </Badge>
        )
      case "failed":
        return (
          <Badge variant="outline" className="bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20 flex items-center gap-1">
            <XCircle className="h-3 w-3" />
            Failed
          </Badge>
        )
      case "cancelled":
        return (
          <Badge variant="outline" className="bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20 flex items-center gap-1">
            <XCircle className="h-3 w-3" />
            Cancelled
          </Badge>
        )
      case "cancelling":
        return (
          <Badge variant="outline" className="bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20 flex items-center gap-1">
            <Loader2 className="h-3 w-3 animate-spin" />
            Cancelling
          </Badge>
        )
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  // Format job type for display
  const formatJobType = (type: string) => {
    switch (type) {
      case "load_data":
        return "Load Data"
      case "clean_data":
        return "Clean Data"
      default:
        return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
    }
  }

  // Get the time ago from a timestamp
  const getTimeAgo = (timestamp: string) => {
    try {
      return formatDistanceToNow(new Date(timestamp), { addSuffix: true })
    } catch (err) {
      return "unknown time"
    }
  }
  
  // Handle user dismissing the card
  const handleDismiss = (e: React.MouseEvent) => {
    // Prevent the event from propagating to parent elements
    e.preventDefault();
    e.stopPropagation();
    
    // Immediately hide the card regardless of minimized state
    // This ensures a single click is sufficient to dismiss the card
    setVisible(false);
    setUserDismissed(true);
  }

  // Handle cancelling a job with visual feedback
  const handleCancelJob = async (jobId: string, e: React.MouseEvent) => {
    // Prevent the event from propagating
    e.preventDefault();
    e.stopPropagation();
    
    // Add job to cancelling list
    setCancellingJobs(prev => [...prev, jobId]);
    
    try {
      // Call the cancelJob function
      await cancelJob(jobId);
    } finally {
      // Remove job from cancelling list after a short delay for UI feedback
      setTimeout(() => {
        setCancellingJobs(prev => prev.filter(id => id !== jobId));
      }, 1000);
    }
  }

  if (!visible) {
    if (activeJobs.length > 0 && userDismissed) {
      const notificationBubble = (
        <div className="fixed bottom-4 right-4 z-10 pointer-events-auto">
          <div 
            className="bg-blue-500 dark:bg-blue-700 text-white rounded-full p-2 shadow-lg cursor-pointer flex items-center gap-2"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setUserDismissed(false);
              setVisible(true);
              setMinimized(false);
            }}
          >
            <RefreshCw className="h-4 w-4 animate-spin" />
            <span className="font-medium">{activeJobs.length} active</span>
          </div>
        </div>
      );
      
      return mounted ? createPortal(notificationBubble, document.body) : null;
    }
    return null;
  }

  // Minimized view that shows just a summary
  if (minimized) {
    const minimizedView = (
      <div className="fixed bottom-4 right-4 z-10 pointer-events-auto">
        <div className="bg-card dark:bg-gray-900 border border-border dark:border-gray-700 rounded-lg shadow-lg p-2 flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" />
          <span className="font-medium text-sm text-foreground dark:text-gray-200">
            KG Jobs: {activeJobs.length > 0 ? `${activeJobs.length} active` : (completedJobs.length + failedJobs.length > 0 ? `${completedJobs.length + failedJobs.length} completed` : 'None')}
          </span>
          <div className="flex items-center gap-1 ml-2">
            <div className="flex rounded-md border border-border dark:border-gray-700 overflow-hidden">
              <Button 
                variant="ghost" 
                size="sm"
                className="h-7 rounded-none border-r border-border dark:border-gray-700 px-2 text-foreground dark:text-gray-200 hover:bg-accent dark:hover:bg-gray-700" 
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setMinimized(false);
                }}
                title="Expand"
              >
                <ChevronUp className="h-4 w-4" />
              </Button>
              <Button 
                variant="ghost" 
                size="sm"
                className="h-7 rounded-none px-2 text-foreground dark:text-gray-200 hover:bg-accent dark:hover:bg-gray-700" 
                onClick={(e) => handleDismiss(e)}
                title="Close"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
    
    return mounted ? createPortal(minimizedView, document.body) : null;
  }

  return mounted ? createPortal(
    <div className="fixed bottom-4 right-4 z-10 w-96 max-w-[calc(100vw-2rem)] pointer-events-none">
      <Card className="shadow-lg border overflow-hidden bg-card/95 backdrop-blur-sm dark:bg-gray-900/95 dark:border-gray-700 pointer-events-auto">
        <CardHeader className="py-2 px-4 border-b border-border dark:border-gray-700 flex flex-row items-center justify-between space-y-0">
          <CardTitle className="font-medium text-sm flex gap-2 items-center text-foreground dark:text-gray-100">
            <Activity className="h-4 w-4 text-primary" />
            KG Processing Jobs {activeJobs.length > 0 ? `(${activeJobs.length} active)` : ''}
          </CardTitle>
          <div className="flex items-center space-x-2">
            <Button 
              variant="ghost" 
              size="sm"
              className="h-7 px-2 text-xs text-foreground dark:text-gray-200 hover:bg-accent dark:hover:bg-gray-700 flex items-center gap-1" 
              onClick={(e) => {
                e.preventDefault();
                refreshJobs();
                setLastRefreshTime(Date.now());
              }}
              disabled={isLoading}
              title="Refresh"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin text-primary' : ''}`} />
              Refresh
            </Button>
            <div className="flex rounded-md border border-border dark:border-gray-700 overflow-hidden">
              <Button 
                variant="ghost" 
                size="sm"
                className="h-7 rounded-none border-r border-border dark:border-gray-700 px-2 text-foreground dark:text-gray-200 hover:bg-accent dark:hover:bg-gray-700" 
                onClick={(e) => {
                  e.preventDefault();
                  setMinimized(true);
                }}
                title="Minimize"
              >
                <ChevronDown className="h-4 w-4" />
              </Button>
              <Button 
                variant="ghost" 
                size="sm"
                className="h-7 rounded-none px-2 text-foreground dark:text-gray-200 hover:bg-accent dark:hover:bg-gray-700" 
                onClick={(e) => handleDismiss(e)}
                title="Close"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        
        <CardContent className="p-3 max-h-80 overflow-y-auto">
          {/* Tabs for job types */}
          <div className="flex border-b border-border dark:border-gray-700 mb-3">
            <button
              className={`px-3 py-1.5 text-sm font-medium ${activeTab === "active" ? "border-b-2 border-primary text-primary" : "text-muted-foreground"}`}
              onClick={(e) => {
                e.preventDefault();
                setActiveTab("active");
              }}
              type="button"
            >
              Active ({activeJobs.length})
            </button>
            <button
              className={`px-3 py-1.5 text-sm font-medium ${activeTab === "completed" ? "border-b-2 border-primary text-primary" : "text-muted-foreground"}`}
              onClick={(e) => {
                e.preventDefault();
                setActiveTab("completed");
              }}
              type="button"
            >
              Completed ({completedJobs.length})
            </button>
            <button
              className={`px-3 py-1.5 text-sm font-medium ${activeTab === "failed" ? "border-b-2 border-primary text-primary" : "text-muted-foreground"}`}
              onClick={(e) => {
                e.preventDefault();
                setActiveTab("failed");
              }}
              type="button"
            >
              Failed ({failedJobs.length})
            </button>
          </div>
          
          {/* Active Jobs Tab Content */}
          {activeTab === "active" && (
            <div className="space-y-3">
              {activeJobs.length === 0 ? (
                <div className="text-center py-4 text-muted-foreground text-sm">
                  No active jobs
                </div>
              ) : (
                activeJobs.map(job => (
                  <motion.div
                    key={job.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="relative bg-card dark:bg-gray-800 border border-border dark:border-gray-700 rounded-lg p-3 overflow-hidden"
                  >
                    {/* Progress bar background for running jobs */}
                    {job.status === "running" && (
                      <div 
                        className="absolute inset-0 bg-blue-500/5 dark:bg-blue-500/10 z-0"
                        style={{ 
                          width: `${job.progress}%`,
                          transition: 'width 0.5s ease-in-out'
                        }}
                      />
                    )}
                    
                    {/* Job content */}
                    <div className="relative z-10">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <h4 className="font-medium text-foreground dark:text-gray-200 text-sm">
                            {formatJobType(job.job_type)} - Schema #{job.schema_id}
                          </h4>
                          <p className="text-xs text-muted-foreground dark:text-gray-400 break-words max-w-[220px]">
                            {job.message || 'Processing...'}
                          </p>
                        </div>
                        <div className="flex flex-col items-end space-y-1">
                          {getStatusBadge(job.status)}
                          <span className="text-xs text-muted-foreground dark:text-gray-400">
                            {getTimeAgo(job.created_at)}
                          </span>
                        </div>
                      </div>
                      
                      {/* Progress indicator for running jobs */}
                      {job.status === "running" && (
                        <div className="mt-2">
                          <div className="flex justify-between text-xs mb-1">
                            <span className="text-muted-foreground dark:text-gray-400">Progress</span>
                            <span className="text-foreground dark:text-gray-300 font-medium">{job.progress || 0}%</span>
                          </div>
                          <Progress value={job.progress || 0} className="h-1.5 dark:bg-gray-700" />
                        </div>
                      )}
                      
                      {/* Error message for failed jobs */}
                      {job.error && (
                        <p className="text-xs text-red-600 dark:text-red-400 mt-1 bg-red-50 dark:bg-red-900/20 p-1.5 rounded border border-red-100 dark:border-red-900/30">
                          Error: {job.error}
                        </p>
                      )}
                      
                      {/* Action buttons */}
                      {(job.status === "pending" || job.status === "running") && (
                        <div className="flex justify-end mt-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => handleCancelJob(job.id, e)}
                            disabled={cancellingJobs.includes(job.id)}
                            className="h-7 px-2 text-destructive hover:bg-destructive/10 text-xs"
                          >
                            {cancellingJobs.includes(job.id) ? (
                              <>
                                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                Cancelling...
                              </>
                            ) : (
                              "Cancel"
                            )}
                          </Button>
                        </div>
                      )}
                    </div>
                  </motion.div>
                ))
              )}
            </div>
          )}
          
          {/* Completed Jobs Tab Content */}
          {activeTab === "completed" && (
            <div className="space-y-3">
              {completedJobs.length === 0 ? (
                <div className="text-center py-4 text-muted-foreground text-sm">
                  No completed jobs
                </div>
              ) : (
                completedJobs.map(job => (
                  <motion.div
                    key={job.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-card dark:bg-gray-800 border border-border dark:border-gray-700 rounded-lg p-3"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="font-medium text-foreground dark:text-gray-200 text-sm">
                          {formatJobType(job.job_type)} - Schema #{job.schema_id}
                        </h4>
                        <p className="text-xs text-muted-foreground dark:text-gray-400 break-words max-w-[220px]">
                          Completed successfully
                        </p>
                      </div>
                      <div className="flex flex-col items-end">
                        {getStatusBadge(job.status)}
                        <span className="text-xs text-muted-foreground dark:text-gray-400 mt-1">
                          {getTimeAgo(job.updated_at)}
                        </span>
                      </div>
                    </div>
                  </motion.div>
                ))
              )}
            </div>
          )}
          
          {/* Failed Jobs Tab Content */}
          {activeTab === "failed" && (
            <div className="space-y-3">
              {failedJobs.length === 0 ? (
                <div className="text-center py-4 text-muted-foreground text-sm">
                  No failed jobs
                </div>
              ) : (
                failedJobs.map(job => (
                  <motion.div
                    key={job.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-card dark:bg-gray-800 border border-border dark:border-gray-700 rounded-lg p-3"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="font-medium text-foreground dark:text-gray-200 text-sm">
                          {formatJobType(job.job_type)} - Schema #{job.schema_id}
                        </h4>
                        <p className="text-xs text-muted-foreground dark:text-gray-400 break-words max-w-[220px]">
                          {job.error || (job.status === "cancelled" ? "Cancelled by user" : "Failed")}
                        </p>
                      </div>
                      <div className="flex flex-col items-end">
                        {getStatusBadge(job.status)}
                        <span className="text-xs text-muted-foreground dark:text-gray-400 mt-1">
                          {getTimeAgo(job.updated_at)}
                        </span>
                      </div>
                    </div>
                  </motion.div>
                ))
              )}
            </div>
          )}
        </CardContent>
        
        <CardFooter className="p-2 bg-muted/50 dark:bg-gray-800 flex justify-between border-t border-border dark:border-gray-700">
          {jobs.some(job => job.status === "completed" || job.status === "failed" || job.status === "cancelled") && (
            <Button 
              variant="ghost" 
              size="sm"
              className="text-xs text-foreground dark:text-gray-200 hover:bg-accent dark:hover:bg-gray-700"
              onClick={(e) => {
                e.preventDefault();
                clearCompletedJobs();
              }}
            >
              Clear Completed
            </Button>
          )}
          {!jobs.some(job => job.status === "completed" || job.status === "failed" || job.status === "cancelled") && (
            <div></div> // Empty div to maintain flex layout
          )}
          <div className="text-xs text-muted-foreground">
            {activeJobs.length > 0 ? `${activeJobs.length} active job${activeJobs.length > 1 ? 's' : ''}` : ''}
          </div>
        </CardFooter>
      </Card>
    </div>,
    document.body
  ) : null;
}
