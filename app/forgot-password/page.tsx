"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { SparklesCore } from "@/components/sparkles"
import { motion } from "framer-motion"
import { Bot, User, ArrowLeft, CheckCircle, AlertTriangle, Lock, KeyRound, Check, X, Mail, Send } from "lucide-react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useAuth } from "@/lib/auth-context"
import { useRouter } from "next/navigation"
import Image from "next/image"
import { cn } from "@/lib/utils"

export default function ForgotPasswordPage() {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { resetPasswordDirect, useFallbackMode } = useAuth()
  const router = useRouter()
  const [isLogoAnimating, setIsLogoAnimating] = useState(false)

  // Password validation state
  const [passwordValidation, setPasswordValidation] = useState({
    valid: false,
    length: false,
    hasUpperCase: false,
    hasLowerCase: false,
    hasNumber: false,
    hasSpecial: false
  })
  
  // Confirm password validation
  const [passwordsMatch, setPasswordsMatch] = useState(false)

  // Password validation
  useEffect(() => {
    if (!password) {
      setPasswordValidation({
        valid: false,
        length: false,
        hasUpperCase: false,
        hasLowerCase: false,
        hasNumber: false,
        hasSpecial: false
      })
      return
    }
    
    const length = password.length >= 8
    const hasUpperCase = /[A-Z]/.test(password)
    const hasLowerCase = /[a-z]/.test(password)
    const hasNumber = /[0-9]/.test(password)
    const hasSpecial = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)
    
    const isValid = length && hasUpperCase && hasLowerCase && hasNumber
    
    setPasswordValidation({
      valid: isValid,
      length,
      hasUpperCase,
      hasLowerCase,
      hasNumber,
      hasSpecial
    })
    
    // Clear validation error if password is valid
    if (isValid) {
      setValidationError(null)
    }
  }, [password])
  
  // Check if passwords match
  useEffect(() => {
    if (confirmPassword === '') {
      setPasswordsMatch(false)
      return
    }
    setPasswordsMatch(password === confirmPassword)
    
    // Update validation error for password match
    if (password && confirmPassword && password !== confirmPassword) {
      setValidationError("Passwords do not match")
    } else if (validationError === "Passwords do not match") {
      setValidationError(null)
    }
  }, [password, confirmPassword, validationError])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Check password validation
    if (!passwordValidation.valid) {
      setValidationError("Password does not meet the requirements")
      return
    }
    
    if (password !== confirmPassword) {
      setValidationError("Passwords do not match")
      return
    }
    
    setIsSubmitting(true)
    setError(null)

    try {
      // If in fallback mode, simulate success
      if (useFallbackMode) {
        // Simulate API delay
        await new Promise((resolve) => setTimeout(resolve, 1000))
        setIsSubmitted(true)
        return
      }

      // Call the direct password reset API
      await resetPasswordDirect(username, password)
      setIsSubmitted(true)
    } catch (err) {
      console.error("Password reset error:", err)
      setError(err instanceof Error ? err.message : "Failed to reset password")

      // If we get a network error, suggest fallback mode
      if (err instanceof TypeError && err.message === "Failed to fetch") {
        setError("Cannot connect to the server. The system is in demo mode.")
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  // Redirect to login after success (after 3 seconds delay)
  useEffect(() => {
    if (isSubmitted) {
      const timer = setTimeout(() => {
        router.push('/login')
      }, 3000)
      
      return () => clearTimeout(timer)
    }
  }, [isSubmitted, router])

  return (
    <main className="min-h-screen bg-gradient-to-br from-background via-background/95 to-background/90 dark:from-black dark:via-black/95 dark:to-black/90 antialiased relative overflow-hidden">
      {/* Return to login button */}
      <Link
        href="/login"
        className="absolute top-6 left-6 z-20 w-10 h-10 flex items-center justify-center rounded-full bg-white/10 dark:bg-white/10 hover:bg-white/20 dark:hover:bg-white/20 transition-colors duration-200 backdrop-blur-sm"
        aria-label="Return to login page"
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
              <h1 className="text-2xl font-bold text-foreground text-center mt-4 mb-1">Reset Password</h1>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary via-secondary to-accent font-semibold text-sm">
                Cognitive Data Expert
              </span>
            </div>

            {isSubmitted ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-green-500/10 border border-green-500/20 text-green-700 dark:text-green-400 p-6 rounded-lg mb-6 flex flex-col items-center"
              >
                <CheckCircle className="w-16 h-16 text-green-500 mb-4" />
                <h3 className="text-xl font-semibold mb-2">Password Reset Successful</h3>
                <p className="text-center mb-4">Your password has been reset successfully.</p>
                <p className="text-sm text-muted-foreground">Redirecting to login page...</p>
              </motion.div>
            ) : (
              <>
                {(error || validationError) && (
                  <motion.div 
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="bg-red-500/10 border border-red-500/20 text-red-700 dark:text-red-400 px-4 py-3 rounded-lg mb-6 shadow-sm relative backdrop-blur-sm"
                  >
                    <button 
                      onClick={() => {
                        setError(null)
                        setValidationError(null)
                      }}
                      className="absolute top-2 right-2 text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
                      aria-label="Close notification"
                    >
                      <X size={18} />
                    </button>
                    <p className="font-medium text-center pr-6">{error || validationError}</p>
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
                      <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground group-focus-within:text-primary h-5 w-5 transition-colors duration-200" />
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
                      New Password
                    </label>
                    <div className="relative group">
                      <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground group-focus-within:text-primary h-5 w-5 transition-colors duration-200" />
                      <Input
                        id="password"
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="pl-10 h-11 bg-white/5 dark:bg-white/5 border-white/10 dark:border-white/10 focus:border-primary focus:ring-1 focus:ring-primary text-foreground rounded-lg"
                        placeholder="Enter new password"
                        required
                      />
                    </div>
                  </div>

                  {/* Password Requirements */}
                  <div className="bg-white/5 dark:bg-white/5 rounded-lg p-3 border border-white/10 dark:border-white/10">
                    <p className="text-sm font-medium mb-2 text-foreground">Password must contain:</p>
                    <ul className="space-y-1 text-sm">
                      <li className="flex items-center">
                        <span className={`mr-2 ${passwordValidation.length ? 'text-green-500' : 'text-red-500'}`}>
                          {passwordValidation.length ? <Check size={16} /> : <X size={16} />}
                        </span>
                        <span className={passwordValidation.length ? 'text-green-500' : 'text-muted-foreground'}>
                          At least 8 characters
                        </span>
                      </li>
                      <li className="flex items-center">
                        <span className={`mr-2 ${passwordValidation.hasUpperCase ? 'text-green-500' : 'text-red-500'}`}>
                          {passwordValidation.hasUpperCase ? <Check size={16} /> : <X size={16} />}
                        </span>
                        <span className={passwordValidation.hasUpperCase ? 'text-green-500' : 'text-muted-foreground'}>
                          At least one uppercase letter
                        </span>
                      </li>
                      <li className="flex items-center">
                        <span className={`mr-2 ${passwordValidation.hasLowerCase ? 'text-green-500' : 'text-red-500'}`}>
                          {passwordValidation.hasLowerCase ? <Check size={16} /> : <X size={16} />}
                        </span>
                        <span className={passwordValidation.hasLowerCase ? 'text-green-500' : 'text-muted-foreground'}>
                          At least one lowercase letter
                        </span>
                      </li>
                      <li className="flex items-center">
                        <span className={`mr-2 ${passwordValidation.hasNumber ? 'text-green-500' : 'text-red-500'}`}>
                          {passwordValidation.hasNumber ? <Check size={16} /> : <X size={16} />}
                        </span>
                        <span className={passwordValidation.hasNumber ? 'text-green-500' : 'text-muted-foreground'}>
                          At least one number
                        </span>
                      </li>
                      <li className="flex items-center">
                        <span className={`mr-2 ${passwordValidation.hasSpecial ? 'text-green-500' : 'text-red-500'}`}>
                          {passwordValidation.hasSpecial ? <Check size={16} /> : <X size={16} />}
                        </span>
                        <span className={passwordValidation.hasSpecial ? 'text-green-500' : 'text-muted-foreground'}>
                          Special character (recommended)
                        </span>
                      </li>
                    </ul>
                  </div>

                  <div className="space-y-1">
                    <label
                      htmlFor="confirmPassword"
                      className="block text-sm font-medium text-foreground mb-1 ml-1"
                    >
                      Confirm Password
                    </label>
                    <div className="relative group">
                      <KeyRound className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground group-focus-within:text-primary h-5 w-5 transition-colors duration-200" />
                      <Input
                        id="confirmPassword"
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        className={cn(
                          "pl-10 h-11 bg-white/5 dark:bg-white/5 border-white/10 dark:border-white/10 focus:ring-1 text-foreground rounded-lg",
                          confirmPassword && (passwordsMatch ? "focus:border-green-500 focus:ring-green-500" : "focus:border-red-500 focus:ring-red-500"),
                          confirmPassword && (passwordsMatch ? "border-green-500/50" : "border-red-500/50")
                        )}
                        placeholder="Confirm your password"
                        required
                      />
                      {confirmPassword && (
                        <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                          {passwordsMatch ? (
                            <Check className="h-5 w-5 text-green-500" />
                          ) : (
                            <X className="h-5 w-5 text-red-500" />
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  <Button
                    type="submit"
                    className={cn(
                      "w-full h-11 bg-gradient-to-r from-primary via-primary to-primary/90 hover:from-primary/90 hover:to-primary",
                      "text-white font-medium rounded-lg shadow-md hover:shadow-lg transition-all duration-200",
                      "flex items-center justify-center gap-2 mt-2"
                    )}
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? (
                      <>
                        <div className="h-5 w-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        <span>Processing...</span>
                      </>
                    ) : (
                      <>
                        <KeyRound className="h-5 w-5" />
                        <span>Reset Password</span>
                      </>
                    )}
                  </Button>
                </form>
              </>
            )}
          </motion.div>
          
          <p className="text-center text-muted-foreground text-sm mt-6">
            RSW Smart Data Intelligence Platform
          </p>
        </div>
      </div>
    </main>
  )
}
