/**
 * ╔══════════════════════════════════════════════════════════════════════════════╗
 * ║                    IRONSHELL TYPE DEFINITIONS                                ║
 * ╚══════════════════════════════════════════════════════════════════════════════╝
 */

// ══════════════════════════════════════════════════════════════════════════════
// TRADE TYPES
// ══════════════════════════════════════════════════════════════════════════════

export type TradeType = 'BUY' | 'SELL' | 'SHORT' | 'COVER'

export interface Trade {
  id: string
  symbol: string
  trade_type: TradeType
  quantity: number
  price: number
  total_value: number
  trade_date: string
  leverage?: number
  stop_loss_price?: number
  take_profit_price?: number
  position_size_percent?: number
  notes?: string
  broker_source?: string
  confidence?: number
  warnings?: string[]
}

export interface ParsedTrade extends Trade {
  raw_row?: Record<string, any>
}

// ══════════════════════════════════════════════════════════════════════════════
// ANALYSIS TYPES
// ══════════════════════════════════════════════════════════════════════════════

export type RiskLevel = 'low' | 'medium' | 'high' | 'extreme'

export interface TradeAnalysis {
  trade_id: string
  symbol: string
  risk_level: RiskLevel
  risk_score: number
  risk_factors: string[]
  position_type: string
  suggested_stop_loss?: number
  suggested_take_profit?: number
  risk_reward_ratio?: number
  analysis_summary: string
  key_observations: string[]
  warnings: string[]
  suggestions: string[]
  guardrail_violations: string[]
  requires_manual_approval: boolean
  confidence: number
  model_used: string
  rag_context_used: boolean
  similar_corrections_count: number
}

export interface AnalysisResponse {
  analysis: TradeAnalysis
  guardrails: GuardrailCheckResult
  can_execute: boolean
  requires_override: boolean
}

// ══════════════════════════════════════════════════════════════════════════════
// GUARDRAIL TYPES
// ══════════════════════════════════════════════════════════════════════════════

export type GuardrailSeverity = 'warning' | 'block' | 'critical'

export interface GuardrailViolation {
  rule_id: string
  rule_name: string
  severity: GuardrailSeverity
  message: string
  details: Record<string, any>
  actual_value?: number | string
  threshold_value?: number | string
  can_override: boolean
  override_requires_reason: boolean
}

export interface GuardrailCheckResult {
  passed: boolean
  violations: GuardrailViolation[]
  warnings: string[]
  requires_manual_approval: boolean
  can_proceed_with_override: boolean
  summary: string
}

export interface GuardrailConfig {
  id: string
  name: string
  threshold?: string | number
  enabled?: boolean
  description: string
}

// ══════════════════════════════════════════════════════════════════════════════
// FEEDBACK/CORRECTION TYPES
// ══════════════════════════════════════════════════════════════════════════════

export interface CorrectionInput {
  original_input: Record<string, any>
  ai_output: Record<string, any>
  user_final_version: Record<string, any>
  user_id?: string
  analysis_id?: string
  correction_type?: string
  domain_tags?: string[]
}

export interface CorrectionResponse {
  success: boolean
  correction_id: string
  message: string
  flywheel_size: number
  moat_strength: string
}

export interface FlywheelStats {
  total_corrections: number
  flywheel_status: string
  moat_strength: string
  breakdown_by_type?: Record<string, number>
  recent_corrections?: CorrectionRecord[]
}

export interface CorrectionRecord {
  id: string
  original_input: Record<string, any>
  ai_output: Record<string, any>
  user_correction: Record<string, any>
  diff_summary: string
  change_magnitude: number
  correction_type: string
  domain_tags: string[]
  created_at: string
}

// ══════════════════════════════════════════════════════════════════════════════
// INGESTION TYPES
// ══════════════════════════════════════════════════════════════════════════════

export interface IngestionResult {
  success: boolean
  batch_id: string
  trades: ParsedTrade[]
  total_rows: number
  parsed_rows: number
  failed_rows: number
  warnings: string[]
  errors: IngestionError[]
  column_mapping?: Record<string, string>
  requires_user_input: boolean
  user_questions: string[]
}

export interface IngestionError {
  type: string
  message: string
  suggestion?: string
  row_number?: number
  raw_data?: Record<string, any>
}

// ══════════════════════════════════════════════════════════════════════════════
// API RESPONSE TYPES
// ══════════════════════════════════════════════════════════════════════════════

export interface ApiError {
  error: string
  message: string
  type: string
}

export interface HealthStatus {
  status: string
  components: Record<string, {
    status: string
    description?: string
    error?: string
    stats?: Record<string, any>
  }>
}
