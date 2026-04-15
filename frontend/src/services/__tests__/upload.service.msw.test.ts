import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { testServer } from '@/test/setup'
import { uploadService } from '../upload.service'

describe('uploadService (MSW)', () => {
  it('posts multipart upload to the PDF proxy path', async () => {
    testServer.use(
      http.post('*/pdf_processor/pdf_processor/upload_new_pdf', async ({ request }) => {
        expect(request.url).toContain('user_id=u-42')
        return HttpResponse.json({
          id: 'upload-key-1',
          title: 'My Book',
          pdf_path: 'path/to/file.pdf',
          status: 'COMPLETED',
          message: 'ok',
        })
      }),
    )

    const file = new File(['%PDF-1.4 minimal'], 'chapter.pdf', { type: 'application/pdf' })
    const res = await uploadService.uploadPDF(file, 'u-42')

    expect(res.id).toBe('upload-key-1')
    expect(res.pdfPath).toBe('path/to/file.pdf')
    expect(res.status).toBe('completed')
  })

  it('requests job status with user_id query', async () => {
    testServer.use(
      http.get('*/pdf_processor/pdf_processor/job/job_abc', ({ request }) => {
        expect(request.url).toContain('user_id=u-99')
        return HttpResponse.json({
          job_id: 'job_abc',
          status: 'processing',
          progress: 40,
          message: 'working',
          created_at: 'now',
        })
      }),
    )

    const data = await uploadService.getStatus('job_abc', 'u-99')
    expect(data.status).toBe('processing')
    expect(data.progress).toBe(40)
  })

  it('starts process_pdf with JSON body and user_id', async () => {
    testServer.use(
      http.post('*/pdf_processor/pdf_processor/process_pdf', async ({ request }) => {
        expect(request.url).toContain('user_id=u-7')
        const body = await request.json()
        expect(body).toEqual({ r2_pdf_path: 'books/a.pdf' })
        return HttpResponse.json({ job_id: 'job_x', status: 'accepted' })
      }),
    )

    const data = await uploadService.processPDF('books/a.pdf', 'u-7')
    expect(data.job_id).toBe('job_x')
  })
})
