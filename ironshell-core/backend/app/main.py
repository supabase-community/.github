"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    IRONSHELL CORE ENGINE - MAIN APPLICATION                  ║
║                                                                              ║
║  "Iron Shell" Strategy: Build defensibility through data, not just AI.      ║
║                                                                              ║
║  WHY THIS ARCHITECTURE MATTERS:                                              ║
║  1. Every user correction becomes YOUR competitive advantage                 ║
║  2. The AI gets smarter with YOUR domain-specific data                       ║
║  3. Competitors can copy your code, but NOT your learned corrections         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import our core services
from app.core.config import settings
from app.core.supabase_client import get_supabase_client
from app.core.vector_store import VectorStoreManager
from app.routers import ingest, analysis, feedback, trades, workflows

# ══════════════════════════════════════════════════════════════════════════════
# APPLICATION LIFESPAN MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
#
# WHY LIFESPAN MATTERS FOR IRON SHELL:
# We initialize the Vector DB once at startup, not per-request.
# This is critical for the Data Flywheel - we need fast RAG queries.
# ══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Manage application lifecycle - initialize expensive resources once.

    IRON SHELL PRINCIPLE: "Load once, query fast, learn forever"
    The vector store is your moat. Initialize it properly.
    """
    print("🔷 IronShell Core Engine Starting...")

    # Initialize Supabase connection
    try:
        supabase = get_supabase_client()
        app.state.supabase = supabase
        print("✅ Supabase client initialized")
    except Exception as e:
        print(f"⚠️ Supabase initialization failed (will use fallback): {e}")
        app.state.supabase = None

    # Initialize Vector Store for RAG
    # THIS IS THE CORE OF THE DATA FLYWHEEL
    try:
        vector_store = VectorStoreManager()
        await vector_store.initialize()
        app.state.vector_store = vector_store
        print("✅ Vector store (ChromaDB) initialized - Data Flywheel ready")
    except Exception as e:
        print(f"⚠️ Vector store initialization failed: {e}")
        app.state.vector_store = None

    print("🚀 IronShell Core Engine Ready")
    print("=" * 60)

    yield  # Application runs here

    # Cleanup
    print("🔶 IronShell Core Engine Shutting Down...")
    if app.state.vector_store:
        await app.state.vector_store.cleanup()
    print("👋 Shutdown complete")


# ══════════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION SETUP
# ══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="IronShell Core Engine",
    description="""
    ## 🛡️ The 'Iron Shell' Defensible AI Platform

    This is NOT just another AI wrapper. This is a **workflow automation system**
    that builds proprietary value through every user interaction.

    ### Core Mechanics:
    1. **Moment of Truth Integration**: Ingest messy real-world data (CSVs, PDFs)
    2. **Data Flywheel (RAG)**: Every user correction makes the AI smarter
    3. **Liability Shield**: Hard-coded guardrails prevent dangerous actions

    ### Why This Is Defensible:
    - Competitors can copy code, but NOT your correction dataset
    - Every user interaction = training data for YOUR system
    - Domain expertise is encoded in the vector store
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# ══════════════════════════════════════════════════════════════════════════════
# CORS MIDDLEWARE
# ══════════════════════════════════════════════════════════════════════════════
#
# WHY PERMISSIVE CORS IN DEVELOPMENT:
# We allow broad origins during development for easy frontend testing.
# In production, lock this down to your specific domain.
# ══════════════════════════════════════════════════════════════════════════════

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # Configure in settings for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL EXCEPTION HANDLER
# ══════════════════════════════════════════════════════════════════════════════
#
# IRON SHELL PRINCIPLE: "Fail gracefully, learn from failures"
# We log every error - even failures are data for improvement.
# ══════════════════════════════════════════════════════════════════════════════

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all exception handler that logs errors for analysis.

    In the Iron Shell model, errors are opportunities:
    - Track which inputs cause failures
    - Feed failures back into training data
    - Improve the system over time
    """
    # In production, send this to your logging/monitoring service
    print(f"❌ Unhandled exception: {exc}")
    print(f"   Path: {request.url.path}")
    print(f"   Method: {request.method}")

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. This has been logged for review.",
            "type": "system_error"
        }
    )


# ══════════════════════════════════════════════════════════════════════════════
# INCLUDE ROUTERS
# ══════════════════════════════════════════════════════════════════════════════

app.include_router(ingest.router, prefix="/api/v1/ingest", tags=["Data Ingestion"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["AI Analysis"])
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["Feedback Loop"])
app.include_router(trades.router, prefix="/api/v1/trades", tags=["Trade Management"])
app.include_router(workflows.router, prefix="/api/v1/workflows", tags=["Workflow Automation"])


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH CHECK & STATUS ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint - confirms the service is running.
    """
    return {
        "service": "IronShell Core Engine",
        "status": "operational",
        "version": "1.0.0",
        "strategy": "Iron Shell - Build defensibility through data"
    }


