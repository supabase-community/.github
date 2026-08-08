"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    AI ENGINE - THE RAG PIPELINE                              ║
║                                                                              ║
║  IRON SHELL CORE MECHANIC:                                                   ║
║  This is NOT just an AI wrapper. This is an AI that LEARNS from your users. ║
║                                                                              ║
║  THE RAG FLOW:                                                               ║
║  1. User submits data (e.g., new trade)                                      ║
║  2. We query Vector DB for similar past corrections                          ║
║  3. We build a prompt that includes those corrections as context             ║
║  4. AI generates response informed by past user feedback                     ║
║  5. User reviews and potentially corrects                                    ║
║  6. Correction feeds back into Vector DB (Data Flywheel spins)               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from abc import ABC, abstractmethod

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings, get_active_ai_config
from app.core.vector_store import VectorStoreManager


# ══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════════════════════

class TradeAnalysis(BaseModel):
    """Structured analysis of a trade."""
    trade_id: str
    symbol: str

    # Risk Assessment
    risk_level: str = Field(description="low, medium, high, extreme")
    risk_score: float = Field(ge=0, le=1, description="0-1 risk score")
    risk_factors: List[str] = Field(default_factory=list)

    # Position Analysis
    position_type: str = Field(description="day_trade, swing, position, scalp")
    suggested_stop_loss: Optional[float] = None
    suggested_take_profit: Optional[float] = None
    risk_reward_ratio: Optional[float] = None

    # AI Insights
    analysis_summary: str
    key_observations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)

    # Guardrail Flags
    guardrail_violations: List[str] = Field(default_factory=list)
    requires_manual_approval: bool = False

    # Metadata
    confidence: float = Field(ge=0, le=1, default=0.8)
    model_used: str = ""
    rag_context_used: bool = False
    similar_corrections_count: int = 0


class AnalysisRequest(BaseModel):
    """Request for trade analysis."""
    trade_data: Dict[str, Any]
    user_id: Optional[str] = None
    include_suggestions: bool = True
    check_guardrails: bool = True


class RAGContext(BaseModel):
    """Context retrieved from the vector store."""
    corrections: List[Dict[str, Any]] = Field(default_factory=list)
    total_found: int = 0
    context_text: str = ""


# ══════════════════════════════════════════════════════════════════════════════
# AI PROVIDER INTERFACE
# ══════════════════════════════════════════════════════════════════════════════

class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str) -> str:
        """Generate a response from the AI."""
        pass


class GeminiProvider(AIProvider):
    """Google Gemini API provider (Free Tier)."""

    def __init__(self):
        self.api_key = settings.GOOGLE_API_KEY
        self.model = settings.GEMINI_MODEL
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def generate(self, prompt: str, system_prompt: str) -> str:
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not configured")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/models/{self.model}:generateContent",
                params={"key": self.api_key},
                json={
                    "contents": [{
                        "parts": [{"text": f"{system_prompt}\n\n{prompt}"}]
                    }],
                    "generationConfig": {
                        "temperature": 0.3,
                        "topP": 0.8,
                        "maxOutputTokens": 2048,
                    }
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            # Extract text from Gemini response
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")

            return ""


class OllamaProvider(AIProvider):
    """Ollama local provider (Free, Private)."""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL

    async def generate(self, prompt: str, system_prompt: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                    }
                },
                timeout=60.0  # Longer timeout for local models
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")


class OpenAIProvider(AIProvider):
    """OpenAI API provider."""

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL

    async def generate(self, prompt: str, system_prompt: str) -> str:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not configured")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2048,
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


class AnthropicProvider(AIProvider):
    """Anthropic Claude API provider."""

    def __init__(self):
        self.api_key = settings.ANTHROPIC_API_KEY
        self.model = settings.ANTHROPIC_MODEL

    async def generate(self, prompt: str, system_prompt: str) -> str:
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 2048,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]


