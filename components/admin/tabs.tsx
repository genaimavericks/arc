import { motion, AnimatePresence } from "framer-motion"
import LoadingSpinner from "@/components/loading-spinner"
import { DashboardTab } from "@/components/admin/tabs/dashboard-tab"
import { UsersTab } from "@/components/admin/tabs/users-tab"
import { ActivityTab } from "@/components/admin/tabs/activity-tab"
import { PermissionsTab } from "@/components/admin/tabs/permissions-tab"
import { SettingsTab } from "@/components/admin/tabs/settings-tab"
import { JobControlTab } from "@/components/admin/tabs/job-control-tab"

interface AdminTabsProps {
  activeTab: string
  loading: boolean
  error: string | null
  onTabChange?: (tab: string) => void
}

export function AdminTabs({ activeTab, loading, error, onTabChange }: AdminTabsProps) {
  // Animation variants
  const fadeIn = {
    hidden: { opacity: 0, y: 20 },
    visible: { 
      opacity: 1, 
      y: 0,
      transition: {
        duration: 0.4,
        ease: "easeOut"
      }
    },
    exit: { 
      opacity: 0, 
      y: -20,
      transition: {
        duration: 0.2,
        ease: "easeIn"
      }
    }
  }

  if (loading) {
    return (
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex justify-center py-12"
      >
        <motion.div
          animate={{ 
            scale: [1, 1.05, 1],
            rotate: [0, 5, 0, -5, 0],
          }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        >
          <LoadingSpinner />
        </motion.div>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
    >
      <AnimatePresence mode="wait">
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
            className="bg-yellow-500/20 border border-yellow-500 text-yellow-700 dark:text-yellow-200 px-4 py-2 rounded-md mb-4"
          >
            <p>{error}</p>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence mode="wait">
        {activeTab === "dashboard" && (
          <motion.div
            key="dashboard"
            variants={fadeIn}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <DashboardTab onTabChange={onTabChange} />
          </motion.div>
        )}
        
        {activeTab === "users" && (
          <motion.div
            key="users"
            variants={fadeIn}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <UsersTab />
          </motion.div>
        )}
        
        {activeTab === "activity" && (
          <motion.div
            key="activity"
            variants={fadeIn}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <ActivityTab />
          </motion.div>
        )}
        
        {activeTab === "permissions" && (
          <motion.div
            key="permissions"
            variants={fadeIn}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <PermissionsTab />
          </motion.div>
        )}
        
        {activeTab === "settings" && (
          <motion.div
            key="settings"
            variants={fadeIn}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <SettingsTab />
          </motion.div>
        )}
        
        {activeTab === "jobs" && (
          <motion.div
            key="jobs"
            variants={fadeIn}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <JobControlTab />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