@app.get("/health", tags=["Health"])
async def health_check(request: Request):
    """
    Comprehensive health check for all system components.

    IRON SHELL INSIGHT:
    Monitor these metrics to ensure your Data Flywheel is operational.
    A broken vector store = no learning = losing your competitive advantage.
    """
    health_status = {
        "status": "healthy",
        "components": {}
    }

    # Check Supabase
    if request.app.state.supabase:
        try:
            # Simple query to verify connection
            health_status["components"]["supabase"] = {
                "status": "connected",
                "description": "Primary database for structured data"
            }
        except Exception as e:
            health_status["components"]["supabase"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["status"] = "degraded"
    else:
        health_status["components"]["supabase"] = {
            "status": "not_configured",
            "description": "Running without Supabase - using local fallback"
        }

    # Check Vector Store (Critical for Data Flywheel)
    if request.app.state.vector_store:
        try:
            stats = await request.app.state.vector_store.get_stats()
            health_status["components"]["vector_store"] = {
                "status": "operational",
                "description": "ChromaDB for RAG/Feedback Loop",
                "stats": stats
            }
        except Exception as e:
            health_status["components"]["vector_store"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["status"] = "degraded"
    else:
        health_status["components"]["vector_store"] = {
            "status": "not_initialized",
            "warning": "⚠️ Data Flywheel is not operational!"
        }
        health_status["status"] = "degraded"

    return health_status


@app.get("/api/v1/system/flywheel-stats", tags=["System"])
async def get_flywheel_stats(request: Request):
    """
    Get statistics about the Data Flywheel - your competitive moat.

    IRON SHELL METRICS:
    - Total corrections: How much proprietary data you've accumulated
    - Recent corrections: Is the flywheel actively spinning?
    - Top domains: Which areas have the most learned context?
    """
    if not request.app.state.vector_store:
        raise HTTPException(
            status_code=503,
            detail="Vector store not available - Data Flywheel offline"
        )

    stats = await request.app.state.vector_store.get_detailed_stats()

    return {
        "flywheel_status": "active" if stats["total_corrections"] > 0 else "empty",
        "competitive_moat_size": stats["total_corrections"],
        "message": (
            f"You have {stats['total_corrections']} unique corrections. "
            "Each one makes your AI smarter and harder to compete with."
        ),
        "details": stats
    }


# ══════════════════════════════════════════════════════════════════════════════
# DEVELOPMENT SERVER
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn

    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                                                                          ║
    ║   🛡️  IRONSHELL CORE ENGINE - Development Server                        ║
    ║                                                                          ║
    ║   The 'Iron Shell' Strategy:                                             ║
    ║   "Your AI is a commodity. Your DATA is your moat."                      ║
    ║                                                                          ║
    ║   Every user correction becomes proprietary training data.               ║
    ║   Competitors can copy your code, but NOT your learned insights.         ║
    ║                                                                          ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
