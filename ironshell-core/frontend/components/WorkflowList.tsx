/**
 * ╔══════════════════════════════════════════════════════════════════════════════╗
 * ║                    WORKFLOW LIST - SEARCHABLE WORKFLOW BROWSER              ║
 * ║                                                                              ║
 * ║  IRON SHELL EXTENSION:                                                       ║
 * ║  Browse, search, and filter N8N workflows with documentation.                ║
 * ╚══════════════════════════════════════════════════════════════════════════════╝
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Search,
  Filter,
  Workflow,
  Zap,
  Layers,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Activity,
} from 'lucide-react'
import toast from 'react-hot-toast'

interface WorkflowSummary {
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

interface WorkflowListProps {
  onSelectWorkflow: (filename: string) => void
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function WorkflowList({ onSelectWorkflow }: WorkflowListProps) {
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [filters, setFilters] = useState({
    trigger: 'all',
    complexity: 'all',
    category: 'all',
    activeOnly: false,
  })
  const [pagination, setPagination] = useState({
    page: 1,
    perPage: 20,
    total: 0,
    pages: 0,
  })
  const [categories, setCategories] = useState<string[]>([])
  const [stats, setStats] = useState<any>(null)

  // Load categories
  useEffect(() => {
    fetch(`${API_URL}/api/v1/workflows/categories`)
      .then((res) => res.json())
      .then((data) => setCategories(data.categories || []))
      .catch(console.error)
  }, [])

  // Load stats
  useEffect(() => {
    fetch(`${API_URL}/api/v1/workflows/stats`)
      .then((res) => res.json())
      .then((data) => setStats(data))
      .catch(console.error)
  }, [])

  // Search workflows
  const searchWorkflows = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        q: searchQuery,
        trigger: filters.trigger,
        complexity: filters.complexity,
        category: filters.category,
        active_only: String(filters.activeOnly),
        page: String(pagination.page),
        per_page: String(pagination.perPage),
      })

      const response = await fetch(`${API_URL}/api/v1/workflows?${params}`)
      if (!response.ok) throw new Error('Failed to fetch workflows')

      const data = await response.json()
      setWorkflows(data.workflows)
      setPagination((prev) => ({
        ...prev,
        total: data.total,
        pages: data.pages,
      }))
    } catch (error) {
      toast.error('Failed to load workflows')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }, [searchQuery, filters, pagination.page, pagination.perPage])

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(searchWorkflows, 300)
    return () => clearTimeout(timer)
  }, [searchWorkflows])

  const handleFilterChange = (key: string, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
    setPagination((prev) => ({ ...prev, page: 1 }))
  }

  const complexityColors = {
    low: 'text-success-500 bg-success-500/20',
    medium: 'text-warning-500 bg-warning-500/20',
    high: 'text-danger-500 bg-danger-500/20',
    enterprise: 'text-danger-500 bg-danger-500/20',
  }

  return (
    <div className="space-y-6">
      {/* Stats Bar */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="card p-4">
            <div className="flex items-center gap-2 text-gray-400 text-sm">
              <Workflow className="w-4 h-4" />
              Total Workflows
            </div>
            <p className="text-2xl font-bold text-gradient mt-1">{stats.total}</p>
          </div>
          <div className="card p-4">
            <div className="flex items-center gap-2 text-gray-400 text-sm">
              <Activity className="w-4 h-4" />
              Active
            </div>
            <p className="text-2xl font-bold text-success-500 mt-1">{stats.active}</p>
          </div>
          <div className="card p-4">
            <div className="flex items-center gap-2 text-gray-400 text-sm">
              <Layers className="w-4 h-4" />
              Total Nodes
            </div>
            <p className="text-2xl font-bold text-blue-400 mt-1">{stats.total_nodes}</p>
          </div>
          <div className="card p-4">
            <div className="flex items-center gap-2 text-gray-400 text-sm">
              <Zap className="w-4 h-4" />
              Integrations
            </div>
            <p className="text-2xl font-bold text-purple-400 mt-1">
              {stats.unique_integrations}
            </p>
          </div>
        </div>
      )}

      {/* Search and Filters */}
      <div className="card p-4">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search Input */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value)
                setPagination((prev) => ({ ...prev, page: 1 }))
              }}
              placeholder="Search workflows..."
              className="input pl-10"
            />
          </div>

          {/* Filters */}
          <div className="flex gap-2 flex-wrap">
            <select
              value={filters.trigger}
              onChange={(e) => handleFilterChange('trigger', e.target.value)}
              className="input w-auto"
            >
              <option value="all">All Triggers</option>
              <option value="Webhook">Webhook</option>
              <option value="Schedule">Schedule</option>
              <option value="Manual">Manual</option>
              <option value="Email">Email</option>
            </select>

            <select
              value={filters.complexity}
              onChange={(e) => handleFilterChange('complexity', e.target.value)}
              className="input w-auto"
            >
              <option value="all">All Complexity</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="enterprise">Enterprise</option>
            </select>

            <select
              value={filters.category}
              onChange={(e) => handleFilterChange('category', e.target.value)}
              className="input w-auto"
            >
              <option value="all">All Categories</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>

            <label className="flex items-center gap-2 px-3 py-2 bg-iron-800 rounded-lg cursor-pointer">
              <input
                type="checkbox"
                checked={filters.activeOnly}
                onChange={(e) => handleFilterChange('activeOnly', e.target.checked)}
                className="rounded"
              />
              <span className="text-sm">Active only</span>
            </label>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="space-y-4">
        {loading ? (
          <div className="card p-8 text-center">
            <RefreshCw className="w-8 h-8 mx-auto text-blue-500 animate-spin" />
            <p className="mt-2 text-gray-400">Loading workflows...</p>
          </div>
        ) : workflows.length === 0 ? (
          <div className="card p-8 text-center">
            <Workflow className="w-12 h-12 mx-auto text-gray-600" />
            <p className="mt-2 text-gray-400">No workflows found</p>
            <p className="text-sm text-gray-500 mt-1">
              Try adjusting your search or filters
            </p>
          </div>
        ) : (
          <>
            {/* Results count */}
            <p className="text-sm text-gray-400">
              Showing {workflows.length} of {pagination.total} workflows
            </p>

            {/* Workflow grid */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {workflows.map((workflow) => (
                <button
                  key={workflow.filename}
                  onClick={() => onSelectWorkflow(workflow.filename)}
                  className="card p-4 text-left hover:border-blue-500/50 transition-all duration-200"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <div
                        className={`p-1.5 rounded ${
                          workflow.active
                            ? 'bg-success-500/20'
                            : 'bg-gray-500/20'
                        }`}
                      >
                        <Workflow
                          className={`w-4 h-4 ${
                            workflow.active ? 'text-success-500' : 'text-gray-400'
                          }`}
                        />
                      </div>
                      <div>
                        <h3 className="font-medium text-sm truncate max-w-[200px]">
                          {workflow.name}
                        </h3>
                        <p className="text-xs text-gray-500">{workflow.filename}</p>
                      </div>
                    </div>
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${
                        complexityColors[
                          workflow.complexity as keyof typeof complexityColors
                        ] || 'bg-gray-500/20 text-gray-400'
                      }`}
                    >
                      {workflow.complexity}
                    </span>
                  </div>

                  {workflow.description && (
                    <p className="mt-2 text-xs text-gray-400 line-clamp-2">
                      {workflow.description}
                    </p>
                  )}

                  <div className="mt-3 flex items-center gap-2 flex-wrap">
                    <span className="text-xs px-2 py-0.5 bg-iron-800 rounded text-gray-300">
                      {workflow.trigger_type}
                    </span>
                    <span className="text-xs px-2 py-0.5 bg-iron-800 rounded text-gray-300">
                      {workflow.node_count} nodes
                    </span>
                    {workflow.integrations.slice(0, 2).map((int) => (
                      <span
                        key={int}
                        className="text-xs px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded"
                      >
                        {int}
                      </span>
                    ))}
                    {workflow.integrations.length > 2 && (
                      <span className="text-xs text-gray-500">
                        +{workflow.integrations.length - 2}
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>

            {/* Pagination */}
            {pagination.pages > 1 && (
              <div className="flex items-center justify-center gap-2">
                <button
                  onClick={() =>
                    setPagination((prev) => ({
                      ...prev,
                      page: Math.max(1, prev.page - 1),
                    }))
                  }
                  disabled={pagination.page === 1}
                  className="btn-secondary p-2 disabled:opacity-50"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-sm text-gray-400">
                  Page {pagination.page} of {pagination.pages}
                </span>
                <button
                  onClick={() =>
                    setPagination((prev) => ({
                      ...prev,
                      page: Math.min(prev.pages, prev.page + 1),
                    }))
                  }
                  disabled={pagination.page === pagination.pages}
                  className="btn-secondary p-2 disabled:opacity-50"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
