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
  Clock,
  Factory,
  Sparkles
} from "lucide-react"
import { useAuth } from "@/lib/auth-context"
import { useDjinniStore } from "@/lib/djinni/store"
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
  
  // Check if this is a tab navigation link (contains query parameters)
  const hasQueryParams = href.includes('?')
  
  // For items with query parameters, use a custom handler to ensure navigation works correctly
  if (hasQueryParams) {
    // Determine if this item is active based on the URL and query parameters
    const basePath = href.split('?')[0]
    const queryParam = href.split('?')[1]
    
    // Check if we're on the correct page and have the correct query parameter
    const isItemActive = typeof window !== 'undefined' && 
      window.location.pathname === basePath && 
      window.location.search.includes(queryParam)
    
    // Special case for Telecom Churn Dashboard to reduce spacing
    const isChurnDashboard = label === "Churn Dashboard"
    
    return (
      <a
        href={href}
        onClick={(e) => {
          // Force a full navigation to ensure the page reloads with the new query parameters
          // This is necessary for tab switching within the same base URL
          window.location.href = href
          e.preventDefault()
        }}
        className={cn(
          "flex items-center rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200",
          isChurnDashboard ? "gap-1" : "gap-3", // Reduced gap for Telecom Churn Dashboard
          isItemActive 
            ? "bg-accent text-accent-foreground" 
            : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
        )}
        title={collapsed ? label : undefined}
      >
        <Icon className="h-4 w-4" />
        {!collapsed && <span>{label}</span>}
        {isItemActive && (
          <motion.div
            layoutId="sidebar-indicator"
            className="absolute left-0 w-1 h-8 bg-primary rounded-r-full"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.2 }}
          />
        )}
      </a>
    )
  }
  
  // Regular menu item (no query parameters)
  // Special case for Telecom Churn Dashboard to reduce spacing
  const isChurnDashboard = label === "Churn Dashboard"
  
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200",
        isChurnDashboard ? "gap-1" : "gap-3", // Reduced gap for Telecom Churn Dashboard
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
  key?: string
  requiredPermission?: string
  subItems?: {
    label: string
    href: string
    icon: React.ElementType
    requiredPermission?: string
  }[]
}

