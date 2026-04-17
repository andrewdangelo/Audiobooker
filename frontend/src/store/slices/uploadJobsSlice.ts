/**
 * Tracks in-flight PDF uploads and conversion pipeline stages for the uploads progress UI.
 */

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import type { RootState } from '../index'
import { audiobookService } from '@/services/audiobook.service'
import { uploadService } from '@/services/upload.service'
import { addAudiobook } from './audiobooksSlice'

export const PIPELINE_STAGE_DEFS = [
  { id: 'uploading', label: 'Uploading' },
  { id: 'pdf_processing', label: 'PDF Processing' },
  { id: 'text_extraction', label: 'Text Extraction' },
  { id: 'character_voice', label: 'Character Voice Assignment & Customization' },
  { id: 'tts', label: 'TTS Conversion' },
  { id: 'finalizing', label: 'Finalizing' },
  { id: 'complete', label: 'Complete' },
] as const

export type PipelineStageId = (typeof PIPELINE_STAGE_DEFS)[number]['id']
export type StageStatus = 'pending' | 'in_progress' | 'complete' | 'failed'

export interface UploadJobStage {
  id: PipelineStageId
  label: string
  status: StageStatus
  progressPercent?: number
  updatedAt?: string
  errorMessage?: string
}

export interface UploadJob {
  localId: string
  bookId?: string
  uploadId: string
  pdfPath?: string
  processorJobId?: string
  title: string
  author?: string
  coverUrl?: string
  fileName: string
  fileSize: number
  creditType: 'basic' | 'premium'
  stages: UploadJobStage[]
  createdAt: string
  updatedAt: string
  tailSimulationStarted: boolean
}

export interface RegisterUploadJobPayload {
  localId: string
  bookId?: string
  uploadId: string
  pdfPath?: string
  processorJobId?: string
  title: string
  author?: string
  coverUrl?: string
  fileName: string
  fileSize: number
  creditType: 'basic' | 'premium'
  uploadStageFailedMessage?: string
  pdfJobStartFailedMessage?: string
}

function nowIso() {
  return new Date().toISOString()
}

function buildInitialStages(
  uploadComplete: boolean,
  pdfJobActive: boolean,
  uploadError?: string,
  pdfJobError?: string,
): UploadJobStage[] {
  return PIPELINE_STAGE_DEFS.map((def) => {
    if (def.id === 'uploading') {
      return {
        id: def.id,
        label: def.label,
        status: uploadError ? 'failed' : uploadComplete ? 'complete' : 'in_progress',
        progressPercent: uploadError ? undefined : uploadComplete ? 100 : 0,
        updatedAt: nowIso(),
        errorMessage: uploadError,
      }
    }
    if (def.id === 'pdf_processing') {
      if (uploadError) {
        return { id: def.id, label: def.label, status: 'pending', updatedAt: nowIso() }
      }
      if (pdfJobError) {
        return {
          id: def.id,
          label: def.label,
          status: 'failed',
          updatedAt: nowIso(),
          errorMessage: pdfJobError,
        }
      }
      if (pdfJobActive) {
        return {
          id: def.id,
          label: def.label,
          status: 'in_progress',
          progressPercent: 5,
          updatedAt: nowIso(),
        }
      }
      return {
        id: def.id,
        label: def.label,
        status: uploadComplete ? 'pending' : 'pending',
        progressPercent: 0,
        updatedAt: nowIso(),
      }
    }
    return {
      id: def.id,
      label: def.label,
      status: 'pending',
      updatedAt: nowIso(),
    }
  })
}

function patchStage(
  stages: UploadJobStage[],
  id: PipelineStageId,
  patch: Partial<UploadJobStage>,
): UploadJobStage[] {
  return stages.map((s) => (s.id === id ? { ...s, ...patch, updatedAt: nowIso() } : s))
}

interface UploadJobsState {
  jobs: UploadJob[]
}

const initialState: UploadJobsState = {
  jobs: [],
}

