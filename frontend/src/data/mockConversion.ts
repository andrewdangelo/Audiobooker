import type {
  Audiobook,
  ConversionCharacter,
  ConversionCreditType,
  ConversionMetadata,
  ConversionVoiceOption,
} from '@/store/slices/audiobooksSlice'

const BASIC_VOICES: ConversionVoiceOption[] = [
  {
    id: 'voice-atlas',
    name: 'Atlas Reed',
    style: 'Warm cinematic',
    accent: 'Neutral American',
    description: 'Balanced pacing with clean diction for fiction and narrative nonfiction.',
    sampleLine: 'Every chapter lands with a calm, confident read that feels polished without sounding stiff.',
    recommendedFor: 'Suspense, literary fiction, memoir',
  },
  {
    id: 'voice-junie',
    name: 'Junie Vale',
    style: 'Bright conversational',
    accent: 'Soft Midwestern',
    description: 'Friendly tone that keeps long-form listening approachable and clear.',
    sampleLine: 'The voice stays intimate and easy to follow, even through exposition-heavy passages.',
    recommendedFor: 'Romance, YA, self-help',
  },
  {
    id: 'voice-soren',
    name: 'Soren Hale',
    style: 'Gravelly dramatic',
    accent: 'Light British',
    description: 'More texture and weight for atmospheric scenes or high-stakes narration.',
    sampleLine: 'Tension reads well here because the pauses and emphasis feel deliberate.',
    recommendedFor: 'Thriller, fantasy, historical drama',
  },
  {
    id: 'voice-nia',
    name: 'Nia Sol',
    style: 'Measured premium documentary',
    accent: 'Contemporary American',
    description: 'Clear articulation and a more polished premium-brand cadence.',
    sampleLine: 'Dense sections remain understandable because the cadence is steady and precise.',
    recommendedFor: 'Business, science, narrative journalism',
  },
]

const PREMIUM_CAST: ConversionVoiceOption[] = [
  ...BASIC_VOICES,
  {
    id: 'voice-marlow',
    name: 'Marlow Quinn',
    style: 'Velvet antagonist',
    accent: 'Refined Transatlantic',
    description: 'Sharper consonants and a slightly theatrical delivery for conflict-heavy scenes.',
    sampleLine: 'Dialogue lands with bite and subtext instead of flattening into a single tone.',
    recommendedFor: 'Villains, rivals, authority figures',
  },
  {
    id: 'voice-ives',
    name: 'Ives Mercer',
    style: 'Grounded elder',
    accent: 'Southern American',
    description: 'Textured lower register suited for mentors, parents, and reflective narration.',
    sampleLine: 'This voice brings weight to exposition without sounding slow.',
    recommendedFor: 'Mentors, fathers, historians',
  },
]

function hashString(input: string) {
  return input.split('').reduce((sum, char) => sum + char.charCodeAt(0), 0)
}

function titleizeFileName(fileName: string) {
  return fileName
    .replace(/\.pdf$/i, '')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

function pickAuthor(seed: number) {
  const authors = [
    'Evelyn Hart',
    'Marcus Vale',
    'Talia Winters',
    'Noah Carden',
    'Priya Bell',
    'Dorian Rowe',
  ]
  return authors[seed % authors.length]
}

function pickGenre(seed: number) {
  const genres = [
    'Speculative Fiction',
    'Contemporary Drama',
    'Mystery',
    'Leadership',
    'Historical Adventure',
    'Romantic Suspense',
  ]
  return genres[seed % genres.length]
}

function buildMetadata(title: string, author: string, genre: string, seed: number, creditType: ConversionCreditType): ConversionMetadata {
  const pageCount = 180 + (seed % 120)
  const estimatedDurationMinutes = pageCount * (creditType === 'premium' ? 2.6 : 2.2)
  const characterPool = [
    {
      id: 'char-protagonist',
      name: 'Mira Vale',
      role: 'Lead',
      summary: 'The point-of-view lead carrying most of the emotional arc.',
    },
    {
      id: 'char-rival',
      name: 'Jonah Mercer',
      role: 'Foil',
      summary: 'A skeptical counterpart whose scenes need clear contrast.',
    },
    {
      id: 'char-mentor',
      name: 'Sister Arden',
      role: 'Mentor',
      summary: 'Provides exposition and emotional grounding in key chapters.',
    },
    {
      id: 'char-antagonist',
      name: 'Lucien Thorne',
      role: 'Antagonist',
      summary: 'Dialogue should read with a colder and more calculated edge.',
    },
  ]

  return {
    title,
    author,
    description: `${title} is a mock conversion draft for ${author}. This filler copy stands in for the PDF processor metadata response and demonstrates how synopsis, extracted themes, and downstream narration suggestions will be surfaced before conversion begins.`,
    genre,
    language: 'English',
    pageCount,
    estimatedDurationMinutes: Math.round(estimatedDurationMinutes),
    toneTags: creditType === 'premium'
      ? ['Dialogue-heavy', 'High tension', 'Character-driven']
      : ['Narrative', 'Accessible pacing', 'Long-form listening'],
    hook: creditType === 'premium'
      ? 'Premium conversion favors a cast-forward production with differentiated character reads.'
      : 'Basic conversion favors a single narrator with a clean, consistent long-form performance.',
    chaptersPreview: [
      'Opening incident and world setup',
      'Conflict escalates around the midpoint reveal',
      'Final act resolves with a reflective epilogue',
    ],
    characters: characterPool.slice(0, creditType === 'premium' ? 4 : 2),
  }
}

function buildCharacters(metadata: ConversionMetadata, voices: ConversionVoiceOption[]): ConversionCharacter[] {
  return metadata.characters.map((character, index) => ({
    id: character.id,
    name: character.name,
    role: character.role,
    summary: character.summary,
    suggestedVoiceId: voices[(index + 1) % voices.length].id,
    selectedVoiceId: voices[(index + 1) % voices.length].id,
  }))
}

export function createMockUploadedAudiobook({
  file,
  uploadId,
  creditType,
}: {
  file: File
  uploadId?: string
  creditType: ConversionCreditType
}): Audiobook {
  const seed = hashString(file.name)
  const title = titleizeFileName(file.name)
  const author = pickAuthor(seed)
  const genre = pickGenre(seed)
  const narratorOptions = creditType === 'premium' ? PREMIUM_CAST : BASIC_VOICES
  const metadata = buildMetadata(title, author, genre, seed, creditType)
  const suggestedNarratorId = narratorOptions[seed % narratorOptions.length].id
  const now = new Date().toISOString()

  return {
    id: `upload-${uploadId ?? crypto.randomUUID()}`,
    title,
    author,
    description: metadata.description,
    duration: metadata.estimatedDurationMinutes * 60,
    audioUrl: '',
    narrator: narratorOptions.find(voice => voice.id === suggestedNarratorId)?.name ?? narratorOptions[0].name,
    genre,
    createdAt: now,
    updatedAt: now,
    status: 'draft',
    progress: 0,
    isPremium: creditType === 'premium',
    purchaseType: creditType,
    conversion: {
      uploadId,
      creditType,
      stage: 'configuring',
      sourceFileName: file.name,
      sourceFileSize: file.size,
      metadata,
      narratorOptions,
      selectedNarratorId: suggestedNarratorId,
      suggestedNarratorId,
      characters: buildCharacters(metadata, narratorOptions),
      progress: 0,
      currentStep: 'Metadata review and voice setup ready',
      etaLabel: creditType === 'premium' ? 'Premium conversion typically takes longer' : 'Basic conversion typically finishes faster',
      lastUpdatedAt: now,
    },
  }
}

export function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
