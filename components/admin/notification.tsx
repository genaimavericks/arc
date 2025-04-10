"use client"

import { useState, useEffect } from "react"
import { CheckCircle, AlertCircle, X } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"

interface NotificationProps {
  notification: {
    type: "success" | "error"
    message: string
  }
}

export function NotificationDisplay({ notification }: NotificationProps) {
  const [isVisible, setIsVisible] = useState(true)
  const [progress, setProgress] = useState(100)

  // Auto-dismiss after 10 seconds
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false)
    }, 10000)

    // Progress bar animation
    const interval = setInterval(() => {
      setProgress((prev) => {
        const newProgress = prev - 1
        return newProgress <= 0 ? 0 : newProgress
      })
    }, 100)

    return () => {
      clearTimeout(timer)
      clearInterval(interval)
    }
  }, [])

  if (!isVisible) return null

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -20, scale: 0.95 }}
      transition={{ 
        type: "spring",
        stiffness: 500,
        damping: 40
      }}
      className={`mb-4 p-4 rounded-lg flex items-start justify-between backdrop-blur-sm border shadow-md ${
        notification.type === "success"
          ? "bg-primary/10 border-primary text-primary"
          : "bg-destructive/10 border-destructive text-destructive"
      }`}
    >
      <div className="flex items-start">
        <motion.div
          initial={{ rotate: -10, scale: 0.8 }}
          animate={{ rotate: 0, scale: 1 }}
          transition={{ 
            type: "spring", 
            stiffness: 500,
            damping: 20
          }}
          className="mt-0.5"
        >
          {notification.type === "success" ? (
            <motion.div
              animate={{ 
                scale: [1, 1.2, 1],
              }}
              transition={{ 
                duration: 1.5,
                repeat: 1,
                repeatType: "reverse"
              }}
            >
              <CheckCircle className="h-5 w-5 mr-3" />
            </motion.div>
          ) : (
            <motion.div
              animate={{ 
                rotate: [0, 5, 0, -5, 0],
              }}
              transition={{ 
                duration: 1.5,
                repeat: 1,
                repeatType: "reverse"
              }}
            >
              <AlertCircle className="h-5 w-5 mr-3" />
            </motion.div>
          )}
        </motion.div>
        <div>
          <motion.p
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="font-medium"
          >
            {notification.type === "success" ? "Success" : "Alert"}
          </motion.p>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="text-sm opacity-90"
          >
            {notification.message}
          </motion.p>
        </div>
      </div>
      
      <motion.button
        whileHover={{ scale: 1.1, rotate: 90 }}
        whileTap={{ scale: 0.9 }}
        onClick={() => setIsVisible(false)}
        className="text-current opacity-70 hover:opacity-100 transition-opacity p-1 rounded-full hover:bg-card"
      >
        <X className="h-4 w-4" />
      </motion.button>

      {/* Progress bar */}
      <motion.div 
        className={`absolute bottom-0 left-0 h-0.5 ${
          notification.type === "success" ? "bg-primary" : "bg-destructive"
        }`}
        initial={{ width: "100%" }}
        animate={{ width: `${progress}%` }}
        transition={{ duration: 0.1, ease: "linear" }}
      />
    </motion.div>
  )
}
