/**
 * TTS Service
 *
 * All calls go through the API proxy's `/tts_infra` prefix:
 *   Frontend  →  Proxy (/tts_infra/{path})  →  TTS service (/api/v1/tts/{path})
 *
 * TTS service mounts its router at:
 *   prefix = "/api/v1/tts/tts_processor"
 *
 * So the proxy path required is:
 *   /tts_infra/tts_processor/{endpoint}
 */

import api from './api'

const T = '/tts_infra/tts_processor'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TTSVoice {
  voice_id: string
  name: string
  description?: string
  gender?: string
  accent?: string
  sample_url?: string
  provider?: string
}

export interface TTSGenerateRequest {
  chunk_id: string
  text: string
  provider?: string
  voice_id?: string
  model_id?: string
  voice_settings?: Record<string, unknown>
}

export interface TTSGenerateResponse {
  chunk_id: string
  status: string
  audio_path?: string
  duration_seconds?: number
  error?: string
}

export interface TTSBatchRequest {
  provider?: string
  voice_id?: string
  model_id?: string
  json_data?: TTSGenerateRequest[]
}

export interface TTSBatchResponse {
  results: TTSGenerateResponse[]
  total: number
  succeeded: number
  failed: number
}

export interface CharacterVoiceAssignment {
  characterName: string
  voiceId: string
}

// ---------------------------------------------------------------------------
// ttsService
// ---------------------------------------------------------------------------

export const ttsService = {
  /**
   * GET /tts_infra/tts_processor/voices
   * Returns all available voices from registered TTS providers.
   */
  getAvailableVoices: async (): Promise<TTSVoice[]> => {
    const res = await api.get<TTSVoice[]>(`${T}/voices`)
    return res.data
  },

  /**
   * POST /tts_infra/tts_processor/generate
   * Generate audio for a single text chunk.
   */
  generateSpeech: async (request: TTSGenerateRequest): Promise<TTSGenerateResponse> => {
    const res = await api.post<TTSGenerateResponse>(`${T}/generate`, request)
    return res.data
  },

  /**
   * POST /tts_infra/tts_processor/batch
   * Generate audio for multiple text chunks in one call.
   */
  generateBatch: async (request: TTSBatchRequest): Promise<TTSBatchResponse> => {
    const res = await api.post<TTSBatchResponse>(`${T}/batch`, request)
    return res.data
  },

  /**
   * PUT /tts_infra/tts_processor/previews/{previewId}/character-voices
   * Assign a voice to a character in a preview.
   */
  assignCharacterVoice: async (
    previewId: string,
    characterName: string,
    voiceId: string
  ): Promise<void> => {
    await api.put(`${T}/previews/${previewId}/character-voices`, {
      characterName,
      voiceId,
    })
  },

  /**
   * POST /tts_infra/tts_processor/previews/{previewId}/character-voices/bulk
   * Assign voices to multiple characters at once.
   */
  assignCharacterVoicesBulk: async (
    previewId: string,
    assignments: CharacterVoiceAssignment[]
  ): Promise<void> => {
    await api.post(`${T}/previews/${previewId}/character-voices/bulk`, {
      assignments,
    })
  },

  /**
   * GET /tts_infra/tts_processor/previews/{previewId}/sample/basic
   * Returns a short audio sample using the basic (single) voice.
   */
  getBasicVoiceSample: async (previewId: string): Promise<{ sample_url: string }> => {
    const res = await api.get<{ sample_url: string }>(`${T}/previews/${previewId}/sample/basic`)
    return res.data
  },

  /**
   * GET /tts_infra/tts_processor/previews/{previewId}/sample/characters
   * Returns per-character audio samples.
   */
  getCharacterSamples: async (
    previewId: string
  ): Promise<{ characterName: string; sampleUrl: string }[]> => {
    const res = await api.get<{ characterName: string; sampleUrl: string }[]>(
      `${T}/previews/${previewId}/sample/characters`
    )
    return res.data
  },
}

export default ttsService
