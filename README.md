# EverAfter — Event Planning Assistant

A full-stack, UI-first event planning workspace for weddings, birthdays, anniversaries, community events, and the little gatherings that become big memories.

The project is designed around a warm editorial look: soft blush, peach, sage, lilac and honey colours; floral illustration details; small motion transitions; a task board; editable budget allocations; vendor and guest management; and a celebration burst when a task is completed.

## What is included

- **Login and registration:** separate welcome/auth experience, hashed passwords, signed expiring bearer tokens, demo account in development.
- **Overview:** countdown, event details, progress metrics, upcoming tasks, budget snapshot, guest RSVP progress, vendor booking count, and a custom CSS wedding-garden illustration.
- **My events:** create events, switch between plans, and edit event details. When the event date moves, existing task deadlines shift by the same number of days. When the total budget changes, category budgets scale proportionally.
- **Task board:** To do / In progress / Done columns, filters, board/list views, due-date labels, priorities, edit and delete controls, and task completion animations with confetti + a popper toast.
- **Budget:** category allocation pie chart, total planned/actual/remaining values, editable planned values and actual spend, category progress bars, and overspend indicators.
- **Vendors:** category, quote, contact and notes records, status transitions, rating, edit and remove controls. The sample entries are fictional and are not live recommendations.
- **Guest list:** guest groups, RSVP states, dietary notes, plus-one marker, inline RSVP updates, filtering and deletion.
- **AI planning studio + conversational agent:** event-specific structured drafts plus a chat-based planning partner with context from the active event and existing tasks, personalized suggestions, follow-up questions, and candidate tasks that require an explicit save action. A centralized system prompt defines safety, task, budget and uncertainty rules. Every displayed AI suggestion comes from a configured provider and passes schema/guardrail validation; there is no hardcoded plan fallback.
- **Light/dark themes:** responsive theme controls in the navbar and Settings, with a circular spill/reveal transition that starts at the clicked button. The selection persists on the device; reduced-motion and reminder-indicator preferences are also available.
- **PDF export:** download the current saved event workspace from the navbar or Settings, or download an AI-generated plan directly from the AI draft. Includes event details, tasks, budget, vendors, guests, categories, suggested ideas and caveats as appropriate.
- **Database:** SQLAlchemy models backed by SQLite by default. A connection string can be changed through `DATABASE_URL`.
- **Guardrails and starter evals:** Gemini-first model generation, optional Groq fallback after Gemini errors or quota limits, encrypted per-user API keys, no canned AI replies, no unsupported booking/availability guarantees, tenant-ownership checks, and API/AI tests.

## Technology

**Frontend:** React 18, TypeScript, Vite, Framer Motion, Lucide icons, Recharts, Canvas Confetti, custom CSS.

**Backend:** Python, FastAPI, Pydantic v2, SQLAlchemy 2, SQLite, PBKDF2-HMAC-SHA256 password hashing, HMAC-signed expiring bearer tokens, encrypted per-account provider credentials, Gemini REST API integration, and Groq-compatible chat-completions fallback.

## Run locally

You need Python 3.11+ and Node.js 20+.

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

The API starts at `http://localhost:8000`. Interactive API docs are at `http://localhost:8000/docs`, and the health check is `http://localhost:8000/api/health`.

In development mode, the backend seeds an example wedding workspace the first time the database starts.

**Demo sign-in**

- Email: `hello@everafter.app`
- Password: `EverAfter2026!`

The demo names, vendors, guest details and budget values are fictional. Do not use demo credentials for personal work or production.

### 2. Frontend

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open `http://localhost:5173`. The frontend uses `VITE_API_URL=http://localhost:8000` by default. Theme selection and UI preferences are saved locally in the browser; event data is stored in the backend database and is restored when the same user signs in again.

### 3. Configure AI providers

AI keys are entered in the authenticated app under **Settings → GenAI provider keys**. Gemini is the required primary provider. Groq is optional and is tried automatically if Gemini returns a provider error, quota/rate limit, or unusable response. Both plan generation and chat call the model; the app never substitutes hardcoded suggestion templates when a provider fails.

