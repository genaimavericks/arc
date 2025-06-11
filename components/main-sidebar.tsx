"use client"

import React, { useState, useEffect } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { 
  LayoutDashboard, 
  FileInput, 
  Wand2, 
  Download, 
  BarChart2, 
  GitBranch, 
  MessageSquare, 
  Settings,
  ChevronDown,
  ChevronRight,
  ChevronLeft,
  HelpCircle,
  Database,
  NetworkIcon,
  LogOut,
  User,
  Bot,
  Brain,
  Zap,
  Clock
} from "lucide-react"
import { useAuth } from "@/lib/auth-context"
import { motion } from "framer-motion"

interface SidebarMenuItemProps {
  href: string
  icon: React.ElementType
  label: string
  isActive: boolean
  collapsed?: boolean
}

const SidebarMenuItem: React.FC<SidebarMenuItemProps> = ({ href, icon: Icon, label, isActive, collapsed }) => {
  const { logout } = useAuth()
  
  // Handle special case for logout link
  if (label === "Logout") {
    return (
      <button
        onClick={(e) => {
          e.preventDefault()
          logout()
        }}
        className={cn(
          "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200 w-full text-left",
          "text-muted-foreground hover:text-foreground hover:bg-accent/50"
        )}
        title={collapsed ? label : undefined}
      >
        <Icon className="h-4 w-4" />
        {!collapsed && <span>{label}</span>}
      </button>
    )
  }
  
  // Regular menu item
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200",
        isActive 
          ? "bg-accent text-accent-foreground" 
          : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
      )}
      title={collapsed ? label : undefined}
    >
      <Icon className="h-4 w-4" />
      {!collapsed && <span>{label}</span>}
      {isActive && (
        <motion.div
          layoutId="sidebar-indicator"
          className="absolute left-0 w-1 h-8 bg-primary rounded-r-full"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.2 }}
        />
      )}
    </Link>
  )
}

interface MenuSection {
  label: string
  icon: React.ElementType
  href: string
  subItems?: {
    label: string
    href: string
    icon: React.ElementType
  }[]
}

