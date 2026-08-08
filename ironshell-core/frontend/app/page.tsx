/**
 * ╔══════════════════════════════════════════════════════════════════════════════╗
 * ║                    IRONSHELL MAIN DASHBOARD                                  ║
 * ║                                                                              ║
 * ║  IRON SHELL PRINCIPLE: The UI must guide users through the workflow         ║
 * ║  that builds your competitive moat.                                          ║
 * ╚══════════════════════════════════════════════════════════════════════════════╝
 */

'use client'

import { useState } from 'react'
import {
  Upload,
  BarChart3,
  Shield,
  Brain,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
} from 'lucide-react'

import { FileUploader } from '@/components/FileUploader'
import { SmartEditor } from '@/components/SmartEditor'
import { GuardrailPanel } from '@/components/GuardrailPanel'
import { FlywheelStats } from '@/components/FlywheelStats'
import { TradeList } from '@/components/TradeList'

type View = 'upload' | 'analyze' | 'review'

export default function Dashboard() {
  const [currentView, setCurrentView] = useState<View>('upload')
  const [trades, setTrades] = useState<any[]>([])
  const [selectedTrade, setSelectedTrade] = useState<any>(null)
  const [analysis, setAnalysis] = useState<any>(null)

  // Handle file upload completion
  const handleUploadComplete = (parsedTrades: any[]) => {
    setTrades(parsedTrades)
    if (parsedTrades.length > 0) {
      setSelectedTrade(parsedTrades[0])
      setCurrentView('analyze')
    }
  }

  // Handle analysis completion
  const handleAnalysisComplete = (analysisResult: any) => {
    setAnalysis(analysisResult)
    setCurrentView('review')
  }

  // Handle correction save (Data Flywheel)
  const handleCorrectionSaved = () => {
    // Move to next trade or back to upload
    const currentIndex = trades.findIndex(t => t.id === selectedTrade?.id)
    if (currentIndex < trades.length - 1) {
      setSelectedTrade(trades[currentIndex + 1])
      setCurrentView('analyze')
    } else {
      setCurrentView('upload')
      setTrades([])
      setSelectedTrade(null)
      setAnalysis(null)
    }
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-iron-800 bg-iron-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <Shield className="w-8 h-8 text-blue-500" />
              <div>
                <h1 className="text-xl font-bold text-gradient">IronShell</h1>
                <p className="text-xs text-gray-500">Defensible AI Trading</p>
              </div>
            </div>

            {/* Navigation */}
            <nav className="flex items-center gap-2">
              <NavButton
                icon={<Upload className="w-4 h-4" />}
                label="Upload"
                active={currentView === 'upload'}
                onClick={() => setCurrentView('upload')}
              />
              <NavButton
                icon={<Brain className="w-4 h-4" />}
                label="Analyze"
                active={currentView === 'analyze'}
                onClick={() => setCurrentView('analyze')}
                disabled={!selectedTrade}
              />
              <NavButton
                icon={<CheckCircle className="w-4 h-4" />}
                label="Review"
                active={currentView === 'review'}
                onClick={() => setCurrentView('review')}
                disabled={!analysis}
              />
            </nav>

            {/* Flywheel Status */}
            <FlywheelStats compact />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Progress Indicator */}
        <div className="mb-8">
          <WorkflowProgress
            currentStep={currentView}
            tradesCount={trades.length}
          />
        </div>

        {/* View Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Panel */}
          <div className="lg:col-span-2">
            {currentView === 'upload' && (
              <FileUploader onUploadComplete={handleUploadComplete} />
            )}

            {currentView === 'analyze' && selectedTrade && (
              <SmartEditor
                trade={selectedTrade}
                onAnalysisComplete={handleAnalysisComplete}
              />
            )}

            {currentView === 'review' && analysis && (
              <SmartEditor
                trade={selectedTrade}
                analysis={analysis}
                editMode
                onCorrectionSaved={handleCorrectionSaved}
              />
            )}
          </div>

          {/* Side Panel */}
          <div className="space-y-6">
            {/* Guardrails Panel */}
            <GuardrailPanel
              trade={selectedTrade}
              analysis={analysis}
            />

            {/* Trade List */}
            {trades.length > 0 && (
              <div className="card p-4">
                <h3 className="text-sm font-medium text-gray-400 mb-3">
                  Uploaded Trades ({trades.length})
                </h3>
                <TradeList
                  trades={trades}
                  selectedId={selectedTrade?.id}
                  onSelect={(trade) => {
                    setSelectedTrade(trade)
                    setAnalysis(null)
                    setCurrentView('analyze')
                  }}
                />
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-iron-800 mt-16 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center text-sm text-gray-500">
            <p className="mb-2">
              <span className="text-gradient font-medium">Iron Shell Strategy:</span>
              {' '}"Your AI is a commodity. Your DATA is your moat."
            </p>
            <p>
              Every correction you make trains your AI and builds your competitive advantage.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// HELPER COMPONENTS
// ══════════════════════════════════════════════════════════════════════════════

function NavButton({
  icon,
  label,
  active,
  disabled,
  onClick,
}: {
  icon: React.ReactNode
  label: string
  active: boolean
  disabled?: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`
        flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium
        transition-all duration-200
        ${active
          ? 'bg-blue-600 text-white'
          : disabled
            ? 'text-gray-600 cursor-not-allowed'
            : 'text-gray-400 hover:text-white hover:bg-iron-800'
        }
      `}
    >
      {icon}
      {label}
    </button>
  )
}

function WorkflowProgress({
  currentStep,
  tradesCount,
}: {
  currentStep: View
  tradesCount: number
}) {
  const steps = [
    {
      id: 'upload',
      label: 'Upload Data',
      description: 'Import your broker statements',
      icon: Upload,
    },
    {
      id: 'analyze',
      label: 'AI Analysis',
      description: 'Review AI-generated insights',
      icon: Brain,
    },
    {
      id: 'review',
      label: 'Correct & Save',
      description: 'Your corrections train the AI',
      icon: RefreshCw,
    },
  ]

  const currentIndex = steps.findIndex(s => s.id === currentStep)

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between">
        {steps.map((step, index) => (
          <div key={step.id} className="flex items-center">
            {/* Step */}
            <div className="flex items-center gap-3">
              <div
                className={`
                  w-10 h-10 rounded-full flex items-center justify-center
                  transition-all duration-300
                  ${index < currentIndex
                    ? 'bg-success-500 text-white'
                    : index === currentIndex
                      ? 'bg-blue-600 text-white glow-blue'
                      : 'bg-iron-800 text-gray-500'
                  }
                `}
              >
                {index < currentIndex ? (
                  <CheckCircle className="w-5 h-5" />
                ) : (
                  <step.icon className="w-5 h-5" />
                )}
              </div>
              <div>
                <p className={`text-sm font-medium ${
                  index === currentIndex ? 'text-white' : 'text-gray-400'
                }`}>
                  {step.label}
                </p>
                <p className="text-xs text-gray-500">{step.description}</p>
              </div>
            </div>

            {/* Connector */}
            {index < steps.length - 1 && (
              <div
                className={`
                  w-20 h-0.5 mx-4
                  ${index < currentIndex ? 'bg-success-500' : 'bg-iron-800'}
                `}
              />
            )}
          </div>
        ))}
      </div>

      {/* Info Banner */}
      {currentStep === 'review' && (
        <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
          <div className="flex items-center gap-2 text-blue-400 text-sm">
            <Brain className="w-4 h-4" />
            <span>
              <strong>Data Flywheel Active:</strong>
              {' '}Your corrections will make the AI smarter for similar future trades.
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
