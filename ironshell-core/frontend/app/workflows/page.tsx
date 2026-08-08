/**
 * ╔══════════════════════════════════════════════════════════════════════════════╗
 * ║                    WORKFLOWS PAGE - N8N AUTOMATION BROWSER                   ║
 * ║                                                                              ║
 * ║  IRON SHELL EXTENSION:                                                       ║
 * ║  Browse and manage N8N workflow automations integrated with trading.         ║
 * ╚══════════════════════════════════════════════════════════════════════════════╝
 */

'use client'

import { useState } from 'react'
import Link from 'next/link'
import {
  ArrowLeft,
  Workflow,
  Shield,
} from 'lucide-react'
import toast from 'react-hot-toast'

import { WorkflowList } from '@/components/WorkflowList'
import { WorkflowViewer } from '@/components/WorkflowViewer'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function WorkflowsPage() {
  const [selectedWorkflow, setSelectedWorkflow] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const handleSelectWorkflow = async (filename: string) => {
    setLoading(true)
    try {
      const response = await fetch(`${API_URL}/api/v1/workflows/${filename}`)
      if (!response.ok) throw new Error('Failed to load workflow')

      const data = await response.json()
      setSelectedWorkflow(data)
    } catch (error) {
      toast.error('Failed to load workflow details')
      console.error(error)
    } finally {
      setLoading(false)
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
              <Link href="/" className="flex items-center gap-3 hover:opacity-80">
                <Shield className="w-8 h-8 text-blue-500" />
                <div>
                  <h1 className="text-xl font-bold text-gradient">IronShell</h1>
                  <p className="text-xs text-gray-500">Workflow Automation</p>
                </div>
              </Link>
            </div>

            {/* Navigation */}
            <nav className="flex items-center gap-2">
              <Link
                href="/"
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-gray-400 hover:text-white hover:bg-iron-800 transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to Dashboard
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Workflow className="w-8 h-8 text-blue-500" />
            <h1 className="text-2xl font-bold">Workflow Automation</h1>
          </div>
          <p className="text-gray-400">
            Browse, search, and manage N8N workflow automations. Link workflows to
            your trading strategies for automated execution.
          </p>
        </div>

        {/* Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Workflow List */}
          <div className={selectedWorkflow ? 'lg:col-span-1' : 'lg:col-span-3'}>
            <WorkflowList onSelectWorkflow={handleSelectWorkflow} />
          </div>

          {/* Workflow Detail */}
          {selectedWorkflow && (
            <div className="lg:col-span-2">
              {loading ? (
                <div className="card p-8 text-center">
                  <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto" />
                  <p className="mt-4 text-gray-400">Loading workflow...</p>
                </div>
              ) : (
                <WorkflowViewer
                  workflow={selectedWorkflow}
                  onClose={() => setSelectedWorkflow(null)}
                />
              )}
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-iron-800 mt-16 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center text-sm text-gray-500">
            <p className="mb-2">
              <span className="text-gradient font-medium">Iron Shell Strategy:</span>
              {' '}Automate your trading workflows while maintaining guardrails.
            </p>
            <p>
              Workflows integrate with the Data Flywheel for continuous improvement.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
