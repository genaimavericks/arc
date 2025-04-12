"use client"

import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { BarChart3 } from "lucide-react"

export interface FloatingChartProps {
  count?: number;
  avoidRightSide?: boolean;
  zIndex?: number;
}

export function FloatingChart({ 
  count = 5, 
  avoidRightSide = true,
  zIndex = 0 
}: FloatingChartProps) {
  const [dimensions, setDimensions] = useState({ width: 1200, height: 800 })

  useEffect(() => {
    // Update dimensions only on client side
    setDimensions({
      width: window.innerWidth,
      height: window.innerHeight,
    })

    const handleResize = () => {
      setDimensions({
        width: window.innerWidth,
        height: window.innerHeight,
      })
    }

    window.addEventListener("resize", handleResize)
    return () => window.removeEventListener("resize", handleResize)
  }, [])

  // Calculate the maximum x position based on whether we should avoid the right side
  // If avoidRightSide is true, limit the x position to 60% of the screen width
  // This prevents floating charts from overlapping with the chat interface
  const getMaxX = () => {
    return avoidRightSide ? dimensions.width * 0.6 : dimensions.width
  }

  return (
    <div className="relative w-full h-full" style={{ zIndex }}>
      {Array.from({ length: count }).map((_, i) => {
        // Calculate random positions that respect the boundaries
        const maxX = getMaxX()
        const initialX = Math.random() * maxX
        const randomX1 = Math.random() * maxX
        const randomX2 = Math.random() * maxX
        const randomX3 = Math.random() * maxX
        
        return (
          <motion.div
            key={i}
            className="absolute"
            initial={{
              x: initialX,
              y: Math.random() * dimensions.height,
            }}
            animate={{
              x: [randomX1, randomX2, randomX3],
              y: [
                Math.random() * dimensions.height,
                Math.random() * dimensions.height,
                Math.random() * dimensions.height,
              ],
              rotate: [0, 180, 360],
            }}
            transition={{
              duration: 20 + Math.random() * 10,
              repeat: Number.POSITIVE_INFINITY,
              ease: "linear",
            }}
          >
            <div className="relative w-16 h-20 bg-card/50 backdrop-blur-sm rounded-lg border border-border flex items-center justify-center transform hover:scale-110 transition-transform shadow-sm">
              <BarChart3 className="w-8 h-8 text-primary/50" />
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}
