"use client"

import React, { useState, useEffect } from "react"
import { UserPlus, Edit, Trash2, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useAdminStore } from "@/lib/admin/store"
import { EditRoleDialog } from "@/components/admin/dialogs/edit-role-dialog"
import { AddRoleDialog } from "@/components/admin/dialogs/add-role-dialog"
import { syncRoles, syncAvailablePermissions, saveRoleToBackend, deleteRole } from "@/lib/admin/sync-roles"
import { Role } from "@/lib/admin/store"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"

export function PermissionsTab() {
  const { roles, availablePermissions, setNotification } = useAdminStore()
  const [editRoleDialog, setEditRoleDialog] = useState(false)
  const [addRoleDialog, setAddRoleDialog] = useState(false)
  const [currentRole, setCurrentRole] = useState<Role | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [roleToDelete, setRoleToDelete] = useState<Role | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  const openEditRoleDialog = (role: Role) => {
    // Create a copy of the role with properly formatted permissions
    const formattedRole = {
      ...role,
      // Ensure permissions is an array
      permissions: Array.isArray(role.permissions) && role.permissions.length > 0 
        ? role.permissions 
        : (Array.isArray(role.permissions_list) && role.permissions_list.length > 0 
          ? role.permissions_list 
          : [])
    };
    
    console.log("Opening edit dialog with formatted role:", formattedRole);
    setCurrentRole(formattedRole);
    setEditRoleDialog(true);
  }

  const handleDeleteRole = async () => {
    if (!roleToDelete || typeof roleToDelete.id !== 'number') return;
    
    setIsDeleting(true);
    try {
      const success = await deleteRole(roleToDelete.id);
      if (success) {
        // Success notification is handled in the deleteRole function
        setDeleteDialogOpen(false);
      }
    } catch (error) {
      console.error("Error in delete handler:", error);
    } finally {
      setIsDeleting(false);
      setRoleToDelete(null);
    }
  };

  const openDeleteDialog = (role: Role) => {
    setRoleToDelete(role);
    setDeleteDialogOpen(true);
  };

  // Fetch roles when the component mounts
  useEffect(() => {
    const fetchRoles = async () => {
      setIsLoading(true)
      try {
        await syncRoles()
        console.log("Roles synced successfully")
      } catch (error: any) {
        console.error("Failed to sync roles:", error)
        setNotification({
          type: "error",
          message: "Failed to load roles from the server",
        })
      } finally {
        setIsLoading(false)
      }
    }

    fetchRoles()
  }, [setNotification])

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-foreground">Role Management</h2>
        <Button
          className="bg-violet-600 hover:bg-violet-700 text-white btn-glow"
          onClick={() => setAddRoleDialog(true)}
        >
          <UserPlus className="h-4 w-4 mr-2" />
          Add Role
        </Button>
      </div>

      <p className="text-muted-foreground mb-6">
        Configure role-based permissions and access controls for your application.
      </p>

      <div className="bg-card p-6 rounded-lg border border-border">
        {isLoading ? (
          <div className="flex justify-center items-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-violet-700"></div>
          </div>
        ) : roles.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            No roles found. Click "Add Role" to create your first role.
          </div>
        ) : (
          <div className="space-y-4">
            {roles.map((role: Role) => (
              <div key={role.id} className="p-4 border border-border rounded-lg">
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="text-card-foreground font-medium mb-2">
                      {role.name}
                      {role.is_system_role && (
                        <span className="ml-2 px-2 py-0.5 bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300 rounded text-xs">
                          System
                        </span>
                      )}
                    </h4>
                    <p className="text-muted-foreground text-sm mb-2">{role.description}</p>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {role.permissions &&
                        role.permissions.map((permission: string) => (
                          <span key={permission} className="px-2 py-1 bg-accent rounded-md text-xs text-foreground">
                            {permission}
                          </span>
                        ))}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {/* Don't show edit button for admin role */}
                    {role.name !== "admin" && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="border-violet-600 text-violet-600 hover:bg-violet-600/20 text-xs h-7"
                        onClick={() => openEditRoleDialog(role)}
                        disabled={role.is_system_role}
                        title={role.is_system_role ? "System roles cannot be modified" : "Edit role"}
                      >
                        <Edit className="h-3.5 w-3.5 mr-1" />
                        Edit
                      </Button>
                    )}
                    {/* Don't show delete button for admin role */}
                    {role.name !== "admin" && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="border-red-600 text-red-600 hover:bg-red-600/20 text-xs h-7"
                        onClick={() => openDeleteDialog(role)}
                        disabled={role.is_system_role}
                        title={role.is_system_role ? "System roles cannot be deleted" : "Delete role"}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Role Dialog */}
      <AddRoleDialog open={addRoleDialog} onOpenChange={setAddRoleDialog} />

      {/* Edit Role Dialog */}
      {currentRole && (
        <EditRoleDialog open={editRoleDialog} onOpenChange={setEditRoleDialog} role={currentRole} />
      )}

      {/* Delete Role Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              {roleToDelete ? (
                <>
                  This will permanently delete the role <strong>{roleToDelete.name}</strong>.
                  <br />
                  <div className="flex items-center mt-2 p-2 bg-amber-50 border border-amber-200 rounded-md text-amber-700 dark:bg-amber-900/20 dark:border-amber-800 dark:text-amber-300">
                    <AlertCircle className="h-4 w-4 mr-2 flex-shrink-0" />
                    <span className="text-sm">
                      If any users are assigned to this role, deletion will fail. Make sure to reassign users first.
                    </span>
                  </div>
                </>
              ) : (
                'This will permanently delete the selected role.'
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleDeleteRole}
              className="bg-red-600 hover:bg-red-700 focus:ring-red-600"
              disabled={isDeleting}
            >
              {isDeleting ? 'Deleting...' : 'Delete Role'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
