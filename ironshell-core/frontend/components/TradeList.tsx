/**
 * Trade List Component
 */

'use client'

import { TrendingUp, TrendingDown, AlertCircle } from 'lucide-react'
import type { Trade } from '@/types'

interface TradeListProps {
  trades: Trade[]
  selectedId?: string
  onSelect: (trade: Trade) => void
}

export function TradeList({ trades, selectedId, onSelect }: TradeListProps) {
  if (trades.length === 0) {
    return (
      <div className="text-center py-4 text-gray-500">
        <p className="text-sm">No trades uploaded</p>
      </div>
    )
  }

  return (
    <div className="space-y-2 max-h-64 overflow-y-auto">
      {trades.map((trade) => (
        <button
          key={trade.id}
          onClick={() => onSelect(trade)}
          className={`
            w-full p-3 rounded-lg text-left transition-all duration-200
            ${selectedId === trade.id
              ? 'bg-blue-600/20 border border-blue-500/50'
              : 'bg-iron-800 hover:bg-iron-700 border border-transparent'
            }
          `}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {trade.trade_type === 'BUY' || trade.trade_type === 'COVER' ? (
                <TrendingUp className="w-4 h-4 text-success-500" />
              ) : (
                <TrendingDown className="w-4 h-4 text-danger-500" />
              )}
              <span className="font-medium">{trade.symbol}</span>
            </div>
            <span className={`text-xs px-2 py-0.5 rounded ${
              trade.trade_type === 'BUY' ? 'bg-success-500/20 text-success-500' :
              trade.trade_type === 'SELL' ? 'bg-danger-500/20 text-danger-500' :
              'bg-gray-500/20 text-gray-400'
            }`}>
              {trade.trade_type}
            </span>
          </div>
          <div className="mt-1 text-sm text-gray-400">
            {trade.quantity} @ ${trade.price.toFixed(2)}
          </div>
          {trade.warnings && trade.warnings.length > 0 && (
            <div className="mt-1 flex items-center gap-1 text-xs text-warning-500">
              <AlertCircle className="w-3 h-3" />
              {trade.warnings.length} warning{trade.warnings.length > 1 ? 's' : ''}
            </div>
          )}
        </button>
      ))}
    </div>
  )
}
