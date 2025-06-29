"use client"

import React, { createContext, useContext, useState, useEffect } from 'react'
import { useDjinniStore } from '@/lib/djinni/store'

// Define the context shape
type AssistantContextType = {
  activeAstroType: 'factory_astro' | 'churn_astro'
  isAstroEnabled: boolean
  isKgInsightsEnabled: boolean
  setActiveAstroType: (type: 'factory_astro' | 'churn_astro') => void
}

// Create context with default values
const AssistantContext = createContext<AssistantContextType>({
  activeAstroType: 'factory_astro',
  isAstroEnabled: true,
  isKgInsightsEnabled: true,
  setActiveAstroType: () => {}
})

// Custom hook to use the assistant context
export const useAssistant = () => useContext(AssistantContext)

export const AssistantProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Get active model from Djinni store
  const { activeModel, setActiveModel } = useDjinniStore()
  
  // Default to factory_astro if not set
  const [activeAstroType, setActiveAstroTypeState] = useState<'factory_astro' | 'churn_astro'>(
    (activeModel as 'factory_astro' | 'churn_astro') || 'factory_astro'
  )
  
  // For now, assume both are enabled - in a real implementation, 
  // these would be fetched from an admin settings API
  const [isAstroEnabled] = useState(true)
  const [isKgInsightsEnabled] = useState(true)
  
  // Update the active Astro type and sync with Djinni store
  const setActiveAstroType = (type: 'factory_astro' | 'churn_astro') => {
    setActiveAstroTypeState(type)
    setActiveModel(type)
    // Also save to localStorage for persistence
    localStorage.setItem('djinni_active_model', type)
  }
  
  // Effect to sync with localStorage and Djinni store
  useEffect(() => {
    const savedModel = localStorage.getItem('djinni_active_model') as 'factory_astro' | 'churn_astro' | null
    
    if (savedModel && (savedModel === 'factory_astro' || savedModel === 'churn_astro')) {
      setActiveAstroTypeState(savedModel)
      setActiveModel(savedModel)
    } else if (activeModel && (activeModel === 'factory_astro' || activeModel === 'churn_astro')) {
      setActiveAstroTypeState(activeModel as 'factory_astro' | 'churn_astro')
    }
    
    // Set up storage event listener for cross-tab synchronization
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'djinni_active_model') {
        const newModel = e.newValue as 'factory_astro' | 'churn_astro' | null
        if (newModel && (newModel === 'factory_astro' || newModel === 'churn_astro')) {
          setActiveAstroTypeState(newModel)
          setActiveModel(newModel)
        }
      }
    }
    
    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [activeModel, setActiveModel])
  
  // Provide the context values to the children
  return (
    <AssistantContext.Provider
      value={{
        activeAstroType,
        isAstroEnabled,
        isKgInsightsEnabled,
        setActiveAstroType
      }}
    >
      {children}
    </AssistantContext.Provider>
  )
}
