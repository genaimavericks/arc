"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { motion, AnimatePresence } from "framer-motion"
import { 
  BarChart, Users, Activity, Shield, 
  Settings, ArrowLeft, Bell, LogOut 
} from "lucide-react"
import { useAuth } from "@/lib/auth-context"
import { useAdminLogout } from "@/components/admin-logout-fix"
import { fetchAdminData } from "@/lib/admin/api"
import { AdminTabs } from "@/components/admin/tabs"
import { NotificationDisplay } from "@/components/admin/notification"
import { useAdminStore } from "@/lib/admin/store"
import LoadingSpinner from "@/components/loading-spinner"

export default function AdminDashboard() {
  const { user } = useAuth()
  const logout = useAdminLogout()
  const [activeTab, setActiveTab] = useState("dashboard")
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [isHovering, setIsHovering] = useState<string | null>(null)
  const {
    loading,
    setLoading,
    error,
    setError,
    notification,
    setNotification,
    stats,
    setStats,
    users,
    setUsers,
    activity,
    setActivity,
    systemSettings,
    setSystemSettings,
    addRoleIfNotExists,
  } = useAdminStore()

  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      try {
        const data = await fetchAdminData()

        // Ensure we have valid data before setting state
        if (data) {
          setStats(data.stats || {})
          setUsers(data.users || [])
          setActivity(data.activity || [])
          setSystemSettings(data.systemSettings || {})

          // Ensure all roles from users are in our roles list
          if (data.users && data.users.length > 0) {
            data.users.forEach((user) => {
              if (user.role) {
                addRoleIfNotExists(user.role)
              }
            })
          }
        }

        setError(null)
      } catch (err) {
        console.error("Error fetching admin data:", err)
        setError("Failed to load admin data. Using mock data instead.")
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [])

  useEffect(() => {
    if (notification) {
      const timeoutId = setTimeout(() => {
        setNotification(null)
      }, 30000)

      return () => clearTimeout(timeoutId)
    }
  }, [notification, setNotification])

  const tabs = [
    { id: "dashboard", label: "Dashboard", icon: BarChart },
    { id: "users", label: "Users", icon: Users },
    { id: "activity", label: "Activity Log", icon: Activity },
    { id: "permissions", label: "Permissions", icon: Shield },
    { id: "jobs", label: "Job Control", icon: Activity },
    { id: "settings", label: "Settings", icon: Settings },
  ]

  // Enhanced animation variants
  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        duration: 0.4,
      },
    },
  }

  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { 
      opacity: 1, 
      y: 0,
      transition: {
        type: "spring",
        stiffness: 300,
        damping: 24
      }
    },
  }

  const fadeIn = {
    hidden: { opacity: 0 },
    show: { 
      opacity: 1,
      transition: { duration: 0.4 }
    },
  }

  const glowingBorder = {
    rest: { 
      boxShadow: "0 0 0 rgba(var(--primary), 0)" 
    },
    hover: { 
      boxShadow: "0 0 15px rgba(var(--primary), 0.5)",
      transition: {
        duration: 0.3,
        repeatType: "reverse",
        repeat: Infinity
      }
    }
  }

  return (
    <div className="min-h-screen bg-background antialiased relative overflow-hidden">
      {/* Ambient background with moving particles */}
      <div className="h-full w-full absolute inset-0 z-0">
        <SparklesCore
          id="tsparticlesfullpage"
          background="transparent"
          minSize={0.6}
          maxSize={1.4}
          particleDensity={100}
          className="w-full h-full"
          particleColor="var(--primary)"
        />
      </div>

      <motion.div 
        className="relative z-10 pt-20 px-6 md:px-8"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6 }}
      >
        {/* Back button - aligned with the dashboard content */}
        <div className="max-w-7xl mx-auto relative">
          <motion.div
            initial={{ x: -50, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ duration: 0.4, delay: 0.2 }}
          >
            <Link
              href="/"
              className="absolute -top-12 left-0 z-20 flex items-center justify-center rounded-md bg-card/80 backdrop-blur-sm border border-border hover:bg-accent transition-colors duration-200 px-3 py-2"
              aria-label="Back to home"
            >
              <ArrowLeft className="w-4 h-4 text-foreground mr-2" />
              <span className="body-text">Back to Home</span>
            </Link>
          </motion.div>
        </div>

        <div className="max-w-7xl mx-auto">
          <div className="flex justify-between items-center mb-8 relative">
            <motion.h1
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ 
                duration: 0.6, 
                type: "spring", 
                stiffness: 100 
              }}
              className="page-title text-black"
            >
              Admin Dashboard
            </motion.h1>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="flex items-center relative"
            >
              <motion.div 
                className="relative"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <motion.button
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  className="px-4 py-2 bg-card/80 backdrop-blur-sm rounded-lg border border-border flex items-center gap-2 hover:bg-accent/50 transition-all duration-200"
                  whileHover={{ 
                    backgroundColor: "rgba(var(--primary), 0.1)",
                    borderColor: "var(--primary)"
                  }}
                >
                  <span className="body-text font-medium flex items-center">
                    Welcome, <span className="text-primary font-bold ml-1">{user?.username}</span>
                  </span>
                  <motion.span
                    animate={{ rotate: showUserMenu ? 180 : 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    <Bell className="w-4 h-4 text-primary" />
                  </motion.span>
                </motion.button>
              </motion.div>
            </motion.div>
          </div>

          {/* Notification */}
          <AnimatePresence>
            {notification && (
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
              >
                <NotificationDisplay notification={notification} />
              </motion.div>
            )}
          </AnimatePresence>

          {/* User menu dropdown rendered at the top level for proper z-index */}
          <AnimatePresence>
            {showUserMenu && (
              <motion.div
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 10, scale: 0.95 }}
                transition={{ duration: 0.2 }}
                className="absolute right-0 top-full mt-2 w-48 bg-card/95 backdrop-blur-md border border-border rounded-lg shadow-lg overflow-hidden z-50"
                style={{ 
                  transformOrigin: "top right",
                }}
              >
                <div className="p-2">
                  <button
                    onClick={logout}
                    className="w-full flex items-center gap-2 px-3 py-2 text-left rounded-md hover:bg-primary/10 transition-colors"
                  >
                    <LogOut className="w-4 h-4 text-primary" />
                    <span className="body-text">Logout</span>
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <motion.div
            variants={container}
            initial="hidden"
            animate="show"
            className="bg-card/80 backdrop-blur-sm rounded-lg border border-border overflow-hidden shadow-md"
          >
            <div className="flex border-b border-border overflow-x-auto">
              {tabs.map((tab, index) => {
                const isActive = activeTab === tab.id;
                
                return (
                  <motion.button
                    key={tab.id}
                    variants={item}
                    initial="hidden"
                    animate="show"
                    whileHover={{ scale: isActive ? 1 : 1.05 }}
                    whileTap={{ scale: 0.98 }}
                    className={`relative flex items-center space-x-2 px-6 py-4 text-sm font-medium transition-all whitespace-nowrap overflow-hidden ${
                      isActive
                        ? "text-primary-foreground bg-primary z-10"
                        : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
                    }`}
                    onClick={() => setActiveTab(tab.id)}
                    onMouseEnter={() => setIsHovering(tab.id)}
                    onMouseLeave={() => setIsHovering(null)}
                  >
                    <motion.span 
                      animate={isHovering === tab.id && !isActive ? { scale: 1.2, rotate: 5 } : { scale: 1, rotate: 0 }}
                      transition={{ type: "spring", stiffness: 400, damping: 10 }}
                      className="mr-2"
                    >
                      <tab.icon className={`w-5 h-5 ${isActive ? "text-primary-foreground" : "text-muted-foreground"}`} />
                    </motion.span>
                    <span className="body-text">{tab.label}</span>
                    
                    {isActive && (
                      <motion.div 
                        className="absolute bottom-0 left-0 right-0 h-1 bg-primary-foreground" 
                        layoutId="activeTabIndicator"
                        transition={{ 
                          type: "spring", 
                          stiffness: 300, 
                          damping: 30 
                        }}
                      />
                    )}
                  </motion.button>
                );
              })}
            </div>

            <div className="p-6">
              {loading ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex flex-col items-center justify-center py-12"
                >
                  <motion.div
                    animate={{ 
                      scale: [1, 1.1, 1],
                      rotate: [0, 180, 360],
                    }}
                    transition={{ 
                      duration: 2, 
                      repeat: Infinity,
                      ease: "easeInOut" 
                    }}
                  >
                    <LoadingSpinner />
                  </motion.div>
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.5 }}
                    className="description mt-4"
                  >
                    Loading admin dashboard...
                  </motion.p>
                </motion.div>
              ) : (
                <AnimatePresence mode="wait">
                  <motion.div
                    key={activeTab}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    transition={{ duration: 0.3 }}
                  >
                    <AdminTabs 
                      activeTab={activeTab} 
                      loading={loading} 
                      error={error} 
                      onTabChange={setActiveTab} 
                    />
                  </motion.div>
                </AnimatePresence>
              )}
            </div>
          </motion.div>
        </div>
      </motion.div>
    </div>
  )
}

import { SparklesCore } from "@/components/sparkles"
