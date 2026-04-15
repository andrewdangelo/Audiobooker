import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Clock3,
  FileText,
  Loader2,
  Mic2,
  Play,
  Radio,
  Sparkles,
  Users,
} from 'lucide-react'

import { formatFileSize } from '@/data/mockConversion'
import { useAppDispatch } from '@/store'
import {
  setCharacterVoiceSelection,
  setNarratorSelection,
  startMockConversion,
  type Audiobook,
  type AudiobookConversion,
  type ConversionVoiceOption,
} from '@/store/slices/audiobooksSlice'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { cn } from '@/lib/utils'

function getVoice(voices: ConversionVoiceOption[], voiceId: string) {
  return voices.find(voice => voice.id === voiceId) ?? voices[0]
}

function getProcessingSteps(conversion: AudiobookConversion) {
  const progress = conversion.progress

  return [
    {
      label: 'PDF uploaded through the API proxy',
      description: 'Current behavior: upload succeeds and the PDF is stored before conversion begins.',
      done: true,
      active: false,
    },
    {
      label: 'Metadata staged for user review',
      description: 'Future behavior: replace mock metadata with the processor response.',
      done: true,
      active: false,
    },
    {
      label: 'Conversion job created',
      description: 'The selected credit, narrator, and cast need to be POSTed to the orchestration endpoint.',
      done: progress >= 24,
      active: progress < 24,
    },
    {
      label: conversion.creditType === 'premium' ? 'Cast-aware narration rendering' : 'Narration rendering',
      description: conversion.creditType === 'premium'
        ? 'Premium flow should fan out character voice assignments to the TTS pipeline.'
        : 'Basic flow should send the chosen single narrator voice into the TTS pipeline.',
      done: progress >= 56,
      active: progress >= 24 && progress < 56,
    },
    {
      label: 'Chapter packaging and library sync',
      description: 'The library record should update from live backend progress instead of this mock ticker.',
      done: progress >= 80,
      active: progress >= 56 && progress < 80,
    },
  ]
}

