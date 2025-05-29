"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { useAuth } from "@/lib/auth-context"
import { motion, AnimatePresence } from "framer-motion"
import { Lock, Mail, ArrowLeft, X, LogIn, ShieldCheck } from "lucide-react"
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
  const [formFocused, setFormFocused] = useState<"username" | "password" | null>(null)

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
    <main className="min-h-screen bg-gradient-to-br from-background via-background/95 to-background/90 dark:from-background dark:via-background/95 dark:to-background/90 antialiased relative overflow-hidden">


      
      {/* Animated gradient orbs in background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -left-40 w-80 h-80 bg-primary/20 rounded-full filter blur-3xl opacity-30 animate-blob"></div>
        <div className="absolute top-40 -right-40 w-80 h-80 bg-secondary/20 rounded-full filter blur-3xl opacity-30 animate-blob animation-delay-2000"></div>
        <div className="absolute bottom-40 left-20 w-80 h-80 bg-accent/20 rounded-full filter blur-3xl opacity-30 animate-blob animation-delay-4000"></div>
      </div>

      <div className="relative z-10 flex items-center justify-center min-h-screen px-4 sm:px-6">
        <div className="w-full max-w-md">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="p-8 bg-card/80 backdrop-blur-md rounded-2xl border border-border shadow-xl card-animated"
          >
            <div className="flex flex-col items-center mb-8">
              <motion.div
                className="relative w-24 h-24"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onHoverStart={() => setIsLogoAnimating(true)}
                onHoverEnd={() => setIsLogoAnimating(false)}
                onClick={() => setIsLogoAnimating(true)}
              >
                <motion.div
                  className="absolute inset-0 rounded-full bg-gradient-to-r from-primary/40 via-secondary/40 to-accent/40 z-0"
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
                  <div className="relative w-20 h-20 rounded-full bg-card flex items-center justify-center shadow-lg">
                    <Image
                      src="https://hebbkx1anhila5yf.public.blob.vercel-storage.com/no_bg_logo-M7cBq60PCuZ1sN7MH6T2WMZRrdyQMZ.png"
                      alt="RSW Logo"
                      width={80}
                      height={80}
                      className="object-contain"
                    />
                  </div>
                </motion.div>
              </motion.div>
              <h1 className="text-2xl font-bold text-foreground text-center mt-4 mb-1">Welcome Back</h1>
              <motion.span 
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3, duration: 0.5 }}
                className="text-transparent bg-clip-text bg-gradient-to-r from-primary via-secondary to-accent font-semibold text-sm"
              >
                Cognitive Data Expert
              </motion.span>
            </div>

            <AnimatePresence>
              {showError && (
                <motion.div 
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="bg-destructive/10 border border-destructive/20 text-destructive-foreground px-4 py-3 rounded-lg mb-6 shadow-sm relative backdrop-blur-sm"
                >
                  <button 
                    onClick={handleDismissError}
                    className="absolute top-2 right-2 text-destructive-foreground/70 hover:text-destructive-foreground"
                    aria-label="Close notification"
                  >
                    <X size={18} />
                  </button>
                  <p className="font-medium text-center pr-6">{showError}</p>
                </motion.div>
              )}
            </AnimatePresence>

            <form onSubmit={handleSubmit} className="space-y-5">
              <motion.div 
                className="space-y-1"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1, duration: 0.3 }}
              >
                <label
                  htmlFor="username"
                  className="block text-sm font-medium text-foreground mb-1 ml-1"
                >
                  Username
                </label>
                <div className="relative group">
                  <Mail 
                    className={cn(
                      "absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 transition-colors duration-200",
                      formFocused === "username" ? "text-primary" : "text-muted-foreground"
                    )} 
                  />
                  <Input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    onFocus={() => setFormFocused("username")}
                    onBlur={() => setFormFocused(null)}
                    className={cn(
                      "pl-10 h-11 bg-card/50 border-input/50 focus:border-primary focus:ring-1 focus:ring-primary text-foreground rounded-lg",
                      formFocused === "username" && "border-primary/50 shadow-sm shadow-primary/20"
                    )}
                    placeholder="Enter your username"
                    required
                  />
                </div>
              </motion.div>

              <motion.div 
                className="space-y-1"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2, duration: 0.3 }}
              >
                <label
                  htmlFor="password"
                  className="block text-sm font-medium text-foreground mb-1 ml-1"
                >
                  Password
                </label>
                <div className="relative group">
                  <Lock 
                    className={cn(
                      "absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 transition-colors duration-200",
                      formFocused === "password" ? "text-primary" : "text-muted-foreground"
                    )}
                  />
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onFocus={() => setFormFocused("password")}
                    onBlur={() => setFormFocused(null)}
                    className={cn(
                      "pl-10 h-11 bg-card/50 border-input/50 focus:border-primary focus:ring-1 focus:ring-primary text-foreground rounded-lg",
                      formFocused === "password" && "border-primary/50 shadow-sm shadow-primary/20"
                    )}
                    placeholder="Enter your password"
                    required
                  />
                </div>
              </motion.div>

              <motion.div 
                className="flex justify-end"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3, duration: 0.3 }}
              >
                <Link
                  href="/forgot-password"
                  className="text-sm font-medium text-primary hover:text-primary/80 transition-colors duration-200 hover:underline"
                >
                  Forgot password?
                </Link>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4, duration: 0.3 }}
              >
                <Button
                  type="submit"
                  className={cn(
                    "w-full h-12 bg-gradient-to-r from-primary via-primary to-primary/90 hover:from-primary/90 hover:to-primary",
                    "text-primary-foreground font-medium rounded-lg shadow-md hover:shadow-lg transition-all duration-200",
                    "flex items-center justify-center gap-2 relative overflow-hidden group"
                  )}
                  disabled={isLoading}
                >
                  <span className="absolute inset-0 w-full h-full bg-gradient-to-r from-primary/10 via-primary/5 to-primary/10 animate-shimmer"></span>
                  {isLoading ? (
                    <>
                      <div className="h-5 w-5 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
                      <span>Logging in...</span>
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="h-5 w-5 group-hover:scale-110 transition-transform" />
                      <span>Sign In</span>
                    </>
                  )}
                </Button>
              </motion.div>
            </form>
          </motion.div>
          
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.5 }}
          >
            <p className="text-center text-muted-foreground text-sm mt-6">
              RSW Smart Data Intelligence Platform
            </p>
          </motion.div>
        </div>
      </div>
    </main>
  )
}
