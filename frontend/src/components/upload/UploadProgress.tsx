// TODO: Implement UploadProgress component
// This component displays upload and conversion progress

import { Progress } from '../ui/progress'

interface UploadProgressProps {
  progress: number
  fileName: string
}

export default function UploadProgress({ progress, fileName }: UploadProgressProps) {
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span>{fileName}</span>
        <span>{progress}%</span>
      </div>
      <Progress value={progress} />
    </div>
  )
}
