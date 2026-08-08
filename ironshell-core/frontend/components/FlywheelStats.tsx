/**
 * ╔══════════════════════════════════════════════════════════════════════════════╗
 * ║                    FLYWHEEL STATS - YOUR COMPETITIVE MOAT                    ║
 * ║                                                                              ║
 * ║  Shows how many corrections you've collected and how defensible your AI is.  ║
 * ╚══════════════════════════════════════════════════════════════════════════════╝
 */

'use client'

import { useState, useEffect } from 'react'
import { RefreshCw, TrendingUp, Shield, Database } from 'lucide-react'

import type { FlywheelStats as FlywheelStatsType } from '@/types'
import { getFlywheelStats } from '@/lib/api'

interface FlywheelStatsProps {
  compact?: boolean
}

export function FlywheelStats({ compact = false }: FlywheelStatsProps) {
  const [stats, setStats] = useState<FlywheelStatsType | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStats()
    // Refresh every 30 seconds
    const interval = setInterval(loadStats, 30000)
    return () => clearInterval(interval)
  }, [])

  const loadStats = async () => {
    try {
      const data = await getFlywheelStats()
      setStats(data)
    } catch (error) {
      console.error('Failed to load flywheel stats:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className={compact ? 'flex items-center gap-2 text-gray-500' : 'card p-4'}>
        <RefreshCw className="w-4 h-4 animate-spin" />
        {!compact && <span>Loading...</span>}
      </div>
    )
  }

  if (!stats) {
    return null
  }

  const moatColor =
    stats.moat_strength.includes('deep') ? 'text-success-500' :
    stats.moat_strength.includes('strong') ? 'text-success-500' :
    stats.moat_strength.includes('emerging') ? 'text-warning-500' :
    'text-gray-400'

  if (compact) {
    return (
      <div className="flex items-center gap-3 px-3 py-2 bg-iron-800 rounded-lg">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-blue-500" />
          <span className="text-sm font-medium">{stats.total_corrections}</span>
        </div>
        <div className="h-4 w-px bg-iron-700" />
        <div className="flex items-center gap-2">
          <Shield className={`w-4 h-4 ${moatColor}`} />
          <span className={`text-sm ${moatColor}`}>
            {stats.moat_strength.split(' - ')[0]}
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium flex items-center gap-2">
          <RefreshCw className="w-4 h-4 text-blue-500" />
          Data Flywheel
        </h3>
        <span className={`badge ${
          stats.flywheel_status === 'spinning' ? 'badge-success' : 'badge-warning'
        }`}>
          {stats.flywheel_status}
        </span>
      </div>

      <div className="space-y-4">
        {/* Total Corrections */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-400">Total Corrections</span>
          <span className="text-2xl font-bold text-gradient">
            {stats.total_corrections}
          </span>
        </div>

        {/* Moat Strength */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-gray-400">Moat Strength</span>
            <Shield className={`w-4 h-4 ${moatColor}`} />
          </div>
          <p className={`text-sm ${moatColor}`}>
            {stats.moat_strength}
          </p>
        </div>

        {/* Progress Bar */}
        <div>
          <div className="h-2 bg-iron-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-500"
              style={{
                width: `${Math.min(100, (stats.total_corrections / 1000) * 100)}%`
              }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-1">
            {stats.total_corrections < 10 ? 'Just getting started' :
             stats.total_corrections < 100 ? 'Building momentum' :
             stats.total_corrections < 1000 ? 'Strong foundation' :
             'Deep competitive moat'}
          </p>
        </div>
      </div>
    </div>
  )
}
