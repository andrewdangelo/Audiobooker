import { useState } from 'react';
import { VoiceOption } from '@/types/preview';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { VoicePreview } from './VoicePreview';
import { User } from 'lucide-react';

interface VoiceSelectorProps {
  characterName: string;
  characterDescription?: string;
  availableVoices: VoiceOption[];
  selectedVoiceId?: string;
  onVoiceChange: (voiceId: string) => void;
  previewUrl?: string;
}

/**
 * VoiceSelector Component
 * 
 * Allows author/publishers to select voices for specific characters
 * Displays dropdown with available voice options and live preview
 */
export function VoiceSelector({
  characterName,
  characterDescription,
  availableVoices,
  selectedVoiceId,
  onVoiceChange,
  previewUrl
}: VoiceSelectorProps) {
  const [localSelectedVoice, setLocalSelectedVoice] = useState<string>(
    selectedVoiceId || ''
  );

  const selectedVoice = availableVoices.find(v => v.id === localSelectedVoice);

  const handleVoiceChange = (voiceId: string) => {
    setLocalSelectedVoice(voiceId);
    onVoiceChange(voiceId);
    
    // BACKEND INTEGRATION NOTE:
    // When voice is changed, make API call to update character voice selection
    // Endpoint: PUT /api/previews/{previewId}/character-voices
    // Body: { characterName: string, voiceId: string }
    // This should trigger generation of a new preview with the selected voice
  };

  return (
    <div className="space-y-4 p-4 border-2 border-gray-200 rounded-lg bg-gray-50">
      {/* Character Information */}
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 p-2 bg-primary/10 rounded-full">
          <User className="h-5 w-5 text-primary" />
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-base">{characterName}</h3>
          {characterDescription && (
            <p className="text-sm text-muted-foreground mt-1">
              {characterDescription}
            </p>
          )}
        </div>
      </div>

      {/* Voice Selection Dropdown */}
      <div className="space-y-2">
        <Label htmlFor={`voice-select-${characterName}`} className="text-sm font-medium">
          Select Voice for {characterName}
        </Label>
        <Select
          value={localSelectedVoice}
          onValueChange={handleVoiceChange}
        >
          <SelectTrigger 
            id={`voice-select-${characterName}`}
            className="w-full bg-white"
          >
            <SelectValue placeholder="Choose a voice..." />
          </SelectTrigger>
          <SelectContent>
            {availableVoices.map((voice) => (
              <SelectItem key={voice.id} value={voice.id}>
                <div className="flex flex-col">
                  <span className="font-medium">{voice.name}</span>
                  <span className="text-xs text-muted-foreground">
                    {voice.gender} • {voice.accent}
                  </span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Voice Preview Player */}
      {selectedVoice && (
        <div className="space-y-2">
          <Label className="text-sm font-medium">Preview Selected Voice</Label>
          <VoicePreview
            audioUrl={previewUrl || selectedVoice.sampleUrl}
            voiceName={selectedVoice.name}
            voiceDescription={`${selectedVoice.gender} • ${selectedVoice.accent} - ${selectedVoice.description}`}
          />
        </div>
      )}

      {/* BACKEND INTEGRATION NOTE:
          Available voices should be fetched from:
          GET /api/voices/available?gender=all&accent=all
          
          Response format:
          {
            voices: [
              {
                id: string,
                name: string,
                description: string,
                gender: 'male' | 'female' | 'neutral',
                accent: string,
                sampleUrl: string
              }
            ]
          }
      */}
    </div>
  );
}
