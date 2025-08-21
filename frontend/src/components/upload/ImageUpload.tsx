import React, { useState, useRef } from 'react'
import { Upload, X, Image as ImageIcon, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useToast } from '@/hooks/use-toast'

interface ImageUploadProps {
  onUpload: (file: File, fileInfo: any) => void
  onRemove?: () => void
  currentImageUrl?: string
  category?: string
  maxSize?: number // in MB
  accept?: string
  disabled?: boolean
  className?: string
}

export function ImageUpload({
  onUpload,
  onRemove,
  currentImageUrl,
  category = 'general',
  maxSize = 10,
  accept = 'image/*',
  disabled = false,
  className = ''
}: ImageUploadProps) {
  const [isUploading, setIsUploading] = useState(false)
  const [preview, setPreview] = useState<string | null>(currentImageUrl || null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { toast } = useToast()

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // Validate file type
    if (!file.type.startsWith('image/')) {
      toast({
        title: 'Invalid file type',
        description: 'Please select an image file.',
        variant: 'destructive',
      })
      return
    }

    // Validate file size
    const maxBytes = maxSize * 1024 * 1024
    if (file.size > maxBytes) {
      toast({
        title: 'File too large',
        description: `File size must be less than ${maxSize}MB.`,
        variant: 'destructive',
      })
      return
    }

    uploadFile(file)
  }

  const uploadFile = async (file: File) => {
    setIsUploading(true)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(`/api/v1/files/upload/image?category=${category}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Upload failed')
      }

      const data = await response.json()

      // Create preview URL
      const previewUrl = URL.createObjectURL(file)
      setPreview(previewUrl)

      // Call the onUpload callback
      onUpload(file, data.file)

      toast({
        title: 'Upload successful',
        description: 'Your image has been uploaded successfully.',
      })
    } catch (error) {
      console.error('Upload failed:', error)
      toast({
        title: 'Upload failed',
        description: 'Failed to upload image. Please try again.',
        variant: 'destructive',
      })
    } finally {
      setIsUploading(false)
    }
  }

  const handleRemove = () => {
    setPreview(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
    onRemove?.()
  }

  const handleClick = () => {
    if (!disabled && fileInputRef.current) {
      fileInputRef.current.click()
    }
  }

  return (
    <div className={`w-full ${className}`}>
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        onChange={handleFileSelect}
        className="hidden"
        disabled={disabled || isUploading}
      />

      {preview ? (
        <Card className="relative overflow-hidden">
          <div className="aspect-video relative">
            <img
              src={preview}
              alt="Preview"
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-black bg-opacity-0 hover:bg-opacity-20 transition-opacity duration-200 flex items-center justify-center opacity-0 hover:opacity-100">
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={handleClick}
                  disabled={disabled || isUploading}
                >
                  {isUploading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Upload className="w-4 h-4" />
                  )}
                  Replace
                </Button>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={handleRemove}
                  disabled={disabled || isUploading}
                >
                  <X className="w-4 h-4" />
                  Remove
                </Button>
              </div>
            </div>
          </div>
        </Card>
      ) : (
        <Card
          className={`border-2 border-dashed border-gray-300 hover:border-gray-400 transition-colors cursor-pointer ${
            disabled ? 'opacity-50 cursor-not-allowed' : ''
          }`}
          onClick={handleClick}
        >
          <div className="flex flex-col items-center justify-center py-12 px-6 text-center">
            {isUploading ? (
              <Loader2 className="w-12 h-12 text-gray-400 animate-spin mb-4" />
            ) : (
              <ImageIcon className="w-12 h-12 text-gray-400 mb-4" />
            )}
            <p className="text-lg font-medium text-gray-900 mb-2">
              {isUploading ? 'Uploading...' : 'Upload an image'}
            </p>
            <p className="text-sm text-gray-500 mb-4">
              Drag and drop or click to select
            </p>
            <p className="text-xs text-gray-400">
              PNG, JPG, WEBP up to {maxSize}MB
            </p>
          </div>
        </Card>
      )}
    </div>
  )
}