/**
 * ╔══════════════════════════════════════════════════════════════════════════════╗
 * ║                    WORKFLOW VIEWER - N8N VISUALIZATION                       ║
 * ║                                                                              ║
 * ║  IRON SHELL EXTENSION:                                                       ║
 * ║  Displays workflow diagrams and documentation with Mermaid.js               ║
 * ╚══════════════════════════════════════════════════════════════════════════════╝
 */

'use client'

import { useState, useEffect, useRef } from 'react'
import {
  Play,
  Pause,
  Download,
  Copy,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Workflow,
  Zap,
  Clock,
  Layers,
  Tag,
} from 'lucide-react'
import toast from 'react-hot-toast'

interface WorkflowMetadata {
  id?: number
  filename: string
  name: string
  active: boolean
  description: string
  trigger_type: string
  complexity: string
  node_count: number
  integrations: string[]
  tags: string[]
  category: string
}

interface WorkflowViewerProps {
  workflow: {
    metadata: WorkflowMetadata
    raw_json: Record<string, any>
    diagram?: string
  }
  onClose?: () => void
}

export function WorkflowViewer({ workflow, onClose }: WorkflowViewerProps) {
  const [showRawJson, setShowRawJson] = useState(false)
  const [diagramRendered, setDiagramRendered] = useState(false)
  const diagramRef = useRef<HTMLDivElement>(null)

  const { metadata, raw_json, diagram } = workflow

  // Render Mermaid diagram
  useEffect(() => {
    if (diagram && diagramRef.current && !diagramRendered) {
      // Dynamically import mermaid to avoid SSR issues
      import('mermaid').then((mermaid) => {
        mermaid.default.initialize({
          startOnLoad: false,
          theme: 'dark',
          themeVariables: {
            primaryColor: '#3b82f6',
            primaryTextColor: '#fff',
            primaryBorderColor: '#60a5fa',
            lineColor: '#6b7280',
            secondaryColor: '#1e293b',
            tertiaryColor: '#334155',
          },
        })

        try {
          const id = `mermaid-${Date.now()}`
          mermaid.default.render(id, diagram).then((result) => {
            if (diagramRef.current) {
              diagramRef.current.innerHTML = result.svg
              setDiagramRendered(true)
            }
          })
        } catch (error) {
          console.error('Mermaid rendering error:', error)
          if (diagramRef.current) {
            diagramRef.current.innerHTML = `<pre class="text-sm text-gray-400">${diagram}</pre>`
          }
        }
      })
    }
  }, [diagram, diagramRendered])

  const handleCopyJson = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(raw_json, null, 2))
      toast.success('JSON copied to clipboard')
    } catch {
      toast.error('Failed to copy')
    }
  }

  const handleDownload = () => {
    const blob = new Blob([JSON.stringify(raw_json, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = metadata.filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    toast.success('Workflow downloaded')
  }

  const complexityColors = {
    low: 'badge-success',
    medium: 'badge-warning',
    high: 'badge-danger',
    enterprise: 'badge-danger',
  }

  return (
    <div className="card">
      {/* Header */}
      <div className="p-4 border-b border-iron-800">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${
              metadata.active ? 'bg-success-500/20' : 'bg-gray-500/20'
            }`}>
              <Workflow className={`w-5 h-5 ${
                metadata.active ? 'text-success-500' : 'text-gray-400'
              }`} />
            </div>
            <div>
              <h2 className="font-semibold text-lg">{metadata.name}</h2>
              <p className="text-sm text-gray-400">{metadata.filename}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopyJson}
              className="btn-secondary p-2"
              title="Copy JSON"
            >
              <Copy className="w-4 h-4" />
            </button>
            <button
              onClick={handleDownload}
              className="btn-secondary p-2"
              title="Download"
            >
              <Download className="w-4 h-4" />
            </button>
            {onClose && (
              <button onClick={onClose} className="btn-secondary p-2">
                Close
              </button>
            )}
          </div>
        </div>

        {/* Description */}
        {metadata.description && (
          <p className="mt-3 text-sm text-gray-300">{metadata.description}</p>
        )}

        {/* Metadata badges */}
        <div className="mt-4 flex flex-wrap gap-2">
          <span className={`badge ${metadata.active ? 'badge-success' : 'badge-warning'}`}>
            {metadata.active ? 'Active' : 'Inactive'}
          </span>

          <span className="badge badge-info flex items-center gap-1">
            <Zap className="w-3 h-3" />
            {metadata.trigger_type}
          </span>

          <span className={`badge ${complexityColors[metadata.complexity as keyof typeof complexityColors] || 'badge-info'}`}>
            {metadata.complexity} complexity
          </span>

          <span className="badge badge-info flex items-center gap-1">
            <Layers className="w-3 h-3" />
            {metadata.node_count} nodes
          </span>
        </div>

        {/* Integrations */}
        {metadata.integrations.length > 0 && (
          <div className="mt-3">
            <p className="text-xs text-gray-500 mb-1">Integrations:</p>
            <div className="flex flex-wrap gap-1">
              {metadata.integrations.map((integration) => (
                <span
                  key={integration}
                  className="px-2 py-0.5 text-xs bg-iron-800 rounded text-gray-300"
                >
                  {integration}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Tags */}
        {metadata.tags.length > 0 && (
          <div className="mt-2">
            <div className="flex flex-wrap gap-1">
              {metadata.tags.map((tag) => (
                <span
                  key={tag}
                  className="px-2 py-0.5 text-xs bg-blue-500/20 text-blue-400 rounded flex items-center gap-1"
                >
                  <Tag className="w-3 h-3" />
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Diagram */}
      {diagram && (
        <div className="p-4 border-b border-iron-800">
          <h3 className="text-sm font-medium text-gray-400 mb-3">
            Workflow Diagram
          </h3>
          <div
            ref={diagramRef}
            className="bg-iron-800 rounded-lg p-4 overflow-x-auto"
          >
            <div className="text-gray-400 text-sm">Loading diagram...</div>
          </div>
        </div>
      )}

      {/* Raw JSON Section */}
      <div className="p-4">
        <button
          onClick={() => setShowRawJson(!showRawJson)}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
        >
          {showRawJson ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
          {showRawJson ? 'Hide' : 'Show'} Raw JSON
        </button>

        {showRawJson && (
          <div className="mt-3">
            <pre className="bg-iron-800 rounded-lg p-4 overflow-x-auto text-xs text-gray-300 max-h-96">
              {JSON.stringify(raw_json, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}