export function MainSidebar() {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    "datapuur": pathname.startsWith("/datapuur"),
    "kginsights": pathname.startsWith("/kginsights") && !pathname.startsWith("/kginsights/insights"),
    "k-graff": pathname.startsWith("/kginsights") && !pathname.startsWith("/djinni/kgraph-insights"),
    "factory-dashboard": pathname === "/" || pathname.includes("?tab=") || pathname.startsWith("/factory_dashboard"),
    "djinni-assistant": pathname.startsWith("/djinni")
  })
  const { user, logout } = useAuth()
  const { activeModel } = useDjinniStore()
  
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
  
  // Update expanded sections when pathname changes
  useEffect(() => {
    setExpandedSections(prev => ({
      ...prev,
      "datapuur": pathname.startsWith("/datapuur"),
      "kginsights": pathname.startsWith("/kginsights") && !pathname.startsWith("/kginsights/insights"),
      "k-graff": pathname.startsWith("/kginsights") && !pathname.startsWith("/djinni/kgraph-insights"),
      "factory-dashboard": pathname === "/" || pathname.startsWith("/factory_dashboard"),
      "churn-dashboard": pathname.startsWith("/churn_dashboard"),
      "sales-overview": pathname === "/" || pathname.startsWith("/sales-performance"),
      "djinni-assistant": pathname.startsWith("/djinni")
    }))
  }, [pathname])

  // Track the active model from both Zustand store and localStorage for dashboard filtering
  const djinniStore = useDjinniStore();
  const [activeModelState, setActiveModelState] = useState<string>(() => {
    // Initialize from localStorage if available, otherwise use store
    if (typeof window !== 'undefined') {
      const localModel = localStorage.getItem('djinni_active_model');
      return localModel || djinniStore.activeModel || "factory_astro"; // Default to factory_astro if not set
    }
    return djinniStore.activeModel || "factory_astro";
  });
  
  // Effect to keep track of model changes for dashboard filtering
  useEffect(() => {
    // Function to check and update the active model - defined inside the effect
    const checkActiveModel = () => {
      if (typeof window !== 'undefined') {
        const localModel = localStorage.getItem('djinni_active_model');
        const storeModel = djinniStore.activeModel;
        
        // Prioritize localStorage value as it's updated by the admin settings
        const newModel = localModel || storeModel;
        
        if (newModel !== activeModelState) {
          console.log(`Model changed: ${activeModelState} -> ${newModel}`);
          setActiveModelState(newModel);
          
          // Also update the Zustand store to keep it in sync
          if (localModel && localModel !== storeModel) {
            djinniStore.setActiveModel(localModel as any);
          }
        }
      }
    };
    
    // Check immediately
    checkActiveModel();
    
    // Set up an interval to check for changes
    const intervalId = setInterval(checkActiveModel, 1000);
    
    // Set up storage event listener for immediate updates
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'djinni_active_model') {
        checkActiveModel();
      }
    };
    
    window.addEventListener('storage', handleStorageChange);
    
    return () => {
      clearInterval(intervalId);
      window.removeEventListener('storage', handleStorageChange);
    };
  }, [djinniStore, activeModelState]);
  
  // Removed getActiveModelSubmenu function as we're no longer using submenu items for Djinni Assistant

  // Define all possible command centers
  const factoryDashboard: MenuSection = {
    label: "Factory Dashboard",
    icon: Factory,
    href: "/",
    key: "factory-dashboard",
    requiredPermission: "command:read",
    subItems: [
      { 
        label: "Performance Overview", 
        href: "/", 
        icon: LayoutDashboard,
        requiredPermission: "command:read" 
      },
      {
        label: "Operations & Maintenance",
        icon: BarChart2,
        href: "/factory_dashboard/operations",
        requiredPermission: "command:read"
      },
      {
        label: "Workforce & Resources",
        icon: BarChart2,
        href: "/factory_dashboard/workforce",
        requiredPermission: "command:read"
      }
    ]
  };
  
  const churnDashboard: MenuSection = {
    label: "Churn Dashboard",
    icon: BarChart2,
    href: "/churn_dashboard",
    key: "churn-dashboard",
    requiredPermission: "command:read",
    subItems: [
      {
        label: "Summary",
        icon: LayoutDashboard,
        href: "/churn_dashboard",
        requiredPermission: "command:read"
      },
      {
        label: "Customer Profile",
        icon: BarChart2,
        href: "/churn_dashboard/customer",
        requiredPermission: "command:read"
      },
      {
        label: "Churner Profile",
        icon: BarChart2,
        href: "/churn_dashboard/churner",
        requiredPermission: "command:read"
      }
    ]
  };
  
  // Conditionally include dashboards based on active model
  const allCommandCenters: MenuSection[] = [];
  
  // Add the appropriate dashboard based on active model
  if (activeModelState === "churn_astro") {
    allCommandCenters.push(churnDashboard);
  } else {
    // Default to factory dashboard for any other model or factory_astro
    allCommandCenters.push(factoryDashboard);
  }
  
  // Filter command centers based on user permissions
  const commandCenters = allCommandCenters.filter(item => {
    if (!user || !user.permissions || !item.requiredPermission) return false
    return user.permissions.includes(item.requiredPermission as string)
  })
  
  // Check for changes in localStorage and Zustand store
  useEffect(() => {
    const checkActiveModel = () => {
      if (typeof window !== 'undefined') {
        const localModel = localStorage.getItem('djinni_active_model');
        const storeModel = djinniStore.activeModel;
        
        // Prioritize localStorage value as it's updated by the admin settings
        const newModel = localModel || storeModel;
        
        if (newModel !== activeModelState) {
          console.log(`Model changed: ${activeModelState} -> ${newModel}`);
          setActiveModelState(newModel);
          
          // Also update the Zustand store to keep it in sync
          if (localModel && localModel !== storeModel) {
            djinniStore.setActiveModel(localModel as any);
          }
        }
      }
    };
    
    // Check immediately
    checkActiveModel();
    
    // Set up an interval to check for changes
    const intervalId = setInterval(checkActiveModel, 1000);
    
    // Set up storage event listener for immediate updates
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'djinni_active_model') {
        checkActiveModel();
      }
    };
    
    window.addEventListener('storage', handleStorageChange);
    
    return () => {
      clearInterval(intervalId);
      window.removeEventListener('storage', handleStorageChange);
    };
  }, [djinniStore, activeModelState]);
  
  // Define all possible djinni items
  const allDjinni: MenuSection[] = [
    {
      label: "Djinni Assistant",
      icon: Bot,
      href: "/djinni/assistant",
      key: "djinni-assistant",
      requiredPermission: "djinni:read"
    },
    {
      label: "Conversations",
      icon: Clock,
      href: "/conversations",
      key: "conversations",
      requiredPermission: "djinni:read"
    }
  ]

  // Filter djinni items based on user permissions
  const djinni = allDjinni.filter(item => {
    if (!user || !user.permissions || !item.requiredPermission) return false
    return user.permissions.includes(item.requiredPermission as string)
  })
  
  // Define all possible tools
  const allTools: MenuSection[] = [
    {
      label: "DataPuur",
      icon: Database,
      href: "/datapuur",
      requiredPermission: "datapuur:read",
      key: "datapuur", // Add a key property for consistent identification
      subItems: [
        { label: "Dashboard", href: "/datapuur", icon: LayoutDashboard, requiredPermission: "datapuur:read" },
        { label: "Ingestion", href: "/datapuur/ingestion", icon: FileInput, requiredPermission: "datapuur:write" },
        { label: "AI Profile", href: "/datapuur/ai-profile", icon: Brain, requiredPermission: "datapuur:write" },
        { label: "AI Transformation", href: "/datapuur/ai-transformation", icon: Zap, requiredPermission: "datapuur:write" },
        { label: "Data Catalog", href: "/datapuur/data-catalog", icon: Database, requiredPermission: "datapuur:read" },
        { label: "Export", href: "/datapuur/export", icon: Download, requiredPermission: "datapuur:write" }
      ]
    },
    {
      label: "K-Graff",
      icon: NetworkIcon,
      href: "/kginsights/dashboard",
      requiredPermission: "kginsights:read",
      key: "k-graff", // Add a key property for consistent identification
      subItems: [
        { label: "KGraff Dashboard", href: "/kginsights/dashboard", icon: LayoutDashboard, requiredPermission: "kginsights:read" },
        { label: "Generate Graph", href: "/kginsights/generate", icon: GitBranch, requiredPermission: "kginsights:write" },
        { label: "Manage KGraff", href: "/kginsights/manage", icon: Settings, requiredPermission: "kginsights:write" },
        { label: "KGraff Insights", href: "/kginsights/insights", icon: MessageSquare, requiredPermission: "kginsights:read" }
      ]
    }
  ]
  
  // Filter tools based on user permissions
  const tools = allTools.filter(tool => {
    // Special case for K-Graff menu - only show if user explicitly has kginsights:read permission
    // This ensures users with only djinni:read don't see the K-Graff menu
    if (tool.key === "k-graff") {
      return user?.permissions?.includes("kginsights:read");
    }
    
    if (!user || !user.permissions || !tool.requiredPermission) return false
    
    // Check if user has the required permission for this tool
    return user.permissions.includes(tool.requiredPermission as string)
  })
  
  const allPersonalDashboards: MenuSection[] = [
    {
      label: "My Dashboards",
      icon: LayoutDashboard,
      href: "/dashboards",
      key: "my-dashboards",
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
      href: "",
      requiredPermission: "dashboard:read"
    }
  ]
  
  // Filter personal dashboards based on user permissions
  const personalDashboards = allPersonalDashboards.filter(item => {
    if (!user || !user.permissions || !item.requiredPermission) return false
    return user.permissions.includes(item.requiredPermission as string)
  })
  
  // Filter system options based on user role
  const getSystemOptions = (): MenuSection[] => {
    const baseOptions: MenuSection[] = [
      {
        label: "Help",
        icon: HelpCircle,
        href: "",
        key: "help"
      }
    ]
    
    // Only show Settings to admin users
    if (user?.role === "admin") {
      return [
        {
          label: "Settings",
          icon: Settings,
          href: "/admin",
          key: "settings"
        },
        ...baseOptions
      ]
    }
    
    return baseOptions
  }
  
  const systemOptions = getSystemOptions()

  const toggleSection = (section: string | undefined) => {
    if (!section) return;
    
    setExpandedSections(prev => ({
      ...prev,
      [section]: !(prev[section] === true)
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
                            const sectionKey = section.key || section.label.toLowerCase();
                            setExpandedSections(prev => ({
                              ...prev,
                              [sectionKey]: true
                            }));
                          }, 100);
                        } else {
                          // If sidebar is already expanded, just toggle the section
                          const sectionKey = section.key || section.label.toLowerCase();
                          toggleSection(sectionKey);
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
                      {!collapsed && (Boolean(expandedSections[section.key || section.label.toLowerCase()]) ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      ))}
                    </button>
                    
                    {Boolean(expandedSections[section.key || section.label.toLowerCase()]) && !collapsed && (
                      <div className="ml-4 space-y-1 border-l border-border pl-3">
                        {section.subItems?.map((item) => (
                          <SidebarMenuItem
                            key={item.href}
                            href={item.href}
                            icon={item.icon}
                            label={item.label}
                            isActive={
                              pathname === item.href ||
                              (item.href !== section.href && 
                               (item.href.includes('?') ? 
                                 (pathname === item.href.split('?')[0] && 
                                  typeof window !== 'undefined' && 
                                  window.location.search.includes(item.href.split('?')[1])) : 
                                 pathname.startsWith(item.href)))
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
                    isActive={!section.href ? false : (section.href === "/" ? pathname === "/" : (pathname === section.href || pathname.startsWith(`${section.href}/`)))}
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
                  isActive={!section.href ? false : (section.href === "/" ? pathname === "/" : (pathname === section.href || pathname.startsWith(`${section.href}/`)))}
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
                            const sectionKey = section.key || section.label.toLowerCase();
                            setExpandedSections(prev => ({
                              ...prev,
                              [sectionKey]: true
                            }));
                          }, 100);
                        } else {
                          // If sidebar is already expanded, just toggle the section
                          const sectionKey = section.key || section.label.toLowerCase();
                          toggleSection(sectionKey);
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
                      {!collapsed && (Boolean(expandedSections[section.key || section.label.toLowerCase()]) ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      ))}
                    </button>
                    
                    {Boolean(expandedSections[section.key || section.label.toLowerCase()]) && !collapsed && (
                      <div className="ml-4 space-y-1 border-l border-border pl-3">
                        {section.subItems?.filter(item => {
                          // Special case for KGraph Insights in the Djinni menu - always show to users with djinni:read
                          if (item.label === "KGraff Insights" && user?.permissions?.includes("djinni:read")) {
                            return true;
                          }
                          
                          // Standard permission filtering for other items
                          if (!item.requiredPermission) return true;
                          if (!user || !user.permissions) return false;
                          return user.permissions.includes(item.requiredPermission);
                        }).map((item) => (
                          <SidebarMenuItem
                            key={item.href}
                            href={item.href}
                            icon={item.icon}
                            label={item.label}
                            isActive={
                              pathname === item.href ||
                              (item.href !== section.href && 
                               (item.href.includes('?') ? 
                                 (pathname === item.href.split('?')[0] && 
                                  typeof window !== 'undefined' && 
                                  window.location.search.includes(item.href.split('?')[1])) : 
                                 pathname.startsWith(item.href)))
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
                          const sectionKey = section.key || section.label.toLowerCase();
                          setExpandedSections(prev => ({
                            ...prev,
                            [sectionKey]: true
                          }));
                        }, 100);
                      } else {
                        // If sidebar is already expanded, just toggle the section
                        const sectionKey = section.key || section.label.toLowerCase();
                        toggleSection(sectionKey);
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
                    {!collapsed && (Boolean(expandedSections[section.key || section.label.toLowerCase()]) ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    ))}
                  </button>
                  
                  {Boolean(expandedSections[section.key || section.label.toLowerCase()]) && !collapsed && (
                    <div className="ml-4 space-y-1 border-l border-border pl-3">
                      {section.subItems?.filter(item => {
                        // If no required permission is specified, show the item
                        if (!item.requiredPermission) return true;
                        
                        // If user doesn't exist or has no permissions, don't show the item
                        if (!user || !user.permissions) return false;
                        
                        // Show the item if user has the required permission
                        return user.permissions.includes(item.requiredPermission);
                      }).map((item) => (
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
                  isActive={!section.href ? false : (section.href === "/" ? pathname === "/" : (pathname === section.href || pathname.startsWith(`${section.href}/`)))}
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
            
            {!collapsed && user && (
              <div className="flex-1 overflow-hidden">
                <p className="text-sm font-medium truncate">{user?.username}</p>
                <p className="text-xs text-muted-foreground truncate capitalize">{user?.role}</p>
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
