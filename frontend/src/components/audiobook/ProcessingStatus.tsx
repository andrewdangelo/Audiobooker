import { ProcessingStatus } from '@/types/preview';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, CheckCircle2, XCircle } from 'lucide-react';

interface ProcessingStatusProps {
  status: ProcessingStatus;
  progress?: number;
  errorMessage?: string;
  estimatedTime?: string;
}

/**
 * ProcessingStatus Component
 * 
 * Displays the current status of TTS processing after file upload
 * Shows progress indicator, completion status, or error messages
 */
export function ProcessingStatusComponent({ 
  status, 
  progress = 0, 
  errorMessage,
  estimatedTime 
}: ProcessingStatusProps) {
  
  const getStatusConfig = () => {
    switch (status) {
      case 'uploading':
        return {
          icon: <Loader2 className="h-6 w-6 animate-spin text-blue-500" />,
          title: 'Uploading File...',
          description: 'Your audiobook file is being uploaded to our servers.',
          showProgress: true,
          variant: 'default' as const
        };
      case 'processing':
        return {
          icon: <Loader2 className="h-6 w-6 animate-spin text-purple-500" />,
          title: 'Processing TTS Conversion...',
          description: estimatedTime 
            ? `Generating your audiobook preview. Estimated time: ${estimatedTime}`
            : 'This may take a few minutes depending on the file size.',
          showProgress: true,
          variant: 'default' as const
        };
      case 'completed':
        return {
          icon: <CheckCircle2 className="h-6 w-6 text-green-500" />,
          title: 'Processing Complete!',
          description: 'Your audiobook preview is ready. Listen to the sample below.',
          showProgress: false,
          variant: 'default' as const
        };
      case 'failed':
        return {
          icon: <XCircle className="h-6 w-6 text-red-500" />,
          title: 'Processing Failed',
          description: errorMessage || 'An error occurred during processing. Please try again.',
          showProgress: false,
          variant: 'destructive' as const
        };
    }
  };

  const config = getStatusConfig();

  return (
    <div className="w-full max-w-2xl mx-auto p-6 space-y-4">
      <Alert variant={config.variant} className="border-2">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 mt-0.5">
            {config.icon}
          </div>
          <div className="flex-1 space-y-2">
            <div>
              <h3 className="font-semibold text-lg">{config.title}</h3>
              <AlertDescription className="mt-1">
                {config.description}
              </AlertDescription>
            </div>
            
            {config.showProgress && (
              <div className="space-y-2">
                <Progress value={progress} className="h-2" />
                <p className="text-sm text-muted-foreground text-right">
                  {progress}% Complete
                </p>
              </div>
            )}
          </div>
        </div>
      </Alert>

      {/* BACKEND INTEGRATION NOTE:
          Poll backend API every 2-3 seconds to get updated processing status
          Endpoint: GET /api/previews/{previewId}/status
          Response should include: status, progress, estimatedTime, errorMessage
      */}
    </div>
  );
}
