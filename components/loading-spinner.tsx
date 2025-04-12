"use client"

import { motion } from "framer-motion"

interface LoadingSpinnerProps {
  size?: "default" | "sm";
  text?: string;
  hideText?: boolean;
}

export default function LoadingSpinner({ 
  size = "default", 
  text = "Loading data...",
  hideText = false 
}: LoadingSpinnerProps) {
  const spinnerSize = size === "sm" ? "w-8 h-8 border-2" : "w-16 h-16 border-4"
  const textSize = size === "sm" ? "text-sm mt-2" : "mt-4"
  
  return (
    <div className="flex flex-col items-center justify-center">
      <motion.div
        className={`${spinnerSize} border-primary border-t-transparent rounded-full shadow-[0_0_15px_rgba(26,35,126,0.3)]`}
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
      />
      {!hideText && text && (
        <p className={`${textSize} text-foreground`}>{text}</p>
      )}
    </div>
  )
}
