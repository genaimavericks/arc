import type React from "react"
import "./globals.css"
import { AuthProvider } from "@/lib/auth-context"
import { ThemeProvider } from "@/lib/theme-context"
import { IngestionProvider } from "@/lib/ingestion-context"
import { ActivityTracker } from "@/components/activity-tracker"
import { FloatingJobCard } from "@/components/datapuur/floating-job-card"

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <ThemeProvider>
            <IngestionProvider>
              <ActivityTracker />
              <FloatingJobCard />
              {children}
            </IngestionProvider>
          </ThemeProvider>
        </AuthProvider>
      </body>
    </html>
  )
}



import './globals.css'

export const metadata = {
      generator: 'v0.dev'
    };
