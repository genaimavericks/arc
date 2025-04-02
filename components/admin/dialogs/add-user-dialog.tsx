"use client"

import { useState, useEffect } from "react"
import { RefreshCw, Check, X } from "lucide-react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useAdminStore } from "@/lib/admin/store"
import { createUser } from "@/lib/admin/api"

interface AddUserDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function AddUserDialog({ open, onOpenChange }: AddUserDialogProps) {
  const { users, setUsers, isProcessing, setIsProcessing, setNotification, roles, addRoleIfNotExists } = useAdminStore()
  const [newUser, setNewUser] = useState({
    username: "",
    email: "",
    password: "",
    role: "admin",
    is_active: true,
  })
  
  // Validation states
  const [validations, setValidations] = useState({
    email: { valid: false, message: "" },
    password: {
      valid: false,
      length: false,
      hasUpperCase: false,
      hasLowerCase: false,
      hasNumber: false,
      hasSpecial: false
    }
  })

  // Email validation
  useEffect(() => {
    if (!newUser.email) {
      setValidations(prev => ({
        ...prev,
        email: { valid: false, message: "" }
      }))
      return
    }
    
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
    const isValid = emailRegex.test(newUser.email)
    
    setValidations(prev => ({
      ...prev,
      email: { 
        valid: isValid, 
        message: isValid ? "" : "Please enter a valid email address" 
      }
    }))
  }, [newUser.email])

  // Password validation
  useEffect(() => {
    if (!newUser.password) {
      setValidations(prev => ({
        ...prev,
        password: {
          valid: false,
          length: false,
          hasUpperCase: false,
          hasLowerCase: false,
          hasNumber: false,
          hasSpecial: false
        }
      }))
      return
    }
    
    const length = newUser.password.length >= 8
    const hasUpperCase = /[A-Z]/.test(newUser.password)
    const hasLowerCase = /[a-z]/.test(newUser.password)
    const hasNumber = /[0-9]/.test(newUser.password)
    const hasSpecial = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(newUser.password)
    
    const isValid = length && hasUpperCase && hasLowerCase && hasNumber
    
    setValidations(prev => ({
      ...prev,
      password: {
        valid: isValid,
        length,
        hasUpperCase,
        hasLowerCase,
        hasNumber,
        hasSpecial
      }
    }))
  }, [newUser.password])

