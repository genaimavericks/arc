  "use client"

import React, { useEffect, useState } from "react"
import { useTheme } from "@/lib/theme-context"
import { cn } from "@/lib/utils"

type Particle = {
  id: number
  x: number
  y: number
  size: number
  color: string
  speed: number
  opacity: number
}

export const AnimatedBackground: React.FC = () => {
  const { theme } = useTheme()
  const [mounted, setMounted] = useState(false)
  const [particles, setParticles] = useState<Particle[]>([])

  useEffect(() => {
    setMounted(true)
    
    // Generate random particles for both themes
    const generateParticles = () => {
      const newParticles: Particle[] = []
      const count = Math.min(window.innerWidth / 20, 25) // Responsive particle count
      
      for (let i = 0; i < count; i++) {
        newParticles.push({
          id: i,
          x: Math.random() * 100,
          y: Math.random() * 100,
          size: Math.random() * 10 + 2,
          color: theme === "dark" 
            ? `hsla(${Math.random() * 60 + 200}, 70%, 70%, ${Math.random() * 0.4 + 0.1})` 
            : `hsla(${Math.random() * 60 + 180}, 70%, 50%, ${Math.random() * 0.2 + 0.1})`,
          speed: Math.random() * 3 + 1,
          opacity: Math.random() * 0.7 + 0.3
        })
      }
      
      setParticles(newParticles)
    }

    generateParticles()
    
    // Regenerate particles when window resizes
    const handleResize = () => {
      generateParticles()
    }

    window.addEventListener('resize', handleResize)
    return () => {
      window.removeEventListener('resize', handleResize)
    }
  }, [theme])

  // Handle server-side rendering
  if (!mounted) return null

  return (
    <>
      {/* Light Mode Animated Elements */}
      {theme === "light" && (
        <>
          <div className="light-mode-background fixed inset-0 -z-10 bg-gradient-to-br from-blue-50 to-indigo-50" />
          
          {/* Animated particles */}
          <div className="light-mode-particles fixed inset-0 -z-10">
            {particles.map((particle) => (
              <div
                key={particle.id}
                className="absolute rounded-full animate-particle-float"
                style={{
                  left: `${particle.x}%`,
                  top: `${particle.y}%`,
                  width: `${particle.size}px`,
                  height: `${particle.size}px`,
                  backgroundColor: particle.color,
                  opacity: particle.opacity,
                  animationDuration: `${particle.speed + 5}s`,
                  animationDelay: `${particle.id * 0.2}s`
                }}
              />
            ))}
          </div>
          
          {/* Floating orbs */}
          <div className="light-mode-orbs fixed inset-0 -z-10">
            <div className="absolute w-40 h-40 rounded-full bg-blue-200/20 animate-float" 
                 style={{ left: '10%', top: '20%', animationDelay: '0s' }} />
            <div className="absolute w-64 h-64 rounded-full bg-indigo-200/10 animate-float" 
                 style={{ right: '15%', bottom: '10%', animationDelay: '1s' }} />
            <div className="absolute w-32 h-32 rounded-full bg-sky-200/15 animate-float" 
                 style={{ right: '30%', top: '15%', animationDelay: '2s' }} />
          </div>
          
          {/* Gradient mesh */}
          <div className="light-mode-mesh fixed inset-0 -z-10 opacity-20 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-primary/5 via-transparent to-transparent" />
        </>
      )}

      {/* Dark Mode Animated Elements */}
      {theme === "dark" && (
        <>
          <div className="dark-mode-background fixed inset-0 -z-10 bg-gradient-to-br from-gray-950 to-indigo-950" />
          
          {/* Star field */}
          <div className="dark-mode-stars fixed inset-0 -z-10">
            {particles.map((particle) => (
              <div
                key={particle.id}
                className={cn(
                  "absolute rounded-full",
                  particle.size > 6 ? "animate-pulse-glow" : "animate-particle-float"
                )}
                style={{
                  left: `${particle.x}%`,
                  top: `${particle.y}%`,
                  width: `${particle.size}px`,
                  height: `${particle.size}px`,
                  backgroundColor: particle.color,
                  opacity: particle.opacity,
                  boxShadow: `0 0 ${particle.size * 2}px ${particle.color}`,
                  animationDuration: `${particle.speed + 5}s`,
                  animationDelay: `${particle.id * 0.2}s`
                }}
              />
            ))}
          </div>
          
          {/* Cosmic elements */}
          <div className="dark-mode-cosmic fixed inset-0 -z-10">
            <div className="absolute w-64 h-64 rounded-full bg-indigo-500/5 blur-2xl animate-rotate-spin" 
                 style={{ left: '30%', top: '40%', transformOrigin: 'center' }} />
            <div className="absolute w-80 h-80 rounded-full bg-purple-500/5 blur-3xl animate-rotate-spin" 
                 style={{ right: '25%', bottom: '35%', animationDirection: 'reverse', transformOrigin: 'center' }} />
          </div>
          
          {/* Animated waves */}
          <div className="dark-mode-waves fixed inset-0 -z-10 overflow-hidden">
            <div className="wave absolute w-[200%] h-[150px] bottom-[-2%] left-[-50%] opacity-10 bg-gradient-to-r from-blue-600 to-indigo-600 animate-[float_15s_ease-in-out_infinite]" 
                 style={{ borderRadius: '40%' }} />
            <div className="wave absolute w-[200%] h-[200px] bottom-[-5%] left-[-50%] opacity-5 bg-gradient-to-r from-indigo-600 to-purple-600 animate-[float_20s_ease-in-out_infinite_reverse]" 
                 style={{ borderRadius: '35%' }} />
            <div className="wave absolute w-[200%] h-[250px] bottom-[-8%] left-[-50%] opacity-5 bg-gradient-to-r from-purple-600 to-blue-600 animate-[float_25s_ease-in-out_infinite]" 
                 style={{ borderRadius: '30%' }} />
          </div>
          
          {/* Gradient overlay */}
          <div className="dark-mode-overlay fixed inset-0 -z-10 bg-gradient-radial from-transparent to-background/80" />
        </>
      )}
    </>
  )
}
