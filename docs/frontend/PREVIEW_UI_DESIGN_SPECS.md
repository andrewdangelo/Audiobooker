# Audiobook Preview UI - Visual Design Specifications

## Color Palette

### Credit Type Colors
```css
/* Basic Credit */
--basic-accent: hsl(221, 83%, 53%);        /* Blue */
--basic-light: hsl(221, 83%, 95%);
--basic-border: hsl(221, 83%, 80%);

/* Premium Credit */
--premium-accent: hsl(270, 70%, 60%);      /* Purple */
--premium-light: hsl(270, 70%, 95%);
--premium-border: hsl(270, 70%, 80%);

/* Author/Publisher Credit */
--author-accent: hsl(210, 100%, 50%);      /* Bright Blue */
--author-light: hsl(210, 100%, 95%);
--author-border: hsl(210, 100%, 80%);
```

### Status Colors
```css
/* Processing States */
--uploading: hsl(200, 90%, 50%);           /* Light Blue */
--processing: hsl(270, 70%, 60%);          /* Purple */
--completed: hsl(142, 76%, 36%);           /* Green */
--failed: hsl(0, 84%, 60%);                /* Red */
```

## Typography Scale

```css
/* Headings */
--heading-xl: 30px / 36px;  /* Page title */
--heading-lg: 20px / 28px;  /* Section headers */
--heading-md: 16px / 24px;  /* Card titles */
--heading-sm: 14px / 20px;  /* Subsections */

/* Body Text */
--body-base: 14px / 20px;   /* Standard text */
--body-sm: 13px / 18px;     /* Supporting text */
--body-xs: 12px / 16px;     /* Labels, metadata */

/* Font Weights */
--weight-regular: 400;
--weight-medium: 500;
--weight-semibold: 600;
--weight-bold: 700;
```

## Spacing System

```css
/* Spacing Scale (based on 4px) */
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-8: 32px;
--space-10: 40px;
--space-12: 48px;
--space-16: 64px;

/* Common Patterns */
--card-padding: var(--space-4);
--section-gap: var(--space-6);
--component-gap: var(--space-4);
```

## Layout Specifications

### Page Container
```
Max Width: 1280px (max-w-6xl)
Padding: 32px (py-8)
Margin: auto-centered
```

### Grid Layouts

#### Two Column Grid (Premium Character Voices)
```
Display: grid
Columns: 2 (md:grid-cols-2)
Gap: 16px
Responsive: Stacks on mobile
```

#### Voice Selector Layout
```
Display: flex-col
Gap: 16px
Border: 2px solid gray-200
Padding: 16px
Border Radius: 8px
Background: gray-50
```

## Component Specifications

### 1. Processing Status Card

```
┌─────────────────────────────────────────────────────┐
│  [Icon]  Processing TTS Conversion...              │
│                                                     │
│          Generating your audiobook preview.        │
│          Estimated time: 2 minutes                 │
│                                                     │
│          ████████████░░░░░░░░░░░░░░░  60%         │
│                                          60% Complete│
└─────────────────────────────────────────────────────┘

Dimensions:
- Max width: 672px (max-w-2xl)
- Padding: 24px
- Border: 2px solid
- Border radius: 8px
- Icon size: 24px x 24px
- Progress bar height: 8px
```

### 2. Voice Preview Card

```
┌─────────────────────────────────────────┐
│  Character Name          [Theatrical]   │
│  Voice Name                             │
│  Character description text...          │
│                                         │
│  [▶]  ━━━━━●━━━━━━━━━━━━━━━          │
│       0:15              2:30            │
└─────────────────────────────────────────┘

Dimensions:
- Width: 100% (responsive)
- Padding: 16px
- Border: 1px solid
- Border radius: 8px
- Hover: shadow-md transition
- Play button: 40px x 40px
- Progress bar: height 4px
```

### 3. Voice Selector Card

```
┌─────────────────────────────────────────┐
│  [👤]  Character Name                   │
│        Character description            │
│                                         │
│  Select Voice for Character Name       │
│  ┌───────────────────────────────────┐ │
│  │  Choose a voice...            ▼  │ │
│  └───────────────────────────────────┘ │
│                                         │
│  Preview Selected Voice                │
│  ┌─────────────────────────────────┐   │
│  │  [Voice Preview Component]      │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘

Dimensions:
- Width: 100%
- Padding: 16px
- Border: 2px solid gray-200
- Border radius: 8px
- Background: gray-50
- Gap between elements: 16px
- Icon: 20px x 20px
```

### 4. Credit Type Banner

```
┌─────────────────────────────────────────────────────┐
│  [Icon]  Premium Credit Plan                       │
│          Theatrical experience with multiple       │
│          character voices                          │
└─────────────────────────────────────────────────────┘

Dimensions:
- Width: 100%
- Padding: 16px
- Border: 2px solid (primary/20)
- Background: (primary/5)
- Border radius: 8px
- Icon size: 24px x 24px
- Icon color: Based on credit type
```

### 5. Action Buttons

