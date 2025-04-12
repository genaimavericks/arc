"use client"

import { useAdminStore } from "@/lib/admin/store"
import { motion, MotionConfig } from "framer-motion"
import { Users, Activity, Zap, ChevronRight } from "lucide-react"

interface DashboardTabProps {
  onTabChange?: (tab: string) => void;
}

export function DashboardTab({ onTabChange }: DashboardTabProps) {
  const { stats, activity } = useAdminStore()

  // Animation variants
  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.2,
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

  const pulseEffect = {
    initial: { scale: 1 },
    hover: {
      scale: 1.02,
      boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)",
      transition: {
        duration: 0.3,
      },
    },
    tap: {
      scale: 0.98,
    }
  };

  // Add a check for stats being null or undefined
  if (!stats) {
    return (
      <MotionConfig>
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="space-y-6"
        >
          <motion.h2 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="card-title mb-4"
          >
            System Overview
          </motion.h2>
          
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ 
              opacity: 1,
              transition: { delay: 0.2 }
            }}
            className="bg-card/80 backdrop-blur-sm p-6 rounded-lg border border-border"
          >
            <motion.div 
              animate={{ 
                opacity: [0.5, 1, 0.5],
              }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            >
              <p className="body-text">Loading system statistics...</p>
            </motion.div>
          </motion.div>
        </motion.div>
      </MotionConfig>
    )
  }

  return (
    <MotionConfig>
      <motion.div variants={container} initial="hidden" animate="show" className="space-y-8">
        <motion.div variants={item} className="flex items-center justify-between">
          <h2 className="card-title">System Overview</h2>
          
          <motion.div 
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="px-3 py-1.5 rounded-full bg-primary/10 text-primary text-sm font-medium flex items-center cursor-pointer"
          >
            <Zap className="h-3.5 w-3.5 mr-1.5" />
            <span>Refresh Data</span>
          </motion.div>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <motion.div
            variants={item}
            whileHover="hover"
            whileTap="tap"
            initial="initial"
            className="bg-card/80 backdrop-blur-sm p-6 rounded-lg border border-border shadow-md transition-all duration-300 overflow-hidden relative group"
          >
            <motion.div 
              className="absolute -right-12 -top-12 w-24 h-24 rounded-full bg-primary/5"
              animate={{
                scale: [1, 1.2, 1],
              }}
              transition={{
                duration: 4,
                repeat: Infinity,
                ease: "easeInOut",
              }}
            />
            
            <h3 className="card-title mb-4 flex items-center">
              <motion.div
                whileHover={{ rotate: 15 }}
                transition={{ type: "spring", stiffness: 300 }}
                className="bg-primary/10 p-2 rounded-md mr-3 flex items-center justify-center"
              >
                <Users className="h-5 w-5 text-primary" />
              </motion.div>
              User Statistics
            </h3>
            
            <div className="space-y-3 relative z-10">
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground body-text">Total Users:</span>
                <motion.span 
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="body-text font-medium"
                >
                  {stats?.total_users || 0}
                </motion.span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground body-text">Active Users:</span>
                <motion.span 
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                  className="body-text font-medium"
                >
                  {stats?.active_users || 0}
                </motion.span>
              </div>
              <motion.div 
                initial={{ scaleX: 0 }}
                animate={{ scaleX: 1 }}
                transition={{ delay: 0.5, duration: 0.5 }}
                className="h-0.5 w-full bg-gradient-to-r from-primary/50 to-transparent mt-2"
              />
            </div>
            
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
              className="flex items-center text-primary helper-text font-medium mt-4 cursor-pointer group"
              onClick={() => onTabChange && onTabChange("users")}
            >
              <span>View all users</span>
              <motion.div
                initial={{ x: 0 }}
                animate={{ x: 0 }}
                whileHover={{ x: 3 }}
                transition={{ duration: 0.2 }}
              >
                <ChevronRight className="h-3.5 w-3.5 ml-1" />
              </motion.div>
            </motion.div>
          </motion.div>

          <motion.div
            variants={item}
            whileHover="hover"
            whileTap="tap"
            initial="initial"
            className="bg-card/80 backdrop-blur-sm p-6 rounded-lg border border-border shadow-md transition-all duration-300 overflow-hidden relative group md:col-span-2"
          >
            <motion.div 
              className="absolute -right-16 -top-16 w-32 h-32 rounded-full bg-primary/5"
              animate={{
                scale: [1, 1.2, 1],
              }}
              transition={{
                duration: 5,
                repeat: Infinity,
                ease: "easeInOut",
              }}
            />
            
            <h3 className="card-title mb-4 flex items-center">
              <motion.div
                whileHover={{ rotate: 15 }}
                transition={{ type: "spring", stiffness: 300 }}
                className="bg-primary/10 p-2 rounded-md mr-3 flex items-center justify-center"
              >
                <Activity className="h-5 w-5 text-primary" />
              </motion.div>
              Recent Activity
            </h3>
            
            {activity && activity.length > 0 ? (
              <div className="space-y-4 relative z-10">
                {activity.slice(0, 3).map((item, index) => (
                  <motion.div 
                    key={index}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 + (index * 0.1) }}
                    className="flex items-start"
                  >
                    <div className={`w-2 h-2 rounded-full mt-1.5 mr-3 ${
                      item.type === 'login' ? 'bg-green-500' : 
                      item.type === 'data_update' ? 'bg-blue-500' : 
                      item.type === 'settings_change' ? 'bg-yellow-500' : 
                      'bg-primary'
                    }`} />
                    <div className="flex-1">
                      <p className="body-text">
                        {item.description}
                      </p>
                      <p className="helper-text text-muted-foreground">
                        {new Date(item.timestamp).toLocaleString()}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </div>
            ) : (
              <p className="description text-center py-4">No recent activity to display</p>
            )}
              
            <motion.div 
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={{ delay: 0.5, duration: 0.5 }}
              className="h-0.5 w-full bg-gradient-to-r from-primary/50 to-transparent mt-2"
            />
            
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
              className="flex items-center text-primary helper-text font-medium mt-4 cursor-pointer group"
              onClick={() => onTabChange && onTabChange("activity")}
            >
              <span>View all activity</span>
              <motion.div
                initial={{ x: 0 }}
                animate={{ x: 0 }}
                whileHover={{ x: 3 }}
                transition={{ duration: 0.2 }}
              >
                <ChevronRight className="h-3.5 w-3.5 ml-1" />
              </motion.div>
            </motion.div>
          </motion.div>
        </div>
      </motion.div>
    </MotionConfig>
  )
}
