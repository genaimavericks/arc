"use client"

import React, { useState, useEffect } from "react"
import { MainSidebar } from "@/components/main-sidebar"
import Navbar from "@/components/navbar"

import { DjinniProvider, useDjinni } from "@/lib/djinni-context"

interface MainLayoutProps {
  children: React.ReactNode
}

export function MainLayout({ children }: MainLayoutProps) {
  return (
    <DjinniProvider>
      <MainLayoutContent>{children}</MainLayoutContent>
    </DjinniProvider>
  )
}

function MainLayoutContent({ children }: MainLayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const { isCollapsed, isOpen } = useDjinni()

  // Check if the sidebar is collapsed from localStorage
  useEffect(() => {
    const savedState = localStorage.getItem('datapuur-sidebar-collapsed')
    if (savedState) {
      setSidebarCollapsed(savedState === 'true')
    }

    // Listen for changes to the sidebar collapsed state
    const handleStorageChange = () => {
      const currentState = localStorage.getItem('datapuur-sidebar-collapsed')
      setSidebarCollapsed(currentState === 'true')
    }

    // Create a custom event listener for localStorage changes
    window.addEventListener('storage', handleStorageChange)
    
    // Also listen for a custom event that we'll dispatch when the sidebar state changes
    window.addEventListener('sidebarStateChange', handleStorageChange)
    window.addEventListener('djinniStateChange', handleStorageChange)

    return () => {
      window.removeEventListener('storage', handleStorageChange)
      window.removeEventListener('sidebarStateChange', handleStorageChange)
      window.removeEventListener('djinniStateChange', handleStorageChange)
    }
  }, [])



  return (
    <div className="flex min-h-screen bg-background">
      <div className={`hidden md:flex flex-col fixed inset-y-0 z-30 transition-all duration-300 ${sidebarCollapsed ? 'w-16' : 'w-64'}`}>
        <MainSidebar />
      </div>
      <div className={`flex flex-col flex-1 transition-all duration-300 ${sidebarCollapsed ? 'md:pl-16' : 'md:pl-64'}`}>
        <Navbar />
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>

    </div>
  )
}
