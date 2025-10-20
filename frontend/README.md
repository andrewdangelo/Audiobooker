# Audiobooker Frontend

React-based frontend application for the Audiobooker PDF-to-Audiobook conversion system.

## 🚀 Tech Stack

- **React 18** with TypeScript
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **shadcn/ui** - High-quality React components
- **React Router** - Client-side routing
- **Axios** - HTTP client for API requests

## 📁 Project Structure

```
src/
├── components/       # Reusable components
│   ├── ui/          # shadcn/ui components
│   ├── layout/      # Layout components (Header, Footer, etc.)
│   ├── upload/      # Upload-related components
│   ├── audiobook/   # Audiobook-specific components
│   └── common/      # Common shared components
├── pages/           # Page components
├── hooks/           # Custom React hooks
├── services/        # API service layer
├── types/           # TypeScript type definitions
├── utils/           # Utility functions
├── lib/             # Library configurations
└── config/          # Configuration files
```

## 🛠️ Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

1. Install dependencies:
   ```bash
   npm install
   ```

2. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open your browser to `http://localhost:5173`

## 📝 Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run test` - Run tests

## 🎨 UI Components

This project uses **shadcn/ui** components. To add new components:

```bash
npx shadcn-ui@latest add [component-name]
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the frontend directory:

```env
VITE_API_URL=http://localhost:8000
```

## 📚 Key Features

- **File Upload**: Drag-and-drop PDF upload with progress tracking
- **Audiobook Library**: Browse and manage converted audiobooks
- **Audio Player**: Built-in player with playback controls
- **Responsive Design**: Mobile-first, responsive UI
- **Type Safety**: Full TypeScript support

## 🧪 Testing

```bash
npm run test
```

## 🏗️ Building for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## 📖 Documentation

- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)
- [Tailwind CSS Documentation](https://tailwindcss.com/)
- [shadcn/ui Documentation](https://ui.shadcn.com/)
