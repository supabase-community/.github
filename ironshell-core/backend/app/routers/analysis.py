"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    ANALYSIS ROUTER - AI RAG ENDPOINT                         ║
║                                                                              ║
║  IRON SHELL CORE: This endpoint triggers the RAG pipeline                    ║
║  that makes your AI smarter with every user interaction.                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field

from app.services.ai_engine import AIEngine, TradeAnalysis, AnalysisRequest
from app.services.guardrails import GuardrailValidator, GuardrailCheckResult


router = APIRouter()


# ══════════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ══════════════════════════════════════════════════════════════════════════════

class AnalyzeTradeRequest(BaseModel):
    """Request to analyze a trade."""
    trade: Dict[str, Any] = Field(description="Trade data to analyze")
    user_id: Optional[str] = None
    include_suggestions: bool = True
    check_guardrails: bool = True


class BatchAnalyzeRequest(BaseModel):
    """Request to analyze multiple trades."""
    trades: List[Dict[str, Any]]
    user_id: Optional[str] = None


class AnalysisResponse(BaseModel):
    """Full analysis response including guardrails."""
    analysis: TradeAnalysis
    guardrails: GuardrailCheckResult
    can_execute: bool = Field(
        description="Whether the trade can proceed without override"
    )
    requires_override: bool = Field(
        description="Whether manual override is needed"
    )


# ══════════════════════════════════════════════════════════════════════════════
# DEPENDENCY INJECTION
# ══════════════════════════════════════════════════════════════════════════════

def get_ai_engine(request: Request) -> AIEngine:
    """Get AI engine with vector store from app state."""
    vector_store = request.app.state.vector_store
    return AIEngine(vector_store=vector_store)


def get_guardrail_validator() -> GuardrailValidator:
    """Get guardrail validator."""
    return GuardrailValidator()


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/trade", response_model=AnalysisResponse)
async def analyze_trade(
    request: AnalyzeTradeRequest,
    ai_engine: AIEngine = Depends(get_ai_engine),
    guardrails: GuardrailValidator = Depends(get_guardrail_validator)
):
    """
    Analyze a single trade with AI and guardrails.

    IRON SHELL RAG FLOW:
    1. Query vector store for similar past corrections
    2. Build context-aware prompt
    3. Generate AI analysis
    4. Check guardrails
    5. Return structured response with UI hints

    Returns:
    - analysis: AI-generated analysis with confidence
    - guardrails: Guardrail check results
    - can_execute: Whether to enable the Execute button
    - requires_override: Whether manual approval is needed
    """
    try:
        # Step 1-3: AI Analysis with RAG
        analysis = await ai_engine.analyze_trade(
            AnalysisRequest(
                trade_data=request.trade,
                user_id=request.user_id,
                include_suggestions=request.include_suggestions,
                check_guardrails=request.check_guardrails
            )
        )

        # Step 4: Guardrail check on trade data
        trade_guardrails = guardrails.check_trade(request.trade)

        # Step 5: Guardrail check on AI output
        ai_guardrails = guardrails.check_ai_output(
            analysis.model_dump(),
            request.trade
        )

        # Combine guardrail results
        combined_violations = trade_guardrails.violations + ai_guardrails.violations
        combined_result = GuardrailCheckResult(
            passed=trade_guardrails.passed and ai_guardrails.passed,
            violations=combined_violations,
            warnings=trade_guardrails.warnings + ai_guardrails.warnings,
            requires_manual_approval=(
                trade_guardrails.requires_manual_approval or
                ai_guardrails.requires_manual_approval
            ),
            can_proceed_with_override=(
                trade_guardrails.can_proceed_with_override and
                ai_guardrails.can_proceed_with_override
            ),
            summary=f"{len(combined_violations)} total violations"
        )

        # Determine execution status
        can_execute = combined_result.passed and not combined_result.requires_manual_approval
        requires_override = not can_execute and combined_result.can_proceed_with_override

        return AnalysisResponse(
            analysis=analysis,
            guardrails=combined_result,
            can_execute=can_execute,
            requires_override=requires_override
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post("/batch", response_model=List[AnalysisResponse])
async def analyze_batch(
    request: BatchAnalyzeRequest,
    ai_engine: AIEngine = Depends(get_ai_engine),
    guardrails: GuardrailValidator = Depends(get_guardrail_validator)
):
    """
    Analyze multiple trades in batch.

    IRON SHELL EFFICIENCY:
    For bulk uploads (like a day's trades from a broker statement),
    we analyze all trades but the RAG context is shared.
    """
    results = []

    for trade in request.trades:
        try:
            analysis = await ai_engine.analyze_trade(
                AnalysisRequest(
                    trade_data=trade,
                    user_id=request.user_id
                )
            )

            trade_guardrails = guardrails.check_trade(trade)

            can_execute = trade_guardrails.passed
            requires_override = not can_execute and trade_guardrails.can_proceed_with_override

            results.append(AnalysisResponse(
                analysis=analysis,
                guardrails=trade_guardrails,
                can_execute=can_execute,
                requires_override=requires_override
            ))
        except Exception as e:
            # Create error analysis for failed trades
            from app.services.ai_engine import TradeAnalysis
            error_analysis = TradeAnalysis(
                trade_id=trade.get("id", "unknown"),
                symbol=trade.get("symbol", "UNKNOWN"),
                risk_level="unknown",
                risk_score=0.5,
                analysis_summary=f"Analysis failed: {str(e)}",
                warnings=[f"Error: {str(e)}"],
                confidence=0.0
            )
            results.append(AnalysisResponse(
                analysis=error_analysis,
                guardrails=GuardrailCheckResult(
                    passed=False,
                    summary="Analysis error"
                ),
                can_execute=False,
                requires_override=False
            ))

    return results


@router.get("/guardrails")
async def get_active_guardrails(
    guardrails: GuardrailValidator = Depends(get_guardrail_validator)
):
    """
    Get current guardrail configuration.

    IRON SHELL UX:
    Let users see what rules are in place BEFORE they submit trades.
    Transparency builds trust.
    """
    return guardrails.get_guardrail_summary()


@router.post("/custom-prompt")
async def custom_analysis(
    prompt: str,
    context: Optional[Dict[str, Any]] = None,
    ai_engine: AIEngine = Depends(get_ai_engine)
):
    """
    Run a custom analysis prompt.

    IRON SHELL FLEXIBILITY:
    Sometimes users need analysis that doesn't fit the trade template.
    This endpoint allows custom prompts while still using RAG context.
    """
    full_prompt = prompt
    if context:
        full_prompt = f"Context: {context}\n\nQuestion: {prompt}"

    try:
        response = await ai_engine.get_raw_completion(full_prompt)
        return {
            "response": response,
            "prompt_used": full_prompt[:200] + "..." if len(full_prompt) > 200 else full_prompt
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Custom analysis failed: {str(e)}"
        )
