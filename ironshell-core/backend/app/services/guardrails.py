"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    GUARDRAILS - THE LIABILITY SHIELD                         ║
║                                                                              ║
║  IRON SHELL PRINCIPLE: "Hard limits prevent hard consequences"               ║
║                                                                              ║
║  WHY GUARDRAILS ARE NON-NEGOTIABLE:                                          ║
║  1. AI can hallucinate dangerous recommendations                             ║
║  2. Users might not catch risky suggestions                                  ║
║  3. You need legal protection ("we warned them")                             ║
║  4. Guardrails are your "safety moat" - competitors who skip them lose       ║
║                                                                              ║
║  THE GUARDRAIL CONTRACT:                                                     ║
║  If a guardrail is violated, the UI MUST:                                    ║
║  - Block the "Execute" button                                                ║
║  - Show a prominent red warning                                              ║
║  - Require explicit manual override with reason                              ║
║  - Log the override for audit                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.core.config import settings, get_guardrail_config


# ══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════════════════════

class GuardrailSeverity(str, Enum):
    """Severity levels for guardrail violations."""
    WARNING = "warning"       # Show warning, allow proceed
    BLOCK = "block"          # Block execution, require override
    CRITICAL = "critical"    # Block execution, no override allowed


class GuardrailViolation(BaseModel):
    """A single guardrail violation."""
    rule_id: str
    rule_name: str
    severity: GuardrailSeverity
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    actual_value: Optional[Any] = None
    threshold_value: Optional[Any] = None
    can_override: bool = True
    override_requires_reason: bool = True


class GuardrailCheckResult(BaseModel):
    """Result of a guardrail check."""
    passed: bool
    violations: List[GuardrailViolation] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    requires_manual_approval: bool = False
    can_proceed_with_override: bool = True
    summary: str = ""


class OverrideRequest(BaseModel):
    """Request to override a guardrail."""
    violations: List[str]  # Rule IDs being overridden
    reason: str = Field(min_length=10, description="Must explain why override is safe")
    user_id: str
    acknowledged_risks: bool = False


class OverrideRecord(BaseModel):
    """Record of a guardrail override for audit."""
    id: str
    user_id: str
    violations_overridden: List[str]
    reason: str
    trade_data: Dict[str, Any]
    timestamp: datetime
    ip_address: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# GUARDRAIL VALIDATOR
# ══════════════════════════════════════════════════════════════════════════════

