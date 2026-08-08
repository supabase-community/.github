/**
 * ╔══════════════════════════════════════════════════════════════════════════════╗
 * ║                    GUARDRAIL PANEL - LIABILITY SHIELD UI                     ║
 * ║                                                                              ║
 * ║  IRON SHELL PRINCIPLE: "Hard limits prevent hard consequences"               ║
 * ║                                                                              ║
 * ║  This panel shows guardrail violations and BLOCKS dangerous actions.         ║
 * ║  When guardrails are violated, the Execute button MUST be disabled.          ║
 * ╚══════════════════════════════════════════════════════════════════════════════╝
 */

'use client'

import { useState, useEffect } from 'react'
import {
  Shield,
  AlertTriangle,
  AlertOctagon,
  CheckCircle,
  Lock,
  Unlock,
  Info,
} from 'lucide-react'

import type { Trade, AnalysisResponse, GuardrailViolation } from '@/types'
import { getGuardrails } from '@/lib/api'

interface GuardrailPanelProps {
  trade?: Trade | null
  analysis?: AnalysisResponse | null
}

export function GuardrailPanel({ trade, analysis }: GuardrailPanelProps) {
  const [guardrailConfig, setGuardrailConfig] = useState<any>(null)
  const [showOverride, setShowOverride] = useState(false)
  const [overrideReason, setOverrideReason] = useState('')
  const [acknowledgedRisks, setAcknowledgedRisks] = useState(false)

  // Load guardrail configuration
  useEffect(() => {
    getGuardrails()
      .then(setGuardrailConfig)
      .catch(console.error)
  }, [])

  const violations = analysis?.guardrails?.violations || []
  const hasViolations = violations.length > 0
  const hasCritical = violations.some(v => v.severity === 'critical')
  const canOverride = !hasCritical && analysis?.guardrails?.can_proceed_with_override

  // Severity icon mapping
  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <AlertOctagon className="w-4 h-4 text-danger-500" />
      case 'block':
        return <AlertTriangle className="w-4 h-4 text-danger-500" />
      case 'warning':
        return <Info className="w-4 h-4 text-warning-500" />
      default:
        return <Info className="w-4 h-4 text-gray-400" />
    }
  }

  return (
    <div className="card">
      {/* Header */}
      <div className="p-4 border-b border-iron-800">
        <div className="flex items-center gap-2">
          <Shield className={`w-5 h-5 ${
            hasViolations ? 'text-danger-500' : 'text-success-500'
          }`} />
          <h3 className="font-medium">Liability Shield</h3>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Status */}
        {!trade && !analysis ? (
          <div className="text-center py-4 text-gray-500">
            <Shield className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">Upload a trade to check guardrails</p>
          </div>
        ) : hasViolations ? (
          <>
            {/* Violations List */}
            <div className={`rounded-lg p-4 ${
              hasCritical ? 'guardrail-warning' : 'guardrail-caution'
            }`}>
              <div className="flex items-center gap-2 mb-3">
                {hasCritical ? (
                  <Lock className="w-5 h-5 text-danger-500" />
                ) : (
                  <AlertTriangle className="w-5 h-5 text-warning-500" />
                )}
                <span className="font-medium text-white">
                  {violations.length} Guardrail{violations.length > 1 ? 's' : ''} Triggered
                </span>
              </div>

              <ul className="space-y-3">
                {violations.map((violation, i) => (
                  <ViolationItem key={i} violation={violation} />
                ))}
              </ul>
            </div>

            {/* Override Section */}
            {canOverride && (
              <div className="space-y-3">
                <button
                  onClick={() => setShowOverride(!showOverride)}
                  className="text-sm text-gray-400 hover:text-white flex items-center gap-2"
                >
                  <Unlock className="w-4 h-4" />
                  Request Manual Override
                </button>

                {showOverride && (
                  <div className="p-4 bg-iron-800 rounded-lg space-y-3">
                    <p className="text-sm text-gray-300">
                      To override these guardrails, you must:
                    </p>

                    <div>
                      <label className="label">Reason for Override</label>
                      <textarea
                        value={overrideReason}
                        onChange={(e) => setOverrideReason(e.target.value)}
                        placeholder="Explain why this override is safe..."
                        className="input"
                        rows={2}
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Minimum 10 characters required
                      </p>
                    </div>

                    <label className="flex items-start gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={acknowledgedRisks}
                        onChange={(e) => setAcknowledgedRisks(e.target.checked)}
                        className="mt-1"
                      />
                      <span className="text-sm text-gray-300">
                        I acknowledge the risks and take full responsibility for this action
                      </span>
                    </label>

                    <button
                      disabled={overrideReason.length < 10 || !acknowledgedRisks}
                      className="btn-danger w-full"
                    >
                      Confirm Override
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Critical - No Override */}
            {hasCritical && (
              <div className="p-3 bg-danger-500/10 border border-danger-500/30 rounded-lg">
                <div className="flex items-center gap-2 text-danger-500 text-sm">
                  <Lock className="w-4 h-4" />
                  <span>
                    Critical violations cannot be overridden
                  </span>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="p-4 bg-success-500/10 border border-success-500/30 rounded-lg">
            <div className="flex items-center gap-2 text-success-500">
              <CheckCircle className="w-5 h-5" />
              <span className="font-medium">All Guardrails Passed</span>
            </div>
            <p className="text-sm text-gray-400 mt-2">
              This trade meets all risk requirements
            </p>
          </div>
        )}

        {/* Active Guardrails Info */}
        {guardrailConfig && (
          <div className="pt-4 border-t border-iron-800">
            <p className="text-xs text-gray-500 mb-2">Active Guardrails:</p>
            <ul className="text-xs text-gray-400 space-y-1">
              {guardrailConfig.active_guardrails?.slice(0, 4).map((g: any) => (
                <li key={g.id} className="flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-gray-600" />
                  {g.name}: {g.threshold || (g.enabled ? 'Enabled' : 'Disabled')}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}

function ViolationItem({ violation }: { violation: GuardrailViolation }) {
  const severityColors = {
    critical: 'text-danger-500 bg-danger-500/10',
    block: 'text-danger-500 bg-danger-500/10',
    warning: 'text-warning-500 bg-warning-500/10',
  }

  return (
    <li className="text-sm">
      <div className="flex items-start gap-2">
        <span className={`badge ${
          violation.severity === 'critical' ? 'badge-danger' :
          violation.severity === 'block' ? 'badge-danger' :
          'badge-warning'
        }`}>
          {violation.severity.toUpperCase()}
        </span>
        <div>
          <p className="font-medium text-white">{violation.rule_name}</p>
          <p className="text-gray-400">{violation.message}</p>
          {violation.actual_value !== undefined && (
            <p className="text-xs text-gray-500 mt-1">
              Actual: {violation.actual_value} | Threshold: {violation.threshold_value}
            </p>
          )}
        </div>
      </div>
    </li>
  )
}