```
Primary Button:
- Height: 44px (size-lg)
- Padding: 16px 32px (px-8)
- Font size: 16px
- Font weight: 600
- Border radius: 6px
- Min width: 200px

Secondary Button:
- Height: 40px
- Padding: 8px 16px
- Font size: 14px
- Font weight: 500
- Border radius: 6px
- Border: 1px solid
```

## Responsive Breakpoints

```css
/* Mobile First Approach */
--mobile: default;              /* < 640px */
--tablet: 640px;               /* sm: */
--desktop: 768px;              /* md: */
--large-desktop: 1024px;       /* lg: */
--extra-large: 1280px;         /* xl: */

/* Key Responsive Changes */
@media (max-width: 768px) {
  /* Two column grid becomes single column */
  .grid-cols-2 { grid-template-columns: 1fr; }
  
  /* Reduce padding */
  .page-container { padding: 16px; }
  
  /* Stack buttons vertically */
  .button-group { flex-direction: column; }
}
```

## Animation Specifications

### Loading States
```css
/* Spinner Animation */
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.animate-spin {
  animation: spin 1s linear infinite;
}

/* Progress Bar Fill */
transition: width 0.3s ease-in-out;
```

### Hover Effects
```css
/* Card Hover */
.card:hover {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  transition: box-shadow 0.2s ease;
}

/* Button Hover */
.button:hover {
  opacity: 0.9;
  transition: opacity 0.2s ease;
}
```

### Fade In (Status Changes)
```css
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
.fade-in {
  animation: fadeIn 0.3s ease-in;
}
```

## Icon Usage

### From lucide-react

```tsx
import {
  BookOpen,        // Basic credit icon
  Sparkles,        // Premium credit icon
  Users,           // Author/Publisher icon
  Play,            // Play audio
  Pause,           // Pause audio
  Loader2,         // Loading spinner
  CheckCircle2,    // Success state
  XCircle,         // Error state
  ArrowLeft,       // Back navigation
  ChevronDown,     // Dropdown indicator
  User             // Character icon
} from 'lucide-react';
```

### Icon Sizes
```
- Small: 16px (h-4 w-4)
- Medium: 20px (h-5 w-5)
- Large: 24px (h-6 w-6)
```

## Accessibility Specifications

### Focus States
```css
/* Keyboard focus indicator */
.focusable:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}
```

### ARIA Labels
```tsx
// Audio player
<button aria-label="Play audio preview">
  <Play />
</button>

// Progress bar
<div role="progressbar" aria-valuenow={60} aria-valuemin={0} aria-valuemax={100}>
  60% Complete
</div>

// Status announcements
<div role="status" aria-live="polite">
  Processing complete
</div>
```

### Color Contrast
```
Text on Background: 4.5:1 minimum
Large Text: 3:1 minimum
Interactive Elements: 3:1 minimum
```

## Dark Mode Considerations

```css
/* Light Mode (default) */
--background: hsl(0, 0%, 100%);
--foreground: hsl(0, 0%, 10%);
--card: hsl(0, 0%, 100%);
--border: hsl(0, 0%, 90%);

/* Dark Mode */
@media (prefers-color-scheme: dark) {
  --background: hsl(0, 0%, 10%);
  --foreground: hsl(0, 0%, 90%);
  --card: hsl(0, 0%, 15%);
  --border: hsl(0, 0%, 25%);
}
```

## Print Styles (if needed)

```css
@media print {
  /* Hide interactive elements */
  button, .audio-player { display: none; }
  
  /* Expand cards */
  .card { border: 1px solid #000; }
  
  /* Black and white */
  * { color: #000 !important; }
}
```

## Example CSS Classes

```css
/* Credit Type Badges */
.badge-basic {
  background-color: var(--basic-light);
  color: var(--basic-accent);
  padding: 2px 8px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 500;
}

.badge-premium {
  background-color: var(--premium-light);
  color: var(--premium-accent);
  padding: 2px 8px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 500;
}

/* Progress Bar */
.progress-bar {
  height: 8px;
  background-color: hsl(0, 0%, 90%);
  border-radius: 9999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: var(--primary);
  transition: width 0.3s ease-in-out;
}

/* Audio Timeline */
.audio-timeline {
  height: 4px;
  background-color: hsl(0, 0%, 85%);
  border-radius: 9999px;
  position: relative;
  cursor: pointer;
}

.audio-timeline-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background-color: var(--primary);
  border-radius: 9999px;
}
```

## State Variations

### Processing States Visual Guide

1. **Uploading**
   - Icon: Spinning Loader (blue)
   - Progress: 0-20%
   - Message: "Uploading file..."

2. **Processing**
   - Icon: Spinning Loader (purple)
   - Progress: 20-100%
   - Message: "Processing TTS conversion..."

3. **Completed**
   - Icon: CheckCircle (green)
   - Progress: 100%
   - Message: "Processing complete!"

4. **Failed**
   - Icon: XCircle (red)
   - Progress: N/A
   - Message: Error details

---

**Design System:** Based on shadcn/ui and Tailwind CSS
**Last Updated:** December 11, 2025
