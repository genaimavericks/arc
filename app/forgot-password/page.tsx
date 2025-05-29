"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { User, ArrowLeft, CheckCircle, AlertTriangle, Lock, KeyRound, Check, X, Mail, Send, ShieldCheck } from "lucide-react"
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
  const [formFocused, setFormFocused] = useState<"username" | "password" | "confirmPassword" | null>(null)

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
    <main className="min-h-screen bg-gradient-to-br from-background via-background/95 to-background/90 dark:from-background dark:via-background/95 dark:to-background/90 antialiased relative overflow-hidden">
      {/* Return to login button */}
      <Link
        href="/login"
        className="absolute top-6 left-6 z-20 w-10 h-10 flex items-center justify-center rounded-full bg-card/50 hover:bg-card/80 transition-colors duration-200 backdrop-blur-sm border border-border shadow-md"
        aria-label="Return to login page"
      >
        <ArrowLeft className="w-5 h-5 text-foreground" />
      </Link>


      
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
              <h1 className="text-2xl font-bold text-foreground text-center mt-4 mb-1">Reset Password</h1>
              <motion.span 
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3, duration: 0.5 }}
                className="text-transparent bg-clip-text bg-gradient-to-r from-primary via-secondary to-accent font-semibold text-sm"
              >
                Cognitive Data Expert
              </motion.span>
            </div>

            {isSubmitted ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-green-500/15 border border-green-500/30 text-green-700 dark:text-green-400 p-6 rounded-lg mb-6 flex flex-col items-center backdrop-blur-sm shadow-md"
              >
                <div className="relative">
                  <motion.div 
                    className="absolute inset-0 rounded-full bg-green-500/20 filter blur-md"
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
                  />
                  <CheckCircle className="w-16 h-16 text-green-500 mb-4 relative z-10" />
                </div>
                <h3 className="text-xl font-semibold mb-2">Password Reset Successful</h3>
                <p className="text-center mb-4">Your password has been reset successfully.</p>
                <motion.div
                  className="w-full max-w-[120px] h-1 bg-muted rounded-full overflow-hidden mt-2"
                >
                  <motion.div
                    className="h-full bg-green-500"
                    initial={{ width: 0 }}
                    animate={{ width: "100%" }}
                    transition={{ duration: 3, ease: "linear" }}
                  />
                </motion.div>
                <p className="text-sm text-muted-foreground mt-2">Redirecting to login page...</p>
              </motion.div>
            ) : (
              <>
                <AnimatePresence>
                  {(error || validationError) && (
                    <motion.div 
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="bg-destructive/10 border border-destructive/20 text-destructive-foreground px-4 py-3 rounded-lg mb-6 shadow-sm relative backdrop-blur-sm"
                    >
                      <button 
                        onClick={() => {
                          setError(null)
                          setValidationError(null)
                        }}
                        className="absolute top-2 right-2 text-destructive-foreground/70 hover:text-destructive-foreground"
                        aria-label="Close notification"
                      >
                        <X size={18} />
                      </button>
                      <p className="font-medium text-center pr-6">{error || validationError}</p>
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
                      <User 
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
                      New Password
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
                        placeholder="Enter new password"
                        required
                      />
                    </div>
                  </motion.div>

                  {/* Password Requirements */}
                  <motion.div 
                    className="bg-card/50 rounded-lg p-4 border border-border shadow-sm"
                    initial={{ opacity: 0, scale: 0.98 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.3, duration: 0.3 }}
                  >
                    <p className="text-sm font-medium mb-2 text-foreground">Password must contain:</p>
                    <ul className="space-y-2 text-sm">
                      <li className="flex items-center">
                        <span className={`mr-2 ${passwordValidation.length ? 'text-green-500' : 'text-destructive'}`}>
                          {passwordValidation.length ? <Check size={16} /> : <X size={16} />}
                        </span>
                        <span className={passwordValidation.length ? 'text-green-500' : 'text-muted-foreground'}>
                          At least 8 characters
                        </span>
                      </li>
                      <li className="flex items-center">
                        <span className={`mr-2 ${passwordValidation.hasUpperCase ? 'text-green-500' : 'text-destructive'}`}>
                          {passwordValidation.hasUpperCase ? <Check size={16} /> : <X size={16} />}
                        </span>
                        <span className={passwordValidation.hasUpperCase ? 'text-green-500' : 'text-muted-foreground'}>
                          At least one uppercase letter
                        </span>
                      </li>
                      <li className="flex items-center">
                        <span className={`mr-2 ${passwordValidation.hasLowerCase ? 'text-green-500' : 'text-destructive'}`}>
                          {passwordValidation.hasLowerCase ? <Check size={16} /> : <X size={16} />}
                        </span>
                        <span className={passwordValidation.hasLowerCase ? 'text-green-500' : 'text-muted-foreground'}>
                          At least one lowercase letter
                        </span>
                      </li>
                      <li className="flex items-center">
                        <span className={`mr-2 ${passwordValidation.hasNumber ? 'text-green-500' : 'text-destructive'}`}>
                          {passwordValidation.hasNumber ? <Check size={16} /> : <X size={16} />}
                        </span>
                        <span className={passwordValidation.hasNumber ? 'text-green-500' : 'text-muted-foreground'}>
                          At least one number
                        </span>
                      </li>
                      <li className="flex items-center">
                        <span className={`mr-2 ${passwordValidation.hasSpecial ? 'text-green-500' : 'text-destructive/50'}`}>
                          {passwordValidation.hasSpecial ? <Check size={16} /> : <X size={16} />}
                        </span>
                        <span className={passwordValidation.hasSpecial ? 'text-green-500' : 'text-muted-foreground'}>
                          Special character (recommended)
                        </span>
                      </li>
                    </ul>
                  </motion.div>

                  <motion.div 
                    className="space-y-1"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4, duration: 0.3 }}
                  >
                    <label
                      htmlFor="confirmPassword"
                      className="block text-sm font-medium text-foreground mb-1 ml-1"
                    >
                      Confirm Password
                    </label>
                    <div className="relative group">
                      <KeyRound 
                        className={cn(
                          "absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 transition-colors duration-200",
                          formFocused === "confirmPassword" ? "text-primary" : "text-muted-foreground"
                        )}
                      />
                      <Input
                        id="confirmPassword"
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        onFocus={() => setFormFocused("confirmPassword")}
                        onBlur={() => setFormFocused(null)}
                        className={cn(
                          "pl-10 h-11 bg-card/50 border-input/50 focus:ring-1 text-foreground rounded-lg",
                          confirmPassword && (passwordsMatch ? "focus:border-green-500 focus:ring-green-500" : "focus:border-destructive focus:ring-destructive"),
                          confirmPassword && (passwordsMatch ? "border-green-500/50" : "border-destructive/50"),
                          formFocused === "confirmPassword" && !confirmPassword && "border-primary/50 shadow-sm shadow-primary/20"
                        )}
                        placeholder="Confirm your password"
                        required
                      />
                      {confirmPassword && (
                        <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                          {passwordsMatch ? (
                            <Check className="h-5 w-5 text-green-500" />
                          ) : (
                            <X className="h-5 w-5 text-destructive" />
                          )}
                        </div>
                      )}
                    </div>
                  </motion.div>

                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5, duration: 0.3 }}
                    className="pt-2"
                  >
                    <Button
                      type="submit"
                      className={cn(
                        "w-full h-12 bg-gradient-to-r from-primary via-primary to-primary/90 hover:from-primary/90 hover:to-primary",
                        "text-primary-foreground font-medium rounded-lg shadow-md hover:shadow-lg transition-all duration-200",
                        "flex items-center justify-center gap-2 relative overflow-hidden group"
                      )}
                      disabled={isSubmitting}
                    >
                      <span className="absolute inset-0 w-full h-full bg-gradient-to-r from-primary/10 via-primary/5 to-primary/10 animate-shimmer"></span>
                      {isSubmitting ? (
                        <>
                          <div className="h-5 w-5 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
                          <span>Processing...</span>
                        </>
                      ) : (
                        <>
                          <ShieldCheck className="h-5 w-5 group-hover:scale-110 transition-transform" />
                          <span>Reset Password</span>
                        </>
                      )}
                    </Button>
                  </motion.div>
                </form>
              </>
            )}
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
