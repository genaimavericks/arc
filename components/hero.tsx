"use client"
import { motion } from "framer-motion"
import type React from "react"

import { FloatingPaper } from "@/components/floating-paper"
import { RoboAnimation } from "@/components/robo-animation"
import { Database, Network, ArrowRight } from "lucide-react"
import Link from "next/link"
import { useAuth } from "@/lib/auth-context"
import { useRouter } from "next/navigation"

export default function Hero() {
  const { user } = useAuth()

  return (
    <div className="relative min-h-[calc(100vh-76px)] flex flex-col items-center justify-center py-8">
      {/* Floating papers background */}
      <div className="absolute inset-0 overflow-hidden">
        <FloatingPaper count={6} />
      </div>

      <div className="container mx-auto px-6 relative z-10 flex flex-col items-center">
        <div className="max-w-4xl mx-auto text-center mb-8">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-foreground mb-4">
              Unlock the Power of Your Data
            </h1>
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="text-lg md:text-xl text-transparent bg-clip-text bg-gradient-to-r from-primary via-secondary to-accent font-medium mb-8"
            >
              Where AI meets insight, decisions meet success.
            </motion.p>
          </motion.div>
        </div>

        {/* Platform Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-5xl mx-auto w-full">
          {/* DataPuur Card */}
          <PlatformCard
            title="DataPuur Platform"
            description="Manage, transform, and analyze your data with our powerful data processing tools."
            icon={Database}
            href="/datapuur"
            color="from-primary via-secondary to-accent"
            features={[
              "Data ingestion from multiple sources",
              "Advanced transformation pipelines",
              "Interactive dashboards",
              "Export in various formats",
            ]}
            delay={0}
            requiresAuth={true}
            isLoggedIn={!!user}
          />

          {/* KGInsights Card */}
          <PlatformCard
            title="KGInsights Platform"
            description="Visualize and explore knowledge graphs with our advanced analytics tools."
            icon={Network}
            href="/kginsights/dashboard"
            color="from-secondary via-primary to-accent"
            features={[
              "Interactive graph visualization",
              "Entity relationship analysis",
              "Pattern detection algorithms",
              "Custom graph configurations",
            ]}
            delay={0.2}
            requiresAuth={true}
            isLoggedIn={!!user}
          />
        </div>
      </div>

      {/* Animated robot - moved to the side to avoid overlapping with cards */}
      <div className="absolute bottom-0 right-0 w-72 h-72 md:w-96 md:h-96">
        <RoboAnimation />
      </div>
    </div>
  )
}

interface PlatformCardProps {
  title: string
  description: string
  icon: React.ElementType
  href: string
  color: string
  features: string[]
  delay: number
  requiresAuth: boolean
  isLoggedIn: boolean
}

function PlatformCard({
  title,
  description,
  icon: Icon,
  href,
  color,
  features,
  delay,
  requiresAuth,
  isLoggedIn,
}: PlatformCardProps) {
  const { user } = useAuth()
  const router = useRouter()
  const hasKGInsightsAccess = user?.permissions?.includes('kginsights:access') || false

  const handleLoginRedirect = (e: React.MouseEvent) => {
    e.preventDefault()
    // Store the intended destination URL for post-login redirection
    localStorage.setItem("loginRedirectUrl", href)
    // Redirect to login page
    router.push("/login")
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      whileHover={{ y: -5 }}
      className="bg-card/80 backdrop-blur-sm rounded-xl border border-border overflow-hidden group"
    >
      <div className="p-5">
        <div className="flex items-center mb-4">
          <div className={`w-10 h-10 rounded-full bg-gradient-to-r ${color} flex items-center justify-center mr-3`}>
            <Icon className="w-5 h-5 text-white" />
          </div>
          <h3 className="text-xl font-semibold text-foreground">{title}</h3>
        </div>
        <p className="text-muted-foreground mb-4">{description}</p>
        <div className="space-y-2 mb-6">
          {features.map((feature, index) => (
            <div key={index} className="flex items-center text-sm text-muted-foreground">
              <ArrowRight className="w-4 h-4 mr-2 text-primary" />
              {feature}
            </div>
          ))}
        </div>
        {requiresAuth && !isLoggedIn ? (
          <button
            onClick={handleLoginRedirect}
            className="inline-flex items-center justify-center px-4 py-2 rounded-md text-sm text-primary-foreground bg-primary/80 hover:bg-primary/90 transition-colors"
          >
            Please login to access this platform
          </button>
        ) : (
          <Link
            href={href}
            className={`inline-flex items-center justify-center px-4 py-2 rounded-md ${
              (requiresAuth && !isLoggedIn)
                ? 'bg-gray-300 cursor-not-allowed'
                : 'bg-primary hover:bg-primary/90 text-primary-foreground'
            }`}
          >
            Explore Platform
          </Link>
        )}
      </div>
    </motion.div>
  )
}
