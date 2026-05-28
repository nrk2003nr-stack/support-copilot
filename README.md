# Support Copilot

Full-stack AI customer-support app with FastAPI, LangGraph, ChromaDB, mem0, React, Vite, and Tailwind.

## Local Setup

1. Copy `.env.example` to `.env`.
2. Backend:
   ```bash
   pip install -r requirements.txt
   cd backend
   uvicorn main:app --reload --port 8000
   ```
3. Frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
4. Open `http://localhost:3000`.

Demo users are seeded by default:

- `customer@example.com` / `password123`
- `agent@example.com` / `password123`
- `admin@example.com` / `password123`

## Local Fallbacks

The app runs without third-party credentials. Without `OPENAI_API_KEY`, chat uses approved KB retrieval plus a deterministic support fallback, mem0 writes are skipped, voice returns a disabled message, and image troubleshooting returns a local-mode explanation. Channels run in mock mode unless provider env vars are enabled.

## Main Routes

- `POST /auth/login`, `/auth/logout`, `/auth/refresh`, `GET /auth/me`
- `POST /chat`
- `/tickets` for ticket CRUD, comments, timeline, feedback, assignment
- `/handoff` for escalation, takeover, and bot resume
- `/knowledge` for draft/approved KB entries
- `/channels/{provider}/webhook` and `/channels/{provider}/send`
- `/analytics/overview`, status, priority, channel mix, feedback
- `/admin/users`, `/admin/config`

## Tests

```bash
pytest
cd frontend
npm run build
```

## Widget

Serve `widget/embed.js` on a host page. Set `VITE_WIDGET_URL` or `data-support-copilot-url` to the frontend origin; it mounts the React chat route in an iframe and defaults to local development.