  const handleAddUser = async () => {
    if (!newUser.username || !newUser.email || !newUser.password) {
      setNotification({
        type: "error",
        message: "Please fill in all required fields",
      })
      return
    }

    if (!validations.email.valid) {
      setNotification({
        type: "error",
        message: "Please enter a valid email address",
      })
      return
    }

    if (!validations.password.valid) {
      setNotification({
        type: "error",
        message: "Password does not meet the requirements",
      })
      return
    }

    // Make sure the role exists in our store
    addRoleIfNotExists(newUser.role)

    setIsProcessing(true)
    try {
      const addedUser = await createUser(newUser)

      // Ensure created_at is set
      if (!addedUser.created_at) {
        addedUser.created_at = new Date().toISOString()
      }
      // Update users list
      setUsers([...users, addedUser])

      setNotification({
        type: "success",
        message: `User ${addedUser.username} created successfully`,
      })

      // Close dialog and reset form
      onOpenChange(false)
      setNewUser({
        username: "",
        email: "",
        password: "",
        role: "admin",
        is_active: true,
      })

      // Clear notification after 3 seconds
      setTimeout(() => setNotification(null), 3000)
    } catch (error) {
      console.error("Error creating user:", error)
      setNotification({
        type: "error",
        message: `Failed to create user: ${error instanceof Error ? error.message : String(error)}`
      })

      // Clear notification after 3 seconds
      setTimeout(() => setNotification(null), 3000)
    } finally {
      setIsProcessing(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-card border border-border text-card-foreground">
        <DialogHeader>
          <DialogTitle>Add New User</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="username">
              Username <span className="text-destructive">*</span>
            </Label>
            <Input
              id="username"
              value={newUser.username}
              onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
              className="bg-background border-input text-foreground"
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">
              Email <span className="text-destructive">*</span>
            </Label>
            <div className="relative">
              <Input
                id="email"
                type="email"
                value={newUser.email}
                onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                className={`bg-background border-input text-foreground pr-10 ${
                  newUser.email && !validations.email.valid ? "border-red-500" : ""
                }`}
                required
              />
              {newUser.email && (
                <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                  {validations.email.valid ? (
                    <Check className="h-4 w-4 text-green-500" />
                  ) : (
                    <X className="h-4 w-4 text-red-500" />
                  )}
                </div>
              )}
            </div>
            {newUser.email && !validations.email.valid && (
              <p className="text-xs text-red-500 mt-1">{validations.email.message}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">
              Password <span className="text-destructive">*</span>
            </Label>
            <div className="relative">
              <Input
                id="password"
                type="password"
                value={newUser.password}
                onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                className={`bg-background border-input text-foreground pr-10 ${
                  newUser.password && !validations.password.valid ? "border-red-500" : ""
                }`}
                required
              />
              {newUser.password && (
                <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                  {validations.password.valid ? (
                    <Check className="h-4 w-4 text-green-500" />
                  ) : (
                    <X className="h-4 w-4 text-red-500" />
                  )}
                </div>
              )}
            </div>
            {newUser.password && (
              <div className="mt-2 space-y-1">
                <p className="text-xs font-medium">Password must contain:</p>
                <ul className="space-y-1">
                  <li className={`text-xs flex items-center ${validations.password.length ? "text-green-500" : "text-muted-foreground"}`}>
                    {validations.password.length ? <Check className="h-3 w-3 mr-1" /> : <X className="h-3 w-3 mr-1" />}
                    At least 8 characters
                  </li>
                  <li className={`text-xs flex items-center ${validations.password.hasUpperCase ? "text-green-500" : "text-muted-foreground"}`}>
                    {validations.password.hasUpperCase ? <Check className="h-3 w-3 mr-1" /> : <X className="h-3 w-3 mr-1" />}
                    At least one uppercase letter
                  </li>
                  <li className={`text-xs flex items-center ${validations.password.hasLowerCase ? "text-green-500" : "text-muted-foreground"}`}>
                    {validations.password.hasLowerCase ? <Check className="h-3 w-3 mr-1" /> : <X className="h-3 w-3 mr-1" />}
                    At least one lowercase letter
                  </li>
                  <li className={`text-xs flex items-center ${validations.password.hasNumber ? "text-green-500" : "text-muted-foreground"}`}>
                    {validations.password.hasNumber ? <Check className="h-3 w-3 mr-1" /> : <X className="h-3 w-3 mr-1" />}
                    At least one number
                  </li>
                  <li className={`text-xs flex items-center ${validations.password.hasSpecial ? "text-green-500" : "text-muted-foreground"}`}>
                    {validations.password.hasSpecial ? <Check className="h-3 w-3 mr-1" /> : <X className="h-3 w-3 mr-1" />}
                    Special character (recommended)
                  </li>
                </ul>
              </div>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="role">Role</Label>
            <Select value={newUser.role} onValueChange={(value) => setNewUser({ ...newUser, role: value })}>
              <SelectTrigger>
                <SelectValue placeholder="Select a role" />
              </SelectTrigger>
              <SelectContent>
                {roles.map((role) => (
                  <SelectItem key={role.id} value={role.name}>
                    {role.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox 
              id="is_active" 
              checked={newUser.is_active} 
              onCheckedChange={(checked) => {
                if (checked === true || checked === false) {
                  setNewUser({ ...newUser, is_active: checked });
                }
              }}
            />
            <Label htmlFor="is_active">Active</Label>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            className="bg-violet-600 hover:bg-violet-700 text-white btn-glow"
            onClick={handleAddUser}
            disabled={isProcessing || (!validations.email.valid && newUser.email) || (!validations.password.valid && newUser.password)}
          >
            {isProcessing ? (
              <>
                <RefreshCw className="h-3 w-3 mr-1 animate-spin text-white" />
                Creating...
              </>
            ) : (
              "Add User"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
