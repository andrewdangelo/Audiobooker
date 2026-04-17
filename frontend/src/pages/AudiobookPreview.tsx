import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ProcessingStatusComponent } from '@/components/audiobook/ProcessingStatus';
import { VoicePreview } from '@/components/audiobook/VoicePreview';
import { VoiceSelector } from '@/components/audiobook/VoiceSelector';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AudioPreview } from '@/types/preview';
import { ArrowLeft, Sparkles, Users, BookOpen } from 'lucide-react';
import api from '@/services/api';

/**
 * AudiobookPreview Page
 * 
 * Main page for previewing TTS-generated audiobook after upload
 * Supports three credit types:
 * - Basic: Single voice for entire book
 * - Premium: Multiple character voices (theatrical)
 * - Author/Publisher: Custom voice selection per character
 */
export default function AudiobookPreview() {
  const { previewId } = useParams<{ previewId: string }>();
  const navigate = useNavigate();

  // State management
  const [preview, setPreview] = useState<AudioPreview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch preview data on component mount
  // Proxy route: GET /backend/previews/{previewId}
  useEffect(() => {
    const fetchPreview = async () => {
      try {
        setIsLoading(true);
        const response = await api.get<AudioPreview>(`/backend/previews/${previewId}`);
        setPreview(response.data);
      } catch (err) {
        setError('Failed to load preview. Please try again.');
        console.error('Error fetching preview:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchPreview();
  }, [previewId]);

  // BACKEND INTEGRATION NOTE:
  // Poll for status updates if processing is not complete
  useEffect(() => {
    if (!preview || preview.processingStatus === 'completed' || preview.processingStatus === 'failed') {
      return;
    }

    const pollInterval = setInterval(async () => {
      try {
        // Proxy route: GET /backend/previews/{previewId}/status
        const response = await api.get<Partial<AudioPreview>>(`/backend/previews/${previewId}/status`);
        setPreview(prev => prev ? { ...prev, ...response.data } : null);
      } catch (err) {
        console.error('Error polling status:', err);
      }
    }, 3000); // Poll every 3 seconds

    return () => clearInterval(pollInterval);
  }, [preview, previewId]);

  // Handle voice selection change for author/publisher mode
  const handleVoiceChange = async (characterName: string, voiceId: string) => {
    if (!preview) return;

    try {
      // Proxy route: PUT /tts_infra/tts_processor/previews/{previewId}/character-voices
      await api.put(`/tts_infra/tts_processor/previews/${previewId}/character-voices`, {
        characterName,
        voiceId,
      });

      // Update local state
      setPreview(prev => {
        if (!prev || !prev.characterVoices) return prev;
        
        const updatedVoices = prev.characterVoices.map(cv =>
          cv.characterName === characterName
            ? { ...cv, selectedVoiceId: voiceId }
            : cv
        );
        
        return { ...prev, characterVoices: updatedVoices };
      });
    } catch (err) {
      console.error('Error updating voice selection:', err);
    }
  };

  // Handle final confirmation and proceed to conversion
  const handleConfirmAndProceed = async () => {
    try {
      // Proxy route: POST /backend/previews/{previewId}/confirm
      // Queues the full TTS conversion job
      await api.post(`/backend/previews/${previewId}/confirm`);

      // Navigate to conversion progress page or library
      navigate('/library');
    } catch (err) {
      console.error('Error confirming preview:', err);
      setError('Failed to start conversion. Please try again.');
    }
  };

  if (isLoading) {
    return (
      <div className="container max-w-6xl mx-auto py-8">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
            <p className="text-muted-foreground">Loading preview...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !preview) {
    return (
      <div className="container max-w-6xl mx-auto py-8">
        <Card>
          <CardContent className="py-8">
            <div className="text-center">
              <p className="text-red-500 mb-4">{error || 'Preview not found'}</p>
              <Button onClick={() => navigate('/upload')}>
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Upload
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const isProcessing = preview.processingStatus === 'uploading' || preview.processingStatus === 'processing';

  return (
    <div className="container max-w-6xl mx-auto py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/upload')}
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold">Audiobook Preview</h1>
            <p className="text-muted-foreground mt-1">
              Listen to samples and customize your audiobook narration
            </p>
          </div>
        </div>
      </div>

      {/* Processing Status */}
      {isProcessing && (
        <ProcessingStatusComponent
          status={preview.processingStatus}
          progress={preview.processingProgress}
          errorMessage={preview.errorMessage}
          estimatedTime={preview.estimatedCompletionTime}
        />
      )}

      {/* Preview Content - Only show when processing is complete */}
      {preview.processingStatus === 'completed' && (
        <div className="space-y-6">
          {/* Credit Type Indicator */}
          <Card className="border-2 border-primary/20 bg-primary/5">
            <CardContent className="py-4">
              <div className="flex items-center gap-3">
                {preview.creditType === 'basic' && (
                  <>
                    <BookOpen className="h-6 w-6 text-primary" />
                    <div>
                      <h3 className="font-semibold">Basic Credit Plan</h3>
                      <p className="text-sm text-muted-foreground">
                        Single professional voice narration for your entire audiobook
                      </p>
                    </div>
                  </>
                )}
                {preview.creditType === 'premium' && (
                  <>
                    <Sparkles className="h-6 w-6 text-purple-600" />
                    <div>
                      <h3 className="font-semibold">Premium Credit Plan</h3>
                      <p className="text-sm text-muted-foreground">
                        Theatrical experience with multiple character voices
                      </p>
                    </div>
                  </>
                )}
                {preview.creditType === 'author_publisher' && (
                  <>
                    <Users className="h-6 w-6 text-blue-600" />
                    <div>
                      <h3 className="font-semibold">Author/Publisher Plan</h3>
                      <p className="text-sm text-muted-foreground">
                        Custom voice selection for each character
                      </p>
                    </div>
                  </>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Voice Previews - Different layouts based on credit type */}
          {preview.creditType === 'basic' && preview.basicVoicePreviewUrl && (
            <Card>
              <CardHeader>
                <CardTitle>Preview Your Audiobook</CardTitle>
                <CardDescription>
                  Listen to a sample of your audiobook with our professional narrator
                </CardDescription>
              </CardHeader>
              <CardContent>
                <VoicePreview
                  audioUrl={preview.basicVoicePreviewUrl}
                  voiceName="Professional Narrator"
                  voiceDescription="Standard single-voice narration"
                />
              </CardContent>
            </Card>
          )}

          {preview.creditType === 'premium' && preview.characterVoices && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-purple-600" />
                  Theatrical Character Voices
                </CardTitle>
                <CardDescription>
                  Experience your story with unique voices for each character
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-2">
                  {preview.characterVoices.map((character) => {
                    const voice = preview.availableVoices?.find(
                      v => v.id === character.selectedVoiceId
                    );
                    
                    return (
                      <VoicePreview
                        key={character.characterName}
                        audioUrl={character.previewUrl}
                        characterName={character.characterName}
                        voiceName={voice?.name}
                        voiceDescription={character.characterDescription}
                        isTheatrical={true}
                      />
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}

          {preview.creditType === 'author_publisher' && preview.characterVoices && preview.availableVoices && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5 text-blue-600" />
                  Customize Character Voices
                </CardTitle>
                <CardDescription>
                  Select the perfect voice for each character in your audiobook
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {preview.characterVoices.map((character) => (
                    <VoiceSelector
                      key={character.characterName}
                      characterName={character.characterName}
                      characterDescription={character.characterDescription}
                      availableVoices={preview.availableVoices || []}
                      selectedVoiceId={character.selectedVoiceId}
                      onVoiceChange={(voiceId) => handleVoiceChange(character.characterName, voiceId)}
                      previewUrl={character.previewUrl}
                    />
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Action Buttons */}
          <div className="flex justify-between items-center">
            <Button
              variant="outline"
              onClick={() => navigate('/upload')}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Upload Different File
            </Button>
            
            <Button
              size="lg"
              onClick={handleConfirmAndProceed}
              className="px-8"
            >
              Confirm & Start Full Conversion
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
