# TechMart Support — React Frontend

A React (Vite) chat interface styled after ChatGPT/Gemini: dark theme,
collapsible conversation-history sidebar, centered message column, pill-
shaped composer. Talks to the FastAPI backend in `../backend`.

## Structure

```
frontend/
├── components/     Reusable UI pieces (Sidebar, ChatWindow, MessageBubble,
│                    Composer, TypingIndicator, RoutingBadges, TopBar,
│                    ProtectedRoute, AuthProvider)
├── pages/           Routed screens (LoginPage, ChatPage, AnalyticsPage)
├── hooks/           useAuth, useChat, useSessions, useAnalytics
├── services/        Thin fetch wrappers per API area (api.js is the shared
│                    base client; authService/chatService/sessionService/
│                    analyticsService each call one group of endpoints)
├── styles/          theme.css (design tokens/CSS variables), global.css,
│                    App.css
├── App.jsx          Route definitions
├── main.jsx         Entry point
└── index.html       Vite HTML entry
```

## Setup

```bash
cd frontend
npm install
cp .env.example .env.local   # optional — defaults to http://localhost:8000
npm run dev
```

Visit http://localhost:5500. Make sure the backend is running first
(`uvicorn backend.main:app --reload --port 8000` from the project root).

## Notes

- **Auth token persistence**: unlike the previous single-file HTML version,
  the auth token is stored in `localStorage` (see `AuthProvider.jsx`), so
  logging in survives a page refresh. On mount, the token is validated
  against `GET /api/auth/me`; if it's invalid or expired, the user is
  returned to the login screen automatically.
- **Conversation history sidebar**: fetches `GET /api/sessions` on login and
  after every message, so new conversations and updated previews appear
  without a manual refresh.
- **Analytics page** (`/analytics`) is only reachable if the logged-in user's
  email is in the backend's `ADMIN_EMAILS` — `ProtectedRoute` redirects
  everyone else back to `/`.
- **Design tokens** live in `styles/theme.css` as CSS custom properties —
  change `--accent`, `--bg-app`, etc. there to re-theme the whole app.

## Build for production

```bash
npm run build
```

Outputs to `frontend/dist/`. Serve it with any static host; set
`VITE_API_BASE_URL` at build time if the backend isn't on
`http://localhost:8000`.
