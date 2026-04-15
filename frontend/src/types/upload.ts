// Upload type definitions

export interface UploadResponse {
  id: string
  fileName: string
  fileSize: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
  message?: string
  /** R2/pdf path from the PDF processor (for process_pdf / job polling). */
  pdfPath?: string
  title?: string
}

export interface UploadProgress {
  uploadId: string
  progress: number
  status: string
}
