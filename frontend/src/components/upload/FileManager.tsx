import React, { useState, useEffect } from 'react'
import { Trash2, Download, Eye, Upload, Search, Filter } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { useToast } from '@/hooks/use-toast'

interface FileInfo {
  id: number
  filename: string
  original_filename: string
  content_type: string
  size: number
  category: string
  file_type: string
  url: string
  created_at: string
  variants?: Record<string, string>
}

interface FileManagerProps {
  category?: string
  fileType?: 'image' | 'document' | 'all'
  onSelect?: (file: FileInfo) => void
  allowDelete?: boolean
  allowUpload?: boolean
  className?: string
}

export function FileManager({
  category,
  fileType = 'all',
  onSelect,
  allowDelete = true,
  allowUpload = true,
  className = ''
}: FileManagerProps) {
  const [files, setFiles] = useState<FileInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState(category || '')
  const [page, setPage] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  const { toast } = useToast()

  const loadFiles = async (reset = false) => {
    try {
      setLoading(true)
      const offset = reset ? 0 : page * 20
      const categoryParam = selectedCategory ? `/${selectedCategory}` : '/general'
      
      const response = await fetch(
        `/api/v1/files/list${categoryParam}?limit=20&offset=${offset}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
          },
        }
      )

      if (!response.ok) {
        throw new Error('Failed to load files')
      }

      const data = await response.json()
      
      if (reset) {
        setFiles(data.files)
        setPage(0)
      } else {
        setFiles(prev => [...prev, ...data.files])
      }
      
      setHasMore(data.files.length === 20)
    } catch (error) {
      console.error('Failed to load files:', error)
      toast({
        title: 'Error',
        description: 'Failed to load files.',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadFiles(true)
  }, [selectedCategory])

  const handleDelete = async (fileId: number, filePath: string) => {
    if (!confirm('Are you sure you want to delete this file?')) return

    try {
      const response = await fetch(`/api/v1/files/${filePath}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      })

      if (!response.ok) {
        throw new Error('Failed to delete file')
      }

      setFiles(prev => prev.filter(f => f.id !== fileId))
      toast({
        title: 'Success',
        description: 'File deleted successfully.',
      })
    } catch (error) {
      console.error('Failed to delete file:', error)
      toast({
        title: 'Error',
        description: 'Failed to delete file.',
        variant: 'destructive',
      })
    }
  }

  const handleUpload = () => {
    // Trigger file upload - you might want to integrate with ImageUpload component
    // or implement a file upload modal here
    toast({
      title: 'Info',
      description: 'File upload functionality would be implemented here.',
    })
  }

  const filteredFiles = files.filter(file => {
    const matchesSearch = file.filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         file.original_filename?.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesType = fileType === 'all' || file.file_type === fileType
    return matchesSearch && matchesType
  })

  const formatFileSize = (bytes: number) => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    if (bytes === 0) return '0 Bytes'
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString()
  }

  return (
    <div className={`w-full space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex gap-2 flex-1">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              placeholder="Search files..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
          <Select
            value={selectedCategory}
            onValueChange={setSelectedCategory}
          >
            <option value="">All categories</option>
            <option value="events">Events</option>
            <option value="users">Users</option>
            <option value="documents">Documents</option>
            <option value="general">General</option>
          </Select>
        </div>
        {allowUpload && (
          <Button onClick={handleUpload}>
            <Upload className="w-4 h-4 mr-2" />
            Upload
          </Button>
        )}
      </div>

      {/* Files Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {filteredFiles.map((file) => (
          <Card key={file.id} className="overflow-hidden group hover:shadow-lg transition-shadow">
            <div className="aspect-video bg-gray-100 relative">
              {file.file_type === 'image' ? (
                <img
                  src={file.variants?.thumbnail || file.url}
                  alt={file.original_filename || file.filename}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <div className="text-4xl text-gray-400">📄</div>
                </div>
              )}
              
              {/* Overlay actions */}
              <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-40 transition-opacity duration-200 flex items-center justify-center opacity-0 group-hover:opacity-100">
                <div className="flex gap-2">
                  {onSelect && (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => onSelect(file)}
                    >
                      <Eye className="w-4 h-4" />
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => window.open(file.url, '_blank')}
                  >
                    <Download className="w-4 h-4" />
                  </Button>
                  {allowDelete && (
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => handleDelete(file.id, file.url.replace('/media/', ''))}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              </div>
            </div>
            
            {/* File info */}
            <div className="p-3">
              <h3 className="font-medium text-sm truncate" title={file.original_filename || file.filename}>
                {file.original_filename || file.filename}
              </h3>
              <div className="flex justify-between items-center mt-2 text-xs text-gray-500">
                <span>{formatFileSize(file.size)}</span>
                <span>{formatDate(file.created_at)}</span>
              </div>
              <div className="flex justify-between items-center mt-1 text-xs">
                <span className="bg-gray-100 text-gray-600 px-2 py-1 rounded">
                  {file.category}
                </span>
                <span className="text-gray-500">
                  {file.file_type}
                </span>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Loading state */}
      {loading && files.length === 0 && (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
          <p className="text-gray-500 mt-4">Loading files...</p>
        </div>
      )}

      {/* Empty state */}
      {!loading && filteredFiles.length === 0 && (
        <div className="text-center py-12">
          <div className="text-6xl text-gray-300 mb-4">📁</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No files found</h3>
          <p className="text-gray-500 mb-4">
            {searchTerm || selectedCategory
              ? 'Try adjusting your search or filter criteria.'
              : 'Upload your first file to get started.'}
          </p>
          {allowUpload && (
            <Button onClick={handleUpload}>
              <Upload className="w-4 h-4 mr-2" />
              Upload File
            </Button>
          )}
        </div>
      )}

      {/* Load more */}
      {hasMore && !loading && filteredFiles.length > 0 && (
        <div className="text-center">
          <Button
            variant="outline"
            onClick={() => {
              setPage(p => p + 1)
              loadFiles()
            }}
          >
            Load More
          </Button>
        </div>
      )}
    </div>
  )
}