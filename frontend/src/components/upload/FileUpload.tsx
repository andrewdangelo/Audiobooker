import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle2, Crown, FileUp, Sparkles, UploadCloud, Zap } from 'lucide-react'

import { createMockUploadedAudiobook, formatFileSize } from '@/data/mockConversion'
import { addAudiobook, useAppDispatch, useAppSelector } from '@/store'
import { selectCurrentUser } from '@/store/slices/authSlice'
import { setUserCredits, setUserPremiumCredits } from '@/store/slices/storeSlice'
import { selectUserCredits, selectUserPremiumCredits } from '@/store/slices/storeSlice'
import { uploadService } from '@/services/upload.service'
import UploadProgress from './UploadProgress'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { cn } from '@/lib/utils'

type CreditType = 'basic' | 'premium'

const CREDIT_OPTIONS: Array<{
  type: CreditType
  label: string
  description: string
  icon: typeof Zap
  accent: string
  features: string[]
}> = [
  {
    type: 'basic',
    label: 'Basic credit',
    description: 'Single narrator conversion with a suggested voice swap option before finalizing.',
    icon: Zap,
    accent: 'border-sky-200 bg-sky-50 text-sky-700',
    features: ['1 narrator', 'Fastest turnaround', 'Ideal for straightforward narration'],
  },
  {
    type: 'premium',
    label: 'Premium credit',
    description: 'Theatrical setup with narrator and per-character voice assignments.',
    icon: Crown,
    accent: 'border-amber-200 bg-amber-50 text-amber-700',
    features: ['Lead narrator + cast map', 'Dialogue-focused setup', 'Longer conversion time'],
  },
]

