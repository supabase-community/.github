"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    IRONSHELL CONFIGURATION MANAGEMENT                        ║
║                                                                              ║
║  WHY CONFIGURATION MATTERS FOR IRON SHELL:                                   ║
║  - Different AI providers for different budget levels                        ║
║  - Guardrail thresholds that define your liability shield                    ║
║  - Vector store settings that control your Data Flywheel                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    IRON SHELL PRINCIPLE: "Configure once, enforce everywhere"
    These settings define the boundaries of your AI's behavior.
    """

    # ══════════════════════════════════════════════════════════════════════════
    # APPLICATION SETTINGS
    # ══════════════════════════════════════════════════════════════════════════

    APP_NAME: str = "IronShell Core Engine"
    APP_ENV: str = Field(default="development", description="development, staging, production")
    DEBUG: bool = Field(default=True, description="Enable debug mode")

    # ══════════════════════════════════════════════════════════════════════════
    # SUPABASE CONFIGURATION (Free Tier Database)
    # ══════════════════════════════════════════════════════════════════════════
    #
    # WHY SUPABASE:
    # 1. Free tier is generous for startups
    # 2. Built-in Auth saves development time
    # 3. Real-time subscriptions for live updates
    # 4. pgvector support for hybrid RAG architecture
    # ══════════════════════════════════════════════════════════════════════════

    SUPABASE_URL: Optional[str] = Field(
        default=None,
        description="Your Supabase project URL"
    )
    SUPABASE_ANON_KEY: Optional[str] = Field(
        default=None,
        description="Supabase anonymous/public key"
    )
    SUPABASE_SERVICE_KEY: Optional[str] = Field(
        default=None,
        description="Supabase service role key (for admin operations)"
    )

    # ══════════════════════════════════════════════════════════════════════════
    # AI PROVIDER CONFIGURATION
    # ══════════════════════════════════════════════════════════════════════════
    #
    # IRON SHELL FLEXIBILITY:
    # Support multiple AI providers so users can choose based on:
    # - Budget (Gemini Flash is free, GPT-4 is expensive)
    # - Privacy (Ollama runs locally, no data leaves the machine)
    # - Quality (Claude/GPT-4 for complex analysis)
    # ══════════════════════════════════════════════════════════════════════════

    AI_PROVIDER: str = Field(
        default="gemini",
        description="AI provider: gemini, ollama, openai, anthropic"
    )

    # Google Gemini (Free Tier - Recommended for $0 budget)
    GOOGLE_API_KEY: Optional[str] = Field(
        default=None,
        description="Google AI API key for Gemini"
    )
    GEMINI_MODEL: str = Field(
        default="gemini-1.5-flash",
        description="Gemini model to use"
    )

    # Ollama (Local - Free, Private)
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Ollama API endpoint"
    )
    OLLAMA_MODEL: str = Field(
        default="llama3",
        description="Ollama model to use"
    )

    # OpenAI (Paid - Higher quality)
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )
    OPENAI_MODEL: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model to use"
    )

    # Anthropic (Paid - Highest quality reasoning)
    ANTHROPIC_API_KEY: Optional[str] = Field(
        default=None,
        description="Anthropic API key"
    )
    ANTHROPIC_MODEL: str = Field(
        default="claude-3-haiku-20240307",
        description="Anthropic model to use"
    )

    # ══════════════════════════════════════════════════════════════════════════
    # VECTOR STORE CONFIGURATION (Data Flywheel)
    # ══════════════════════════════════════════════════════════════════════════
    #
    # THIS IS YOUR COMPETITIVE MOAT:
    # The vector store holds all user corrections. The more corrections,
    # the smarter YOUR AI becomes - and competitors can't copy this data.
    # ══════════════════════════════════════════════════════════════════════════

    VECTOR_STORE_TYPE: str = Field(
        default="chromadb",
        description="Vector store: chromadb (local) or pgvector (Supabase)"
    )
    CHROMA_PERSIST_DIR: str = Field(
        default="./data/chromadb",
        description="ChromaDB persistence directory"
    )
    CHROMA_COLLECTION_NAME: str = Field(
        default="ironshell_corrections",
        description="ChromaDB collection for user corrections"
    )

    # Embedding model for vector similarity
    EMBEDDING_MODEL: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence transformer model for embeddings"
    )

    # ══════════════════════════════════════════════════════════════════════════
    # LIABILITY SHIELD - GUARDRAIL THRESHOLDS
    # ══════════════════════════════════════════════════════════════════════════
    #
    # IRON SHELL PRINCIPLE: "Hard limits prevent hard consequences"
    # These are the safety boundaries. When exceeded, the UI MUST block
    # execution and require manual override. This is your legal protection.
    # ══════════════════════════════════════════════════════════════════════════

    # Trading-specific guardrails (domain-specific)
    MAX_LEVERAGE: float = Field(
        default=10.0,
        description="Maximum leverage allowed before blocking"
    )
    MAX_POSITION_SIZE_PERCENT: float = Field(
        default=25.0,
        description="Max % of portfolio in single position"
    )
    MAX_DAILY_LOSS_PERCENT: float = Field(
        default=5.0,
        description="Max daily loss before halt trading suggestions"
    )
    REQUIRE_STOP_LOSS: bool = Field(
        default=True,
        description="Require stop-loss on all trade suggestions"
    )

    # General AI guardrails
    MAX_CONFIDENCE_WITHOUT_REVIEW: float = Field(
        default=0.85,
        description="AI confidence above this still requires review"
    )
    REQUIRE_HUMAN_APPROVAL: bool = Field(
        default=True,
        description="Always require human approval for actions"
    )

    # ══════════════════════════════════════════════════════════════════════════
    # CORS & SECURITY
    # ══════════════════════════════════════════════════════════════════════════

    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins"
    )

    # JWT Settings (for Supabase Auth)
    JWT_SECRET: Optional[str] = Field(
        default=None,
        description="JWT secret for token validation"
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="JWT signing algorithm"
    )

    # ══════════════════════════════════════════════════════════════════════════
    # FILE PROCESSING
    # ══════════════════════════════════════════════════════════════════════════

    MAX_FILE_SIZE_MB: int = Field(
        default=10,
        description="Maximum file size for uploads"
    )
    ALLOWED_FILE_TYPES: List[str] = Field(
        default=["csv", "pdf", "xlsx", "json"],
        description="Allowed file extensions for ingestion"
    )
    TEMP_UPLOAD_DIR: str = Field(
        default="./data/uploads",
        description="Temporary directory for file uploads"
    )

    # ══════════════════════════════════════════════════════════════════════════
    # RAG CONFIGURATION
    # ══════════════════════════════════════════════════════════════════════════

    RAG_TOP_K: int = Field(
        default=5,
        description="Number of similar corrections to retrieve"
    )
    RAG_SIMILARITY_THRESHOLD: float = Field(
        default=0.7,
        description="Minimum similarity score for RAG results"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()


def get_active_ai_config() -> dict:
    """
    Get the configuration for the currently active AI provider.

    IRON SHELL TIP:
    Start with Gemini Flash (free), upgrade to better models as revenue grows.
    The Data Flywheel works regardless of the AI model - it's YOUR data that matters.
    """
    provider = settings.AI_PROVIDER.lower()

    configs = {
        "gemini": {
            "provider": "gemini",
            "api_key": settings.GOOGLE_API_KEY,
            "model": settings.GEMINI_MODEL,
            "description": "Google Gemini - Free tier, fast, good quality"
        },
        "ollama": {
            "provider": "ollama",
            "base_url": settings.OLLAMA_BASE_URL,
            "model": settings.OLLAMA_MODEL,
            "description": "Ollama - Free, local, private"
        },
        "openai": {
            "provider": "openai",
            "api_key": settings.OPENAI_API_KEY,
            "model": settings.OPENAI_MODEL,
            "description": "OpenAI - Paid, high quality"
        },
        "anthropic": {
            "provider": "anthropic",
            "api_key": settings.ANTHROPIC_API_KEY,
            "model": settings.ANTHROPIC_MODEL,
            "description": "Anthropic - Paid, best reasoning"
        }
    }

    return configs.get(provider, configs["gemini"])


def get_guardrail_config() -> dict:
    """
    Get all guardrail thresholds for the Liability Shield.

    IRON SHELL PRINCIPLE:
    These values are your legal protection. When the AI suggests something
    that exceeds these limits, the UI MUST block and require manual override.
    """
    return {
        "max_leverage": settings.MAX_LEVERAGE,
        "max_position_size_percent": settings.MAX_POSITION_SIZE_PERCENT,
        "max_daily_loss_percent": settings.MAX_DAILY_LOSS_PERCENT,
        "require_stop_loss": settings.REQUIRE_STOP_LOSS,
        "max_confidence_without_review": settings.MAX_CONFIDENCE_WITHOUT_REVIEW,
        "require_human_approval": settings.REQUIRE_HUMAN_APPROVAL
    }
