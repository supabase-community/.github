"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    FEEDBACK ROUTER - DATA FLYWHEEL ENDPOINT                  ║
║                                                                              ║
║  THIS IS YOUR COMPETITIVE MOAT                                               ║
║                                                                              ║
║  IRON SHELL CORE: Every correction saved here makes your AI smarter.        ║
║  Competitors can clone your repo, but NOT your correction dataset.           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field

from app.services.feedback_loop import FeedbackLoop, CorrectionInput, CorrectionRecord


router = APIRouter()


# ══════════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ══════════════════════════════════════════════════════════════════════════════

class SaveCorrectionRequest(BaseModel):
    """Request to save a user correction."""
    original_input: Dict[str, Any] = Field(
        description="The original data submitted (e.g., trade data)"
    )
    ai_output: Dict[str, Any] = Field(
        description="What the AI generated"
    )
    user_final_version: Dict[str, Any] = Field(
        description="What the user edited it to (the 'truth')"
    )
    user_id: Optional[str] = None
    analysis_id: Optional[str] = None
    correction_type: str = Field(
        default="general",
        description="Category: risk_assessment, trade_classification, etc."
    )
    domain_tags: List[str] = Field(
        default_factory=list,
        description="Tags for retrieval: hedge, earnings_play, etc."
    )


class CorrectionResponse(BaseModel):
    """Response after saving a correction."""
    success: bool
    correction_id: str
    message: str
    flywheel_size: int = Field(
        description="Total corrections in your Data Flywheel"
    )
    moat_strength: str = Field(
        description="How defensible your AI has become"
    )


class FlywheelStatsResponse(BaseModel):
    """Statistics about the Data Flywheel."""
    total_corrections: int
    flywheel_status: str
    moat_strength: str
    breakdown_by_type: Optional[Dict[str, int]] = None
    recent_corrections: Optional[List[Dict[str, Any]]] = None


# ══════════════════════════════════════════════════════════════════════════════
# DEPENDENCY INJECTION
# ══════════════════════════════════════════════════════════════════════════════

def get_feedback_loop(request: Request) -> FeedbackLoop:
    """Get feedback loop service with vector store from app state."""
    vector_store = request.app.state.vector_store
    if not vector_store:
        raise HTTPException(
            status_code=503,
            detail="Vector store not available - Data Flywheel offline"
        )
    return FeedbackLoop(vector_store=vector_store)


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/correction", response_model=CorrectionResponse)
async def save_correction(
    request: SaveCorrectionRequest,
    feedback_loop: FeedbackLoop = Depends(get_feedback_loop)
):
    """
    Save a user correction to the Data Flywheel.

    THIS IS THE MOST IMPORTANT ENDPOINT IN THE SYSTEM.

    IRON SHELL MECHANIC:
    When a user edits an AI analysis, we:
    1. Analyze the diff (what changed)
    2. Embed the original input
    3. Store the user's correction as "truth"
    4. Next time similar input appears, RAG retrieves this correction

    The more corrections, the smarter YOUR AI becomes.
    Competitors cannot replicate this dataset.

    Request:
    - original_input: The data the user submitted (e.g., trade details)
    - ai_output: What the AI generated (e.g., risk analysis)
    - user_final_version: What the user corrected it to (the "truth")
    - correction_type: Category for filtered retrieval
    - domain_tags: Tags for even more specific retrieval

    Response:
    - correction_id: ID for tracking
    - flywheel_size: How many corrections you've accumulated
    - moat_strength: How defensible your AI has become
    """
    try:
        # Save the correction
        record = await feedback_loop.save_correction(
            original_input=request.original_input,
            ai_output=request.ai_output,
            user_final_version=request.user_final_version,
            user_id=request.user_id,
            analysis_id=request.analysis_id,
            correction_type=request.correction_type,
            domain_tags=request.domain_tags
        )

        # Get current flywheel stats
        stats = await feedback_loop.get_correction_stats(request.user_id)

        return CorrectionResponse(
            success=True,
            correction_id=record.id,
            message=(
                f"Correction saved! Your AI is now smarter. "
                f"Change magnitude: {record.change_magnitude:.1%}"
            ),
            flywheel_size=stats["total_corrections"],
            moat_strength=stats["moat_strength"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save correction: {str(e)}"
        )


@router.get("/stats", response_model=FlywheelStatsResponse)
async def get_flywheel_stats(
    user_id: Optional[str] = None,
    include_recent: bool = False,
    feedback_loop: FeedbackLoop = Depends(get_feedback_loop)
):
    """
    Get statistics about your Data Flywheel.

    IRON SHELL METRICS:
    These numbers tell you how defensible your AI has become:
    - total_corrections: Your dataset size (the moat)
    - moat_strength: Qualitative assessment
    - breakdown: Which types of corrections are most common

    A healthy flywheel should:
    - Have growing correction count over time
    - Show diverse correction types
    - Have high retrieval counts on key corrections
    """
    stats = await feedback_loop.get_correction_stats(user_id)

    response = FlywheelStatsResponse(
        total_corrections=stats["total_corrections"],
        flywheel_status=stats["flywheel_status"],
        moat_strength=stats["moat_strength"],
        breakdown_by_type=stats.get("correction_breakdown")
    )

    if include_recent:
        recent = await feedback_loop.get_recent_corrections(limit=5, user_id=user_id)
        response.recent_corrections = recent

    return response


@router.get("/recent")
async def get_recent_corrections(
    limit: int = 10,
    user_id: Optional[str] = None,
    feedback_loop: FeedbackLoop = Depends(get_feedback_loop)
):
    """
    Get recent corrections for review.

    IRON SHELL ANALYTICS:
    Review recent corrections to:
    - See patterns in what the AI gets wrong
    - Identify areas for prompt improvement
    - Validate that corrections are quality
    """
    corrections = await feedback_loop.get_recent_corrections(
        limit=limit,
        user_id=user_id
    )

    return {
        "corrections": corrections,
        "count": len(corrections)
    }


@router.get("/health")
async def check_flywheel_health(
    feedback_loop: FeedbackLoop = Depends(get_feedback_loop)
):
    """
    Check the health of the Data Flywheel.

    IRON SHELL MONITORING:
    A healthy flywheel is critical. If it's down:
    - New corrections won't be saved
    - RAG won't have context
    - Your AI will make the same mistakes repeatedly
    """
    try:
        stats = await feedback_loop.get_correction_stats()

        return {
            "status": "healthy",
            "flywheel_active": stats["total_corrections"] > 0,
            "total_corrections": stats["total_corrections"],
            "message": (
                "Data Flywheel operational" if stats["total_corrections"] > 0
                else "Data Flywheel empty - start collecting corrections!"
            )
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Data Flywheel needs attention!"
        }
