"use client"

import { Button } from "@/components/ui/button"
import { ChevronLeft, User, LogOut, Settings, Sun, Moon, Search, Bell } from "lucide-react"
import { motion } from "framer-motion"
import Link from "next/link"
import type React from "react"
import { useAuth } from "@/lib/auth-context"
import { useTheme } from "@/lib/theme-context"
import { useState, useEffect, useMemo } from "react"
import Image from "next/image"
import { Input } from "@/components/ui/input"
import { usePathname } from "next/navigation"

export default function Navbar() {
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)

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

  const pathname = usePathname()
  const pageName = useMemo(() => {
    // DataPuur section
    if (pathname === '/datapuur') {
      return 'DataPuur Dashboard'
    } else if (pathname === '/datapuur/ingestion') {
      return 'DataPuur Ingestion'
    } else if (pathname === '/datapuur/profile') {
      return 'DataPuur Profiles'
    } else if (pathname === '/datapuur/transformation') {
      return 'DataPuur Transformation'
    } else if (pathname === '/datapuur/export') {
      return 'DataPuur Export'
    } else if (pathname.startsWith('/datapuur/')) {
      return 'DataPuur'
    }
    
    // KGInsights section
    else if (pathname === '/kginsights/dashboard') {
      return 'KGraph Dashboard'
    } else if (pathname === '/kginsights/insights') {
      return 'KGraph Insights'
    } else if (pathname === '/kginsights/generate') {
      return 'Generate Graph'
    } else if (pathname === '/kginsights/manage') {
      return 'Manage KGraph'
    } else if (pathname.startsWith('/kginsights/')) {
      return 'K-Graff'
    }
    
    // Other pages
    else if (pathname === '/dashboards') {
      return 'My Dashboards'
    } else if (pathname === '/dashboard-creator') {
      return 'Dashboard Creator'
    } else if (pathname === '/activity') {
      return 'Recent Activity'
    } else if (pathname === '/admin') {
      return 'Settings'
    } else if (pathname === '/help') {
      return 'Help'
    } else if (pathname === '/inventory') {
      return 'Inventory Overview'
    } else if (pathname === '/financial') {
      return 'Financial Overview'
    } else if (pathname === '/' || pathname === '/factory_dashboard') {
      return 'Factory Dashboard'
    } else {
      // Default fallback - extract the last part of the path and capitalize it
      const lastSegment = pathname.split('/').filter(Boolean).pop() || 'Dashboard'
      return lastSegment.charAt(0).toUpperCase() + lastSegment.slice(1).replace(/-/g, ' ')
    }
  }, [pathname])

  return (
    <div
      className="flex items-center justify-between px-6 py-3 sticky top-0 z-50 
      bg-background 
      border-b border-border
      transition-all duration-300 ease-in-out"
    >
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          <ChevronLeft className="h-5 w-5 text-muted-foreground" />
        </Button>
        
        <h1 className="text-lg font-semibold">{pageName}</h1>
      </div>
      
      <div className="hidden md:flex items-center gap-4 max-w-md w-full">
        <div className="relative w-full max-w-sm">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input 
            type="search" 
            placeholder="Search data, people..." 
            className="pl-10 bg-muted/50 border-none h-9" 
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          className="text-muted-foreground hover:text-foreground h-9 w-9"
        >
          <Bell className="h-5 w-5" />
        </Button>

        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          className="text-muted-foreground hover:text-foreground h-9 w-9"
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </Button>

        {/* User profile icon removed as requested */}
      </div>

      {/* Mobile menu button already handled above */}

      {/* Mobile menu - outside the main nav for proper z-index layering */}
      {mobileMenuOpen && (
        <motion.div 
          className="fixed inset-0 z-50 md:hidden"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          {/* Backdrop */}
          <motion.div 
            className="fixed inset-0 bg-background/80 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setMobileMenuOpen(false)}
          />
          
          {/* Side drawer */}
          <motion.div 
            className="fixed inset-y-0 left-0 w-64 bg-card/95 p-4 shadow-lg flex flex-col justify-between"
            initial={{ x: "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: "-100%" }}
            transition={{ ease: "easeOut", duration: 0.3 }}
          >
            <div className="flex items-center justify-between mb-4 border-b border-border pb-4">
              <div className="flex items-center gap-2">
                <div className="rounded-full bg-primary h-8 w-8 flex items-center justify-center text-primary-foreground font-semibold">
                  {user?.username?.[0] || 'U'}
                </div>
                <div className="flex flex-col">
                  <span className="text-sm font-medium">{user?.username || 'User'}</span>
                  <span className="text-xs text-muted-foreground">{user?.role || 'user'}</span>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setMobileMenuOpen(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </Button>
            </div>
            
            <div className="flex-1 overflow-y-auto">
              <div className="space-y-1 pb-4">
                <NavLink href="/">Sales Overview</NavLink>
                <NavLink href="/inventory">Inventory Overview</NavLink>
                <NavLink href="/financial">Financial Overview</NavLink>
              </div>
              
              {/* DataPuur Section */}
              <div className="border-t border-border pt-4 pb-4">
                <h3 className="text-sm font-medium mb-2 px-3">DataPuur Dashboard</h3>
                <div className="space-y-1">
                  <NavLink href="/datapuur">DataPuur Dashboard</NavLink>
                  <NavLink href="/datapuur/ingestion">DataPuur Ingestion</NavLink>
                  <NavLink href="/datapuur/profile">DataPuur Profiles</NavLink>
                  <NavLink href="/datapuur/transformation">DataPuur Transformation</NavLink>
                  <NavLink href="/datapuur/export">DataPuur Export</NavLink>
                </div>
              </div>
              
              {/* KGInsights Section */}
              <div className="border-t border-border pt-4 pb-4">
                <h3 className="text-sm font-medium mb-2 px-3">K-Graff</h3>
                <div className="space-y-1">
                  <NavLink href="/kginsights/dashboard">KGraph Dashboard</NavLink>
                  <NavLink href="/kginsights/insights">KGraph Insights</NavLink>
                  <NavLink href="/kginsights/generate">Generate Graph</NavLink>
                  <NavLink href="/kginsights/manage">Manage KGraph</NavLink>
                </div>
              </div>
              
              <div className="border-t border-border pt-4 pb-4">
                <div className="space-y-1">
                  <NavLink href="/dashboards">My Dashboards</NavLink>
                  <NavLink href="/dashboard-creator">Dashboard Creator</NavLink>
                  <NavLink href="/activity">Recent Activity</NavLink>
                </div>
              </div>
              
              <div className="border-t border-border pt-4 pb-4">
                <div className="space-y-1">
                  <NavLink href="/admin">Settings</NavLink>
                  <NavLink href="/help">Help</NavLink>
                </div>
              </div>
            </div>
            
            <div className="border-t border-border pt-4">
              {user ? (
                <Button 
                  variant="outline" 
                  onClick={logout}
                  className="w-full justify-center"
                  size="sm"
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  Logout
                </Button>
              ) : (
                <div className="flex gap-2">
                  <Link href="/login" onClick={() => setMobileMenuOpen(false)} className="flex-1">
                    <Button variant="outline" className="w-full">Log in</Button>
                  </Link>
                  <Link href="/register" onClick={() => setMobileMenuOpen(false)} className="flex-1">
                    <Button className="w-full">Sign up</Button>
                  </Link>
                </div>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </div>
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
