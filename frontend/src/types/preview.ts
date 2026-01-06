// Audiobook Preview Type Definitions

export type CreditType = 'basic' | 'premium' | 'author_publisher';

export type ProcessingStatus = 'uploading' | 'processing' | 'completed' | 'failed';

export interface VoiceOption {
  id: string;
  name: string;
  description: string;
  gender: 'male' | 'female' | 'neutral';
  accent: string;
  sampleUrl: string; // URL to short sample of this voice
}

export interface CharacterVoice {
  characterName: string;
  characterDescription?: string;
  selectedVoiceId: string;
  previewUrl: string; // URL to preview audio for this character
}

export interface AudioPreview {
  id: string;
  audiobookId: string;
  creditType: CreditType;
  processingStatus: ProcessingStatus;
  processingProgress?: number; // 0-100
  
  // Basic credit preview (single voice)
  basicVoicePreviewUrl?: string;
  basicVoiceId?: string;
  
  // Premium credit preview (multiple character voices)
  characterVoices?: CharacterVoice[];
  
  // Available voice options for author/publisher selection
  availableVoices?: VoiceOption[];
  
  estimatedCompletionTime?: string;
  errorMessage?: string;
  
  createdAt: string;
  updatedAt: string;
}

export interface PreviewUpdateRequest {
  characterVoices?: {
    characterName: string;
    voiceId: string;
  }[];
}
