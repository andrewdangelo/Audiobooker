/**
 * Upload Service
 *
 * Handles PDF and EPUB uploads through the API proxy to the PDF processor microservice.
 *
 * Proxy route:  POST /pdf_processor/pdf_processor/upload_new_pdf
 * Job-status:   GET  /pdf_processor/pdf_processor/job/{job_id}
 * Process:      POST /pdf_processor/pdf_processor/process_pdf  (body `r2_pdf_path` may be .pdf or .epub)
 */

import api from './api'
import { UploadResponse } from '../types/upload'

// Path prefix used by the PDF proxy route
const PDF_PROXY = '/pdf_processor/pdf_processor'

export const uploadService = {
  /**
   * Upload a PDF or EPUB for audiobook conversion.
   * Sends multipart/form-data to the PDF processor via the API proxy.
   *
   * @param file        The PDF File object selected by the user
   * @param userId      Authenticated user ID (required by the PDF service)
   * @param onProgress  Optional progress callback (0-100)
   */
  async uploadPDF(
    file: File,
    userId: string,
    onProgress?: (progress: number) => void,
  ): Promise<UploadResponse> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post(
      `${PDF_PROXY}/upload_new_pdf`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        params: { user_id: userId },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total && onProgress) {
            const progress = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total,
            )
            onProgress(progress)
          }
        },
      },
    )

    // Normalise the PDF-service response to the UploadResponse shape
    const data = response.data
    return {
      id: data.id || data.r2_key || '',
      fileName: file.name,
      fileSize: file.size,
      status: data.status === 'COMPLETED' ? 'completed' : 'processing',
      message: data.message,
      pdfPath: data.pdf_path ?? data.pdfPath,
      title: data.title,
    }
  },

  /**
   * Get the processing status of a previously uploaded PDF job.
   */
  async getStatus(jobId: string, userId: string) {
    const response = await api.get(`${PDF_PROXY}/job/${jobId}`, {
      params: { user_id: userId },
    })
    return response.data
  },

  /**
   * Trigger full PDF-to-text processing for an already-uploaded R2 PDF.
   * Called after uploadPDF when the caller wants to start extraction.
   */
  async processPDF(r2PdfPath: string, userId: string, metadata?: Record<string, unknown>) {
    const response = await api.post(
      `${PDF_PROXY}/process_pdf`,
      {
        r2_pdf_path: r2PdfPath,
        ...(metadata && Object.keys(metadata).length > 0 ? { metadata } : {}),
      },
      { params: { user_id: userId } },
    )
    return response.data
  },
}

