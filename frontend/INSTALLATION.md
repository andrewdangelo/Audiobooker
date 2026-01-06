# Installation Instructions

## Required Dependencies

The audiobook preview feature requires two additional Radix UI components that may not be in your current package.json:

### Install Missing Dependencies

```bash
cd frontend
npm install @radix-ui/react-select @radix-ui/react-tabs
```

Or with yarn:
```bash
cd frontend
yarn add @radix-ui/react-select @radix-ui/react-tabs
```

Or with pnpm:
```bash
cd frontend
pnpm add @radix-ui/react-select @radix-ui/react-tabs
```

## Verify Installation

After installation, your `package.json` should include:

```json
{
  "dependencies": {
    "@radix-ui/react-select": "^2.1.1",
    "@radix-ui/react-tabs": "^1.1.0",
    // ... other dependencies
  }
}
```

## Build and Test

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Run linter
npm run lint
```

## Troubleshooting

### TypeScript Errors

If you see TypeScript errors about missing modules:

1. Delete `node_modules` and reinstall:
   ```bash
   rm -rf node_modules
   npm install
   ```

2. Clear TypeScript cache:
   ```bash
   rm -rf node_modules/.cache
   ```

3. Restart VS Code or your IDE

### Import Errors

If imports fail, ensure paths are correct in `tsconfig.json`:

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

### Audio Playback Issues

If audio doesn't play in the preview:

1. Check browser console for CORS errors
2. Verify audio URLs are accessible
3. Test with different audio formats
4. Check browser audio permissions

## Next Steps

After installation:

1. Review `AUDIOBOOK_PREVIEW_UI.md` for feature overview
2. Read `PREVIEW_INTEGRATION_GUIDE.md` for backend integration
3. Check `PREVIEW_UI_DESIGN_SPECS.md` for design details
4. Test the preview page at `/preview/:previewId`

## Development Workflow

```bash
# 1. Navigate to preview page
http://localhost:5173/preview/test-id

# 2. Open browser console to see backend integration notes

# 3. Test each credit type by modifying mock data in AudiobookPreview.tsx

# 4. Customize styling in component files
```

---

**Note:** The preview page currently uses mock data. You'll need to implement the backend API endpoints listed in `PREVIEW_INTEGRATION_GUIDE.md` for full functionality.
