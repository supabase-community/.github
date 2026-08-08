"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         SUPABASE CLIENT MANAGER                              ║
║                                                                              ║
║  WHY SUPABASE FOR IRON SHELL:                                                ║
║  1. Free tier = $0 budget constraint satisfied                               ║
║  2. PostgreSQL = battle-tested, relational data                              ║
║  3. Built-in Auth = secure user management without building it               ║
║  4. Real-time = live updates for collaborative workflows                     ║
║  5. pgvector = hybrid vector search (optional upgrade path)                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Optional
from functools import lru_cache

from supabase import create_client, Client
from .config import settings


class SupabaseManager:
    """
    Manages Supabase client connections with singleton pattern.

    IRON SHELL ARCHITECTURE NOTE:
    We use Supabase for:
    - User authentication (Supabase Auth)
    - Structured data (trades, portfolios, user settings)
    - Audit logs (every AI decision is logged)

    We DO NOT use Supabase for:
    - High-frequency vector searches (use ChromaDB locally for speed)
    - Temporary processing data (stays in memory)
    """

    _client: Optional[Client] = None
    _admin_client: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Optional[Client]:
        """
        Get the Supabase client using the anonymous/public key.
        Use this for user-facing operations that respect RLS policies.
        """
        if cls._client is None:
            if settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY:
                cls._client = create_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_ANON_KEY
                )
            else:
                print("⚠️ Supabase not configured - set SUPABASE_URL and SUPABASE_ANON_KEY")
                return None
        return cls._client

    @classmethod
    def get_admin_client(cls) -> Optional[Client]:
        """
        Get the Supabase client using the service role key.
        Use this for admin operations that bypass RLS.

        ⚠️ WARNING: Only use for server-side operations, never expose to client.
        """
        if cls._admin_client is None:
            if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY:
                cls._admin_client = create_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_SERVICE_KEY
                )
            else:
                return cls.get_client()  # Fallback to regular client
        return cls._admin_client


@lru_cache()
def get_supabase_client() -> Optional[Client]:
    """
    Get a cached Supabase client instance.

    This is the primary entry point for Supabase operations.
    """
    return SupabaseManager.get_client()


def get_supabase_admin() -> Optional[Client]:
    """
    Get the admin Supabase client for privileged operations.
    """
    return SupabaseManager.get_admin_client()


# ══════════════════════════════════════════════════════════════════════════════
# DATABASE SCHEMA HELPERS
# ══════════════════════════════════════════════════════════════════════════════
#
# These functions help set up the required database tables.
# Run these in Supabase SQL editor or via migrations.
# ══════════════════════════════════════════════════════════════════════════════

