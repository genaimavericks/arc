"use client"

import { AdminLayout } from "@/components/admin/admin-layout"
import { AdminTabsContent } from "@/components/admin/admin-tabs-content"
import { NotificationDisplay } from "@/components/admin/notification"
import { useAdminStore } from "@/lib/admin/store"

export default function AdminPage() {
  const { notification } = useAdminStore()

  return (
    <AdminLayout>
      <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold tracking-tight">Admin Dashboard</h2>

        </div>

        {notification && <NotificationDisplay notification={notification} />}
        
        <AdminTabsContent />
      </div>
    </AdminLayout>
  )
}

