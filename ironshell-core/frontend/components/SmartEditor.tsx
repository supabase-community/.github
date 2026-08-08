/**
 * ╔══════════════════════════════════════════════════════════════════════════════╗
 * ║                    SMART EDITOR - THE DATA FLYWHEEL UI                       ║
 * ║                                                                              ║
 * ║  THIS COMPONENT IS CRITICAL FOR THE IRON SHELL STRATEGY                      ║
 * ║                                                                              ║
 * ║  WHAT IT DOES:                                                               ║
 * ║  1. Displays AI-generated analysis as editable blocks                        ║
 * ║  2. Tracks what the user changes                                             ║
 * ║  3. When saved, sends the DIFF to the feedback endpoint                      ║
 * ║  4. The diff becomes training data for YOUR AI                               ║
 * ║                                                                              ║
 * ║  RESULT: Every user interaction makes your AI smarter.                       ║
 * ║  Competitors can copy your code, but NOT your correction dataset.            ║
 * ╚══════════════════════════════════════════════════════════════════════════════╝
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Brain,
  Save,
  RotateCcw,
  AlertTriangle,
  CheckCircle,
  Edit3,
  Loader2,
  Sparkles,
  TrendingUp,
  TrendingDown,
  Shield,
} from 'lucide-react'
import toast from 'react-hot-toast'

import type { Trade, TradeAnalysis, AnalysisResponse } from '@/types'
import { analyzeTrade, saveCorrection } from '@/lib/api'

interface SmartEditorProps {
  trade: Trade
  analysis?: AnalysisResponse
  editMode?: boolean
  onAnalysisComplete?: (analysis: AnalysisResponse) => void
  onCorrectionSaved?: () => void
}

type EditableField = keyof TradeAnalysis

interface FieldEdit {
  field: EditableField
  original: any
  current: any
  modified: boolean
}

export function SmartEditor({
  trade,
  analysis: initialAnalysis,
  editMode = false,
  onAnalysisComplete,
  onCorrectionSaved,
}: SmartEditorProps) {
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [analysis, setAnalysis] = useState<TradeAnalysis | null>(
    initialAnalysis?.analysis || null
  )
  const [guardrails, setGuardrails] = useState(initialAnalysis?.guardrails || null)

  // Track edits for the Data Flywheel
  const [edits, setEdits] = useState<Map<EditableField, FieldEdit>>(new Map())
  const [hasChanges, setHasChanges] = useState(false)

  // Editable state
  const [editedAnalysis, setEditedAnalysis] = useState<Partial<TradeAnalysis>>({})

  // Initialize edited analysis when analysis loads
  useEffect(() => {
    if (analysis) {
      setEditedAnalysis({ ...analysis })
      setEdits(new Map())
      setHasChanges(false)
    }
  }, [analysis])

  // Run analysis
  const runAnalysis = useCallback(async () => {
    if (!trade) return

    setIsAnalyzing(true)
    try {
      const result = await analyzeTrade(trade)
      setAnalysis(result.analysis)
      setGuardrails(result.guardrails)
      setEditedAnalysis({ ...result.analysis })

      if (result.analysis.rag_context_used) {
        toast.success(
          `AI used ${result.analysis.similar_corrections_count} past corrections for context`,
          { icon: '🧠' }
        )
      }

      onAnalysisComplete?.(result)
    } catch (error) {
      toast.error(`Analysis failed: ${error}`)
    } finally {
      setIsAnalyzing(false)
    }
  }, [trade, onAnalysisComplete])

  // Auto-run analysis if not in edit mode and no initial analysis
  useEffect(() => {
    if (!editMode && !initialAnalysis && trade) {
      runAnalysis()
    }
  }, [editMode, initialAnalysis, trade, runAnalysis])

  // Track field edits
  const handleFieldChange = (field: EditableField, value: any) => {
    const original = analysis?.[field]
    const modified = JSON.stringify(original) !== JSON.stringify(value)

    setEditedAnalysis(prev => ({ ...prev, [field]: value }))

    const newEdits = new Map(edits)
    newEdits.set(field, {
      field,
      original,
      current: value,
      modified,
    })
    setEdits(newEdits)

    // Check if any field is modified
    const anyModified = Array.from(newEdits.values()).some(e => e.modified)
    setHasChanges(anyModified)
  }

  // Save correction (Data Flywheel)
  const handleSaveCorrection = async () => {
    if (!analysis || !hasChanges) return

    setIsSaving(true)
    try {
      // Build the correction payload
      const result = await saveCorrection({
        original_input: trade,
        ai_output: analysis,
        user_final_version: editedAnalysis as Record<string, any>,
        correction_type: 'trade_analysis',
        domain_tags: [trade.symbol, trade.trade_type.toLowerCase()],
      })

      toast.success(result.message, { icon: '💾' })
      toast.success(`Moat strength: ${result.moat_strength}`, {
        icon: '🛡️',
        duration: 5000,
      })

      onCorrectionSaved?.()
    } catch (error) {
      toast.error(`Failed to save correction: ${error}`)
    } finally {
      setIsSaving(false)
    }
  }

  // Reset to original
  const handleReset = () => {
    if (analysis) {
      setEditedAnalysis({ ...analysis })
      setEdits(new Map())
      setHasChanges(false)
    }
  }

  // ══════════════════════════════════════════════════════════════════════════
  // RENDER
  // ══════════════════════════════════════════════════════════════════════════

  if (isAnalyzing) {
    return (
      <div className="card p-8">
        <div className="flex flex-col items-center justify-center py-12">
          <div className="relative">
            <Brain className="w-16 h-16 text-blue-500 animate-pulse" />
            <Sparkles className="w-6 h-6 text-yellow-400 absolute -top-1 -right-1 animate-spin-slow" />
          </div>
          <h3 className="mt-4 text-lg font-medium">Analyzing Trade...</h3>
          <p className="text-sm text-gray-400 mt-2">
            Checking for similar past corrections (RAG)
          </p>
          <Loader2 className="w-6 h-6 mt-4 animate-spin text-blue-500" />
        </div>
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="card p-8">
        <div className="text-center py-12">
          <Brain className="w-12 h-12 mx-auto text-gray-600" />
          <h3 className="mt-4 text-lg font-medium text-gray-400">
            No Analysis Available
          </h3>
          <button
            onClick={runAnalysis}
            className="btn-primary mt-4"
          >
            Run Analysis
          </button>
        </div>
      </div>
    )
  }

  const riskColors = {
    low: 'text-success-500',
    medium: 'text-warning-500',
    high: 'text-danger-500',
    extreme: 'text-danger-500',
  }

  return (
    <div className="card">
      {/* Header */}
      <div className="p-4 border-b border-iron-800 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${
            analysis.risk_level === 'low' ? 'bg-success-500/20' :
            analysis.risk_level === 'medium' ? 'bg-warning-500/20' :
            'bg-danger-500/20'
          }`}>
            <Shield className={`w-5 h-5 ${riskColors[analysis.risk_level]}`} />
          </div>
          <div>
            <h2 className="font-semibold">
              {trade.symbol} - {trade.trade_type}
            </h2>
            <p className="text-sm text-gray-400">
              {trade.quantity} shares @ ${trade.price.toFixed(2)}
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {hasChanges && (
            <button
              onClick={handleReset}
              className="btn-secondary flex items-center gap-2"
            >
              <RotateCcw className="w-4 h-4" />
              Reset
            </button>
          )}
          <button
            onClick={handleSaveCorrection}
            disabled={!hasChanges || isSaving}
            className="btn-primary flex items-center gap-2"
          >
            {isSaving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Save Correction
          </button>
        </div>
      </div>

      {/* RAG Context Indicator */}
      {analysis.rag_context_used && (
        <div className="px-4 py-2 bg-blue-500/10 border-b border-blue-500/20">
          <div className="flex items-center gap-2 text-sm text-blue-400">
            <Sparkles className="w-4 h-4" />
            <span>
              AI used {analysis.similar_corrections_count} past corrections for context
            </span>
          </div>
        </div>
      )}

      {/* Edit Mode Banner */}
      {editMode && (
        <div className="px-4 py-2 bg-yellow-500/10 border-b border-yellow-500/20">
          <div className="flex items-center gap-2 text-sm text-yellow-400">
            <Edit3 className="w-4 h-4" />
            <span>
              <strong>Edit Mode:</strong> Your corrections will train the AI
            </span>
          </div>
        </div>
      )}

      {/* Content */}
      <div className="p-6 space-y-6">
        {/* Risk Assessment */}
        <EditableSection
          title="Risk Assessment"
          icon={<AlertTriangle className="w-4 h-4" />}
        >
          <div className="grid grid-cols-2 gap-4">
            <EditableField
              label="Risk Level"
              field="risk_level"
              value={editedAnalysis.risk_level || ''}
              onChange={(v) => handleFieldChange('risk_level', v)}
              type="select"
              options={['low', 'medium', 'high', 'extreme']}
              modified={edits.get('risk_level')?.modified}
            />
            <EditableField
              label="Risk Score"
              field="risk_score"
              value={editedAnalysis.risk_score || 0}
              onChange={(v) => handleFieldChange('risk_score', parseFloat(v))}
              type="number"
              min={0}
              max={1}
              step={0.05}
              modified={edits.get('risk_score')?.modified}
            />
          </div>

          <EditableField
            label="Risk Factors"
            field="risk_factors"
            value={(editedAnalysis.risk_factors || []).join('\n')}
            onChange={(v) => handleFieldChange('risk_factors', v.split('\n').filter(Boolean))}
            type="textarea"
            modified={edits.get('risk_factors')?.modified}
            placeholder="One risk factor per line"
          />
        </EditableSection>

        {/* Analysis Summary */}
        <EditableSection
          title="Analysis Summary"
          icon={<Brain className="w-4 h-4" />}
        >
          <EditableField
            label="Summary"
            field="analysis_summary"
            value={editedAnalysis.analysis_summary || ''}
            onChange={(v) => handleFieldChange('analysis_summary', v)}
            type="textarea"
            modified={edits.get('analysis_summary')?.modified}
          />

          <EditableField
            label="Key Observations"
            field="key_observations"
            value={(editedAnalysis.key_observations || []).join('\n')}
            onChange={(v) => handleFieldChange('key_observations', v.split('\n').filter(Boolean))}
            type="textarea"
            modified={edits.get('key_observations')?.modified}
            placeholder="One observation per line"
          />
        </EditableSection>

        {/* Warnings & Suggestions */}
        <EditableSection
          title="Warnings & Suggestions"
          icon={<CheckCircle className="w-4 h-4" />}
        >
          <EditableField
            label="Warnings"
            field="warnings"
            value={(editedAnalysis.warnings || []).join('\n')}
            onChange={(v) => handleFieldChange('warnings', v.split('\n').filter(Boolean))}
            type="textarea"
            modified={edits.get('warnings')?.modified}
            placeholder="One warning per line"
          />

          <EditableField
            label="Suggestions"
            field="suggestions"
            value={(editedAnalysis.suggestions || []).join('\n')}
            onChange={(v) => handleFieldChange('suggestions', v.split('\n').filter(Boolean))}
            type="textarea"
            modified={edits.get('suggestions')?.modified}
            placeholder="One suggestion per line"
          />
        </EditableSection>

        {/* Position Details */}
        <EditableSection
          title="Position Details"
          icon={<TrendingUp className="w-4 h-4" />}
        >
          <div className="grid grid-cols-2 gap-4">
            <EditableField
              label="Position Type"
              field="position_type"
              value={editedAnalysis.position_type || ''}
              onChange={(v) => handleFieldChange('position_type', v)}
              type="select"
              options={['day_trade', 'swing', 'position', 'scalp']}
              modified={edits.get('position_type')?.modified}
            />
            <EditableField
              label="Risk/Reward Ratio"
              field="risk_reward_ratio"
              value={editedAnalysis.risk_reward_ratio || ''}
              onChange={(v) => handleFieldChange('risk_reward_ratio', parseFloat(v) || null)}
              type="number"
              step={0.1}
              modified={edits.get('risk_reward_ratio')?.modified}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <EditableField
              label="Suggested Stop Loss"
              field="suggested_stop_loss"
              value={editedAnalysis.suggested_stop_loss || ''}
              onChange={(v) => handleFieldChange('suggested_stop_loss', parseFloat(v) || null)}
              type="number"
              step={0.01}
              modified={edits.get('suggested_stop_loss')?.modified}
            />
            <EditableField
              label="Suggested Take Profit"
              field="suggested_take_profit"
              value={editedAnalysis.suggested_take_profit || ''}
              onChange={(v) => handleFieldChange('suggested_take_profit', parseFloat(v) || null)}
              type="number"
              step={0.01}
              modified={edits.get('suggested_take_profit')?.modified}
            />
          </div>
        </EditableSection>

        {/* Metadata */}
        <div className="text-xs text-gray-500 flex items-center gap-4">
          <span>Model: {analysis.model_used}</span>
          <span>Confidence: {(analysis.confidence * 100).toFixed(0)}%</span>
          {analysis.rag_context_used && (
            <span className="text-blue-400">
              RAG: {analysis.similar_corrections_count} corrections used
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// HELPER COMPONENTS
// ══════════════════════════════════════════════════════════════════════════════

function EditableSection({
  title,
  icon,
  children,
}: {
  title: string
  icon: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm font-medium text-gray-300">
        {icon}
        {title}
      </div>
      <div className="space-y-3">
        {children}
      </div>
    </div>
  )
}

function EditableField({
  label,
  field,
  value,
  onChange,
  type = 'text',
  options,
  modified,
  placeholder,
  min,
  max,
  step,
}: {
  label: string
  field: string
  value: string | number
  onChange: (value: string) => void
  type?: 'text' | 'textarea' | 'number' | 'select'
  options?: string[]
  modified?: boolean
  placeholder?: string
  min?: number
  max?: number
  step?: number
}) {
  const baseClasses = `
    input
    ${modified ? 'border-yellow-500 bg-yellow-500/10' : ''}
  `

  return (
    <div>
      <label className="label flex items-center gap-2">
        {label}
        {modified && (
          <span className="badge-warning text-xs">Modified</span>
        )}
      </label>

      {type === 'textarea' ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          rows={3}
          className={baseClasses}
        />
      ) : type === 'select' ? (
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={baseClasses}
        >
          {options?.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      ) : (
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          min={min}
          max={max}
          step={step}
          className={baseClasses}
        />
      )}
    </div>
  )
}
