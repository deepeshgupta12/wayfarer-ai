# Wayfarer

**AI-powered travel planning and destination intelligence platform.**

Wayfarer is a full-stack application that uses agentic AI orchestration to help travellers research destinations, build personalised itineraries, compare cities, and monitor their active trips in real time. The system is built backend-first: every planning decision, enrichment step, and notification is driven by LangGraph agents running on a FastAPI backend, with a React frontend that consumes those results.

---

## Table of Contents

- [Architecture](#architecture)
- [Core Features](#core-features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Environment Variables](#environment-variables)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
- [API Overview](#api-overview)
- [Agentic Flows](#agentic-flows)
- [Data Models](#data-models)
- [Background Services](#background-services)
- [Frontend Pages](#frontend-pages)
- [Configuration Reference](#configuration-reference)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        React Frontend                        │
│   Vite · TailwindCSS · TanStack Query · Framer Motion       │
└───────────────────────────┬─────────────────────────────────┘
                            │ REST + NDJSON streaming
┌───────────────────────────▼─────────────────────────────────┐
│                    FastAPI Backend (Python)                   │
│                                                              │
│   ┌───────────────┐  ┌──────────────┐  ┌────────────────┐  │
│   │  LangGraph    │  │  APScheduler │  │  SQLAlchemy ORM│  │
│   │  Agents       │  │  Background  │  │  + Alembic     │  │
│   │  (orchestrate │  │  Sweep       │  │  Migrations    │  │
│   │   / stream)   │  │  (30 min)    │  └──────┬─────────┘  │
│   └───────────────┘  └──────────────┘         │            │
│                                                │            │
│   ┌──────────────┐  ┌─────────────┐  ┌────────▼──────────┐ │
│   │  TripAdvisor │  │  Google     │  │    PostgreSQL     │ │
│   │  API Client  │  │  Places     │  │  (primary store)  │ │
│   └──────────────┘  │  API Client │  └───────────────────┘ │
│                     └─────────────┘                         │
│   ┌──────────────────────────────────────────────────────┐  │
│   │  Redis  (similarity index · session cache)           │  │
│   └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

All agent graphs persist their state via a `PostgresSaver` checkpointer so context survives API restarts. The system falls back to `MemorySaver` gracefully if the checkpoint schema is unavailable.

---

## Core Features

### Destination Intelligence
- **Destination Guide** — generates a structured, slot-based travel guide for any city including curated area cards, photo assets, highlights, and "you'd also love" alternatives.
- **Destination Comparison** — side-by-side weighted comparison of two cities across pace, budget, interests, and group type, with a planning recommendation and next-step chips.
- **Nearby Discovery** — context-aware discovery of walkable or proximate places near an active trip location.
- **Hidden Gems** — surfaces underrated local options filtered against the traveller's active trip context.

### Trip Planning Workspace
- **Brief Parsing** — natural-language trip brief (e.g. "4 days in Kyoto, couple trip, food and culture, mid-budget") parsed into structured constraints with missing-field detection.
- **Slot-based Itinerary Enrichment** — converts a parsed brief into a day-by-day, slot-by-slot itinerary with candidate places, geo-clustering, routing rationale, and fallback candidates per slot.
- **Slot Replacement** — replaces an individual slot (e.g. Day 2 afternoon) with a better alternative based on a follow-up instruction like "make it less hectic" or "more food".
- **Trip Plan Updates** — re-applies constraint changes (destination, group type, pace, interests) and re-enriches the itinerary while preserving the session.
- **Version History** — every trip can be snapshotted and restored to any prior version, with branch labels for history tracking.

### Traveller Persona and Memory
- **Persona Initialisation** — onboarding flow captures interests, travel style, pace preference, budget, and group type and persists a structured persona.
- **Persona Refresh from Memory** — after key events (alert resolved, guide generated), the persona is re-distilled from the traveller's memory log to stay current without requiring explicit re-onboarding.
- **Traveller Memory Log** — a structured event log (selected places, skipped recommendations, plan edits, resolved alerts) used to personalise future recommendations.

### Visual and Review Intelligence
- **Photo Intelligence** — ingests place photos from TripAdvisor and Google Places, scores them for quality and persona relevance, and ranks them per slot context (e.g. evening slot prefers ambience shots over daytime scenes).
- **Review Intelligence** — aggregates review signals from multiple providers, extracts standout themes, authenticity indicators, and derives a review insight and score for each candidate place.
- **Persona Embedding** — embeds traveller personas and place profiles into a vector space (via Redis) to power similarity search.
- **Similar Places** — after indexing a destination's places, surfaces the top-k visually and contextually similar places to any seed location.

### Live Runtime and Proactive Monitoring
- **Live Runtime Orchestration** — an agentic layer that operates on active trips in real time, routing requests to the appropriate sub-agent: gem discovery, live replanning, or proactive monitoring.
- **Proactive Alerts** — the system generates closure-risk, timing-conflict, quality-risk, signal-blocker, and fallback-gap alerts for active itinerary slots before the traveller encounters them.
- **Alert Resolution and Adapt** — travellers can resolve alerts, ignore them, or adapt their itinerary by selecting a suggested alternative directly from the Notifications surface.
- **Background Scheduler** — an APScheduler sweep runs every 30 minutes, inspecting all active and planning trips that haven't been checked in the last hour and generating fresh alerts silently.

### AI Assistant
- **Multi-route Orchestrator** — a single `/assistant/orchestrate` endpoint classifies the traveller's message and routes it to the correct backend flow: destination guide, comparison, trip plan brief, trip plan update, slot replacement, live runtime, or fallback.
- **Streaming** — all enrichment and live-runtime flows support NDJSON streaming so the frontend can show progressive content updates.
- **Continuity Context** — the assistant maintains a `planning_session_id` and `trip_id` across messages so follow-up messages operate on the same session without requiring re-identification.

---

## Tech Stack

### Backend (`apps/api`)

| Layer | Technology |
|---|---|
| HTTP framework | FastAPI 0.116 |
| ASGI server | Uvicorn |
| ORM | SQLAlchemy 2.0 (declarative mapped columns) |
| Database | PostgreSQL (via psycopg 3) |
| Agentic orchestration | LangGraph 1.1 |
| Graph state persistence | `langgraph-checkpoint-postgres` |
| Background jobs | APScheduler 3.10 (BackgroundScheduler) |
| Caching / vector index | Redis 6 |
| Config management | Pydantic Settings |
| Rate limiting | SlowAPI |
| External providers | TripAdvisor API, Google Places API |

### Frontend (`apps/web`)

| Layer | Technology |
|---|---|
| Framework | React 18 |
| Build tool | Vite 6 |
| Routing | React Router v6 |
| Server state | TanStack Query v5 |
| Styling | Tailwind CSS v3 |
| Animation | Framer Motion 11 |
| UI components | Radix UI primitives + shadcn/ui |
| Forms | React Hook Form + Zod |
| Icons | Lucide React |

---

## Project Structure

```
wayfarer/
├── apps/
│   ├── api/                          # FastAPI backend
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   └── routes/           # One file per feature domain
│   │   │   │       ├── assistant.py
│   │   │   │       ├── destinations.py
│   │   │   │       ├── live_runtime.py
│   │   │   │       ├── persona.py
│   │   │   │       ├── persona_embeddings.py
│   │   │   │       ├── review_intelligence.py
│   │   │   │       ├── traveller_memory.py
│   │   │   │       ├── trip_plan.py
│   │   │   │       └── trips.py
│   │   │   ├── clients/              # External API clients
│   │   │   │   ├── google_places_client.py
│   │   │   │   ├── redis_client.py
│   │   │   │   └── tripadvisor_client.py
│   │   │   ├── core/
│   │   │   │   ├── config.py         # Pydantic settings
│   │   │   │   ├── rate_limiter.py   # SlowAPI setup
│   │   │   │   └── scheduler.py      # APScheduler background sweep
│   │   │   ├── db/
│   │   │   │   └── session.py        # SQLAlchemy session + get_db() generator
│   │   │   ├── models/               # SQLAlchemy ORM models
│   │   │   │   ├── live_runtime.py
│   │   │   │   ├── persona.py
│   │   │   │   ├── persona_embedding.py
│   │   │   │   ├── place_embedding.py
│   │   │   │   ├── place_photo.py
│   │   │   │   ├── proactive_alert.py
│   │   │   │   ├── review_intelligence.py
│   │   │   │   ├── saved_trip.py
│   │   │   │   ├── traveller_memory.py
│   │   │   │   └── trip_plan.py
│   │   │   ├── schemas/              # Pydantic request/response schemas
│   │   │   ├── services/             # Business logic
│   │   │   │   ├── assistant_service.py
│   │   │   │   ├── destination_service.py
│   │   │   │   ├── live_runtime_service.py
│   │   │   │   ├── persona_embedding_service.py
│   │   │   │   ├── photo_intelligence_service.py
│   │   │   │   ├── proactive_notification_service.py
│   │   │   │   ├── review_intelligence_service.py
│   │   │   │   └── trip_plan_service.py
│   │   │   └── main.py               # App factory + lifespan
│   │   └── requirements.txt
│   └── web/                          # React frontend
│       ├── src/
│       │   ├── api/
│       │   │   └── wayfarerApi.js    # Typed API client (all endpoints)
│       │   ├── components/
│       │   │   ├── cards/            # PlaceCard, TripPlanCard, etc.
│       │   │   ├── layout/           # AppLayout (sidebar + mobile nav)
│       │   │   ├── ui/               # Radix/shadcn primitives
│       │   │   └── onboarding/
│       │   ├── lib/
│       │   │   ├── travellerProfile.js   # Persona read/write + events
│       │   │   └── tripStorage.js        # Local trip cache helpers
│       │   └── pages/
│       │       ├── Assistant.jsx     # Multi-route AI chat interface
│       │       ├── Compare.jsx       # Destination comparison
│       │       ├── Discover.jsx      # Curated destination discovery
│       │       ├── Itinerary.jsx     # Active trip itinerary view
│       │       ├── Nearby.jsx        # Proximity-aware place discovery
│       │       ├── Notifications.jsx # Proactive alert management
│       │       ├── Plan.jsx          # Trip planning workspace
│       │       ├── Profile.jsx       # Traveller persona management
│       │       └── Trips.jsx         # Saved trips dashboard
│       ├── package.json
│       └── vite.config.js
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Redis 7+
- A TripAdvisor API key
- A Google Places API key
- An Anthropic API key (or whichever LLM provider the LangGraph agents target)

### Environment Variables

Create `apps/api/.env`:

```env
# Database
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/wayfarer

# Redis
REDIS_URL=redis://localhost:6379/0

# External providers
TRIPADVISOR_API_KEY=your_tripadvisor_key
GOOGLE_PLACES_API_KEY=your_google_places_key

# LLM
ANTHROPIC_API_KEY=your_anthropic_key

# Optional photo settings
PHOTO_DEFAULT_LIMIT=12
PHOTO_MAX_LIMIT=30

# Optional rate limiting
RATE_LIMIT_ENABLED=true
```

Create `apps/web/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

### Backend Setup

```bash
cd apps/api

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Start the development server (tables are auto-created on first run)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Frontend Setup

```bash
cd apps/web

# Install dependencies
npm install

# Fix any transitive dependency vulnerabilities in the lockfile
npm audit fix

# Start the development server
npm run dev
```

The frontend will be available at `http://localhost:5173`.

---

## API Overview

All endpoints are prefixed under `http://localhost:8000`. The full OpenAPI schema is available at `/docs`.

### Persona

| Method | Path | Description |
|---|---|---|
| `GET` | `/persona/{traveller_id}` | Fetch traveller persona |
| `POST` | `/persona/initialize-and-save` | Create or update persona from onboarding |
| `POST` | `/persona/refresh-from-memory/{traveller_id}` | Re-distil persona from memory log |
| `DELETE` | `/persona/{traveller_id}` | Delete traveller persona |

### Destinations

| Method | Path | Description |
|---|---|---|
| `POST` | `/destinations/search` | Full-text destination search |
| `POST` | `/destinations/guide` | Generate a destination guide |
| `POST` | `/destinations/guide/stream` | Streaming destination guide (NDJSON) |
| `POST` | `/destinations/compare` | Compare two destinations |
| `POST` | `/destinations/nearby` | Nearby place discovery |
| `POST` | `/destinations/gems` | Hidden gem discovery |
| `POST` | `/destinations/places/index` | Index destination places for similarity search |
| `POST` | `/destinations/places/similar` | Get similar places to a seed location |

### Trip Plans

| Method | Path | Description |
|---|---|---|
| `POST` | `/trip-plans/parse-and-save` | Parse a natural-language trip brief |
| `GET` | `/trip-plans/{id}` | Fetch a trip plan by planning session ID |
| `PATCH` | `/trip-plans/{id}` | Update trip plan constraints |
| `POST` | `/trip-plans/{id}/enrich` | Enrich a plan into a full slot-based itinerary |
| `POST` | `/trip-plans/{id}/enrich/stream` | Streaming enrichment (NDJSON) |
| `POST` | `/trip-plans/{id}/replace-slot` | Replace a single itinerary slot |
| `POST` | `/trip-plans/from-comparison` | Create a trip plan from a comparison result |

### Saved Trips

| Method | Path | Description |
|---|---|---|
| `GET` | `/trips` | List saved trips for a traveller |
| `GET` | `/trips/{trip_id}` | Fetch a single saved trip |
| `POST` | `/trips/from-plan/{planning_session_id}` | Promote a plan to a saved trip |
| `PATCH` | `/trips/{trip_id}/status` | Update trip status |
| `DELETE` | `/trips/{trip_id}` | Delete a saved trip |
| `GET` | `/trips/{trip_id}/versions` | List version snapshots |
| `POST` | `/trips/{trip_id}/versions` | Create a version snapshot |
| `GET` | `/trips/{trip_id}/versions/current` | Get current version |
| `POST` | `/trips/{trip_id}/versions/{version_id}/restore` | Restore a version |
| `GET` | `/trips/{trip_id}/signals` | List trip signals |
| `POST` | `/trips/{trip_id}/signals` | Record a trip signal (save place, skip, etc.) |

### Assistant

| Method | Path | Description |
|---|---|---|
| `POST` | `/assistant/orchestrate` | Route a message to the correct backend flow |
| `POST` | `/assistant/orchestrate/stream` | Streaming orchestration (NDJSON) |

### Live Runtime

| Method | Path | Description |
|---|---|---|
| `POST` | `/live-runtime/context` | Upsert live runtime context for a trip |
| `GET` | `/live-runtime/context/{trip_id}` | Get live runtime context |
| `POST` | `/live-runtime/actions` | Record a runtime action |
| `POST` | `/live-runtime/orchestrate` | Orchestrate a live runtime request |
| `POST` | `/live-runtime/orchestrate/stream` | Streaming live runtime (NDJSON) |
| `POST` | `/live-runtime/monitor/inspect` | Inspect active trip for proactive alerts |
| `GET` | `/live-runtime/alerts/{trip_id}` | List proactive alerts for a trip |
| `POST` | `/live-runtime/alerts/{alert_id}/resolve` | Resolve or ignore an alert |
| `GET` | `/live-runtime/runs/{run_id}` | Fetch a live runtime run record |
| `GET` | `/live-runtime/runs/{run_id}/events` | Fetch events for a run |

### Traveller Memory

| Method | Path | Description |
|---|---|---|
| `POST` | `/traveller-memory` | Record a memory event |
| `GET` | `/traveller-memory/{traveller_id}` | List memory events for a traveller |

---

## Agentic Flows

Wayfarer uses LangGraph to define stateful agent graphs. All graphs share a single `PostgresSaver` checkpointer so state is durable across API restarts.

### Assistant Orchestrator

Entry point: `POST /assistant/orchestrate`

The orchestrator classifies the user's message into one of these routes and delegates to the appropriate handler:

```
user message
    │
    ▼
classify_intent
    │
    ├─► destinations.guide        → generate_destination_guide()
    ├─► destinations.compare      → compare_destinations()
    ├─► trip_plans.parse_and_save → parse_and_save_trip_brief()
    ├─► trip_plans.get_summary    → get_trip_plan() [+ optional slot replace / update]
    ├─► live_runtime.orchestrate  → route to live runtime sub-agents
    └─► unknown                   → fallback message
```

### Live Runtime Orchestrator

Entry point: `POST /live-runtime/orchestrate`

Routes active-trip requests to:

- **`gem_agent`** — finds underrated options near the active trip
- **`live_replan_agent`** — surfaces alternatives for a disrupted slot
- **`proactive_monitor_agent`** — inspects the itinerary for issues and generates alerts

### Proactive Monitor Agent

Generates alerts of these types for each inspectable slot:

| Alert Type | Meaning |
|---|---|
| `closure_risk` | Place shows signals of temporary or permanent closure |
| `timing_conflict` | Available visit window is shorter than the estimated visit duration |
| `quality_risk` | Quality signals have degraded since planning |
| `signal_blocker` | A negative operational signal blocks this slot |
| `fallback_gap` | No viable fallback candidates exist for this slot |

---

## Data Models

### Core entities stored in PostgreSQL

| Model | Key Fields |
|---|---|
| `SavedTripRecord` | `trip_id`, `traveller_id`, `planning_session_id`, `title`, `status`, `current_version_number` |
| `TripPlanRecord` | `planning_session_id`, `traveller_id`, `parsed_constraints`, `itinerary_skeleton`, `candidate_places`, `status` |
| `PersonaRecord` | `traveller_id`, `signals` (JSON), `summary`, `embedding_version` |
| `TravellerMemoryRecord` | `traveller_id`, `event_type`, `source_surface`, `payload` |
| `ProactiveAlertRecord` | `alert_id`, `trip_id`, `traveller_id`, `alert_type`, `severity`, `status`, `alternatives` |
| `PlacePhotoRecord` | `photo_id`, `location_id`, `image_url`, `source`, `scene_type`, `quality_score`, `tags` |
| `ReviewIntelligenceRecord` | `location_id`, `review_score`, `review_signals`, `review_insight`, `review_authenticity` |
| `PersonaEmbeddingRecord` | `traveller_id`, `embedding` (vector), `embedding_version` |
| `PlaceEmbeddingRecord` | `location_id`, `embedding` (vector), `city`, `category` |
| `LiveRuntimeRecord` | `run_id`, `trip_id`, `agent`, `final_output`, `status` |

### Traveller identity

Traveller identity is managed client-side via `localStorage`. A UUID is generated on first visit and reused across sessions. There is no authentication layer — the `traveller_id` is the only identity token.

---

## Background Services

### Proactive Monitor Sweep (`apps/api/app/core/scheduler.py`)

An APScheduler `BackgroundScheduler` is started inside FastAPI's `lifespan` context manager and runs a sweep on a 30-minute interval:

1. Queries all trips with status `planning`, `active`, or `upcoming`.
2. Skips any trip whose most recent alert was generated within the last hour.
3. Calls `inspect_active_trip_alerts()` for each eligible trip.
4. All errors are logged silently — the sweep never raises and never crashes the API process.

The scheduler shuts down gracefully on application exit via the `lifespan` finally block.

---

## Frontend Pages

| Page | Path | Description |
|---|---|---|
| **Assistant** | `/assistant` | Multi-route AI chat. Handles guide, compare, plan, itinerary, and live runtime in one interface with streaming and chip-based follow-ups. |
| **Discover** | `/discover` | Curated destination cards with persona-matched filtering. |
| **Plan** | `/plan` | Trip planning workspace — lists all planning and active trips, shows workspace stats, and links to the assistant for new briefs. |
| **Trips** | `/trips` | Saved trips dashboard with version history, signals timeline, and status management. |
| **Itinerary** | `/itinerary` | Full slot-based itinerary view for the active trip, with per-slot candidate and fallback details. |
| **Nearby** | `/nearby` | Context-aware nearby discovery using active trip location. |
| **Compare** | `/compare` | Side-by-side destination comparison with a persona-aware recommendation. |
| **Notifications** | `/notifications` | Proactive alert management — run inspections, resolve or ignore alerts, and adapt the itinerary from suggested alternatives. After each resolution the traveller persona is refreshed from memory in the background. |
| **Profile** | `/profile` | Traveller persona viewer with one-click refresh and full reset options. |

---

## Configuration Reference

All backend configuration is managed via Pydantic Settings (`apps/api/app/core/config.py`). Values are loaded from environment variables or a `.env` file in the API directory.

| Setting | Default | Description |
|---|---|---|
| `DATABASE_URL` | — | PostgreSQL connection string (`postgresql+psycopg://...`) |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `TRIPADVISOR_API_KEY` | — | TripAdvisor Content API key |
| `GOOGLE_PLACES_API_KEY` | — | Google Places API key |
| `ANTHROPIC_API_KEY` | — | Anthropic API key for LLM calls |
| `PHOTO_DEFAULT_LIMIT` | `12` | Default number of photos to ingest per location |
| `PHOTO_MAX_LIMIT` | `30` | Hard cap on photos per ingestion request |
| `RATE_LIMIT_ENABLED` | `true` | Enable/disable SlowAPI rate limiting |
