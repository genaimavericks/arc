"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Button } from "@/components/ui/button"
import { MinusCircle, PlusCircle, Settings, Circle } from "lucide-react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { ChartTheme } from "./chart-visualization"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"

const THEME_PRESETS = {
  default: {
    name: "Default",
    colors: ["#6366f1", "#8b5cf6", "#ec4899", "#f43f5e", "#f97316", "#eab308", "#22c55e", "#06b6d4"],
    backgroundColor: "transparent",
    textColor: "#64748b", 
    gridColor: "#e2e8f0"
  },
  dark: {
    name: "Dark",
    colors: ["#818cf8", "#a78bfa", "#f472b6", "#fb7185", "#fb923c", "#facc15", "#4ade80", "#22d3ee"],
    backgroundColor: "#1e293b", 
    textColor: "#cbd5e1",
    gridColor: "#334155"
  },
  monochrome: {
    name: "Monochrome",
    colors: ["#1e293b", "#334155", "#475569", "#64748b", "#94a3b8", "#cbd5e1", "#e2e8f0", "#f8fafc"],
    backgroundColor: "transparent",
    textColor: "#475569",
    gridColor: "#e2e8f0"
  },
  pastel: {
    name: "Pastel",
    colors: ["#c4b5fd", "#ddd6fe", "#fbcfe8", "#fecdd3", "#fed7aa", "#fef3c7", "#bbf7d0", "#bae6fd"],
    backgroundColor: "transparent",
    textColor: "#64748b",
    gridColor: "#e2e8f0"
  }
}

interface ThemeConfigProps {
  onThemeChange: (theme: ChartTheme) => void
}

export function ThemeConfig({ onThemeChange }: ThemeConfigProps) {
  const [expanded, setExpanded] = useState(false)
  const [selectedPreset, setSelectedPreset] = useState<string>("default")
  const [customTheme, setCustomTheme] = useState<ChartTheme>({...THEME_PRESETS.default})
  const [useDarkMode, setUseDarkMode] = useState(false)

  const handlePresetChange = (preset: string) => {
    setSelectedPreset(preset)
    const theme = {...THEME_PRESETS[preset as keyof typeof THEME_PRESETS]}
    
    // Apply dark mode if enabled
    if (useDarkMode && preset !== "dark") {
      theme.backgroundColor = "#1e293b"
      theme.textColor = "#cbd5e1"
      theme.gridColor = "#334155"
    }
    
    setCustomTheme(theme)
    onThemeChange(theme)
  }

  const handleDarkModeToggle = (checked: boolean) => {
    setUseDarkMode(checked)
    
    // Update the theme based on dark mode
    const updatedTheme = {...customTheme}
    
    if (checked) {
      updatedTheme.backgroundColor = "#1e293b"
      updatedTheme.textColor = "#cbd5e1"
      updatedTheme.gridColor = "#334155"
    } else {
      // Reset to preset defaults for background/text/grid
      const preset = THEME_PRESETS[selectedPreset as keyof typeof THEME_PRESETS]
      updatedTheme.backgroundColor = preset.backgroundColor
      updatedTheme.textColor = preset.textColor
      updatedTheme.gridColor = preset.gridColor
    }
    
    setCustomTheme(updatedTheme)
    onThemeChange(updatedTheme)
  }

  return (
    <Card className="w-full shadow-sm">
      <CardHeader className="pb-2">
        <div className="flex justify-between items-center">
          <div>
            <CardTitle className="text-sm font-medium flex items-center">
              <Settings className="h-4 w-4 mr-2 text-muted-foreground" />
              Chart Theme
            </CardTitle>
            {expanded && (
              <CardDescription className="text-xs mt-1">
                Customize the appearance of chart visualizations
              </CardDescription>
            )}
          </div>
          <Button 
            variant="ghost" 
            size="sm" 
            className="h-8 w-8 p-0"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? (
              <MinusCircle className="h-4 w-4" />
            ) : (
              <PlusCircle className="h-4 w-4" />
            )}
          </Button>
        </div>
      </CardHeader>

      {expanded && (
        <CardContent className="pt-0">
          <ScrollArea className="max-h-60">
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="theme-preset">Theme Preset</Label>
                <Select 
                  value={selectedPreset} 
                  onValueChange={handlePresetChange}
                >
                  <SelectTrigger id="theme-preset">
                    <SelectValue placeholder="Select theme" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(THEME_PRESETS).map(([key, theme]) => (
                      <SelectItem key={key} value={key}>
                        {theme.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label>Color Palette</Label>
                <div className="flex flex-wrap gap-2">
                  {customTheme.colors.slice(0, 6).map((color, index) => (
                    <div 
                      key={index}
                      className="w-6 h-6 rounded-full border"
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
              </div>
              
              <div className="flex items-center justify-between space-x-2">
                <Label htmlFor="dark-mode">Dark Mode</Label>
                <Switch 
                  id="dark-mode" 
                  checked={useDarkMode}
                  onCheckedChange={handleDarkModeToggle}
                />
              </div>
            </div>
          </ScrollArea>
        </CardContent>
      )}
    </Card>
  )
}
