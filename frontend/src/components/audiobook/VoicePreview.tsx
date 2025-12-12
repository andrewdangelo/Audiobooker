import { useState, useRef, useEffect } from 'react';
import { Play, Pause } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

interface VoicePreviewProps {
  audioUrl: string;
  characterName?: string;
  voiceName?: string;
  voiceDescription?: string;
  isTheatrical?: boolean;
}

/**
 * VoicePreview Component
 * 
 * Displays an audio player for previewing voice samples
 * Supports both basic (single voice) and premium (character-specific) previews
 */
export function VoicePreview({ 
  audioUrl, 
  characterName,
  voiceName,
  voiceDescription,
  isTheatrical = false
}: VoicePreviewProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => setCurrentTime(audio.currentTime);
    const handleDurationChange = () => setDuration(audio.duration);
    const handleEnded = () => setIsPlaying(false);

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('durationchange', handleDurationChange);
    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('durationchange', handleDurationChange);
      audio.removeEventListener('ended', handleEnded);
    };
  }, []);

  const togglePlayPause = async () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
    } else {
      await audio.play();
    }
    setIsPlaying(!isPlaying);
  };

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const progressPercentage = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <Card className="w-full hover:shadow-md transition-shadow">
      <CardContent className="p-4">
        <div className="space-y-3">
          {/* Header with character/voice info */}
          <div className="flex items-start justify-between">
            <div>
              {characterName && (
                <div className="flex items-center gap-2">
                  <h4 className="font-semibold text-sm">{characterName}</h4>
                  {isTheatrical && (
                    <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium">
                      Theatrical
                    </span>
                  )}
                </div>
              )}
              {voiceName && (
                <p className="text-sm text-muted-foreground mt-0.5">
                  {voiceName}
                </p>
              )}
              {voiceDescription && (
                <p className="text-xs text-muted-foreground mt-1">
                  {voiceDescription}
                </p>
              )}
            </div>
          </div>

          {/* Audio player controls */}
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="icon"
              onClick={togglePlayPause}
              className="flex-shrink-0"
            >
              {isPlaying ? (
                <Pause className="h-4 w-4" />
              ) : (
                <Play className="h-4 w-4" />
              )}
            </Button>

            <div className="flex-1 space-y-1">
              {/* Progress bar */}
              <div className="relative h-1 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="absolute top-0 left-0 h-full bg-primary transition-all duration-100"
                  style={{ width: `${progressPercentage}%` }}
                />
              </div>
              
              {/* Time display */}
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>{formatTime(currentTime)}</span>
                <span>{formatTime(duration)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Hidden audio element */}
        <audio ref={audioRef} src={audioUrl} preload="metadata" />

        {/* BACKEND INTEGRATION NOTE:
            Audio URL should be fetched from:
            - Basic: GET /api/previews/{previewId}/basic-voice-sample
            - Premium: GET /api/previews/{previewId}/character-samples
            Ensure CORS is configured for audio file access
        */}
      </CardContent>
    </Card>
  );
}