export function MainSidebar() {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    "datapuur": pathname.startsWith("/datapuur"),
    "kginsights": pathname.startsWith("/kginsights")
  })
  const { user, logout } = useAuth()
  
  // Initialize collapsed state from localStorage
  useEffect(() => {
    const savedState = localStorage.getItem('datapuur-sidebar-collapsed')
    if (savedState) {
      setCollapsed(savedState === 'true')
    }
  }, [])
  
  // Toggle sidebar collapsed state
  const toggleSidebar = () => {
    const newState = !collapsed
    setCollapsed(newState)
    localStorage.setItem('datapuur-sidebar-collapsed', String(newState))
    
    // Dispatch a custom event to notify other components
    window.dispatchEvent(new Event('sidebarStateChange'))
  }

  // Group menu sections by category
  const allCommandCenters = [
    {
      label: "Sales Overview",
      icon: LayoutDashboard,
      href: "/",
      requiredPermission: "command:read",
      subItems: [
        {
          label: "Sales Performance",
          icon: BarChart2,
          href: "/sales-performance",
        }
      ]
    },
    {
      label: "Inventory Overview",
      icon: Database,
      href: "/inventory",
      requiredPermission: "command:read"
    },
    {
      label: "Financial Overview",
      icon: BarChart2,
      href: "/financial",
      requiredPermission: "command:read"
    }
  ]
  
  // Filter command centers based on user permissions
  const commandCenters = allCommandCenters.filter(item => {
    if (!user || !user.permissions) return false
    return user.permissions.includes(item.requiredPermission)
  })
  
  const allDjinni = [
    {
      label: "Djinni Assistant",
      icon: Bot,
      href: "/djinni",
      requiredPermission: "djinni:read"
    },
    {
      label: "Conversations",
      icon: Clock,
      href: "/conversations",
      requiredPermission: "djinni:read"
    }
  ]

  // Filter djinni items based on user permissions
  const djinni = allDjinni.filter(item => {
    if (!user || !user.permissions) return false
    return user.permissions.includes(item.requiredPermission)
  })
  
  // Define all possible tools
  const allTools = [
    {
      label: "DataPuur",
      icon: Database,
      href: "/datapuur",
      requiredPermission: "datapuur:read",
      subItems: [
        { label: "Dashboard", href: "/datapuur", icon: LayoutDashboard },
        { label: "Ingestion", href: "/datapuur/ingestion", icon: FileInput },
        { label: "Profiles", href: "/datapuur/profile", icon: BarChart2 },
        { label: "AI Profile", href: "/datapuur/ai-profile", icon: Brain },
        { label: "AI Transformation", href: "/datapuur/ai-transformation", icon: Zap },
        { label: "Data Catalog", href: "/datapuur/data-catalog", icon: Database },
        { label: "Export", href: "/datapuur/export", icon: Download }
      ]
    },
    {
      label: "K-Graff",
      icon: NetworkIcon,
      href: "/kginsights/dashboard",
      requiredPermission: "kginsights:read",
      subItems: [
        { label: "KGraph Dashboard", href: "/kginsights/dashboard", icon: LayoutDashboard },
        { label: "KGraph Insights", href: "/kginsights/insights", icon: MessageSquare },
        { label: "Generate Graph", href: "/kginsights/generate", icon: GitBranch },
        { label: "Manage KGraph", href: "/kginsights/manage", icon: Settings }
      ]
    }
  ]
  
  // Filter tools based on user permissions
  const tools = allTools.filter(tool => {
    if (!user || !user.permissions) return false
    
    // Check if user has the required permission for this tool
    return user.permissions.includes(tool.requiredPermission)
  })
  
  const allPersonalDashboards = [
    {
      label: "My Dashboards",
      icon: LayoutDashboard,
      href: "/dashboards",
      requiredPermission: "dashboard:read"
    },
    {
      label: "Dashboard Creator",
      icon: Wand2,
      href: "/dashboard-creator",
      requiredPermission: "dashboard:write"
    },
    {
      label: "Recent Activity",
      icon: BarChart2,
      href: "/activity",
      requiredPermission: "dashboard:read"
    }
  ]
  
  // Filter personal dashboards based on user permissions
  const personalDashboards = allPersonalDashboards.filter(item => {
    if (!user || !user.permissions) return false
    return user.permissions.includes(item.requiredPermission)
  })
  
  // Filter system options based on user role
  const getSystemOptions = () => {
    const baseOptions = [
      {
        label: "Help",
        icon: HelpCircle,
        href: "/help",
      }
    ]
    
    // Only show Settings to admin users
    if (user?.role === "admin") {
      return [
        {
          label: "Settings",
          icon: Settings,
          href: "/admin",
        },
        ...baseOptions
      ]
    }
    
    return baseOptions
  }
  
  const systemOptions = getSystemOptions()

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }))
  }

  return (
    <div 
      className={cn(
        "group flex flex-col h-full bg-card/50 border-r border-border transition-all duration-300",
        collapsed && "items-center"
      )}
      data-collapsed={collapsed}
    >
      <div className={cn("px-3 py-2 w-full flex-1 overflow-y-auto", collapsed && "flex flex-col items-center")}>
        <div className="flex flex-col h-full">  
        <div className="flex items-center justify-between w-full mb-2 px-4">
          {!collapsed && user && (
            <div className="flex items-center gap-2">
              <div className="flex items-center justify-center bg-primary/10 text-primary rounded-full w-8 h-8">
                <User size={16} />
              </div>
              <div className="flex flex-col">
                <span className="text-sm font-medium">{user.username || 'admin'}</span>
                <span className="text-xs text-muted-foreground capitalize">{user.role || 'Admin'}</span>
              </div>
            </div>
          )}
          <button 
            onClick={toggleSidebar} 
            className="p-2 rounded-md hover:bg-accent transition-colors"
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>
        
        {/* Separator between user info and menu */}
        {!collapsed && <div className="border-t border-border my-3 mx-2"></div>}
        
        <nav className={cn("space-y-4 px-2", collapsed && "flex flex-col items-center w-full")}>
          {/* Command Centers Section - only show if user has permissions */}
          {commandCenters.length > 0 && (
          <div className="space-y-1">
            {!collapsed && (
              <h3 className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                Command Centers
              </h3>
            )}
            {commandCenters.map((section) => (
              <div key={section.label} className={cn("py-1", collapsed && "w-full flex justify-center")}>
                {section.subItems ? (
                  <div className={cn("space-y-1", collapsed && "w-full flex flex-col items-center")}>
                    <button
                      onClick={() => {
                        if (collapsed) {
                          // If sidebar is collapsed, expand it first
                          setCollapsed(false);
                          localStorage.setItem('datapuur-sidebar-collapsed', 'false');
                          window.dispatchEvent(new Event('sidebarStateChange'));
                          
                          // Then expand the section after a short delay to ensure the sidebar has expanded
                          setTimeout(() => {
                            setExpandedSections(prev => ({
                              ...prev,
                              [section.label.toLowerCase()]: true
                            }));
                          }, 100);
                        } else {
                          // If sidebar is already expanded, just toggle the section
                          toggleSection(section.label.toLowerCase());
                        }
                      }}
                      className={cn(
                        "flex items-center rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                        collapsed ? "justify-center" : "w-full justify-between",
                        (section.href === "/" ? pathname === "/" : pathname.startsWith(section.href))
                          ? "bg-accent text-accent-foreground"
                          : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
                      )}
                      title={collapsed ? section.label : undefined}
                    >
                      <div className={cn("flex items-center", !collapsed && "gap-3")}>
                        <section.icon className="h-4 w-4" />
                        {!collapsed && <span>{section.label}</span>}
                      </div>
                      {!collapsed && (expandedSections[section.label.toLowerCase()] ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      ))}
                    </button>
                    
                    {expandedSections[section.label.toLowerCase()] && !collapsed && (
                      <div className="ml-4 space-y-1 border-l border-border pl-3">
                        {section.subItems?.map((item) => (
                          <SidebarMenuItem
                            key={item.href}
                            href={item.href}
                            icon={item.icon}
                            label={item.label}
                            isActive={
                              pathname === item.href ||
                              (item.href !== section.href && pathname.startsWith(item.href))
                            }
                            collapsed={collapsed}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <SidebarMenuItem
                    href={section.href}
                    icon={section.icon}
                    label={section.label}
                    isActive={section.href === "/" ? pathname === "/" : (pathname === section.href || pathname.startsWith(`${section.href}/`))}
                    collapsed={collapsed}
                  />
                )}
              </div>
            ))}
          </div>
          )}
          
          {/* Personal Dashboard Section - only show if user has permissions */}
          {personalDashboards.length > 0 && (
          <div className="space-y-1 pt-2">
            {!collapsed && (
              <h3 className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                Personal Dashboard
              </h3>
            )}
            {personalDashboards.map((section) => (
              <div key={section.label} className={cn("py-1", collapsed && "w-full flex justify-center")}>
                <SidebarMenuItem
                  href={section.href}
                  icon={section.icon}
                  label={section.label}
                  isActive={section.href === "/" ? pathname === "/" : (pathname === section.href || pathname.startsWith(`${section.href}/`))}
                  collapsed={collapsed}
                />
              </div>
            ))}
          </div>
          )}
          
          {/* Djinni Section - only show if user has permissions */}
          {djinni.length > 0 && (
          <div className="space-y-1 pt-2">
            {!collapsed && (
              <h3 className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                Djinni
              </h3>
            )}
            {djinni.map((section) => (
              <div key={section.label} className={cn("py-1", collapsed && "w-full flex justify-center")}>
                <SidebarMenuItem
                  href={section.href}
                  icon={section.icon}
                  label={section.label}
                  isActive={section.href === "/" ? pathname === "/" : (pathname === section.href || pathname.startsWith(`${section.href}/`))}
                  collapsed={collapsed}
                />
              </div>
            ))}
          </div>
          )}
          
          {/* Tools Section - only show if user has permissions */}
          {tools.length > 0 && (
          <div className="space-y-1 pt-2">
            {!collapsed && (
              <h3 className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                Tools
              </h3>
            )}
            {tools.map((section) => (
              <div key={section.label} className={cn("py-1", collapsed && "w-full flex justify-center")}>
                <div className={cn("space-y-1", collapsed && "w-full flex flex-col items-center")}>
                  <button
                    onClick={() => {
                      if (collapsed) {
                        // If sidebar is collapsed, expand it first
                        setCollapsed(false);
                        localStorage.setItem('datapuur-sidebar-collapsed', 'false');
                        window.dispatchEvent(new Event('sidebarStateChange'));
                        
                        // Then expand the section after a short delay to ensure the sidebar has expanded
                        setTimeout(() => {
                          setExpandedSections(prev => ({
                            ...prev,
                            [section.label.toLowerCase()]: true
                          }));
                        }, 100);
                      } else {
                        // If sidebar is already expanded, just toggle the section
                        toggleSection(section.label.toLowerCase());
                      }
                    }}
                    className={cn(
                      "flex items-center rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                      collapsed ? "justify-center" : "w-full justify-between",
                      (section.href === "/" ? pathname === "/" : pathname.startsWith(section.href))
                        ? "bg-accent text-accent-foreground"
                        : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
                    )}
                    title={collapsed ? section.label : undefined}
                  >
                    <div className={cn("flex items-center", !collapsed && "gap-3")}>
                      <section.icon className="h-4 w-4" />
                      {!collapsed && <span>{section.label}</span>}
                    </div>
                    {!collapsed && (expandedSections[section.label.toLowerCase()] ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    ))}
                  </button>
                  
                  {expandedSections[section.label.toLowerCase()] && !collapsed && (
                    <div className="ml-4 space-y-1 border-l border-border pl-3">
                      {section.subItems?.map((item) => (
                        <SidebarMenuItem
                          key={item.href}
                          href={item.href}
                          icon={item.icon}
                          label={item.label}
                          isActive={
                            pathname === item.href ||
                            (item.href !== section.href && pathname.startsWith(item.href))
                          }
                          collapsed={collapsed}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
          )}
          
          {/* System Options */}
          <div className="space-y-1 pt-2">
            {!collapsed && (
              <h3 className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                System
              </h3>
            )}
            {systemOptions.map((section) => (
              <div key={section.label} className={cn("py-1", collapsed && "w-full flex justify-center")}>
                <SidebarMenuItem
                  href={section.href}
                  icon={section.icon}
                  label={section.label}
                  isActive={section.href === "/" ? pathname === "/" : (pathname === section.href || pathname.startsWith(`${section.href}/`))}
                  collapsed={collapsed}
                />
              </div>
            ))}
          </div>
        </nav>
        </div>
      </div>
      
      {/* User profile section or login option - fixed at bottom */}
      <div className={cn(
        "border-t border-border py-3 px-4 sticky bottom-0 bg-card/95 backdrop-blur-sm",
        collapsed ? "flex justify-center" : ""  
      )}>
        {user ? (
          <div className={cn(
            "flex items-center", 
            collapsed ? "flex-col space-y-2" : "space-x-3"
          )}>
            <div className="flex items-center justify-center bg-primary/10 text-primary rounded-full w-8 h-8">
              <User size={16} />
            </div>
            
            {!collapsed && (
              <div className="flex-1 overflow-hidden">
                <p className="text-sm font-medium truncate">{user.username}</p>
                <p className="text-xs text-muted-foreground truncate capitalize">{user.role}</p>
              </div>
            )}
            
            {!collapsed && (
              <button 
                onClick={logout}
                className="p-1.5 rounded-md hover:bg-accent transition-colors"
                title="Logout"
              >
                <LogOut size={16} />
              </button>
            )}
          </div>
        ) : (
          <div className={collapsed ? "flex flex-col items-center" : ""}>
            {collapsed ? (
              <Link href="/login">
                <div className="flex items-center justify-center bg-primary/10 text-primary rounded-full w-8 h-8" title="Login">
                  <User size={16} />
                </div>
              </Link>
            ) : (
              <Link href="/login" className="flex items-center gap-2 py-1 px-2 rounded-md hover:bg-accent transition-colors w-full">
                <div className="flex items-center justify-center bg-primary/10 text-primary rounded-full w-8 h-8">
                  <User size={16} />
                </div>
                <span className="text-sm font-medium">Login</span>
              </Link>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