def get_schema_sql() -> str:
    """
    Returns the SQL to create the IronShell database schema.

    IRON SHELL DATA MODEL:
    1. trades: Raw trade data from broker statements
    2. analyses: AI-generated analysis with human corrections
    3. corrections: The Data Flywheel - stores diffs for RAG
    4. audit_log: Every AI decision for liability protection
    """
    return """
    -- ═══════════════════════════════════════════════════════════════════════════
    -- IRONSHELL CORE SCHEMA
    -- ═══════════════════════════════════════════════════════════════════════════

    -- Enable UUID extension
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

    -- ─────────────────────────────────────────────────────────────────────────────
    -- TRADES TABLE
    -- Raw trade data ingested from broker statements
    -- ─────────────────────────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS trades (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,

        -- Core trade data
        symbol VARCHAR(20) NOT NULL,
        trade_type VARCHAR(10) NOT NULL CHECK (trade_type IN ('BUY', 'SELL', 'SHORT', 'COVER')),
        quantity DECIMAL(18, 8) NOT NULL,
        price DECIMAL(18, 8) NOT NULL,
        total_value DECIMAL(18, 2) GENERATED ALWAYS AS (quantity * price) STORED,

        -- Risk metrics (calculated by AI, validated by guardrails)
        leverage DECIMAL(5, 2) DEFAULT 1.0,
        position_size_percent DECIMAL(5, 2),
        stop_loss_price DECIMAL(18, 8),
        take_profit_price DECIMAL(18, 8),

        -- Metadata
        broker_source VARCHAR(100),
        trade_date TIMESTAMPTZ NOT NULL,
        settlement_date TIMESTAMPTZ,
        notes TEXT,

        -- Tracking
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        ingestion_batch_id UUID
    );

    -- ─────────────────────────────────────────────────────────────────────────────
    -- ANALYSES TABLE
    -- AI-generated analysis with human override tracking
    -- ─────────────────────────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS analyses (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
        trade_id UUID REFERENCES trades(id) ON DELETE CASCADE,

        -- AI Output
        ai_analysis JSONB NOT NULL,
        ai_confidence DECIMAL(3, 2),
        ai_model VARCHAR(50),

        -- Human Override (The Data Flywheel)
        human_edited BOOLEAN DEFAULT FALSE,
        human_analysis JSONB,
        human_override_reason TEXT,

        -- Guardrail Flags
        guardrail_triggered BOOLEAN DEFAULT FALSE,
        guardrail_details JSONB,
        manual_override_approved BOOLEAN DEFAULT FALSE,
        override_approved_by UUID REFERENCES auth.users(id),
        override_approved_at TIMESTAMPTZ,

        -- Tracking
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- ─────────────────────────────────────────────────────────────────────────────
    -- CORRECTIONS TABLE
    -- The heart of the Data Flywheel - stores diffs for RAG
    -- ─────────────────────────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS corrections (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
        analysis_id UUID REFERENCES analyses(id) ON DELETE CASCADE,

        -- The diff that trains the AI
        original_input TEXT NOT NULL,
        ai_output TEXT NOT NULL,
        user_correction TEXT NOT NULL,

        -- Categorization for retrieval
        correction_type VARCHAR(50),  -- 'risk_assessment', 'trade_classification', etc.
        domain_tags TEXT[],           -- ['hedge', 'swing_trade', 'earnings_play']

        -- Embedding reference (stored in vector DB)
        vector_id VARCHAR(100),

        -- Quality metrics
        correction_impact VARCHAR(20) DEFAULT 'medium',  -- 'low', 'medium', 'high'
        times_retrieved INTEGER DEFAULT 0,  -- How often this correction helped

        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- ─────────────────────────────────────────────────────────────────────────────
    -- AUDIT LOG TABLE
    -- Every AI decision for liability protection
    -- ─────────────────────────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS audit_log (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,

        -- What happened
        action_type VARCHAR(50) NOT NULL,
        action_details JSONB NOT NULL,

        -- AI involvement
        ai_involved BOOLEAN DEFAULT FALSE,
        ai_model VARCHAR(50),
        ai_prompt TEXT,
        ai_response TEXT,

        -- Human involvement
        human_approved BOOLEAN,
        human_approver_id UUID REFERENCES auth.users(id),

        -- Context
        ip_address INET,
        user_agent TEXT,

        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- ─────────────────────────────────────────────────────────────────────────────
    -- INDEXES
    -- ─────────────────────────────────────────────────────────────────────────────
    CREATE INDEX IF NOT EXISTS idx_trades_user_id ON trades(user_id);
    CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
    CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(trade_date);
    CREATE INDEX IF NOT EXISTS idx_analyses_trade_id ON analyses(trade_id);
    CREATE INDEX IF NOT EXISTS idx_corrections_type ON corrections(correction_type);
    CREATE INDEX IF NOT EXISTS idx_corrections_tags ON corrections USING GIN(domain_tags);
    CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action_type);
    CREATE INDEX IF NOT EXISTS idx_audit_date ON audit_log(created_at);

    -- ─────────────────────────────────────────────────────────────────────────────
    -- ROW LEVEL SECURITY
    -- Users can only see their own data
    -- ─────────────────────────────────────────────────────────────────────────────
    ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
    ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;
    ALTER TABLE corrections ENABLE ROW LEVEL SECURITY;

    CREATE POLICY "Users can view own trades" ON trades
        FOR SELECT USING (auth.uid() = user_id);
    CREATE POLICY "Users can insert own trades" ON trades
        FOR INSERT WITH CHECK (auth.uid() = user_id);
    CREATE POLICY "Users can update own trades" ON trades
        FOR UPDATE USING (auth.uid() = user_id);

    CREATE POLICY "Users can view own analyses" ON analyses
        FOR SELECT USING (auth.uid() = user_id);
    CREATE POLICY "Users can insert own analyses" ON analyses
        FOR INSERT WITH CHECK (auth.uid() = user_id);
    CREATE POLICY "Users can update own analyses" ON analyses
        FOR UPDATE USING (auth.uid() = user_id);

    CREATE POLICY "Users can view own corrections" ON corrections
        FOR SELECT USING (auth.uid() = user_id);
    CREATE POLICY "Users can insert own corrections" ON corrections
        FOR INSERT WITH CHECK (auth.uid() = user_id);

    -- ─────────────────────────────────────────────────────────────────────────────
    -- FUNCTIONS
    -- ─────────────────────────────────────────────────────────────────────────────

    -- Auto-update updated_at timestamp
    CREATE OR REPLACE FUNCTION update_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER trades_updated_at
        BEFORE UPDATE ON trades
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at();

    CREATE TRIGGER analyses_updated_at
        BEFORE UPDATE ON analyses
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at();
    """


def print_setup_instructions():
    """
    Print instructions for setting up Supabase.
    """
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                    SUPABASE SETUP INSTRUCTIONS                           ║
    ╚══════════════════════════════════════════════════════════════════════════╝

    1. Go to https://supabase.com and create a free account
    2. Create a new project
    3. Go to Project Settings > API
    4. Copy your Project URL and anon/public key
    5. Create a .env file with:

       SUPABASE_URL=https://your-project.supabase.co
       SUPABASE_ANON_KEY=your-anon-key

    6. Go to SQL Editor and run the schema from get_schema_sql()

    Your Data Flywheel is now ready to spin! 🎡
    """)