- Create a Gemini API key in [Google AI Studio](https://aistudio.google.com/app/apikey).
- Optionally create a Groq key in [Groq Console](https://console.groq.com/keys) for automatic fallback.
- Keys are stored per account, encrypted in the database, and returned to the frontend only as configured/not-configured status plus a masked suffix. They are never stored in `frontend/.env`.
- Default models are `gemini-3.8-flash` and `openai/gpt-oss-120b`. These can be changed using `GEMINI_MODEL` and `GROQ_MODEL` in `backend/.env`.
- To remove a key, use the remove-key controls in Settings. A Gemini key is required to enable AI even when a Groq key has been saved.

Set a separate Fernet encryption key in `backend/.env` for production. Generate one with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output to `AI_KEYS_ENCRYPTION_KEY`. Keep it safe: saved account keys cannot be decrypted without the same encryption key. Also replace the example `JWT_SECRET` with a long, random secret before using real data. Never commit either value.

## Test the backend

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest -q
```

The starter suite covers:

- AI draft structure, missing-key errors, provider failover, and no-template behavior.
- Rejection of unsupported booking claims.
- Validation of invalid budget input.
- Authentication requirements for private endpoints.
- Dashboard and workspace persistence.
- Cross-user event isolation.
- Non-mutating AI draft generation.
- Conversational planning-agent guardrails and structured suggestions.
- Relogin persistence for saved event data.

See [`backend/evals/AI_EVALS.md`](backend/evals/AI_EVALS.md) for the system prompt behavior, guardrails, evaluation matrix, and manual review checklist.

## Main API routes

| Area | Endpoints |
|---|---|
| Health | `GET /api/health` |
| Authentication | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` |
| Events | `GET/POST /api/events`, `GET/PATCH/DELETE /api/events/{id}` |
| Dashboard | `GET /api/dashboard/{event_id}` |
| Tasks | `GET/POST /api/tasks`, `PATCH/DELETE /api/tasks/{id}` |
| Vendors | `GET/POST /api/vendors`, `PATCH/DELETE /api/vendors/{id}` |
| Guests | `GET/POST /api/guests`, `PATCH/DELETE /api/guests/{id}` |
| Budget | `GET/POST /api/expenses`, `PATCH/DELETE /api/expenses/{id}` |
| AI provider settings | `GET/PUT /api/ai/settings` |
| AI draft plan | `POST /api/ai/draft-plan` |
| Conversational planning agent | `POST /api/ai/assistant` |

All workspace routes require a bearer token. Workspace operations verify event ownership before reading or mutating a task, guest, vendor, or budget row.

## Project structure

```text
everafter-planner/
├── README.md
├── backend/
│   ├── app/
│   │   ├── main.py                     # App setup, development seed data, dashboard
│   │   ├── config.py                   # Environment settings
│   │   ├── database.py                 # SQLAlchemy engine and session
│   │   ├── models.py                   # User, Event, Task, Vendor, Guest, Expense
│   │   ├── schemas.py                  # Pydantic input/output contracts
│   │   ├── security.py                 # Password hash and signed expiring tokens
│   │   ├── dependencies.py             # Authentication dependencies
│   │   ├── routers/                    # Authentication, event, workspace and AI APIs
│   │   └── services/
│   │       ├── ai_planner.py           # Structured model-generated plan drafts only
│   │       ├── ai_assistant.py         # Context-aware planning assistant
│   │       └── ai_prompts.py           # Centralized system prompts
│   ├── tests/                          # API, persistence and AI guardrail tests
│   ├── evals/AI_EVALS.md               # Evaluation matrix and manual checklist
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/App.tsx                     # Workspace, theme animation and plan export
    ├── src/components/SettingsPage.tsx # Theme, provider keys and workspace preferences
    ├── src/components/PlanningAssistantPanel.tsx
    ├── src/lib/api.ts                  # Typed API client and helpers
    ├── src/lib/exportPdf.ts             # Browser-side PDF generation
    ├── src/styles.css                  # Responsive design system and interactions
    ├── src/main.tsx
    ├── package.json
    └── .env.example
```

## Important production follow-ups

This is a substantial local starter, not a deployed event marketplace. Before production use, add database migrations, login throttling/rate limiting, email verification and account recovery, more complete audit logging, a production-grade secret manager, an HTTPS deployment, security headers/CSP, monitoring, and automated UI/browser tests. For higher-risk production deployments, consider moving browser authentication from `localStorage` bearer tokens to secure `HttpOnly` cookies with the appropriate CSRF strategy.

The app intentionally does **not** claim live vendor pricing or availability, send invitations, accept contracts, handle payments, or sync real calendars. Those integrations require trusted providers and explicit user permission. AI output is a planning suggestion; review dates, prices, contracts and accessibility requirements with the people involved.
