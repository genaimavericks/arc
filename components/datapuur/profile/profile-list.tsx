"use client"

import { useState, useEffect } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Search, BarChart2, Calendar, Database } from "lucide-react"
import { useToast } from "@/components/ui/use-toast"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination"
import { Badge } from "@/components/ui/badge"
import { format } from "date-fns"
import LoadingSpinner from "@/components/loading-spinner"

interface Profile {
  id: string
  file_id: string
  file_name: string
  total_rows: number
  total_columns: number
  data_quality_score: number
  exact_duplicates_count: number
  fuzzy_duplicates_count: number
  created_at: string
}

interface ProfileListProps {
  onProfileSelect: (profileId: string) => void
  selectedProfileId: string | null
  fileIdFilter?: string
}

export function ProfileList({ onProfileSelect, selectedProfileId, fileIdFilter }: ProfileListProps) {
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState("")
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalProfiles, setTotalProfiles] = useState(0)
  const { toast } = useToast()
  const limit = 10

  const fetchProfiles = async () => {
    try {
      setLoading(true)
      const token = localStorage.getItem("token")
      
      if (!token) {
        toast({
          title: "Authentication Error",
          description: "You must be logged in to view profiles",
          variant: "destructive",
        })
        return
      }

      let url = `/api/profiler/profiles?page=${page}&limit=${limit}`
      
      if (searchQuery) {
        url += `&search=${encodeURIComponent(searchQuery)}`
      }
      
      if (fileIdFilter) {
        url += `&file_id=${encodeURIComponent(fileIdFilter)}`
      }

      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setProfiles(data.items)
      setTotalPages(data.pages)
      setTotalProfiles(data.total)
      
      // If we have results and no profile is selected yet, select the first one
      if (data.items.length > 0 && !selectedProfileId) {
        onProfileSelect(data.items[0].id)
      }
    } catch (error) {
      console.error("Error fetching profiles:", error)
      toast({
        title: "Error",
        description: "Failed to fetch profiles. Please try again.",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProfiles()
  }, [page, fileIdFilter])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1) // Reset to first page when searching
    fetchProfiles()
  }

  const getQualityBadgeVariant = (score: number) => {
    // Score is already multiplied by 100 from the backend
    if (score >= 90) return "success"
    if (score >= 70) return "default"
    if (score >= 50) return "warning"
    return "destructive"
  }

  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex flex-col space-y-4">
          <form onSubmit={handleSearch} className="flex w-full max-w-sm items-center space-x-2">
            <Input
              type="text"
              placeholder="Search profiles..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="flex-1"
            />
            <Button type="submit" size="icon">
              <Search className="h-4 w-4" />
            </Button>
          </form>

          {loading ? (
            <div className="flex justify-center items-center h-64">
              <LoadingSpinner />
            </div>
          ) : profiles.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-center">
              <BarChart2 className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium">No profiles found</h3>
              <p className="text-sm text-muted-foreground mt-1">
                {searchQuery
                  ? "Try a different search term"
                  : fileIdFilter
                  ? "No profiles available for this dataset"
                  : "Upload and profile a dataset to get started"}
              </p>
            </div>
          ) : (
            <>
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Dataset</TableHead>
                      <TableHead>Size</TableHead>
                      <TableHead>Duplicates</TableHead>
                      <TableHead>Quality Score</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {profiles.map((profile) => (
                      <TableRow 
                        key={profile.id}
                        className={selectedProfileId === profile.id ? "bg-accent/30" : ""}
                      >
                        <TableCell className="font-medium">{profile.file_name}</TableCell>
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="flex items-center">
                              <Database className="h-3 w-3 mr-1" />
                              {profile.total_rows.toLocaleString()} rows
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {profile.total_columns} columns
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="flex items-center">
                              Exact: {(profile.exact_duplicates_count !== undefined ? profile.exact_duplicates_count : 0).toLocaleString()}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              Fuzzy: {(profile.fuzzy_duplicates_count !== undefined ? profile.fuzzy_duplicates_count : 0).toLocaleString()}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={getQualityBadgeVariant(profile.data_quality_score) as any}>
                            {profile.data_quality_score !== undefined ? `${Math.round(profile.data_quality_score)}%` : 'N/A'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center">
                            <Calendar className="h-3 w-3 mr-1" />
                            <span>{format(new Date(profile.created_at), "MMM d, yyyy")}</span>
                          </div>
                          <span className="text-xs text-muted-foreground">
                            {format(new Date(profile.created_at), "h:mm a")}
                          </span>
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant={selectedProfileId === profile.id ? "default" : "ghost"}
                            size="sm"
                            onClick={() => onProfileSelect(profile.id)}
                          >
                            {selectedProfileId === profile.id ? "Selected" : "View"}
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  Showing {profiles.length} of {totalProfiles} profiles
                </p>
                <Pagination>
                  <PaginationContent>
                    <PaginationItem>
                      <PaginationPrevious 
                        onClick={() => setPage(Math.max(1, page - 1))}
                        className={page === 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                      />
                    </PaginationItem>
                    
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      // Show pages around the current page
                      let pageNum = page - 2 + i
                      if (pageNum < 1) pageNum += Math.min(5, totalPages)
                      if (pageNum > totalPages) pageNum -= Math.min(5, totalPages)
                      
                      // Ensure we're showing valid page numbers
                      if (pageNum >= 1 && pageNum <= totalPages) {
                        return (
                          <PaginationItem key={pageNum}>
                            <PaginationLink
                              onClick={() => setPage(pageNum)}
                              isActive={page === pageNum}
                              className="cursor-pointer"
                            >
                              {pageNum}
                            </PaginationLink>
                          </PaginationItem>
                        )
                      }
                      return null
                    })}
                    
                    <PaginationItem>
                      <PaginationNext 
                        onClick={() => setPage(Math.min(totalPages, page + 1))}
                        className={page === totalPages ? "pointer-events-none opacity-50" : "cursor-pointer"}
                      />
                    </PaginationItem>
                  </PaginationContent>
                </Pagination>
              </div>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export default ProfileList;
