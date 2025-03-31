import { useAdminStore } from "./store"
import { Role } from "./store"
import { getApiBaseUrl } from '../config'

/**
 * Synchronizes roles between the frontend and backend
 * This should be called when the admin dashboard is loaded
 */
export async function syncRoles() {
  try {
    const apiUrl = getApiBaseUrl()
    const token = localStorage.getItem("token")
    const headers = {
      Authorization: `Bearer ${token}`,
      Accept: "application/json",
      "Content-Type": "application/json",
    }

    // Fetch roles from the backend
    const response = await fetch(`${apiUrl}/api/admin/roles`, { headers })

    if (!response.ok) {
      throw new Error(`Failed to fetch roles: ${response.statusText}`)
    }

    const rolesData = await response.json()
    console.log("Fetched roles from backend:", rolesData)

    const { setRoles } = useAdminStore.getState()

    // Transform the roles data if needed to match the expected format
    const formattedRoles = rolesData.map((role: Role) => {
      // Ensure permissions is properly set from either permissions_list or permissions
      const permissions = Array.isArray(role.permissions_list) 
        ? role.permissions_list 
        : (Array.isArray(role.permissions) ? role.permissions : []);
      
      console.log(`Role ${role.name} permissions:`, permissions);
      
      return {
        id: role.id,
        name: role.name,
        description: role.description || "",
        permissions: permissions,
        permissions_list: permissions, // Keep both for compatibility
        is_system_role: role.is_system_role || false,
        created_at: role.created_at,
        updated_at: role.updated_at
      };
    })

    setRoles(formattedRoles)

    // Also fetch available permissions
    await syncAvailablePermissions()

    return formattedRoles
  } catch (error) {
    console.error("Error syncing roles:", error)

    // If the API call fails, use default roles
    const { setRoles } = useAdminStore.getState()
    const defaultRoles = [
      {
        id: 1,
        name: "admin",
        description: "Administrator with full access",
        permissions: ["datapuur:read", "datapuur:write", "datapuur:manage", "user:read", "user:create", "user:update", "user:delete", "role:read", "role:create", "role:update", "role:delete", "kginsights:read", "kginsights:write", "kginsights:manage"],
        is_system_role: true
      },
      {
        id: 2,
        name: "user",
        description: "Regular user with limited access",
        permissions: ["datapuur:read"],
        is_system_role: true
      },
      {
        id: 3,
        name: "researcher",
        description: "Researcher with data access",
        permissions: ["datapuur:read", "datapuur:write", "kginsights:read"],
        is_system_role: true
      },
    ]

    setRoles(defaultRoles)
    return defaultRoles
  }
}

/**
 * Syncs available permissions from the backend
 */
export async function syncAvailablePermissions() {
  try {
    const apiUrl = getApiBaseUrl()
    const token = localStorage.getItem("token")
    const headers = {
      Authorization: `Bearer ${token}`,
      Accept: "application/json",
      "Content-Type": "application/json",
    }

    // Fetch available permissions from the backend
    const response = await fetch(`${apiUrl}/api/admin/permissions`, { headers })

    if (!response.ok) {
      console.warn(`Failed to fetch permissions: ${response.statusText}. Using default permissions.`)
      // Use default permissions if the API call fails
      const defaultPermissions = [
        // DataPuur permissions
        "datapuur:read", "datapuur:write", "datapuur:manage",
        
        // Database permissions
        "database:connect", "database:read", "database:write",
        
        // User management permissions
        "user:read", "user:create", "user:update", "user:delete",
        
        // Role management permissions
        "role:read", "role:create", "role:update", "role:delete",
        
        // KGInsights permissions
        "kginsights:read", "kginsights:write", "kginsights:manage"
      ]
      
      const { setAvailablePermissions } = useAdminStore.getState()
      setAvailablePermissions(defaultPermissions)
      return defaultPermissions
    }

    const permissionsData = await response.json()
    console.log("Fetched permissions from backend:", permissionsData)

    // Update the store with the fetched permissions
    const { setAvailablePermissions } = useAdminStore.getState()
    setAvailablePermissions(permissionsData)

    return permissionsData
  } catch (error) {
    console.error("Error syncing permissions:", error)
    
    // If the API call fails, use default permissions
    const defaultPermissions = [
      // DataPuur permissions
      "datapuur:read", "datapuur:write", "datapuur:manage",
      
      // Database permissions
      "database:connect", "database:read", "database:write",
      
      // User management permissions
      "user:read", "user:create", "user:update", "user:delete",
      
      // Role management permissions
      "role:read", "role:create", "role:update", "role:delete",
      
      // KGInsights permissions
      "kginsights:read", "kginsights:write", "kginsights:manage"
    ]
    
    const { setAvailablePermissions } = useAdminStore.getState()
    setAvailablePermissions(defaultPermissions)
    
    return defaultPermissions
  }
}

/**
 * Saves a role to the backend
 * @param role The role to save
 * @returns The saved role
 */
export async function saveRoleToBackend(role: Role) {
  try {
    const apiUrl = getApiBaseUrl()
    const token = localStorage.getItem("token")
    const headers = {
      Authorization: `Bearer ${token}`,
      Accept: "application/json",
      "Content-Type": "application/json",
    }

    const isNewRole = !role.id
    // Update the URL to use the correct endpoint
    const url = isNewRole ? `${apiUrl}/api/admin/roles` : `${apiUrl}/api/admin/roles/${role.id}`
    const method = isNewRole ? "POST" : "PUT"

    // Ensure we're sending the permissions in the format the backend expects
    const roleToSend = {
      ...role,
      // The backend expects permissions to be an array of strings
      permissions: Array.isArray(role.permissions) ? role.permissions : []
    };

    console.log(`Saving role to backend: ${JSON.stringify(roleToSend)}`)

    const response = await fetch(url, {
      method,
      headers,
      body: JSON.stringify(roleToSend),
    })

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`Failed to save role: ${response.statusText} - ${errorText}`)
    }

    const savedRole = await response.json()
    console.log(`Role saved successfully: ${JSON.stringify(savedRole)}`)
    
    // Ensure the returned role has the permissions properly formatted for the frontend
    return {
      ...savedRole,
      permissions: savedRole.permissions || savedRole.permissions_list || [],
      permissions_list: savedRole.permissions_list || savedRole.permissions || []
    }
  } catch (error) {
    console.error("Error saving role:", error)
    throw error
  }
}

/**
 * Deletes a role from the backend
 * @param roleId The ID of the role to delete
 * @returns True if deletion was successful
 */
export async function deleteRole(roleId: number) {
  try {
    const apiUrl = getApiBaseUrl()
    const token = localStorage.getItem("token")
    const headers = {
      Authorization: `Bearer ${token}`,
      Accept: "application/json",
      "Content-Type": "application/json",
    }

    // Delete role from the backend
    const response = await fetch(`${apiUrl}/api/admin/roles/${roleId}`, { 
      method: 'DELETE',
      headers 
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || `Failed to delete role: ${response.statusText}`)
    }

    // Update the store
    const { roles, setRoles, setNotification } = useAdminStore.getState()
    setRoles(roles.filter(r => r.id !== roleId))
    setNotification({
      type: "success",
      message: "Role deleted successfully",
    })

    return true
  } catch (error: any) {
    console.error("Error deleting role:", error)
    const { setNotification } = useAdminStore.getState()
    setNotification({
      type: "error",
      message: error.message || "Failed to delete role",
    })
    return false
  }
}