const uploadJobsSlice = createSlice({
  name: 'uploadJobs',
  initialState,
  reducers: {
    registerUploadJob(state, action: PayloadAction<RegisterUploadJobPayload>) {
      const p = action.payload
      const pdfJobActive = !!p.processorJobId && !p.pdfJobStartFailedMessage && !p.uploadStageFailedMessage
      const stages = buildInitialStages(
        !p.uploadStageFailedMessage,
        pdfJobActive,
        p.uploadStageFailedMessage,
        p.pdfJobStartFailedMessage,
      )
      const job: UploadJob = {
        localId: p.localId,
        bookId: p.bookId,
        uploadId: p.uploadId,
        pdfPath: p.pdfPath,
        processorJobId: p.processorJobId,
        title: p.title,
        author: p.author,
        coverUrl: p.coverUrl,
        fileName: p.fileName,
        fileSize: p.fileSize,
        creditType: p.creditType,
        stages,
        createdAt: nowIso(),
        updatedAt: nowIso(),
        tailSimulationStarted: false,
      }
      state.jobs = [job, ...state.jobs.filter((j) => j.localId !== p.localId)]
    },
    linkJobToBackendBook(
      state,
      action: PayloadAction<{ localId: string; bookId: string }>,
    ) {
      const j = state.jobs.find((x) => x.localId === action.payload.localId)
      if (j) {
        j.bookId = action.payload.bookId
        j.updatedAt = nowIso()
      }
    },
    setStage(
      state,
      action: PayloadAction<{
        localId: string
        stageId: PipelineStageId
        status: StageStatus
        progressPercent?: number
        errorMessage?: string
      }>,
    ) {
      const j = state.jobs.find((x) => x.localId === action.payload.localId)
      if (!j) return
      const { stageId, status, progressPercent, errorMessage } = action.payload
      j.stages = patchStage(j.stages, stageId, { status, progressPercent, errorMessage })
      j.updatedAt = nowIso()
    },
    applyProcessorPoll(
      state,
      action: PayloadAction<{
        localId: string
        status: string
        progress: number
        message?: string
        error?: string
        pipelineStage?: string
        audiobookId?: string
      }>,
    ) {
      const { localId, status, progress, error, pipelineStage } = action.payload
      const j = state.jobs.find((x) => x.localId === localId)
      if (!j) return

      const ps = (pipelineStage || '').toLowerCase()

      if (status === 'failed') {
        j.stages = patchStage(j.stages, 'pdf_processing', {
          status: 'failed',
          errorMessage: error || 'PDF processing failed',
        })
        j.updatedAt = nowIso()
        return
      }

      if (status === 'pending' || status === 'processing') {
        j.stages = patchStage(j.stages, 'pdf_processing', {
          status: 'in_progress',
          progressPercent: Math.min(99, Math.max(0, progress)),
        })
        if (ps === 'text_extraction') {
          j.stages = patchStage(j.stages, 'text_extraction', {
            status: 'in_progress',
            progressPercent: Math.min(99, Math.max(0, progress)),
          })
        }
        if (ps === 'ai_enrichment' || ps === 'ai_service') {
          j.stages = patchStage(j.stages, 'character_voice', {
            status: 'in_progress',
            progressPercent: 60,
          })
        }
        if (ps === 'tts') {
          j.stages = patchStage(j.stages, 'tts', {
            status: 'in_progress',
            progressPercent: 70,
          })
        }
        if (ps === 'backend_sync') {
          j.stages = patchStage(j.stages, 'finalizing', {
            status: 'in_progress',
            progressPercent: 85,
          })
        }
        j.updatedAt = nowIso()
        return
      }

      if (status === 'completed') {
        j.stages = patchStage(j.stages, 'pdf_processing', {
          status: 'complete',
          progressPercent: 100,
        })
        j.stages = patchStage(j.stages, 'text_extraction', {
          status: 'complete',
          progressPercent: 100,
        })
        j.stages = patchStage(j.stages, 'character_voice', {
          status: 'complete',
          progressPercent: 100,
        })
        j.stages = patchStage(j.stages, 'tts', {
          status: 'complete',
          progressPercent: 100,
        })
        j.stages = patchStage(j.stages, 'finalizing', {
          status: 'complete',
          progressPercent: 100,
        })
        j.stages = patchStage(j.stages, 'complete', {
          status: 'complete',
          progressPercent: 100,
        })
        j.updatedAt = nowIso()
      }
    },
    dismissUploadJob(state, action: PayloadAction<string>) {
      state.jobs = state.jobs.filter((j) => j.localId !== action.payload)
    },
  },
})

export const pollProcessorJob = createAsyncThunk(
  'uploadJobs/pollProcessorJob',
  async (
    { localId, jobId, userId }: { localId: string; jobId: string; userId: string },
    { getState, dispatch, rejectWithValue },
  ) => {
    try {
      const job = await uploadService.getStatus(jobId, userId)
      const state = getState() as RootState
      const existing = state.uploadJobs.jobs.find((j) => j.localId === localId)
      if (!existing) return rejectWithValue('job_gone')

      const status = String(job.status || '').toLowerCase()
      const progress = typeof job.progress === 'number' ? job.progress : 0
      const pipelineStage =
        job.pipeline_stage != null ? String(job.pipeline_stage) : undefined
      const audiobookId =
        job.audiobook_id != null ? String(job.audiobook_id) : undefined

      dispatch(
        uploadJobsSlice.actions.applyProcessorPoll({
          localId,
          status,
          progress,
          message: job.message,
          error: job.error,
          pipelineStage,
          audiobookId,
        }),
      )

      if (audiobookId) {
        dispatch(
          uploadJobsSlice.actions.linkJobToBackendBook({ localId, bookId: audiobookId }),
        )
      }

      if (status === 'completed' && audiobookId && userId) {
        try {
          const book = await audiobookService.getById(audiobookId, userId)
          dispatch(addAudiobook(book))
        } catch {
          /* library fetch can race rehydration; user can refresh */
        }
      }

      return job
    } catch (e: unknown) {
      return rejectWithValue(e instanceof Error ? e.message : 'poll_failed')
    }
  },
)

export const runProcessorPolling = createAsyncThunk(
  'uploadJobs/runProcessorPolling',
  async (
    { localId, jobId, userId }: { localId: string; jobId: string; userId: string },
    { dispatch },
  ) => {
    const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))
    for (let i = 0; i < 180; i++) {
      const action = await dispatch(pollProcessorJob({ localId, jobId, userId }))
      if (pollProcessorJob.rejected.match(action)) return
      const payload = action.payload as { status?: string } | undefined
      const st = String(payload?.status || '').toLowerCase()
      if (st === 'failed' || st === 'completed') return
      await delay(2000)
    }
  },
)

export const { registerUploadJob, dismissUploadJob } = uploadJobsSlice.actions
export default uploadJobsSlice.reducer

export const selectUploadJobs = (state: RootState) => state.uploadJobs.jobs

export function selectActiveUploadJobs(jobs: UploadJob[]) {
  return jobs.filter((j) => {
    const complete = j.stages.find((s) => s.id === 'complete')
    return complete?.status !== 'complete'
  })
}
