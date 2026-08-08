"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    FEEDBACK LOOP - THE DATA FLYWHEEL CORE                    ║
║                                                                              ║
║  THIS FILE IS YOUR COMPETITIVE MOAT                                          ║
║                                                                              ║
║  IRON SHELL PRINCIPLE:                                                       ║
║  "Your AI is a commodity. Your DATA is your defensibility."                  ║
║                                                                              ║
║  THE FEEDBACK LOOP MECHANIC:                                                 ║
║  1. AI generates analysis                                                    ║
║  2. User sees it in the SmartEditor                                          ║
║  3. User edits/corrects the analysis                                         ║
║  4. THIS SERVICE captures the diff (original + AI + user correction)         ║
║  5. The correction is embedded and stored in Vector DB                       ║
║  6. Next time, RAG retrieves this correction for similar inputs              ║
║                                                                              ║
║  RESULT: Your AI gets smarter with every user interaction.                   ║
║  Competitors can copy your code, but NOT your correction dataset.            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from difflib import unified_diff, SequenceMatcher
import hashlib

from pydantic import BaseModel, Field

from app.core.vector_store import VectorStoreManager
from app.core.supabase_client import get_supabase_client


# ══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════════════════════

class CorrectionInput(BaseModel):
    """Input for saving a correction."""
    original_input: Dict[str, Any] = Field(
        description="The original data that was submitted (e.g., trade data)"
    )
    ai_output: Dict[str, Any] = Field(
        description="What the AI generated (e.g., analysis)"
    )
    user_final_version: Dict[str, Any] = Field(
        description="What the user edited it to (e.g., corrected analysis)"
    )
    user_id: Optional[str] = None
    analysis_id: Optional[str] = None
    correction_type: Optional[str] = Field(
        default="general",
        description="Category: risk_assessment, trade_classification, etc."
    )
    domain_tags: List[str] = Field(
        default_factory=list,
        description="Tags for retrieval: hedge, earnings_play, etc."
    )


class CorrectionRecord(BaseModel):
    """A saved correction record."""
    id: str
    original_input: Dict[str, Any]
    ai_output: Dict[str, Any]
    user_correction: Dict[str, Any]
    diff_summary: str
    change_magnitude: float  # 0-1, how much changed
    correction_type: str
    domain_tags: List[str]
    vector_id: str
    created_at: datetime
    times_retrieved: int = 0


class DiffAnalysis(BaseModel):
    """Analysis of what changed between AI output and user correction."""
    fields_changed: List[str]
    fields_added: List[str]
    fields_removed: List[str]
    change_magnitude: float  # 0-1
    summary: str
    is_significant: bool  # Worth storing in vector DB?


# ══════════════════════════════════════════════════════════════════════════════
# FEEDBACK LOOP SERVICE
# ══════════════════════════════════════════════════════════════════════════════

