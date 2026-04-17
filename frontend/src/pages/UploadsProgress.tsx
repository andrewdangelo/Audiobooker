/**
 * Lists all upload/conversion jobs with per-stage pipeline status.
 */

import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  Circle,
  Clock,
  Loader2,
  Trash2,
  Upload,
} from 'lucide-react'

import { useAppDispatch, useAppSelector } from '@/store/hooks'
import {
  dismissUploadJob,
  pollProcessorJob,
  selectUploadJobs,
  type StageStatus,
  type UploadJob,
} from '@/store/slices/uploadJobsSlice'
import { selectCurrentUser } from '@/store/slices/authSlice'
import { formatFileSize } from '@/data/mockConversion'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'

function stageIcon(status: StageStatus) {
  switch (status) {
    case 'complete':
      return <CheckCircle2 className="h-4 w-4 text-emerald-600" aria-hidden />
    case 'in_progress':
      return <Loader2 className="h-4 w-4 animate-spin text-primary" aria-hidden />
    case 'failed':
      return <AlertCircle className="h-4 w-4 text-destructive" aria-hidden />
    default:
      return <Circle className="h-4 w-4 text-muted-foreground/60" aria-hidden />
  }
}

function jobNeedsProcessorPoll(job: UploadJob): boolean {
  if (!job.processorJobId) return false
  const pdf = job.stages.find((s) => s.id === 'pdf_processing')
  if (!pdf) return false
  return pdf.status === 'pending' || pdf.status === 'in_progress'
}

export default function UploadsProgress() {
  const dispatch = useAppDispatch()
  const jobs = useAppSelector(selectUploadJobs)
  const currentUser = useAppSelector(selectCurrentUser)
  const userId = currentUser?.id ?? ''

  useEffect(() => {
    if (!userId) return

    const tick = () => {
      jobs.filter(jobNeedsProcessorPoll).forEach((j) => {
        if (j.processorJobId) {
          dispatch(pollProcessorJob({ localId: j.localId, jobId: j.processorJobId, userId }))
        }
      })
    }

    tick()
    const id = window.setInterval(tick, 4000)
    return () => window.clearInterval(id)
  }, [dispatch, jobs, userId])

  return (
    <div className="mx-auto max-w-4xl space-y-8 p-6 md:p-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2 text-muted-foreground">
            <Upload className="h-4 w-4" />
            <span className="text-sm font-medium uppercase tracking-wide">Pipeline</span>
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">Uploads &amp; progress</h1>
          <p className="mt-2 max-w-2xl text-muted-foreground">
            Every staged PDF appears here with step-by-step status. PDF stages reflect the processor job; later
            stages advance when orchestration is wired (simulated tail until services are connected).
          </p>
        </div>
        <Button variant="outline" asChild>
          <Link to="/upload">New upload</Link>
        </Button>
      </div>

      {jobs.length === 0 && (
        <Alert>
          <BookOpen className="h-4 w-4" />
          <AlertTitle>No uploads yet</AlertTitle>
          <AlertDescription>
            Start from the upload page. Finished and in-progress jobs will show their pipeline here.
          </AlertDescription>
        </Alert>
      )}

      <div className="space-y-6">
        {jobs.map((job) => (
          <Card key={job.localId} className="overflow-hidden rounded-3xl border shadow-sm">
            <CardHeader className="border-b bg-muted/20 pb-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-1">
                  <CardTitle className="text-xl">{job.title}</CardTitle>
                  <CardDescription className="flex flex-wrap items-center gap-2">
                    {job.author && <span>{job.author}</span>}
                    {job.author && <span className="text-muted-foreground">·</span>}
                    <span>{job.fileName}</span>
                    <Badge variant="outline">{formatFileSize(job.fileSize)}</Badge>
                    <Badge variant="secondary" className="capitalize">
                      {job.creditType} credit
                    </Badge>
                  </CardDescription>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {job.bookId && (
                    <Button variant="secondary" size="sm" asChild>
                      <Link to={`/book/${job.bookId}`}>Open book</Link>
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-muted-foreground"
                    onClick={() => dispatch(dismissUploadJob(job.localId))}
                    aria-label="Remove from list"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Started {new Date(job.createdAt).toLocaleString()}
                </span>
                <span>Updated {new Date(job.updatedAt).toLocaleString()}</span>
                {job.uploadId && (
                  <span className="font-mono text-[11px] text-muted-foreground/80">id {job.uploadId}</span>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4 pt-6">
              <ol className="space-y-4">
                {job.stages.map((stage) => (
                  <li
                    key={stage.id}
                    className={cn(
                      'rounded-2xl border bg-card/50 px-4 py-3',
                      stage.status === 'failed' && 'border-destructive/40 bg-destructive/5',
                    )}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5">{stageIcon(stage.status)}</div>
                        <div>
                          <div className="font-medium leading-snug">{stage.label}</div>
                          <div className="mt-1 text-xs capitalize text-muted-foreground">
                            {stage.status.replace(/_/g, ' ')}
                            {stage.updatedAt && (
                              <span className="ml-2 text-muted-foreground/80">
                                · {new Date(stage.updatedAt).toLocaleTimeString()}
                              </span>
                            )}
                          </div>
                          {stage.errorMessage && (
                            <p className="mt-2 text-sm text-destructive">{stage.errorMessage}</p>
                          )}
                        </div>
                      </div>
                      {typeof stage.progressPercent === 'number' && stage.status === 'in_progress' && (
                        <span className="text-sm tabular-nums text-muted-foreground">
                          {stage.progressPercent}%
                        </span>
                      )}
                    </div>
                    {typeof stage.progressPercent === 'number' && stage.status === 'in_progress' && (
                      <Progress value={stage.progressPercent} className="mt-3 h-2" />
                    )}
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
