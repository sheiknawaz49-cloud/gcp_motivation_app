# Daily Motivation App 🌟

A personalized, AI-powered daily motivation web application built with **FastAPI**, **Google Cloud Vertex AI (Gemini 2.5 Flash)**, **Cloud Text-to-Speech (Journey voices)**, **Cloud Storage**, and **Firestore**.

---

## 🏗️ Project Architecture & Structure

The codebase is organized following clean architecture principles, separating concerns across configuration, domain services, data models, web routers, templates, and static assets:

```text
motiveate/
│
├── .env.example              # Environment variables template
├── .env                      # Local environment configuration (gitignored)
├── .gitignore                # Git exclusions
├── Procfile                  # Production process runner (Cloud Run / Heroku)
├── README.md                 # Project documentation
├── requirements.txt          # Python dependencies
├── main.py                   # Root entrypoint (delegates to app.main:app)
│
└── app/
    ├── __init__.py
    ├── main.py               # FastAPI app factory, middleware, and router mounts
    │
    ├── core/                 # Core configurations and cross-cutting concerns
    │   ├── __init__.py
    │   ├── config.py         # Centralized Settings & environment loaders
    │   └── dependencies.py   # Auth cookie verification & FastAPI dependencies
    │
    ├── schemas/              # Pydantic models for validation and responses
    │   ├── __init__.py
    │   └── quotes.py         # FeedbackRequest, CardItem, BatchResponse schemas
    │
    ├── services/             # Domain logic and GCP integrations
    │   ├── __init__.py
    │   ├── gcp.py            # Client initializations (GenAI, Firestore, TTS, Storage)
    │   ├── audio_service.py  # Text-to-Speech synthesis and Cloud Storage audio uploads
    │   ├── quote_service.py  # Gemini prompt generation & parallel audio batching
    │   └── user_service.py   # Firestore profile management & feedback tracking
    │
    ├── routers/              # HTTP Route Handlers
    │   ├── __init__.py
    │   ├── auth.py           # /login, /logout endpoints and session cookie management
    │   ├── views.py          # / and /app HTML view routes
    │   └── api.py            # /api/batch, /api/feedback, /preferences endpoints
    │
    ├── static/               # Client-side static assets
    │   ├── css/
    │   │   ├── base.css      # Design tokens, variables, typography, resets
    │   │   ├── login.css     # Login card layout and input styling
    │   │   └── app.css       # Main quote card, transitions, modal, and animations
    │   └── js/
    │       └── app.js        # Background prefetching, card transitions, audio, hotkeys
    │
    └── templates/            # Jinja2 HTML templates
        ├── login.html        # Clean, modern login interface
        └── app.html          # Interactive swipeable motivation deck interface
```

---

## 🚀 Key Features

- **⚡ Instant Card Transitions**: Background queue (`/api/batch`) continuously prefetches 3 quotes + audio clips in parallel with zero client-side latency.
- **🎙️ Expressive Audio Synthesis**: Uses Google Cloud Text-to-Speech Journey voices (Female & Male).
- **🧠 Personalization Engine**: Adapts tone to your current mood, goal, and past liked/disliked quotes stored in Firestore.
- **🎨 Modern Dark UI**: Glassmorphic styling, smooth CSS transform transitions, and responsive mobile-first design.
- **⌨️ Keyboard Shortcuts**: Press `Space` or `→` for the next card, and `L` to save/like.

---

## 🛠️ Getting Started

### 1. Prerequisites
- Python 3.9+
- A Google Cloud Project with the following APIs enabled:
  - Vertex AI API
  - Cloud Text-to-Speech API
  - Cloud Storage
  - Cloud Firestore

### 2. Environment Setup
Clone the repository and create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your GCP configuration:
```bash
cp .env.example .env
```
Example `.env`:
```ini
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
AUDIO_BUCKET_NAME=your-gcp-project-id-audio
APP_PASSCODE=your-secret-passcode
```

### 4. Authenticate with Google Cloud
Ensure your local environment has Google Cloud Application Default Credentials (ADC):
```bash
gcloud auth application-default login
```

### 5. Run Locally
Run the development server:
```bash
uvicorn main:app --reload
```
Open your browser at `http://localhost:8000`.

---

## 📦 Deployment

The application is structured for direct deployment to **Google Cloud Run** or any containerized/Procfile host:

```bash
# Deploy to Google Cloud Run
gcloud run deploy motivation-app \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=your-gcp-project-id,APP_PASSCODE=your-secret-passcode
```
