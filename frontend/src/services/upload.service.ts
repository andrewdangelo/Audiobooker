/**
 * Upload Service
 * 
 * Handles PDF file uploads through the API proxy to the PDF processor microservice.
 * 
 * Proxy route:  POST /pdf_processor/pdf_processor/upload_new_pdf
 *   → forwards to: http://PDF_SERVICE/api/v1/pdf/pdf_processor/upload_new_pdf
 *
 * Job-status:   GET  /pdf_processor/pdf_processor/job/{job_id}
 *   → forwards to: http://PDF_SERVICE/api/v1/pdf/pdf_processor/job/{job_id}
 */

import api from './api'
import { UploadResponse } from '../types/upload'

// Path prefix used by the PDF proxy route
const PDF_PROXY = '/pdf_processor/pdf_processor'

export const uploadService = {
  /**
   * Upload a PDF file for audiobook conversion.
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
    }
  },

  /**
   * Get the processing status of a previously uploaded PDF job.
   */
  async getStatus(jobId: string) {
    const response = await api.get(`${PDF_PROXY}/job/${jobId}`)
    return response.data
  },

  /**
   * Trigger full PDF-to-text processing for an already-uploaded R2 PDF.
   * Called after uploadPDF when the caller wants to start extraction.
   */
  async processPDF(r2PdfPath: string, userId: string) {
    const response = await api.post(
      `${PDF_PROXY.replace('/pdf_processor', '')}/pdf_processor/process_pdf`,
      { r2_pdf_path: r2PdfPath },
      { params: { user_id: userId } },
    )
    return response.data
  },
}