class FeedbackLoop:
    """
    The core service that powers the Data Flywheel.

    IRON SHELL MECHANICS:
    This service is responsible for:
    1. Analyzing the diff between AI output and user correction
    2. Determining if the correction is worth storing
    3. Embedding the original input for retrieval
    4. Storing the correction with metadata for filtered RAG
    5. Tracking retrieval stats (which corrections are most useful)
    """

    def __init__(self, vector_store: VectorStoreManager):
        self.vector_store = vector_store
        self.supabase = get_supabase_client()

    async def save_correction(
        self,
        original_input: Dict[str, Any],
        ai_output: Dict[str, Any],
        user_final_version: Dict[str, Any],
        user_id: Optional[str] = None,
        analysis_id: Optional[str] = None,
        correction_type: str = "general",
        domain_tags: Optional[List[str]] = None
    ) -> CorrectionRecord:
        """
        Save a user correction to the Data Flywheel.

        THIS IS THE CORE FUNCTION OF THE IRON SHELL STRATEGY.

        Parameters:
        - original_input: The data the user submitted (e.g., trade details)
        - ai_output: What the AI generated (e.g., risk analysis)
        - user_final_version: What the user edited it to (the "truth")

        Returns:
        - CorrectionRecord with the saved correction details

        IRON SHELL FLOW:
        1. Analyze what changed (diff)
        2. If significant, embed original_input
        3. Store in vector DB with user_final_version as the "truth"
        4. Also store in Supabase for audit/analytics
        """
        # Step 1: Analyze the diff
        diff_analysis = self._analyze_diff(ai_output, user_final_version)

        # Step 2: Check if worth storing
        # ══════════════════════════════════════════════════════════════════════
        # IRON SHELL WISDOM:
        # Not every tiny edit is worth storing. We filter for:
        # - Significant changes (> 10% difference)
        # - Meaningful corrections (not just typo fixes)
        # This keeps the vector DB clean and queries fast.
        # ══════════════════════════════════════════════════════════════════════
        if not diff_analysis.is_significant:
            # Still log it, but don't embed in vector DB
            print(f"ℹ️ Minor correction detected, not storing in vector DB")
            return await self._save_minor_correction(
                original_input, ai_output, user_final_version,
                diff_analysis, user_id, analysis_id
            )

        # Step 3: Prepare data for vector storage
        input_text = self._serialize_for_embedding(original_input)
        ai_text = json.dumps(ai_output, indent=2, default=str)
        user_text = json.dumps(user_final_version, indent=2, default=str)

        # Step 4: Build metadata for filtered retrieval
        metadata = {
            "correction_type": correction_type,
            "domain_tags": ",".join(domain_tags) if domain_tags else "",
            "change_magnitude": diff_analysis.change_magnitude,
            "fields_changed": ",".join(diff_analysis.fields_changed),
            "user_id": user_id or "anonymous",
            "analysis_id": analysis_id or "",
        }

        # Step 5: Store in vector DB
        # ══════════════════════════════════════════════════════════════════════
        # THE FLYWHEEL SPINS:
        # This is where the magic happens. We're storing:
        # - Embedding of original_input (the query key)
        # - user_final_version as the "truth" (what to retrieve)
        # Next time similar input comes in, RAG finds this correction.
        # ══════════════════════════════════════════════════════════════════════
        vector_id = await self.vector_store.save_correction(
            original_input=input_text,
            ai_output=ai_text,
            user_correction=user_text,
            metadata=metadata
        )

        print(f"💾 Correction saved to Data Flywheel: {vector_id}")
        print(f"   Change magnitude: {diff_analysis.change_magnitude:.2%}")
        print(f"   Fields changed: {diff_analysis.fields_changed}")

        # Step 6: Also store in Supabase for analytics
        correction_record = await self._store_in_supabase(
            original_input=original_input,
            ai_output=ai_output,
            user_correction=user_final_version,
            diff_analysis=diff_analysis,
            vector_id=vector_id,
            user_id=user_id,
            analysis_id=analysis_id,
            correction_type=correction_type,
            domain_tags=domain_tags or []
        )

        return correction_record

    def _analyze_diff(
        self,
        ai_output: Dict[str, Any],
        user_final: Dict[str, Any]
    ) -> DiffAnalysis:
        """
        Analyze what changed between AI output and user correction.

        IRON SHELL INSIGHT:
        Understanding WHAT changed helps us:
        1. Filter out noise (typo fixes)
        2. Categorize corrections (risk level changes vs. observations)
        3. Weight the importance of different corrections
        """
        fields_changed = []
        fields_added = []
        fields_removed = []

        ai_keys = set(ai_output.keys())
        user_keys = set(user_final.keys())

        # Find added fields
        fields_added = list(user_keys - ai_keys)

        # Find removed fields
        fields_removed = list(ai_keys - user_keys)

        # Find changed fields
        common_keys = ai_keys & user_keys
        for key in common_keys:
            ai_val = ai_output[key]
            user_val = user_final[key]

            if ai_val != user_val:
                fields_changed.append(key)

        # Calculate change magnitude
        total_fields = len(ai_keys | user_keys)
        changed_count = len(fields_changed) + len(fields_added) + len(fields_removed)
        change_magnitude = changed_count / max(total_fields, 1)

        # Also check text similarity for string fields
        text_similarities = []
        for key in common_keys:
            ai_val = str(ai_output[key])
            user_val = str(user_final[key])
            if len(ai_val) > 20 or len(user_val) > 20:  # Only for substantial text
                similarity = SequenceMatcher(None, ai_val, user_val).ratio()
                text_similarities.append(similarity)

        if text_similarities:
            avg_text_similarity = sum(text_similarities) / len(text_similarities)
            # Combine field changes with text similarity
            change_magnitude = max(change_magnitude, 1 - avg_text_similarity)

        # Build summary
        summary_parts = []
        if fields_changed:
            summary_parts.append(f"Changed: {', '.join(fields_changed[:3])}")
        if fields_added:
            summary_parts.append(f"Added: {', '.join(fields_added[:3])}")
        if fields_removed:
            summary_parts.append(f"Removed: {', '.join(fields_removed[:3])}")

        summary = "; ".join(summary_parts) if summary_parts else "No significant changes"

        # Determine if significant
        # ══════════════════════════════════════════════════════════════════════
        # IRON SHELL THRESHOLD:
        # A correction is "significant" if:
        # - More than 10% of fields changed, OR
        # - Key fields changed (risk_level, warnings, etc.), OR
        # - Text content changed substantially
        # ══════════════════════════════════════════════════════════════════════
        key_fields = {"risk_level", "risk_score", "warnings", "guardrail_violations",
                     "analysis_summary", "suggestions", "position_type"}
        key_field_changed = bool(set(fields_changed) & key_fields)

        is_significant = (
            change_magnitude > 0.1 or
            key_field_changed or
            len(fields_added) > 0 or
            len(fields_removed) > 0
        )

        return DiffAnalysis(
            fields_changed=fields_changed,
            fields_added=fields_added,
            fields_removed=fields_removed,
            change_magnitude=round(change_magnitude, 4),
            summary=summary,
            is_significant=is_significant
        )

    def _serialize_for_embedding(self, data: Dict[str, Any]) -> str:
        """
        Serialize input data for embedding.

        IRON SHELL TIP:
        The embedding should capture the "essence" of the input
        that would make two inputs "similar" for RAG purposes.
        """
        # For trade data, focus on key identifying fields
        key_fields = ["symbol", "trade_type", "quantity", "price", "leverage",
                     "position_size_percent", "trade_date"]

        parts = []
        for field in key_fields:
            if field in data:
                parts.append(f"{field}: {data[field]}")

        # Add any additional context
        if "notes" in data:
            parts.append(f"notes: {data['notes'][:100]}")

        return " | ".join(parts) if parts else json.dumps(data, default=str)

    async def _save_minor_correction(
        self,
        original_input: Dict[str, Any],
        ai_output: Dict[str, Any],
        user_final: Dict[str, Any],
        diff_analysis: DiffAnalysis,
        user_id: Optional[str],
        analysis_id: Optional[str]
    ) -> CorrectionRecord:
        """Save a minor correction (not in vector DB, just logged)."""
        record_id = hashlib.sha256(
            f"{json.dumps(original_input)}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]

        return CorrectionRecord(
            id=record_id,
            original_input=original_input,
            ai_output=ai_output,
            user_correction=user_final,
            diff_summary=diff_analysis.summary,
            change_magnitude=diff_analysis.change_magnitude,
            correction_type="minor",
            domain_tags=[],
            vector_id="",  # Not stored in vector DB
            created_at=datetime.utcnow(),
            times_retrieved=0
        )

    async def _store_in_supabase(
        self,
        original_input: Dict[str, Any],
        ai_output: Dict[str, Any],
        user_correction: Dict[str, Any],
        diff_analysis: DiffAnalysis,
        vector_id: str,
        user_id: Optional[str],
        analysis_id: Optional[str],
        correction_type: str,
        domain_tags: List[str]
    ) -> CorrectionRecord:
        """
        Store correction in Supabase for analytics and audit.

        IRON SHELL ANALYTICS:
        Supabase stores the full correction for:
        1. Audit trail (who corrected what, when)
        2. Analytics (which types of corrections are most common)
        3. Backup (vector DB can be rebuilt from this)
        """
        record_id = vector_id  # Use same ID for consistency

        if self.supabase:
            try:
                self.supabase.table("corrections").insert({
                    "id": record_id,
                    "user_id": user_id,
                    "analysis_id": analysis_id,
                    "original_input": json.dumps(original_input, default=str),
                    "ai_output": json.dumps(ai_output, default=str),
                    "user_correction": json.dumps(user_correction, default=str),
                    "correction_type": correction_type,
                    "domain_tags": domain_tags,
                    "vector_id": vector_id,
                    "correction_impact": self._calculate_impact(diff_analysis),
                }).execute()
            except Exception as e:
                print(f"⚠️ Failed to store in Supabase: {e}")

        return CorrectionRecord(
            id=record_id,
            original_input=original_input,
            ai_output=ai_output,
            user_correction=user_correction,
            diff_summary=diff_analysis.summary,
            change_magnitude=diff_analysis.change_magnitude,
            correction_type=correction_type,
            domain_tags=domain_tags,
            vector_id=vector_id,
            created_at=datetime.utcnow(),
            times_retrieved=0
        )

    def _calculate_impact(self, diff_analysis: DiffAnalysis) -> str:
        """Calculate the impact level of a correction."""
        if diff_analysis.change_magnitude > 0.5:
            return "high"
        elif diff_analysis.change_magnitude > 0.2:
            return "medium"
        else:
            return "low"

    async def get_correction_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about corrections.

        IRON SHELL METRICS:
        These stats tell you:
        1. How active is your Data Flywheel?
        2. What types of corrections are most common?
        3. Which corrections are most useful (retrieved often)?
        """
        vector_stats = await self.vector_store.get_detailed_stats()

        stats = {
            "total_corrections": vector_stats.get("total_corrections", 0),
            "flywheel_status": vector_stats.get("flywheel_status", "unknown"),
            "moat_strength": vector_stats.get("moat_strength", "unknown"),
        }

        # Get breakdown by type from Supabase
        if self.supabase:
            try:
                result = self.supabase.table("corrections").select(
                    "correction_type",
                    count="exact"
                ).execute()
                stats["correction_breakdown"] = result.data
            except Exception:
                pass

        return stats

    async def get_recent_corrections(
        self,
        limit: int = 10,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent corrections for display/review."""
        if not self.supabase:
            return []

        try:
            query = self.supabase.table("corrections").select("*").order(
                "created_at", desc=True
            ).limit(limit)

            if user_id:
                query = query.eq("user_id", user_id)

            result = query.execute()
            return result.data
        except Exception as e:
            print(f"Failed to get recent corrections: {e}")
            return []

    async def increment_retrieval_count(self, vector_id: str) -> None:
        """
        Increment the retrieval count for a correction.

        IRON SHELL ANALYTICS:
        Tracking which corrections are retrieved helps identify:
        1. The most valuable corrections (high impact)
        2. Common patterns in your domain
        3. Areas where the AI needs most help
        """
        if not self.supabase:
            return

        try:
            self.supabase.rpc(
                "increment_correction_retrieval",
                {"correction_vector_id": vector_id}
            ).execute()
        except Exception:
            # Non-critical, just log
            pass