class GuardrailValidator:
    """
    Validates trades and AI outputs against safety guardrails.

    IRON SHELL LIABILITY SHIELD:
    This class is your legal protection. It ensures that:
    1. Dangerous trades are flagged before execution
    2. Users must acknowledge risks explicitly
    3. Every override is logged for audit
    4. The UI knows exactly what to block

    CUSTOMIZATION:
    The guardrails here are for trading. For other domains:
    - Legal: Flag advice that seems like legal counsel
    - Medical: Flag anything that sounds like diagnosis
    - Finance: Flag tax advice, investment recommendations
    """

    def __init__(self):
        self.config = get_guardrail_config()

    def check_trade(self, trade_data: Dict[str, Any]) -> GuardrailCheckResult:
        """
        Check a trade against all guardrails.

        IRON SHELL MECHANIC:
        Run all guardrails and collect violations.
        Even if one passes, others might fail.
        """
        violations = []
        warnings = []

        # Check each guardrail
        violations.extend(self._check_leverage(trade_data))
        violations.extend(self._check_position_size(trade_data))
        violations.extend(self._check_stop_loss(trade_data))
        violations.extend(self._check_daily_loss(trade_data))
        violations.extend(self._check_concentration(trade_data))

        # Determine overall result
        has_blocks = any(v.severity == GuardrailSeverity.BLOCK for v in violations)
        has_critical = any(v.severity == GuardrailSeverity.CRITICAL for v in violations)

        # Build summary
        if not violations:
            summary = "All guardrails passed"
        else:
            summary = f"{len(violations)} guardrail violation(s) detected"

        return GuardrailCheckResult(
            passed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            requires_manual_approval=has_blocks or has_critical,
            can_proceed_with_override=not has_critical,
            summary=summary
        )

    def check_ai_output(
        self,
        ai_output: Dict[str, Any],
        trade_data: Dict[str, Any]
    ) -> GuardrailCheckResult:
        """
        Check AI-generated output against guardrails.

        IRON SHELL INSIGHT:
        The AI might suggest something dangerous.
        We check the AI's recommendations, not just the trade data.
        """
        violations = []

        # Check if AI suggests high-risk action without proper warnings
        risk_level = ai_output.get("risk_level", "").lower()
        warnings = ai_output.get("warnings", [])

        if risk_level in ["high", "extreme"] and not warnings:
            violations.append(GuardrailViolation(
                rule_id="ai_missing_warnings",
                rule_name="AI Missing Risk Warnings",
                severity=GuardrailSeverity.WARNING,
                message="AI identified high risk but provided no specific warnings",
                can_override=True
            ))

        # Check if AI confidence is too high
        confidence = ai_output.get("confidence", 0)
        if confidence > self.config["max_confidence_without_review"]:
            violations.append(GuardrailViolation(
                rule_id="high_confidence_review",
                rule_name="High Confidence Review Required",
                severity=GuardrailSeverity.WARNING,
                message=f"AI confidence ({confidence:.0%}) is high - manual review still recommended",
                actual_value=confidence,
                threshold_value=self.config["max_confidence_without_review"],
                can_override=True
            ))

        # Always require human approval if configured
        requires_approval = self.config["require_human_approval"]

        return GuardrailCheckResult(
            passed=len(violations) == 0,
            violations=violations,
            requires_manual_approval=requires_approval,
            can_proceed_with_override=True,
            summary="AI output check complete"
        )

    def _check_leverage(self, trade_data: Dict[str, Any]) -> List[GuardrailViolation]:
        """
        Check leverage limits.

        IRON SHELL RULE:
        High leverage = high risk of catastrophic loss.
        Above 10x, we BLOCK. Period.
        """
        violations = []
        leverage = trade_data.get("leverage", 1.0)
        max_leverage = self.config["max_leverage"]

        if leverage > max_leverage:
            severity = GuardrailSeverity.CRITICAL if leverage > 20 else GuardrailSeverity.BLOCK

            violations.append(GuardrailViolation(
                rule_id="max_leverage_exceeded",
                rule_name="Maximum Leverage Exceeded",
                severity=severity,
                message=f"Leverage of {leverage}x exceeds maximum allowed ({max_leverage}x)",
                details={
                    "requested_leverage": leverage,
                    "max_allowed": max_leverage,
                    "risk_multiplier": leverage / max_leverage
                },
                actual_value=leverage,
                threshold_value=max_leverage,
                can_override=leverage <= 20,  # Can't override extreme leverage
                override_requires_reason=True
            ))
        elif leverage > max_leverage * 0.8:
            # Warning when approaching limit
            violations.append(GuardrailViolation(
                rule_id="leverage_warning",
                rule_name="Leverage Warning",
                severity=GuardrailSeverity.WARNING,
                message=f"Leverage of {leverage}x is approaching the maximum ({max_leverage}x)",
                actual_value=leverage,
                threshold_value=max_leverage,
                can_override=True
            ))

        return violations

    def _check_position_size(self, trade_data: Dict[str, Any]) -> List[GuardrailViolation]:
        """
        Check position size limits.

        IRON SHELL RULE:
        Concentration risk is a portfolio killer.
        No single position should exceed 25% of portfolio.
        """
        violations = []
        position_pct = trade_data.get("position_size_percent", 0)
        max_position = self.config["max_position_size_percent"]

        if position_pct > max_position:
            violations.append(GuardrailViolation(
                rule_id="position_size_exceeded",
                rule_name="Position Size Exceeded",
                severity=GuardrailSeverity.BLOCK,
                message=f"Position size of {position_pct}% exceeds maximum ({max_position}%)",
                details={
                    "requested_position": position_pct,
                    "max_allowed": max_position,
                    "excess_percent": position_pct - max_position
                },
                actual_value=position_pct,
                threshold_value=max_position,
                can_override=True,
                override_requires_reason=True
            ))

        return violations

    def _check_stop_loss(self, trade_data: Dict[str, Any]) -> List[GuardrailViolation]:
        """
        Check for stop-loss requirement.

        IRON SHELL RULE:
        Trading without a stop-loss is gambling, not trading.
        We require it by default.
        """
        violations = []

        if not self.config["require_stop_loss"]:
            return violations

        has_stop_loss = trade_data.get("stop_loss_price") is not None

        if not has_stop_loss:
            violations.append(GuardrailViolation(
                rule_id="no_stop_loss",
                rule_name="No Stop Loss",
                severity=GuardrailSeverity.BLOCK,
                message="Trade requires a stop-loss order for risk management",
                details={
                    "suggestion": "Set a stop-loss at a level you're comfortable losing"
                },
                can_override=True,
                override_requires_reason=True
            ))

        return violations

    def _check_daily_loss(self, trade_data: Dict[str, Any]) -> List[GuardrailViolation]:
        """
        Check daily loss limits.

        IRON SHELL RULE:
        If you've lost more than X% today, stop trading.
        Emotional trading after losses = more losses.
        """
        violations = []
        daily_loss = trade_data.get("daily_loss_percent", 0)
        max_daily_loss = self.config["max_daily_loss_percent"]

        if daily_loss >= max_daily_loss:
            violations.append(GuardrailViolation(
                rule_id="daily_loss_exceeded",
                rule_name="Daily Loss Limit Reached",
                severity=GuardrailSeverity.CRITICAL,
                message=f"Daily loss of {daily_loss}% has reached the limit ({max_daily_loss}%)",
                details={
                    "current_daily_loss": daily_loss,
                    "max_allowed": max_daily_loss,
                    "recommendation": "Stop trading for today and review your strategy"
                },
                actual_value=daily_loss,
                threshold_value=max_daily_loss,
                can_override=False,  # Critical - no override
                override_requires_reason=True
            ))

        return violations

    def _check_concentration(self, trade_data: Dict[str, Any]) -> List[GuardrailViolation]:
        """
        Check sector/asset concentration.

        IRON SHELL RULE:
        Don't put all eggs in one basket (or sector).
        """
        violations = []
        # This would require portfolio context - placeholder for now
        return violations

    def validate_override(
        self,
        override_request: OverrideRequest,
        original_result: GuardrailCheckResult
    ) -> Tuple[bool, str]:
        """
        Validate an override request.

        IRON SHELL AUDIT:
        Overrides must be:
        1. For violations that CAN be overridden
        2. With a substantial reason (>10 chars)
        3. With acknowledged risks
        """
        # Check that all violations can be overridden
        non_overridable = [
            v for v in original_result.violations
            if v.rule_id in override_request.violations and not v.can_override
        ]

        if non_overridable:
            return False, f"Cannot override critical violations: {[v.rule_name for v in non_overridable]}"

        # Check reason length
        if len(override_request.reason) < 10:
            return False, "Override reason must be at least 10 characters"

        # Check risk acknowledgment
        if not override_request.acknowledged_risks:
            return False, "Must acknowledge risks to proceed with override"

        return True, "Override approved"

    def get_guardrail_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all active guardrails.

        IRON SHELL UX:
        Show users what guardrails are active so they understand
        why certain actions might be blocked.
        """
        return {
            "active_guardrails": [
                {
                    "id": "max_leverage",
                    "name": "Maximum Leverage",
                    "threshold": self.config["max_leverage"],
                    "description": f"Trades with leverage above {self.config['max_leverage']}x are blocked"
                },
                {
                    "id": "max_position_size",
                    "name": "Maximum Position Size",
                    "threshold": f"{self.config['max_position_size_percent']}%",
                    "description": f"Positions larger than {self.config['max_position_size_percent']}% of portfolio are blocked"
                },
                {
                    "id": "require_stop_loss",
                    "name": "Stop Loss Required",
                    "enabled": self.config["require_stop_loss"],
                    "description": "All trades must have a stop-loss order"
                },
                {
                    "id": "max_daily_loss",
                    "name": "Daily Loss Limit",
                    "threshold": f"{self.config['max_daily_loss_percent']}%",
                    "description": f"Trading is halted after {self.config['max_daily_loss_percent']}% daily loss"
                },
            ],
            "human_approval_required": self.config["require_human_approval"],
            "max_ai_confidence": self.config["max_confidence_without_review"]
        }
