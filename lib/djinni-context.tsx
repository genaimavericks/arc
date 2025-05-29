"use client"

import React, { createContext, useContext, useState, useEffect } from "react"

interface DjinniContextType {
  isCollapsed: boolean
  setIsCollapsed: (value: boolean) => void
  isOpen: boolean
  setIsOpen: (value: boolean) => void
  width: number
  setWidth: (value: number) => void
}

const DjinniContext = createContext<DjinniContextType | undefined>(undefined)

export function DjinniProvider({ children }: { children: React.ReactNode }) {
  const [isCollapsed, setIsCollapsed] = useState(true)
  const [isOpen, setIsOpen] = useState(true)
  const [width, setWidth] = useState(320)

  // Load saved state from localStorage
  useEffect(() => {
    const savedCollapsedState = localStorage.getItem('djinni-chat-collapsed')
    if (savedCollapsedState) {
      setIsCollapsed(savedCollapsedState === 'true')
    }
    
    const savedOpenState = localStorage.getItem('djinni-chat-open')
    if (savedOpenState) {
      setIsOpen(savedOpenState === 'true')
    }

    const savedWidth = localStorage.getItem('djinni-chat-width')
    if (savedWidth) {
      setWidth(parseInt(savedWidth))
    }
  }, [])

  // Save state to localStorage when it changes
  useEffect(() => {
    localStorage.setItem('djinni-chat-collapsed', isCollapsed.toString())
  }, [isCollapsed])
  
  useEffect(() => {
    localStorage.setItem('djinni-chat-open', isOpen.toString())
  }, [isOpen])

  useEffect(() => {
    localStorage.setItem('djinni-chat-width', width.toString())
  }, [width])

  return (
    <DjinniContext.Provider value={{ isCollapsed, setIsCollapsed, isOpen, setIsOpen, width, setWidth }}>
      {children}
    </DjinniContext.Provider>
  )
}

export function useDjinni() {
  const context = useContext(DjinniContext)
  if (context === undefined) {
    throw new Error("useDjinni must be used within a DjinniProvider")
  }
  return context
}
