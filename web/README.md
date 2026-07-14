# RAG Platform — Frontend

React SPA with a ChatGPT-style interface for the RAG Platform.

## Tech Stack

| Tool | Purpose |
| ---- | ------- |
| React 19 | UI framework |
| TypeScript 6 | Type safety |
| Vite 8 | Build tool + dev server |
| Tailwind CSS 4 | Styling |
| React Router 7 | Client-side routing |
| Zustand | State management |
| react-markdown + remark-gfm | Markdown rendering |
| react-syntax-highlighter | Code block highlighting |
| Lucide React | Icons |
| react-dropzone | File upload drag-and-drop |
| Sonner | Toast notifications |
| Oxlint | Linting (replaces ESLint) |

## Development

```bash
# Install dependencies
npm install

# Start dev server (port 3000)
npm run dev

# Type check
npx tsc -b

# Lint
npm run lint

# Production build
npm run build
```

Or via Docker Compose from the project root:

```bash
docker compose up web
```

## Project Structure

```text
src/
  lib/
    api.ts              — Fetch wrapper (JWT attach, 401 handling, error class)
    types.ts            — TypeScript interfaces for API responses
  stores/
    auth.ts             — Auth state (login, register, logout, token management)
    conversations.ts    — Conversations + messages state
  pages/
    LoginPage.tsx       — Login form
    RegisterPage.tsx    — Registration form
    ChatPage.tsx        — Main chat view (empty state + conversation)
    DocumentsPage.tsx   — Document upload + list
  components/
    layout/
      AppLayout.tsx     — Shell (sidebar + main content area)
      AuthGuard.tsx     — Redirects to /login if unauthenticated
      Sidebar.tsx       — Conversation list, navigation, user info
    chat/
      ChatMessages.tsx  — Message list with auto-scroll
      ChatInput.tsx     — Auto-expanding textarea + send button
      MessageBubble.tsx — Markdown rendering + code blocks + citations
    ui/
      ThemeToggle.tsx   — Dark/light mode switch
  App.tsx               — Router setup + auth initialization
  main.tsx              — React root
  index.css             — Tailwind imports + dark mode + scrollbar styles
```

## Environment Variables

| Variable | Description | Default |
| -------- | ----------- | ------- |
| `VITE_API_URL` | Backend API base URL | `http://localhost:8010` |

## Features

- **Authentication** — Login, register, auto-redirect on 401
- **Chat** — Create conversations, send messages, view AI responses
- **Markdown** — Full GFM support, code blocks with syntax highlighting + copy
- **Citations** — Source documents displayed under each AI response
- **Documents** — Drag-and-drop upload, status tracking, delete
- **Dark mode** — System preference + manual toggle, no flash on load
- **Responsive** — Collapsible sidebar on mobile
- **Toasts** — Success/error notifications

## Linting

Uses [Oxlint](https://oxc.rs) (Rust-based, fast) instead of ESLint. Config in `.oxlintrc.json`.

Plugins enabled: `react`, `typescript`, `oxc`.
