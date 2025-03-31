"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { SparklesCore } from "@/components/sparkles"
import { motion } from "framer-motion"
import { Bot, User, ArrowLeft, CheckCircle, AlertTriangle, Lock, KeyRound, Check, X } from "lucide-react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useAuth } from "@/lib/auth-context"
import { useRouter } from "next/navigation"
import Image from "next/image"

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
    <main className="min-h-screen bg-background dark:bg-black/[0.96] antialiased bg-grid-white/[0.02] relative overflow-hidden">
      {/* Return to login button */}
      <Link
        href="/login"
        className="absolute top-6 left-6 z-20 w-10 h-10 flex items-center justify-center rounded-full bg-black/10 dark:bg-white/10 hover:bg-black/20 dark:hover:bg-white/20 transition-colors duration-200"
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
          particleDensity={100}
          className="w-full h-full"
          particleColor="var(--foreground)"
        />
      </div>

      <div className="relative z-10 flex items-center justify-center min-h-screen">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md p-8 bg-white/5 dark:bg-white/5 bg-black/5 backdrop-blur-sm rounded-lg border border-white/10 dark:border-white/10 border-black/10"
        >
          <div className="flex flex-col items-center mb-6">
            <motion.div
              className="relative w-16 h-16"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
              onHoverStart={() => setIsLogoAnimating(true)}
              onHoverEnd={() => setIsLogoAnimating(false)}
              onClick={() => setIsLogoAnimating(true)}
            >
              <motion.div
                className="absolute inset-0 rounded-full bg-primary/20 z-0"
                initial={{ scale: 0, opacity: 0 }}
                animate={{
                  scale: isLogoAnimating ? 1.2 : 0,
                  opacity: isLogoAnimating ? 1 : 0,
                }}
                transition={{ duration: 0.3 }}
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
              >
                <Image
                  src="https://hebbkx1anhila5yf.public.blob.vercel-storage.com/no_bg_logo-M7cBq60PCuZ1sN7MH6T2WMZRrdyQMZ.png"
                  alt="RSW Logo"
                  width={64}
                  height={64}
                  className="object-contain relative z-10"
                />
              </motion.div>
            </motion.div>
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary via-secondary to-accent font-bold text-sm mt-2">
              Cognitive Data Expert
            </span>
          </div>

          <h1 className="text-2xl font-bold text-foreground text-center mb-6">Reset Password</h1>

          {error && (
            <div className="bg-red-100 border border-red-400 text-red-800 px-4 py-3 rounded-md mb-4 shadow-sm">
              <p className="font-medium text-center">{error}</p>
            </div>
          )}

          {useFallbackMode && !isSubmitted && (
            <div className="bg-yellow-100 border border-yellow-400 text-yellow-800 px-4 py-2 rounded-md mb-4 flex items-start">
              <AlertTriangle className="h-5 w-5 mr-2 mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-medium">Using Demo Mode</p>
                <p className="text-sm">API server is unavailable. Password reset will be simulated.</p>
              </div>
            </div>
          )}

          {isSubmitted ? (
            <div className="text-center">
              <div className="flex justify-center mb-4">
                <CheckCircle className="w-16 h-16 text-green-500" />
              </div>
              <h2 className="text-xl font-semibold text-foreground mb-2">Password Reset Successful</h2>
              <p className="text-foreground/70 mb-6">
                Your password has been successfully reset. Redirecting to login page...
              </p>
              <Link
                href="/login"
                className="text-primary hover:text-primary/80 flex items-center justify-center"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Login
              </Link>
            </div>
          ) : (
            <>
              <p className="text-foreground/70 mb-6">
                Enter your username and new password to reset your account password.
              </p>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label htmlFor="username" className="block text-sm font-medium text-foreground/70 mb-1">
                    Username
                  </label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
                    <Input
                      id="username"
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      className="pl-10 bg-white/5 dark:bg-white/5 bg-black/5 border-white/10 dark:border-white/10 border-black/10 text-foreground"
                      placeholder="Enter your username"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-foreground/70 mb-1">
                    New Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
                    <Input
                      id="password"
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className={`pl-10 pr-10 bg-white/5 dark:bg-white/5 bg-black/5 border-white/10 dark:border-white/10 border-black/10 text-foreground ${
                        password && !passwordValidation.valid ? "border-red-500" : ""
                      }`}
                      placeholder="Enter new password"
                      required
                    />
                    {password && (
                      <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                        {passwordValidation.valid ? (
                          <Check className="h-4 w-4 text-green-500" />
                        ) : (
                          <X className="h-4 w-4 text-red-500" />
                        )}
                      </div>
                    )}
                  </div>
                  
                  {password && (
                    <div className="mt-2 space-y-1">
                      <p className="text-xs font-medium text-foreground/70">Password must contain:</p>
                      <ul className="space-y-1">
                        <li className={`text-xs flex items-center ${passwordValidation.length ? "text-green-500" : "text-foreground/50"}`}>
                          {passwordValidation.length ? <Check className="h-3 w-3 mr-1" /> : <X className="h-3 w-3 mr-1" />}
                          At least 8 characters
                        </li>
                        <li className={`text-xs flex items-center ${passwordValidation.hasUpperCase ? "text-green-500" : "text-foreground/50"}`}>
                          {passwordValidation.hasUpperCase ? <Check className="h-3 w-3 mr-1" /> : <X className="h-3 w-3 mr-1" />}
                          At least one uppercase letter
                        </li>
                        <li className={`text-xs flex items-center ${passwordValidation.hasLowerCase ? "text-green-500" : "text-foreground/50"}`}>
                          {passwordValidation.hasLowerCase ? <Check className="h-3 w-3 mr-1" /> : <X className="h-3 w-3 mr-1" />}
                          At least one lowercase letter
                        </li>
                        <li className={`text-xs flex items-center ${passwordValidation.hasNumber ? "text-green-500" : "text-foreground/50"}`}>
                          {passwordValidation.hasNumber ? <Check className="h-3 w-3 mr-1" /> : <X className="h-3 w-3 mr-1" />}
                          At least one number
                        </li>
                        <li className={`text-xs flex items-center ${passwordValidation.hasSpecial ? "text-green-500" : "text-foreground/50"}`}>
                          {passwordValidation.hasSpecial ? <Check className="h-3 w-3 mr-1" /> : <X className="h-3 w-3 mr-1" />}
                          Special character (recommended)
                        </li>
                      </ul>
                    </div>
                  )}
                </div>

                <div>
                  <label htmlFor="confirmPassword" className="block text-sm font-medium text-foreground/70 mb-1">
                    Confirm Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
                    <Input
                      id="confirmPassword"
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className={`pl-10 pr-10 bg-white/5 dark:bg-white/5 bg-black/5 border-white/10 dark:border-white/10 border-black/10 text-foreground ${
                        confirmPassword && !passwordsMatch ? "border-red-500" : ""
                      }`}
                      placeholder="Confirm new password"
                      required
                    />
                    {confirmPassword && (
                      <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                        {passwordsMatch ? (
                          <Check className="h-4 w-4 text-green-500" />
                        ) : (
                          <X className="h-4 w-4 text-red-500" />
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {validationError && (
                  <div className="text-red-400 text-sm">{validationError}</div>
                )}

                <Button
                  type="submit"
                  className="w-full bg-primary hover:bg-primary/90 text-white btn-glow"
                  disabled={isSubmitting || !passwordValidation.valid || !passwordsMatch || !username}
                >
                  {isSubmitting ? "Resetting..." : "Reset Password"}
                </Button>
              </form>

              <div className="mt-6 text-center">
                <Link
                  href="/login"
                  className="text-primary hover:text-primary/80 flex items-center justify-center"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to Login
                </Link>
              </div>
            </>
          )}
        </motion.div>
      </div>
    </main>
  )
}