function TodoPanel({ items }: { items: string[] }) {
  return (
    <Card className="border-dashed">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          Backend TODOs
        </CardTitle>
        <CardDescription>
          These are the handoff points that still need real backend wiring.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-muted-foreground">
        {items.map((item) => (
          <div key={item} className="rounded-xl border border-border/70 bg-muted/30 px-3 py-2">
            {item}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

export default function ConversionWorkflow({ book }: { book: Audiobook }) {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const conversion = book.conversion
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [previewVoiceId, setPreviewVoiceId] = useState(
    conversion?.selectedNarratorId ?? '',
  )

  if (!conversion) return null

  const selectedNarrator = getVoice(conversion.narratorOptions, conversion.selectedNarratorId)
  const previewVoice = getVoice(conversion.narratorOptions, previewVoiceId || conversion.selectedNarratorId)
  const isConfiguring = conversion.stage === 'configuring'
  const steps = getProcessingSteps(conversion)

  const lockedCast = conversion.characters.filter(
    character => character.selectedVoiceId !== character.suggestedVoiceId,
  ).length

  const handleConvert = () => {
    dispatch(startMockConversion(book.id))
    setConfirmOpen(false)
    navigate('/library')
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-background via-background to-muted/20">
      <div className="sticky top-0 z-10 border-b bg-background/80 backdrop-blur">
        <div className="container mx-auto flex h-14 items-center gap-3 px-4">
          <Button variant="ghost" size="sm" onClick={() => navigate('/library')} className="-ml-2">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Library
          </Button>
          <div className="flex-1" />
          <Badge variant="secondary" className="gap-1.5">
            {conversion.creditType === 'premium' ? <Users className="h-3 w-3" /> : <Mic2 className="h-3 w-3" />}
            {conversion.creditType === 'premium' ? 'Premium flow' : 'Basic flow'}
          </Badge>
          <Badge variant={isConfiguring ? 'outline' : 'default'} className="gap-1.5">
            {isConfiguring ? <Sparkles className="h-3 w-3" /> : <Radio className="h-3 w-3" />}
            {isConfiguring ? 'Setup required' : 'Conversion running'}
          </Badge>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        <div className="mb-8 grid gap-6 rounded-[28px] border bg-card p-6 shadow-sm lg:grid-cols-[1.35fr_0.65fr]">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <Badge variant="secondary" className="rounded-full px-3 py-1">
                Uploaded PDF
              </Badge>
              <Badge className={cn(
                'rounded-full px-3 py-1',
                conversion.creditType === 'premium'
                  ? 'bg-amber-500 hover:bg-amber-500'
                  : 'bg-sky-600 hover:bg-sky-600',
              )}>
                {conversion.creditType === 'premium' ? 'Premium credit selected' : 'Basic credit selected'}
              </Badge>
            </div>

            <div>
              <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">{book.title}</h1>
              <p className="mt-2 max-w-3xl text-sm text-muted-foreground md:text-base">
                {conversion.metadata.hook}
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <Card className="border-border/70 bg-muted/30">
                <CardContent className="flex items-center gap-3 p-4">
                  <FileText className="h-9 w-9 rounded-2xl bg-background p-2 text-primary" />
                  <div>
                    <div className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Source file</div>
                    <div className="font-medium">{formatFileSize(conversion.sourceFileSize)}</div>
                  </div>
                </CardContent>
              </Card>
              <Card className="border-border/70 bg-muted/30">
                <CardContent className="flex items-center gap-3 p-4">
                  <BookOpen className="h-9 w-9 rounded-2xl bg-background p-2 text-primary" />
                  <div>
                    <div className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Pages</div>
                    <div className="font-medium">{conversion.metadata.pageCount} pages</div>
                  </div>
                </CardContent>
              </Card>
              <Card className="border-border/70 bg-muted/30">
                <CardContent className="flex items-center gap-3 p-4">
                  <Clock3 className="h-9 w-9 rounded-2xl bg-background p-2 text-primary" />
                  <div>
                    <div className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Estimated runtime</div>
                    <div className="font-medium">{Math.round(conversion.metadata.estimatedDurationMinutes / 60)} hr</div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

          <Card className="border-border/70 bg-muted/20">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Library status</CardTitle>
              <CardDescription>
                The uploaded title is already represented in your library while the workflow is in setup or processing.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-2xl border bg-background p-4">
                <div className="mb-2 flex items-center justify-between text-sm">
                  <span className="font-medium">{isConfiguring ? 'Ready for review' : conversion.currentStep}</span>
                  <span className="text-muted-foreground">{isConfiguring ? '0%' : `${conversion.progress}%`}</span>
                </div>
                <Progress value={isConfiguring ? 6 : conversion.progress} />
                <p className="mt-2 text-sm text-muted-foreground">{conversion.etaLabel}</p>
              </div>

              <Alert>
                <Sparkles className="h-4 w-4" />
                <AlertTitle>Current mock behavior</AlertTitle>
                <AlertDescription>
                  This screen uses filler metadata and a mock progress ticker until the PDF processor and conversion services return live data.
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Extracted metadata</CardTitle>
                <CardDescription>
                  Future state: this panel should render the processor response after the PDF is parsed.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                <div>
                  <p className="text-sm text-muted-foreground">{conversion.metadata.description}</p>
                </div>

                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">{conversion.metadata.genre}</Badge>
                  <Badge variant="outline">{conversion.metadata.language}</Badge>
                  {conversion.metadata.toneTags.map((tag) => (
                    <Badge key={tag} variant="outline">{tag}</Badge>
                  ))}
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-2xl border bg-muted/20 p-4">
                    <div className="mb-2 text-sm font-medium">Chapter preview</div>
                    <div className="space-y-2 text-sm text-muted-foreground">
                      {conversion.metadata.chaptersPreview.map((chapter) => (
                        <div key={chapter} className="rounded-xl bg-background px-3 py-2">
                          {chapter}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="rounded-2xl border bg-muted/20 p-4">
                    <div className="mb-2 text-sm font-medium">Character extraction</div>
                    <div className="space-y-2 text-sm text-muted-foreground">
                      {conversion.metadata.characters.map((character) => (
                        <div key={character.id} className="rounded-xl bg-background px-3 py-2">
                          <div className="font-medium text-foreground">{character.name}</div>
                          <div>{character.role}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>
                  {conversion.creditType === 'premium' ? 'Premium voice direction' : 'Narrator selection'}
                </CardTitle>
                <CardDescription>
                  {conversion.creditType === 'premium'
                    ? 'Premium keeps a lead narrator and lets you tune the cast per character.'
                    : 'Basic keeps one narrator across the full conversion.'}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-2xl border bg-primary/5 p-4">
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <div>
                      <div className="text-sm text-muted-foreground">Selected narrator</div>
                      <div className="text-xl font-semibold">{selectedNarrator.name}</div>
                    </div>
                    {conversion.selectedNarratorId === conversion.suggestedNarratorId && (
                      <Badge className="bg-emerald-600 hover:bg-emerald-600">Suggested match</Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">{selectedNarrator.description}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Badge variant="outline">{selectedNarrator.style}</Badge>
                    {selectedNarrator.accent && <Badge variant="outline">{selectedNarrator.accent}</Badge>}
                    {selectedNarrator.recommendedFor && <Badge variant="outline">{selectedNarrator.recommendedFor}</Badge>}
                  </div>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  {conversion.narratorOptions.map((voice) => {
                    const isSelected = conversion.selectedNarratorId === voice.id
                    const isPreviewing = previewVoice.id === voice.id

                    return (
                      <div
                        key={voice.id}
                        className={cn(
                          'rounded-2xl border p-4 transition-colors',
                          isSelected ? 'border-primary bg-primary/5' : 'border-border/70 bg-background',
                        )}
                      >
                        <div className="mb-2 flex items-start justify-between gap-3">
                          <div>
                            <div className="font-medium">{voice.name}</div>
                            <div className="text-sm text-muted-foreground">{voice.style}</div>
                          </div>
                          {voice.id === conversion.suggestedNarratorId && (
                            <Badge variant="outline">Recommended</Badge>
                          )}
                        </div>
                        <p className="mb-3 text-sm text-muted-foreground">{voice.sampleLine}</p>
                        <div className="flex gap-2">
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => setPreviewVoiceId(voice.id)}
                          >
                            <Play className="mr-2 h-3.5 w-3.5" />
                            {isPreviewing ? 'Previewing' : 'Preview'}
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant={isSelected ? 'secondary' : 'default'}
                            onClick={() => dispatch(setNarratorSelection({ id: book.id, voiceId: voice.id }))}
                          >
                            {isSelected ? 'Selected' : 'Use voice'}
                          </Button>
                        </div>
                      </div>
                    )
                  })}
                </div>

                <div className="rounded-2xl border bg-muted/20 p-4">
                  <div className="mb-2 text-sm font-medium">Preview script</div>
                  <p className="text-sm text-muted-foreground">
                    "{previewVoice.sampleLine}"
                  </p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    TODO(back-end): replace this placeholder preview card with streamed sample audio from the voice catalog service.
                  </p>
                </div>
              </CardContent>
            </Card>

            {conversion.creditType === 'premium' && (
              <Card>
                <CardHeader>
                  <CardTitle>Character cast map</CardTitle>
                  <CardDescription>
                    Premium conversion lets you keep the suggested cast or tune each role before conversion starts.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {conversion.characters.map((character) => (
                    <div key={character.id} className="rounded-2xl border p-4">
                      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div className="font-medium">{character.name}</div>
                          <div className="text-sm text-muted-foreground">{character.role}</div>
                        </div>
                        {character.selectedVoiceId === character.suggestedVoiceId && (
                          <Badge variant="outline">Suggested voice kept</Badge>
                        )}
                      </div>
                      <p className="mb-3 text-sm text-muted-foreground">{character.summary}</p>
                      <div className="flex flex-wrap gap-2">
                        {conversion.narratorOptions.slice(0, 4).map((voice) => (
                          <Button
                            key={`${character.id}-${voice.id}`}
                            type="button"
                            size="sm"
                            variant={character.selectedVoiceId === voice.id ? 'default' : 'outline'}
                            onClick={() => dispatch(
                              setCharacterVoiceSelection({
                                id: book.id,
                                characterId: character.id,
                                voiceId: voice.id,
                              }),
                            )}
                          >
                            {voice.name}
                          </Button>
                        ))}
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}
          </div>

          <div className="space-y-6">
            {isConfiguring ? (
              <Card className="overflow-hidden">
                <CardHeader className="bg-muted/30">
                  <CardTitle>Ready to convert</CardTitle>
                  <CardDescription>
                    Review the selection summary below, then confirm the conversion request.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4 p-6">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-2xl border bg-muted/20 p-4">
                      <div className="text-sm text-muted-foreground">Narrator</div>
                      <div className="font-medium">{selectedNarrator.name}</div>
                    </div>
                    <div className="rounded-2xl border bg-muted/20 p-4">
                      <div className="text-sm text-muted-foreground">Cast overrides</div>
                      <div className="font-medium">
                        {conversion.creditType === 'premium' ? `${lockedCast} custom roles` : 'Single voice narration'}
                      </div>
                    </div>
                  </div>

                  <Alert>
                    <ArrowRight className="h-4 w-4" />
                    <AlertTitle>What happens next</AlertTitle>
                    <AlertDescription>
                      Confirming conversion will eventually send the metadata, credit choice, narrator selection, and premium cast map through the API proxy to the conversion microservice.
                    </AlertDescription>
                  </Alert>

                  <Button className="w-full h-12 text-base" onClick={() => setConfirmOpen(true)}>
                    Convert this book
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardHeader>
                  <CardTitle>Conversion progress</CardTitle>
                  <CardDescription>
                    This mirrors the state shown in the library card so the book can be monitored from both places.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div>
                    <div className="mb-2 flex items-center justify-between text-sm">
                      <span className="font-medium">{conversion.currentStep}</span>
                      <span className="text-muted-foreground">{conversion.progress}%</span>
                    </div>
                    <Progress value={conversion.progress} />
                    <p className="mt-2 text-sm text-muted-foreground">{conversion.etaLabel}</p>
                  </div>

                  <div className="space-y-3">
                    {steps.map((step) => (
                      <div key={step.label} className="flex gap-3 rounded-2xl border p-3">
                        <div className="mt-0.5">
                          {step.done ? (
                            <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                          ) : step.active ? (
                            <Loader2 className="h-5 w-5 animate-spin text-primary" />
                          ) : (
                            <div className="h-5 w-5 rounded-full border border-dashed" />
                          )}
                        </div>
                        <div>
                          <div className="font-medium">{step.label}</div>
                          <div className="text-sm text-muted-foreground">{step.description}</div>
                        </div>
                      </div>
                    ))}
                  </div>

                  <Button variant="outline" className="w-full" onClick={() => navigate('/library')}>
                    Back to library queue
                  </Button>
                </CardContent>
              </Card>
            )}

            <TodoPanel
              items={
                isConfiguring
                  ? [
                      'Replace `createMockUploadedAudiobook` data with the real PDF processor response payload after upload completes.',
                      'Persist the chosen basic or premium credit on the backend when the upload is confirmed so credits cannot drift between UI and server state.',
                      'Submit narrator and premium cast selections to the conversion orchestrator instead of using the local `startMockConversion` reducer.',
                    ]
                  : [
                      'Swap the mock progress ticker for polling or server-sent events from the conversion job endpoint.',
                      'Update the library record from real backend progress, including chapter packaging, failure states, and final audiobook ids.',
                      'When conversion finishes, hydrate audio URL, chapter timings, and final metadata so this page can hand off to the existing player view.',
                    ]
              }
            />
          </div>
        </div>
      </div>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm conversion</DialogTitle>
            <DialogDescription>
              This will lock the current selections and move the uploaded PDF into the library conversion queue.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 rounded-2xl border bg-muted/20 p-4 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Credit type</span>
              <span className="font-medium capitalize">{conversion.creditType}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Narrator</span>
              <span className="font-medium">{selectedNarrator.name}</span>
            </div>
            {conversion.creditType === 'premium' && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Custom character voices</span>
                <span className="font-medium">{lockedCast}</span>
              </div>
            )}
          </div>

          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>TODO before production</AlertTitle>
            <AlertDescription>
              The confirm action currently updates local UI state only. It still needs the API-proxy request that creates the real conversion job.
            </AlertDescription>
          </Alert>

          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>
              Keep editing
            </Button>
            <Button onClick={handleConvert}>
              Confirm and convert
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
