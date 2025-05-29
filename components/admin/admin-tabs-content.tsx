"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { AdminTabs } from "@/components/admin/tabs"
import { fetchAdminData } from "@/lib/admin/api"
import { useAdminStore } from "@/lib/admin/store"
import LoadingSpinner from "@/components/loading-spinner"

export function AdminTabsContent() {
  const [activeTab, setActiveTab] = useState("dashboard")
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
            data.users.forEach((user: { role?: string }) => {
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
    { id: "dashboard", label: "Dashboard" },
    { id: "users", label: "Users" },
    { id: "activity", label: "Activity Log" },
    { id: "permissions", label: "Permissions" },
    { id: "jobs", label: "Job Control" },
    { id: "settings", label: "Settings" },
  ]

  return (
    <div className="space-y-4">
      <div className="flex overflow-x-auto border-b border-border">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          
          return (
            <button
              key={tab.id}
              className={`relative px-4 py-2 text-sm font-medium transition-all whitespace-nowrap ${
                isActive
                  ? "text-primary border-b-2 border-primary"
                  : "text-muted-foreground hover:text-foreground hover:border-b-2 hover:border-muted-foreground"
              }`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      <div className="p-1">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <LoadingSpinner />
            <p className="mt-4 text-muted-foreground">Loading admin dashboard...</p>
          </div>
        ) : (
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
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
    </div>
  )
}