# ══════════════════════════════════════════════════════════════════════════════
# AI ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class AIEngine:
    """
    The core AI engine with RAG pipeline.

    IRON SHELL ARCHITECTURE:
    This engine doesn't just call an AI API. It:
    1. Queries the vector store for relevant past corrections
    2. Builds a context-aware prompt
    3. Generates structured output (not just text)
    4. Checks guardrails before returning
    """

    # ══════════════════════════════════════════════════════════════════════════
    # SYSTEM PROMPT - THE SOUL OF YOUR AI
    # ══════════════════════════════════════════════════════════════════════════
    #
    # IRON SHELL WISDOM:
    # This prompt is what makes your AI behave correctly. It encodes:
    # - Domain knowledge (trading, risk management)
    # - Safety rules (guardrails)
    # - Output format expectations
    # Customize this for your specific domain.
    # ══════════════════════════════════════════════════════════════════════════

    SYSTEM_PROMPT = """You are an expert trading analyst and risk manager. Your role is to analyze trades and provide structured risk assessments.

CRITICAL RULES:
1. ALWAYS respond with valid JSON matching the requested schema
2. NEVER recommend trades that exceed risk parameters
3. ALWAYS flag high-risk situations clearly
4. If you're uncertain, express lower confidence scores
5. Consider the context from past user corrections when provided

RISK ASSESSMENT CRITERIA:
- Position size > 25% of portfolio = HIGH RISK
- Leverage > 5x = HIGH RISK, > 10x = EXTREME
- No stop-loss = FLAG AS WARNING
- Day trades on volatile assets = MEDIUM-HIGH RISK

OUTPUT FORMAT:
Always respond with a JSON object containing:
- risk_level: "low" | "medium" | "high" | "extreme"
- risk_score: 0.0 to 1.0
- risk_factors: list of identified risks
- position_type: "day_trade" | "swing" | "position" | "scalp"
- analysis_summary: brief analysis (2-3 sentences)
- key_observations: list of important observations
- warnings: list of warnings (empty if none)
- suggestions: list of actionable suggestions
- confidence: your confidence in this analysis (0.0 to 1.0)

When past corrections are provided, use them to inform your analysis. If a similar situation was corrected before, apply that learning."""

    def __init__(self, vector_store: Optional[VectorStoreManager] = None):
        self.vector_store = vector_store
        self.provider = self._get_provider()

    def _get_provider(self) -> AIProvider:
        """Get the configured AI provider."""
        provider_name = settings.AI_PROVIDER.lower()

        providers = {
            "gemini": GeminiProvider,
            "ollama": OllamaProvider,
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
        }

        provider_class = providers.get(provider_name, GeminiProvider)
        return provider_class()

    async def analyze_trade(self, request: AnalysisRequest) -> TradeAnalysis:
        """
        Analyze a trade with RAG context.

        THIS IS THE CORE RAG PIPELINE.

        Steps:
        1. Serialize trade data for embedding query
        2. Query vector store for similar past corrections
        3. Build context-aware prompt
        4. Call AI provider
        5. Parse structured response
        6. Check guardrails
        7. Return analysis
        """
        trade_data = request.trade_data
        trade_id = trade_data.get("id", "unknown")
        symbol = trade_data.get("symbol", "UNKNOWN")

        # Step 1: Prepare the input for RAG query
        input_text = self._serialize_trade_for_embedding(trade_data)

        # Step 2: Query vector store for similar corrections
        # ══════════════════════════════════════════════════════════════════════
        # THIS IS THE DATA FLYWHEEL IN ACTION:
        # We check if the user has ever corrected a similar analysis.
        # If so, we include that correction in the prompt.
        # ══════════════════════════════════════════════════════════════════════
        rag_context = await self._get_rag_context(input_text)

        # Step 3: Build the prompt with context
        prompt = self._build_analysis_prompt(trade_data, rag_context)

        # Step 4: Call AI
        try:
            raw_response = await self.provider.generate(prompt, self.SYSTEM_PROMPT)
        except Exception as e:
            # Fallback to basic analysis if AI fails
            return self._create_fallback_analysis(trade_data, str(e))

        # Step 5: Parse structured response
        analysis = self._parse_ai_response(raw_response, trade_data, rag_context)

        # Step 6: Check guardrails
        if request.check_guardrails:
            analysis = self._apply_guardrails(analysis, trade_data)

        return analysis

    async def _get_rag_context(self, input_text: str) -> RAGContext:
        """
        Query the vector store for relevant past corrections.

        IRON SHELL MECHANIC:
        This is where the Data Flywheel pays off. We retrieve
        past corrections that are similar to the current input,
        so the AI doesn't repeat mistakes.
        """
        if not self.vector_store:
            return RAGContext()

        try:
            corrections = await self.vector_store.query_similar_corrections(
                input_text=input_text,
                n_results=settings.RAG_TOP_K,
                min_similarity=settings.RAG_SIMILARITY_THRESHOLD
            )

            if not corrections:
                return RAGContext()

            # Build context text from corrections
            context_parts = []
            for i, correction in enumerate(corrections, 1):
                metadata = correction.get("metadata", {})
                context_parts.append(
                    f"--- Past Correction {i} (Similarity: {correction['similarity']:.2f}) ---\n"
                    f"Original situation: {correction['original_input'][:200]}...\n"
                    f"User's correction: {metadata.get('user_correction', 'N/A')[:300]}\n"
                )

            context_text = "\n".join(context_parts)

            return RAGContext(
                corrections=corrections,
                total_found=len(corrections),
                context_text=context_text
            )

        except Exception as e:
            print(f"RAG query failed: {e}")
            return RAGContext()

    def _serialize_trade_for_embedding(self, trade_data: Dict[str, Any]) -> str:
        """
        Serialize trade data for embedding query.

        IRON SHELL TIP:
        The embedding query should capture the "essence" of the trade.
        Include key factors that would make two trades "similar":
        - Symbol, trade type, size relative to typical
        - Time of day, market conditions if available
        """
        parts = [
            f"Symbol: {trade_data.get('symbol', 'UNKNOWN')}",
            f"Type: {trade_data.get('trade_type', 'UNKNOWN')}",
            f"Quantity: {trade_data.get('quantity', 0)}",
            f"Price: {trade_data.get('price', 0)}",
        ]

        if trade_data.get("leverage"):
            parts.append(f"Leverage: {trade_data['leverage']}x")

        if trade_data.get("position_size_percent"):
            parts.append(f"Position Size: {trade_data['position_size_percent']}%")

        return " | ".join(parts)

    def _build_analysis_prompt(
        self,
        trade_data: Dict[str, Any],
        rag_context: RAGContext
    ) -> str:
        """
        Build the analysis prompt with RAG context.

        IRON SHELL ARCHITECTURE:
        The prompt has three sections:
        1. Past corrections (if any) - the Data Flywheel context
        2. Current trade data - what we're analyzing
        3. Instructions - what to output
        """
        prompt_parts = []

        # Section 1: RAG Context (past corrections)
        if rag_context.context_text:
            prompt_parts.append(
                "=== IMPORTANT: PAST USER CORRECTIONS ===\n"
                "The following are corrections the user made to similar analyses. "
                "Use these to inform your analysis and avoid repeating mistakes:\n\n"
                f"{rag_context.context_text}\n"
                "=== END PAST CORRECTIONS ===\n"
            )

        # Section 2: Current trade data
        prompt_parts.append(
            "=== TRADE TO ANALYZE ===\n"
            f"{json.dumps(trade_data, indent=2, default=str)}\n"
            "=== END TRADE DATA ===\n"
        )

        # Section 3: Instructions
        prompt_parts.append(
            "\nAnalyze this trade and provide your assessment. "
            "Remember to output valid JSON matching the schema described in your instructions."
        )

        return "\n".join(prompt_parts)

    def _parse_ai_response(
        self,
        raw_response: str,
        trade_data: Dict[str, Any],
        rag_context: RAGContext
    ) -> TradeAnalysis:
        """
        Parse the AI's response into a structured TradeAnalysis.

        IRON SHELL ROBUSTNESS:
        AI responses can be messy. We:
        1. Try to extract JSON from the response
        2. Validate and fill in missing fields
        3. Never fail - return a partial analysis if needed
        """
        # Try to extract JSON from the response
        json_data = {}

        try:
            # Look for JSON in the response
            if "{" in raw_response and "}" in raw_response:
                start = raw_response.find("{")
                end = raw_response.rfind("}") + 1
                json_str = raw_response[start:end]
                json_data = json.loads(json_str)
        except json.JSONDecodeError:
            # If JSON parsing fails, extract what we can
            json_data = {}

        # Build the analysis with defaults
        config = get_active_ai_config()

        return TradeAnalysis(
            trade_id=trade_data.get("id", "unknown"),
            symbol=trade_data.get("symbol", "UNKNOWN"),
            risk_level=json_data.get("risk_level", "medium"),
            risk_score=float(json_data.get("risk_score", 0.5)),
            risk_factors=json_data.get("risk_factors", []),
            position_type=json_data.get("position_type", "swing"),
            suggested_stop_loss=json_data.get("suggested_stop_loss"),
            suggested_take_profit=json_data.get("suggested_take_profit"),
            risk_reward_ratio=json_data.get("risk_reward_ratio"),
            analysis_summary=json_data.get("analysis_summary", "Analysis completed."),
            key_observations=json_data.get("key_observations", []),
            warnings=json_data.get("warnings", []),
            suggestions=json_data.get("suggestions", []),
            confidence=float(json_data.get("confidence", 0.7)),
            model_used=config.get("model", "unknown"),
            rag_context_used=rag_context.total_found > 0,
            similar_corrections_count=rag_context.total_found
        )

    def _apply_guardrails(
        self,
        analysis: TradeAnalysis,
        trade_data: Dict[str, Any]
    ) -> TradeAnalysis:
        """
        Apply guardrails and flag violations.

        IRON SHELL LIABILITY SHIELD:
        This is your legal protection. When the AI suggests something
        risky, we flag it here. The UI will then block execution
        until the user explicitly approves.
        """
        violations = []

        # Check leverage
        leverage = trade_data.get("leverage", 1.0)
        if leverage > settings.MAX_LEVERAGE:
            violations.append(
                f"LEVERAGE EXCEEDED: {leverage}x exceeds max {settings.MAX_LEVERAGE}x"
            )
            analysis.risk_level = "extreme"
            analysis.risk_score = max(analysis.risk_score, 0.95)

        # Check position size
        position_pct = trade_data.get("position_size_percent", 0)
        if position_pct > settings.MAX_POSITION_SIZE_PERCENT:
            violations.append(
                f"POSITION SIZE EXCEEDED: {position_pct}% exceeds max {settings.MAX_POSITION_SIZE_PERCENT}%"
            )
            analysis.risk_level = "high" if analysis.risk_level != "extreme" else "extreme"
            analysis.risk_score = max(analysis.risk_score, 0.85)

        # Check for stop loss
        if settings.REQUIRE_STOP_LOSS and not trade_data.get("stop_loss_price"):
            violations.append("NO STOP LOSS: Trade requires a stop-loss order")

        # Update analysis with violations
        if violations:
            analysis.guardrail_violations = violations
            analysis.requires_manual_approval = True
            analysis.warnings.extend(violations)

        return analysis

    def _create_fallback_analysis(
        self,
        trade_data: Dict[str, Any],
        error: str
    ) -> TradeAnalysis:
        """Create a basic analysis when AI fails."""
        return TradeAnalysis(
            trade_id=trade_data.get("id", "unknown"),
            symbol=trade_data.get("symbol", "UNKNOWN"),
            risk_level="medium",
            risk_score=0.5,
            risk_factors=["AI analysis unavailable"],
            position_type="swing",
            analysis_summary=f"Basic analysis (AI unavailable: {error})",
            key_observations=["Manual review recommended"],
            warnings=["AI analysis failed - please review manually"],
            suggestions=[],
            confidence=0.3,
            model_used="fallback",
            rag_context_used=False,
            similar_corrections_count=0
        )

    async def get_raw_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Get a raw completion from the AI (for custom use cases).

        IRON SHELL FLEXIBILITY:
        Sometimes you need custom prompts beyond trade analysis.
        This method exposes the raw AI capability.
        """
        return await self.provider.generate(
            prompt,
            system_prompt or self.SYSTEM_PROMPT
        )
