import { ArrowRight, Crown, Library, Mic2, ScanSearch, Sparkles, UploadCloud } from 'lucide-react'

import FileUpload from '@/components/upload/FileUpload'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const stages = [
  {
    icon: UploadCloud,
    title: 'Upload the PDF',
    description: 'The existing proxy flow stores the source file first, then the UI stages a draft library item.',
  },
  {
    icon: Sparkles,
    title: 'Choose basic or premium',
    description: 'The user must pick the credit type before finalizing the upload so the correct setup experience appears next.',
  },
  {
    icon: ScanSearch,
    title: 'Review metadata',
    description: 'Today this is filler data; later it should be populated by the PDF processor microservice response.',
  },
  {
    icon: Library,
    title: 'Send to conversion queue',
    description: 'After confirmation the draft appears in the library with a visible processing state and book-detail progress view.',
  },
]

export default function Upload() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8 grid gap-6 rounded-[32px] border bg-card p-6 shadow-sm lg:grid-cols-[1.2fr_0.8fr] lg:p-8">
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">Upload workflow</Badge>
            <Badge variant="outline">Post-upload UX</Badge>
          </div>
          <div>
            <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">
              Stage the book before conversion starts
            </h1>
            <p className="mt-3 max-w-2xl text-sm text-muted-foreground md:text-base">
              This flow now covers the UI between PDF upload and final conversion. Users choose a basic or premium credit,
              review mock metadata, lock voice selections, and then send the book into the library conversion queue.
            </p>
          </div>
        </div>

        <Card className="border-border/70 bg-muted/20">
          <CardHeader>
            <CardTitle className="text-lg">Experience paths</CardTitle>
            <CardDescription>
              Both conversion tiers are represented now so backend wiring can plug into a stable UI later.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4">
              <div className="mb-2 flex items-center gap-2 font-medium text-sky-700">
                <Mic2 className="h-4 w-4" />
                Basic conversion
              </div>
              <p className="text-sky-900/80">
                Metadata review, narrator recommendation, alternate sample voices, then a single-voice conversion confirmation.
              </p>
            </div>
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
              <div className="mb-2 flex items-center gap-2 font-medium text-amber-700">
                <Crown className="h-4 w-4" />
                Premium conversion
              </div>
              <p className="text-amber-900/80">
                Metadata review, lead narrator selection, character voice assignments, then a theatrical conversion confirmation.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <Card className="overflow-hidden">
          <CardHeader className="border-b bg-muted/20">
            <CardTitle>Upload and assign a credit</CardTitle>
            <CardDescription>
              The credit selection modal is part of the finalize-upload step, not a later conversion step.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-6">
            <FileUpload />
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Workflow map</CardTitle>
              <CardDescription>
                These are the screens and handoffs the backend will eventually need to support.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {stages.map((stage, index) => {
                const Icon = stage.icon
                return (
                  <div key={stage.title} className="flex gap-4 rounded-2xl border p-4">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                      <Icon className="h-5 w-5" />
                    </div>
                    <div className="flex-1">
                      <div className="mb-1 flex items-center gap-2">
                        <span className="text-sm font-medium text-muted-foreground">0{index + 1}</span>
                        <h3 className="font-medium">{stage.title}</h3>
                      </div>
                      <p className="text-sm text-muted-foreground">{stage.description}</p>
                    </div>
                    {index < stages.length - 1 && (
                      <ArrowRight className="mt-3 hidden h-4 w-4 text-muted-foreground lg:block" />
                    )}
                  </div>
                )
              })}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Backend integration notes</CardTitle>
              <CardDescription>
                These TODOs are also echoed in the setup and progress screens where the real service calls will land.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <div className="rounded-2xl border bg-muted/20 p-4">
                Return extracted metadata from the PDF processor so the title, author, description, chapter hints, and character list stop using filler data.
              </div>
              <div className="rounded-2xl border bg-muted/20 p-4">
                Persist the chosen basic or premium credit at upload confirmation time so server-side balance and UI state stay aligned.
              </div>
              <div className="rounded-2xl border bg-muted/20 p-4">
                Add a conversion orchestration endpoint that accepts narrator and cast selections, then exposes live progress back to the library and detail page.
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
