# 🛡️ IronShell Core Engine

> **"Your AI is a commodity. Your DATA is your moat."**

The **Iron Shell** strategy for building defensible AI applications. This is NOT just another AI wrapper—it's a complete system for building competitive advantage through data.

## 🎯 What Makes This Different?

Most AI apps are just wrappers around LLM APIs. Anyone can copy them. **IronShell** is different:

1. **Data Flywheel**: Every user correction trains YOUR AI
2. **Proprietary Dataset**: Competitors can clone your code, but NOT your corrections
3. **Liability Shield**: Hard-coded guardrails protect you legally
4. **Workflow Integration**: Meets users where they are (messy files, not forms)
5. **N8N Workflow Automation**: Document, search, and visualize automation workflows

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                   │
│  Next.js 14 + TailwindCSS + Lucide React                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                   │
│  │FileUploader │ │ SmartEditor │ │GuardrailPanel│                   │
│  │(Ingest)     │ │(Edit+Save)  │ │(Block+Warn)  │                   │
│  └─────────────┘ └─────────────┘ └─────────────┘                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           BACKEND                                    │
│  FastAPI + Python 3.11+                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                   │
│  │  Ingestor   │ │  AI Engine  │ │FeedbackLoop │                   │
│  │(Parse Files)│ │  (RAG+LLM)  │ │(Save Diffs) │                   │
│  └─────────────┘ └─────────────┘ └─────────────┘                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   Supabase    │   │   ChromaDB    │   │   Gemini/     │
│  (Postgres)   │   │ (Vector Store)│   │   Ollama      │
│  Free Tier    │   │   Local       │   │   Free/Local  │
└───────────────┘   └───────────────┘   └───────────────┘
     Trades              Corrections         AI Provider
```

## 🔄 The Data Flywheel

```
     ┌──────────────────────────────────────────────────────┐
     │                                                       │
     ▼                                                       │
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐   │
│  User   │───▶│   AI    │───▶│  User   │───▶│  Save   │───┘
│ Submits │    │Analyzes │    │ Edits   │    │Correction│
│  Data   │    │  Data   │    │ Output  │    │to VectorDB
└─────────┘    └─────────┘    └─────────┘    └─────────┘
                    ▲                              │
                    │                              │
                    └──────────────────────────────┘
                     RAG retrieves past corrections
                     to improve future analyses
```

**Result**: The more users correct the AI, the smarter it becomes. This correction dataset is YOUR competitive moat.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- (Optional) Supabase account (free tier)
- (Optional) Google AI API key or Ollama installed

### Backend Setup

```bash
cd ironshell-core/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run the server
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd ironshell-core/frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with your backend URL

# Run development server
npm run dev
```

### Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 💰 $0 Budget Stack

| Component | Free Option | Notes |
|-----------|-------------|-------|
| Database | Supabase Free Tier | 500MB, unlimited API calls |
| AI | Gemini 1.5 Flash | Free tier, or use Ollama locally |
| Vector Store | ChromaDB | Local, persistent, free |
| Auth | Supabase Auth | Built-in, free |
| Hosting | Vercel + Railway | Free tiers available |

## 🛡️ Liability Shield (Guardrails)

The guardrail system protects you legally by:

1. **Blocking dangerous actions** before they happen
2. **Requiring explicit user acknowledgment** for risky operations
3. **Logging all overrides** for audit trails
4. **Never executing** without human approval

Configure guardrails in `.env`:

```env
MAX_LEVERAGE=10.0
MAX_POSITION_SIZE_PERCENT=25.0
MAX_DAILY_LOSS_PERCENT=5.0
REQUIRE_STOP_LOSS=true
```

## 📁 Project Structure

```
ironshell-core/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── core/
│   │   │   ├── config.py        # Settings & guardrails
│   │   │   ├── supabase_client.py
│   │   │   └── vector_store.py  # ChromaDB (Data Flywheel)
│   │   ├── services/
│   │   │   ├── ingestor.py      # File parsing (Moment of Truth)
│   │   │   ├── ai_engine.py     # RAG pipeline
│   │   │   ├── feedback_loop.py # Save corrections (THE MOAT)
│   │   │   ├── guardrails.py    # Liability shield
│   │   │   └── workflow_db.py   # N8N workflow database
│   │   └── routers/
│   │       ├── ingest.py
│   │       ├── analysis.py
│   │       ├── feedback.py
│   │       ├── trades.py
│   │       └── workflows.py     # Workflow automation API
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx             # Main dashboard
│   │   ├── globals.css
│   │   └── workflows/
│   │       └── page.tsx         # Workflow browser
│   ├── components/
│   │   ├── SmartEditor.tsx      # THE KEY COMPONENT
│   │   ├── FileUploader.tsx
│   │   ├── GuardrailPanel.tsx
│   │   ├── FlywheelStats.tsx
│   │   ├── TradeList.tsx
│   │   ├── WorkflowList.tsx     # Workflow browser
│   │   └── WorkflowViewer.tsx   # Workflow detail + diagram
│   ├── lib/
│   │   └── api.ts
│   ├── types/
│   │   └── index.ts
│   ├── package.json
│   └── .env.example
│
└── README.md
```

## 🔄 Workflow Automation (N8N Integration)

IronShell includes a complete N8N workflow documentation and management system:

### Features

- **Workflow Search**: Full-text search across all workflow metadata
- **Visual Diagrams**: Mermaid.js flowcharts auto-generated from workflow JSON
- **Category Filtering**: Filter by trigger type, complexity, integrations
- **Security**: Path traversal protection, rate limiting, admin authentication

### Workflow API Endpoints

```
GET  /api/v1/workflows              # Search/list workflows
GET  /api/v1/workflows/{filename}   # Get workflow details + diagram
GET  /api/v1/workflows/stats        # Database statistics
GET  /api/v1/workflows/categories   # Available categories
POST /api/v1/workflows/import       # Import new workflow
POST /api/v1/workflows/reindex      # Reindex all workflows (admin)
```

### Adding Workflows

Place N8N workflow JSON files in `data/workflows/` and they'll be automatically indexed:

```bash
# Create workflows directory
mkdir -p data/workflows

# Copy your N8N exports
cp my-workflow.json data/workflows/

# Trigger reindex (requires ADMIN_TOKEN)
curl -X POST "http://localhost:8000/api/v1/workflows/reindex?admin_token=YOUR_TOKEN"
```

## 🔧 Customization

### Swapping the Domain

This template uses "Trading Journal" as the domain. To adapt for other verticals:

1. **Legal**: Replace trade analysis with contract review
2. **Medical**: Replace risk assessment with symptom analysis
3. **Finance**: Replace trading with expense categorization

The **architecture remains the same**—only the prompts and data models change.

### Adding AI Providers

Edit `backend/app/services/ai_engine.py` to add new providers:

```python
class MyCustomProvider(AIProvider):
    async def generate(self, prompt: str, system_prompt: str) -> str:
        # Your implementation
        pass
```

## 📊 Monitoring Your Moat

Check your Data Flywheel health:

```bash
curl http://localhost:8000/api/v1/feedback/stats
```

Response:
```json
{
  "total_corrections": 247,
  "flywheel_status": "spinning",
  "moat_strength": "strong - competitors would need months to catch up"
}
```

## 🤝 Contributing

This is an open architecture. Contributions welcome for:

- Additional AI providers
- New domain templates
- UI/UX improvements
- Documentation

## 📄 License

MIT License - Use freely, but remember: **the code is open, your data is your moat**.

---

Built with the **Iron Shell** strategy: *"Defensibility comes from data, not code."*
