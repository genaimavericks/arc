import type React from "react"
import "./globals.css"
import { AuthProvider } from "@/lib/auth-context"
import { ThemeProvider } from "@/lib/theme-context"
import { IngestionProvider } from "@/lib/ingestion-context"
import { ActivityTracker } from "@/components/activity-tracker"
import { FloatingJobCard } from "@/components/datapuur/floating-job-card"
import { AnimatedBackground } from "@/components/ui/animated-background"
import { Toaster } from "@/components/ui/toaster"

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <ThemeProvider>
            <IngestionProvider>
              <ActivityTracker />
              <FloatingJobCard />
              <AnimatedBackground />
              <Toaster />
              {children}
            </IngestionProvider>
          </ThemeProvider>
        </AuthProvider>
      </body>
    </html>
  )
}

export const metadata = {
  generator: 'Team RSW',
  title: 'Cognitive Data Expert',
  description: 'RSW Application',
  icons: {
    icon: '/favicon.png',
    apple: '/favicon.png',
    shortcut: '/favicon.png'
  }
};
