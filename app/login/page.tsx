"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { useAuth } from "@/lib/auth-context"
import { SparklesCore } from "@/components/sparkles"
import { motion } from "framer-motion"
import { Lock, Mail, ArrowLeft, X, LogIn } from "lucide-react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useRouter } from "next/navigation"
import Image from "next/image"
import { cn } from "@/lib/utils"

export default function LoginPage() {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const { login, isLoading, error } = useAuth()
  const router = useRouter()
  const [isLogoAnimating, setIsLogoAnimating] = useState(false)
  const [showError, setShowError] = useState<string | null>(null)

  // Update showError when error changes
  useEffect(() => {
    setShowError(error)
    
    // Set a timer to clear the error after 5 seconds
    if (error) {
      const timer = setTimeout(() => {
        setShowError(null)
      }, 5000)
      
      // Clean up the timer if component unmounts or error changes
      return () => clearTimeout(timer)
    }
  }, [error])

  const handleDismissError = () => {
    setShowError(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await login(username, password)
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-background via-background/95 to-background/90 dark:from-black dark:via-black/95 dark:to-black/90 antialiased relative overflow-hidden">
      {/* Return to home button */}
      <Link
        href="/"
        className="absolute top-6 left-6 z-20 w-10 h-10 flex items-center justify-center rounded-full bg-white/10 dark:bg-white/10 hover:bg-white/20 dark:hover:bg-white/20 transition-colors duration-200 backdrop-blur-sm"
        aria-label="Return to home page"
      >
        <ArrowLeft className="w-5 h-5 text-foreground" />
      </Link>

      {/* Ambient background with moving particles */}
      <div className="h-full w-full absolute inset-0 z-0">
        <SparklesCore
          id="tsparticlesfullpage"
          background="transparent"
          minSize={0.6}
          maxSize={1.4}
          particleDensity={80}
          className="w-full h-full"
          particleColor="var(--foreground)"
        />
      </div>

      <div className="relative z-10 flex items-center justify-center min-h-screen px-4 sm:px-6">
        <div className="w-full max-w-md">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="p-8 bg-white/10 dark:bg-black/40 backdrop-blur-md rounded-2xl border border-white/20 dark:border-white/10 shadow-xl"
          >
            <div className="flex flex-col items-center mb-8">
              <motion.div
                className="relative w-20 h-20"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onHoverStart={() => setIsLogoAnimating(true)}
                onHoverEnd={() => setIsLogoAnimating(false)}
                onClick={() => setIsLogoAnimating(true)}
              >
                <motion.div
                  className="absolute inset-0 rounded-full bg-gradient-to-r from-primary/30 via-secondary/30 to-accent/30 z-0"
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{
                    scale: isLogoAnimating ? 1.2 : 0,
                    opacity: isLogoAnimating ? 1 : 0,
                  }}
                  transition={{ duration: 0.4 }}
                />
                <motion.div
                  animate={{
                    rotate: isLogoAnimating ? [0, 10, -10, 0] : 0,
                  }}
                  transition={{
                    duration: 0.5,
                    ease: "easeInOut",
                    times: [0, 0.2, 0.8, 1],
                  }}
                  className="relative z-10 flex items-center justify-center w-full h-full"
                >
                  <Image
                    src="https://hebbkx1anhila5yf.public.blob.vercel-storage.com/no_bg_logo-M7cBq60PCuZ1sN7MH6T2WMZRrdyQMZ.png"
                    alt="RSW Logo"
                    width={80}
                    height={80}
                    className="object-contain"
                  />
                </motion.div>
              </motion.div>
              <h1 className="text-2xl font-bold text-foreground text-center mt-4 mb-1">Welcome Back</h1>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary via-secondary to-accent font-semibold text-sm">
                Cognitive Data Expert
              </span>
            </div>

            {showError && (
              <motion.div 
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="bg-red-500/10 border border-red-500/20 text-red-700 dark:text-red-400 px-4 py-3 rounded-lg mb-6 shadow-sm relative backdrop-blur-sm"
              >
                <button 
                  onClick={handleDismissError}
                  className="absolute top-2 right-2 text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
                  aria-label="Close notification"
                >
                  <X size={18} />
                </button>
                <p className="font-medium text-center pr-6">{showError}</p>
              </motion.div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-1">
                <label
                  htmlFor="username"
                  className="block text-sm font-medium text-foreground mb-1 ml-1"
                >
                  Username
                </label>
                <div className="relative group">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground group-focus-within:text-primary h-5 w-5 transition-colors duration-200" />
                  <Input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="pl-10 h-11 bg-white/5 dark:bg-white/5 border-white/10 dark:border-white/10 focus:border-primary focus:ring-1 focus:ring-primary text-foreground rounded-lg"
                    placeholder="Enter your username"
                    required
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label
                  htmlFor="password"
                  className="block text-sm font-medium text-foreground mb-1 ml-1"
                >
                  Password
                </label>
                <div className="relative group">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground group-focus-within:text-primary h-5 w-5 transition-colors duration-200" />
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-10 h-11 bg-white/5 dark:bg-white/5 border-white/10 dark:border-white/10 focus:border-primary focus:ring-1 focus:ring-primary text-foreground rounded-lg"
                    placeholder="Enter your password"
                    required
                  />
                </div>
              </div>

              <div className="flex justify-end">
                <Link
                  href="/forgot-password"
                  className="text-sm font-medium text-primary hover:text-primary/80 transition-colors duration-200"
                >
                  Forgot password?
                </Link>
              </div>

              <Button
                type="submit"
                className={cn(
                  "w-full h-11 bg-gradient-to-r from-primary via-primary to-primary/90 hover:from-primary/90 hover:to-primary",
                  "text-white font-medium rounded-lg shadow-md hover:shadow-lg transition-all duration-200",
                  "flex items-center justify-center gap-2"
                )}
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <div className="h-5 w-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Logging in...</span>
                  </>
                ) : (
                  <>
                    <LogIn className="h-5 w-5" />
                    <span>Sign In</span>
                  </>
                )}
              </Button>
            </form>
          </motion.div>
          
          <p className="text-center text-muted-foreground text-sm mt-6">
            RSW Smart Data Intelligence Platform
          </p>
        </div>
      </div>
    </main>
  )
}