export default function FileUpload() {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const currentUser = useAppSelector(selectCurrentUser)
  const basicCredits = useAppSelector(selectUserCredits)
  const premiumCredits = useAppSelector(selectUserPremiumCredits)

  const [isDragging, setIsDragging] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [uploadResult, setUploadResult] = useState<{ id: string; status: string } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [creditDialogOpen, setCreditDialogOpen] = useState(false)
  const [selectedCreditType, setSelectedCreditType] = useState<CreditType>('basic')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const files = e.dataTransfer.files
    if (files && files.length > 0) {
      handleFileSelect(files[0])
    }
  }

  const handleFileSelect = (file: File) => {
    setError(null)
    setUploadResult(null)

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Please select a PDF file.')
      return
    }

    if (file.size > 52_428_800) {
      setError('File size must be less than 50MB.')
      return
    }

    setSelectedFile(file)
  }

  const handleUpload = async () => {
    if (!selectedFile) return

    const availableCredits = selectedCreditType === 'premium' ? premiumCredits : basicCredits
    if (availableCredits <= 0) {
      setError(`You need an available ${selectedCreditType} credit before you can finalize this upload.`)
      return
    }

    setUploading(true)
    setError(null)
    setProgress(0)

    try {
      const result = await uploadService.uploadPDF(
        selectedFile,
        currentUser?.id ?? '',
        (nextProgress) => setProgress(nextProgress),
      )

      // TODO(back-end): move credit reservation/deduction to the upload confirmation
      // endpoint so the server remains the source of truth for available credits.
      if (selectedCreditType === 'premium') {
        dispatch(setUserPremiumCredits(Math.max(0, premiumCredits - 1)))
      } else {
        dispatch(setUserCredits(Math.max(0, basicCredits - 1)))
      }

      const draftBook = createMockUploadedAudiobook({
        file: selectedFile,
        uploadId: result.id,
        creditType: selectedCreditType,
      })

      // TODO(back-end): replace this optimistic local insert with the audiobook record
      // returned by the API proxy once the PDF processor emits staged metadata.
      dispatch(addAudiobook(draftBook))
      setUploadResult({ id: result.id, status: result.status })
      setProgress(100)
      setCreditDialogOpen(false)
      navigate(`/book/${draftBook.id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const handleClick = () => {
    fileInputRef.current?.click()
  }

  const selectedOption = CREDIT_OPTIONS.find(option => option.type === selectedCreditType) ?? CREDIT_OPTIONS[0]

  return (
    <>
      <div className="space-y-5">
        <div
          className={cn(
            'rounded-[28px] border-2 border-dashed p-8 text-center transition-colors',
            isDragging ? 'border-primary bg-primary/5' : 'border-border bg-card hover:border-primary/50',
          )}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={handleClick}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={(e) => {
              const files = e.target.files
              if (files && files.length > 0) {
                handleFileSelect(files[0])
              }
            }}
            className="hidden"
          />

          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-3xl bg-primary/10 text-primary">
            <UploadCloud className="h-8 w-8" />
          </div>

          {selectedFile ? (
            <div className="space-y-2">
              <p className="text-lg font-semibold">{selectedFile.name}</p>
              <div className="flex flex-wrap items-center justify-center gap-2 text-sm text-muted-foreground">
                <Badge variant="outline">{formatFileSize(selectedFile.size)}</Badge>
                <Badge variant="outline">PDF ready for upload</Badge>
              </div>
              <p className="mx-auto max-w-xl text-sm text-muted-foreground">
                The next step will ask which credit type this upload should consume before the file is finalized.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-lg font-semibold">Drop your PDF here or click to browse</p>
              <p className="text-sm text-muted-foreground">
                PDF files only, up to 50MB. Text-based PDFs will produce the best metadata and narration results.
              </p>
            </div>
          )}
        </div>

        {selectedFile && !uploading && (
          <div className="rounded-3xl border bg-card p-5">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="font-semibold">Upload summary</h3>
                <p className="text-sm text-muted-foreground">
                  Choose whether this PDF enters the basic or premium conversion path.
                </p>
              </div>
              <div className="flex gap-2">
                <Badge variant="outline">{basicCredits} basic credits</Badge>
                <Badge variant="outline">{premiumCredits} premium credits</Badge>
              </div>
            </div>

            <Button className="w-full h-11" onClick={() => setCreditDialogOpen(true)}>
              <Sparkles className="mr-2 h-4 w-4" />
              Continue to credit selection
            </Button>
          </div>
        )}

        {uploading && selectedFile && (
          <div className="rounded-3xl border bg-card p-5">
            <UploadProgress progress={progress} fileName={selectedFile.name} />
          </div>
        )}

        {uploadResult && !uploading && (
          <Alert>
            <CheckCircle2 className="h-4 w-4" />
            <AlertTitle>Upload staged successfully</AlertTitle>
            <AlertDescription>
              Upload id `{uploadResult.id}` is now represented in the library UI with mock metadata until the processor response is wired in.
            </AlertDescription>
          </Alert>
        )}

        {error && (
          <Alert variant="destructive">
            <FileUp className="h-4 w-4" />
            <AlertTitle>Upload blocked</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </div>

      <Dialog open={creditDialogOpen} onOpenChange={setCreditDialogOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Select the conversion credit</DialogTitle>
            <DialogDescription>
              This choice determines which setup screen the user sees after the upload finishes.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 md:grid-cols-2">
            {CREDIT_OPTIONS.map((option) => {
              const Icon = option.icon
              const availableCredits = option.type === 'premium' ? premiumCredits : basicCredits
              const isSelected = selectedCreditType === option.type

              return (
                <button
                  key={option.type}
                  type="button"
                  onClick={() => setSelectedCreditType(option.type)}
                  className={cn(
                    'rounded-3xl border p-5 text-left transition-all',
                    option.accent,
                    isSelected ? 'ring-2 ring-primary/30' : 'opacity-90 hover:opacity-100',
                  )}
                >
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="rounded-2xl bg-white/80 p-2">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div>
                        <div className="font-semibold">{option.label}</div>
                        <div className="text-sm opacity-80">{option.description}</div>
                      </div>
                    </div>
                    <Badge variant="outline" className="bg-white/70">
                      {availableCredits} available
                    </Badge>
                  </div>

                  <div className="space-y-2 text-sm opacity-90">
                    {option.features.map((feature) => (
                      <div key={feature} className="rounded-xl bg-white/70 px-3 py-2">
                        {feature}
                      </div>
                    ))}
                  </div>
                </button>
              )
            })}
          </div>

          <Alert>
            <Sparkles className="h-4 w-4" />
            <AlertTitle>Production TODO</AlertTitle>
            <AlertDescription>
              The chosen credit type is currently tracked in frontend state only. A real confirm endpoint should reserve the credit and return the staged book metadata payload.
            </AlertDescription>
          </Alert>

          <div className="rounded-2xl border bg-muted/30 p-4 text-sm">
            <div className="mb-1 font-medium">Selected path: {selectedOption.label}</div>
            <div className="text-muted-foreground">
              {selectedOption.type === 'premium'
                ? 'After upload you will land on the premium setup view with narrator and character voice assignments.'
                : 'After upload you will land on the basic setup view with a suggested narrator and alternate voice samples.'}
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setCreditDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleUpload}
              disabled={uploading || (selectedCreditType === 'premium' ? premiumCredits : basicCredits) <= 0}
            >
              Use 1 {selectedCreditType === 'premium' ? 'Premium' : 'Basic'} Credit and Upload
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
