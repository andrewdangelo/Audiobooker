// FileUpload component with drag-and-drop and file selection

import { useState, useRef } from 'react'
import { uploadService } from '../../services/upload.service'
import { Button } from '../ui/button'
import UploadProgress from './UploadProgress'

export default function FileUpload() {
  const [isDragging, setIsDragging] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [uploadResult, setUploadResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    
    const files = e.dataTransfer.files
    if (files && files.length > 0) {
      handleFileSelect(files[0])
    }
  }

  const handleFileSelect = (file: File) => {
    setError(null)
    setUploadResult(null)
    
    // Validate file type
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Please select a PDF file')
      return
    }
    
    // Validate file size (50MB max)
    if (file.size > 52428800) {
      setError('File size must be less than 50MB')
      return
    }
    
    setSelectedFile(file)
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      handleFileSelect(files[0])
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) return
    
    setUploading(true)
    setError(null)
    setProgress(0)
    
    try {
      const result = await uploadService.uploadPDF(selectedFile, (prog) => {
        setProgress(prog)
      })
      
      setUploadResult(result)
      setProgress(100)
      console.log('Upload successful:', result)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Upload failed')
      console.error('Upload error:', err)
    } finally {
      setUploading(false)
    }
  }

  const handleClick = () => {
    fileInputRef.current?.click()
  }

  return (
    <div className="space-y-4">
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
          isDragging ? 'border-primary bg-primary/10' : 'border-gray-300 hover:border-gray-400'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleFileInputChange}
          className="hidden"
        />
        
        <svg
          className="mx-auto h-12 w-12 text-gray-400 mb-4"
          stroke="currentColor"
          fill="none"
          viewBox="0 0 48 48"
          aria-hidden="true"
        >
          <path
            d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        
        {selectedFile ? (
          <div>
            <p className="text-sm font-medium text-gray-900">{selectedFile.name}</p>
            <p className="text-xs text-gray-500">
              {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
        ) : (
          <div>
            <p className="text-sm font-medium text-gray-900">
              Drop your PDF here, or click to select
            </p>
            <p className="text-xs text-gray-500 mt-1">
              PDF files only, up to 50MB
            </p>
          </div>
        )}
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {uploading && selectedFile && (
        <UploadProgress progress={progress} fileName={selectedFile.name} />
      )}

      {uploadResult && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm font-medium text-green-800">Upload Successful!</p>
          <p className="text-xs text-green-600 mt-1">
            File ID: {uploadResult.id}
          </p>
          <p className="text-xs text-green-600">
            Status: {uploadResult.status}
          </p>
        </div>
      )}

      {selectedFile && !uploading && !uploadResult && (
        <Button 
          onClick={handleUpload}
          className="w-full"
          disabled={uploading}
        >
          Upload PDF
        </Button>
      )}
    </div>
  )
}
