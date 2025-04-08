"use client"

import { Button } from "@/components/ui/button"
import { Menu, User, LogOut, Settings, Sun, Moon } from "lucide-react"
import { motion } from "framer-motion"
import Link from "next/link"
import type React from "react"
import { useAuth } from "@/lib/auth-context"
import { useTheme } from "@/lib/theme-context"
import { useState, useEffect } from "react"
import Image from "next/image"

export default function Navbar() {
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [isLogoHovered, setIsLogoHovered] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const [activeButton, setActiveButton] = useState<string | null>(null)

  // Add scroll detection
  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 10) {
        setScrolled(true)
      } else {
        setScrolled(false)
      }
    }

    window.addEventListener("scroll", handleScroll)
    return () => {
      window.removeEventListener("scroll", handleScroll)
    }
  }, [])

  return (
    <motion.nav
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      className={`flex items-center justify-between px-6 py-4 backdrop-blur-md sticky top-0 z-50 
      bg-gradient-to-r from-background/80 via-background/95 to-background/80 
      border-b border-white/10 dark:border-white/10 border-black/10
      shadow-sm dark:shadow-md
      transition-all duration-300 ease-in-out ${scrolled ? 'py-3 shadow-md' : 'py-4'}`}
    >
      <Link href="/" className="flex items-center space-x-3 group">
        <motion.div
          className="relative w-12 h-12"
          whileHover={{ scale: 1.1, rotate: 5 }}
          whileTap={{ scale: 0.95 }}
          onHoverStart={() => setIsLogoHovered(true)}
          onHoverEnd={() => setIsLogoHovered(false)}
        >
          <motion.div
            className="absolute inset-0 rounded-full bg-gradient-to-tr from-primary/30 to-secondary/30 z-0 blur-md"
            initial={{ scale: 0, opacity: 0 }}
            animate={{
              scale: isLogoHovered ? 1.5 : 0,
              opacity: isLogoHovered ? 1 : 0,
            }}
            transition={{ duration: 0.3 }}
          />
          <motion.div
            animate={{
              rotate: isLogoHovered ? [0, 10, -10, 0] : 0,
              scale: isLogoHovered ? [1, 1.1, 1.05, 1] : 1,
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
              width={48}
              height={48}
              className="object-contain relative z-10 drop-shadow-md transition-all duration-300"
            />
          </motion.div>
        </motion.div>
        <div className="flex flex-col">
          <motion.span 
            className="text-transparent bg-clip-text bg-gradient-to-r from-primary via-secondary to-accent font-bold text-xl md:text-2xl"
            whileHover={{ scale: 1.03 }}
            transition={{ type: "spring", stiffness: 400, damping: 10 }}
          >
            Cognitive Data Expert
          </motion.span>
          <motion.div 
            initial={{ width: 0, opacity: 0 }}
            animate={{ 
              width: isLogoHovered ? "100%" : "0%", 
              opacity: isLogoHovered ? 1 : 0 
            }}
            transition={{ duration: 0.3 }}
            className="h-0.5 bg-gradient-to-r from-primary to-secondary rounded-full" 
          />
        </div>
      </Link>

      <div className="hidden md:flex items-center space-x-8">
        {/* Main nav links were removed as requested */}
      </div>

      <div className="flex items-center space-x-4">
        {/* Theme Toggle Button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          className="text-foreground hover:text-primary transition-all duration-300 hover:bg-muted/50 rounded-full relative overflow-hidden w-10 h-10"
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          onMouseEnter={() => setActiveButton("theme")}
          onMouseLeave={() => setActiveButton(null)}
        >
          <div className="relative w-full h-full flex items-center justify-center">
            {/* Sun Icon (Light Mode) */}
            <motion.div
              initial={{ y: theme === "dark" ? 0 : 40, opacity: theme === "dark" ? 1 : 0, rotate: -45 }}
              animate={{ 
                y: theme === "dark" ? 0 : 40, 
                opacity: theme === "dark" ? 1 : 0,
                rotate: theme === "dark" ? (activeButton === "theme" ? 0 : -30) : -90,
                scale: theme === "dark" && activeButton === "theme" ? 1.2 : 1
              }}
              transition={{ 
                duration: 0.5, 
                type: "spring", 
                stiffness: 200, 
                damping: 10 
              }}
              className="absolute"
            >
              <Sun className="h-5 w-5" />
            </motion.div>
            
            {/* Moon Icon (Dark Mode) */}
            <motion.div
              initial={{ y: theme === "dark" ? 40 : 0, opacity: theme === "dark" ? 0 : 1, rotate: 45 }}
              animate={{ 
                y: theme === "dark" ? 40 : 0, 
                opacity: theme === "dark" ? 0 : 1,
                rotate: theme === "dark" ? 90 : (activeButton === "theme" ? 0 : 30),
                scale: theme !== "dark" && activeButton === "theme" ? 1.2 : 1
              }}
              transition={{ 
                duration: 0.5, 
                type: "spring", 
                stiffness: 200, 
                damping: 10 
              }}
              className="absolute"
            >
              <Moon className="h-5 w-5" />
            </motion.div>
          </div>
          
          {/* Background effects */}
          <motion.div 
            className="absolute inset-0 rounded-full"
            style={{
              background: theme === "dark" 
                ? "radial-gradient(circle at center, rgba(255, 193, 7, 0.2) 0%, transparent 70%)" 
                : "radial-gradient(circle at center, rgba(76, 136, 252, 0.2) 0%, transparent 70%)"
            }}
            initial={{ scale: 0 }}
            animate={{ 
              scale: activeButton === "theme" ? 1 : 0 
            }}
            transition={{ duration: 0.3 }}
          />
          
          {/* Ripple effect on click */}
          <motion.div
            className="absolute inset-0 z-0"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ 
              scale: [0, 1.5, 1.5], 
              opacity: [0, 0.5, 0] 
            }}
            transition={{ 
              duration: 0.8, 
              times: [0, 0.4, 0.8], 
              ease: "easeInOut",
              repeatDelay: 10,
              repeatType: "loop",
              repeat: 0, 
              delay: 0
            }}
            key={theme} // Force animation to restart when theme changes
            style={{
              background: theme === "dark" 
                ? "radial-gradient(circle at center, rgba(255, 193, 7, 0.3), transparent)" 
                : "radial-gradient(circle at center, rgba(76, 136, 252, 0.3), transparent)" 
            }}
          />
        </Button>

        {user ? (
          <>
            <div className="text-foreground flex items-center space-x-2">
              {user.username === "admin" && user.role === "admin" ? (
                <motion.span 
                  className="text-xs font-medium bg-gradient-to-r from-primary to-secondary px-3 py-1 rounded-full text-white shadow-sm"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  animate={{ 
                    boxShadow: ['0 2px 4px rgba(0,0,0,0.1)', '0 4px 8px rgba(var(--color-primary-rgb), 0.3)', '0 2px 4px rgba(0,0,0,0.1)'],
                  }}
                  transition={{ 
                    boxShadow: { repeat: Infinity, duration: 2, ease: "easeInOut" } 
                  }}
                >
                  admin
                </motion.span>
              ) : (
                <>
                  <motion.span 
                    className="font-medium"
                    whileHover={{ scale: 1.05 }}
                    transition={{ type: "spring", stiffness: 400, damping: 20 }}
                  >
                    {user.username}
                  </motion.span>
                  <motion.span 
                    className="text-xs font-medium bg-gradient-to-r from-primary/80 to-secondary/80 px-3 py-1 rounded-full text-white shadow-sm"
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    initial={{ y: 0 }}
                    animate={{ y: [0, -2, 0] }}
                    transition={{ y: { repeat: Infinity, duration: 2, ease: "easeInOut" } }}
                  >
                    {user.role}
                  </motion.span>
                </>
              )}
            </div>
            <Button 
              variant="ghost" 
              className="relative text-foreground hover:text-destructive transition-colors duration-300 hover:bg-destructive/10 rounded-lg overflow-hidden flex items-center justify-center min-w-10 group" 
              onClick={logout}
              onMouseEnter={() => setActiveButton("logout")}
              onMouseLeave={() => setActiveButton(null)}
            >
              <div className="flex items-center justify-center">
                <LogOut className="w-5 h-5" />
                <motion.span
                  className="ml-2 overflow-hidden whitespace-nowrap"
                  initial={{ width: 0, opacity: 0 }}
                  animate={{ 
                    width: activeButton === "logout" ? "auto" : 0,
                    opacity: activeButton === "logout" ? 1 : 0,
                    marginLeft: activeButton === "logout" ? "0.5rem" : "0rem"
                  }}
                  transition={{ duration: 0.2 }}
                >
                  Logout
                </motion.span>
              </div>
              <motion.div 
                className="absolute inset-0 bg-destructive/5 rounded-lg"
                initial={{ scale: 0 }}
                animate={{ 
                  scale: activeButton === "logout" ? 1 : 0 
                }}
                transition={{ duration: 0.2 }}
              />
            </Button>
            {user.role === "admin" && (
              <motion.div 
                whileHover={{ scale: 1.05 }} 
                whileTap={{ scale: 0.95 }}
                animate={{ 
                  boxShadow: ['0 4px 12px rgba(var(--color-primary-rgb), 0.1)', '0 8px 20px rgba(var(--color-primary-rgb), 0.3)', '0 4px 12px rgba(var(--color-primary-rgb), 0.1)'],
                }}
                transition={{ 
                  boxShadow: { repeat: Infinity, duration: 2, ease: "easeInOut" } 
                }}
              >
                <Link
                  href="/admin"
                  className="flex items-center justify-center w-10 h-10 rounded-md bg-gradient-to-r from-primary to-secondary text-white transition-all duration-300 hover:shadow-lg hover:shadow-primary/20"
                >
                  <Settings className="w-5 h-5" />
                </Link>
              </motion.div>
            )}
          </>
        ) : (
          <>
            <motion.div 
              whileHover={{ scale: 1.05 }} 
              whileTap={{ scale: 0.95 }}
              animate={{ 
                boxShadow: ['0 4px 12px rgba(var(--color-primary-rgb), 0.1)', '0 8px 20px rgba(var(--color-primary-rgb), 0.3)', '0 4px 12px rgba(var(--color-primary-rgb), 0.1)'],
              }}
              transition={{ 
                boxShadow: { repeat: Infinity, duration: 2, ease: "easeInOut" } 
              }}
            >
              <Link
                href="/login"
                className="inline-flex items-center px-4 py-2 rounded-md bg-gradient-to-r from-primary to-secondary text-white font-medium border border-primary/30 shadow-[0_0_15px_rgba(26,35,126,0.3)] transition-all duration-300 group"
              >
                <motion.div
                  className="flex items-center"
                  initial={{ x: 0 }}
                  whileHover={{ x: 3 }}
                  transition={{ type: "spring", stiffness: 400, damping: 10 }}
                >
                  <User className="w-4 h-4 mr-2 transition-transform duration-300 group-hover:scale-110" />
                  Sign In
                </motion.div>
              </Link>
            </motion.div>
          </>
        )}
      </div>

      <div className="md:hidden">
        <Button
          variant="ghost"
          size="icon"
          className="text-foreground hover:bg-muted/50 transition-colors duration-300 rounded-full relative overflow-hidden"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          onMouseEnter={() => setActiveButton("menu")}
          onMouseLeave={() => setActiveButton(null)}
        >
          <motion.div
            animate={{ 
              rotate: activeButton === "menu" ? 90 : 0,
              scale: activeButton === "menu" ? 1.1 : 1 
            }}
            transition={{ duration: 0.3 }}
          >
            <Menu className="w-6 h-6" />
          </motion.div>
          <motion.div 
            className="absolute inset-0 bg-primary/10 rounded-full"
            initial={{ scale: 0 }}
            animate={{ 
              scale: activeButton === "menu" ? 1 : 0 
            }}
            transition={{ duration: 0.2 }}
          />
        </Button>
      </div>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <motion.div 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="md:hidden absolute top-full left-0 right-0 bg-background/95 backdrop-blur-md border-b border-black/10 dark:border-white/10 z-50 shadow-lg"
        >
          <div className="flex flex-col p-4 space-y-4">
            <motion.div 
              className="space-y-2"
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              {/* Mobile nav links were removed as requested */}
            </motion.div>
            
            <motion.div 
              className="pt-2 border-t border-black/10 dark:border-white/10"
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              {user ? (
                <>
                  <div className="text-foreground mb-2 flex items-center">
                    {user.username === "admin" && user.role === "admin" ? (
                      <motion.span 
                        className="text-xs font-medium bg-gradient-to-r from-primary to-secondary px-3 py-1 rounded-full text-white shadow-sm"
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                      >
                        admin
                      </motion.span>
                    ) : (
                      <>
                        <motion.span
                          whileHover={{ scale: 1.05 }}
                          className="font-medium"
                        >
                          {user.username}
                        </motion.span>
                        <motion.span 
                          className="ml-2 text-xs font-medium bg-gradient-to-r from-primary/80 to-secondary/80 px-3 py-1 rounded-full text-white shadow-sm"
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                        >
                          {user.role}
                        </motion.span>
                      </>
                    )}
                  </div>
                  <div className="flex space-x-2">
                    <Button
                      variant="ghost"
                      className="text-foreground hover:text-destructive flex items-center justify-start hover:bg-destructive/10 rounded-lg transition-colors duration-300 overflow-hidden"
                      onClick={() => {
                        logout()
                        setMobileMenuOpen(false)
                      }}
                    >
                      <div className="flex items-center">
                        <LogOut className="w-5 h-5" />
                        <motion.span
                          className="ml-2 overflow-hidden whitespace-nowrap"
                          initial={{ width: 0, opacity: 0 }}
                          animate={{ 
                            width: "auto",
                            opacity: 1,
                            marginLeft: "0.5rem"
                          }}
                          transition={{ duration: 0.3 }}
                        >
                          Logout
                        </motion.span>
                      </div>
                    </Button>
                    {user.role === "admin" && (
                      <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                        <Link
                          href="/admin"
                          className="flex items-center justify-center w-10 h-10 rounded-md bg-gradient-to-r from-primary to-secondary text-white shadow-md"
                          onClick={() => setMobileMenuOpen(false)}
                        >
                          <Settings className="w-5 h-5" />
                        </Link>
                      </motion.div>
                    )}
                  </div>
                </>
              ) : (
                <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                  <Link
                    href="/login"
                    onClick={() => setMobileMenuOpen(false)}
                    className="inline-flex items-center px-4 py-2 rounded-md bg-gradient-to-r from-primary to-secondary text-white font-medium border border-primary/30 shadow-md w-full justify-center"
                  >
                    <User className="w-4 h-4 mr-2" />
                    Sign In
                  </Link>
                </motion.div>
              )}
            </motion.div>
          </div>
        </motion.div>
      )}
    </motion.nav>
  )
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="group relative">
      <span className="text-foreground/80 hover:text-foreground transition-colors duration-300">
        {children}
      </span>
      <span className="absolute bottom-0 left-0 w-0 h-0.5 bg-gradient-to-r from-primary to-secondary group-hover:w-full transition-all duration-300"></span>
    </Link>
  )
}
