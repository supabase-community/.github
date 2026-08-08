/**
 * ╔══════════════════════════════════════════════════════════════════════════════╗
 * ║                    FILE UPLOADER - MOMENT OF TRUTH                           ║
 * ║                                                                              ║
 * ║  IRON SHELL PRINCIPLE: "Meet users where they are"                           ║
 * ║  Users have messy broker statements. Accept them gracefully.                 ║
 * ╚══════════════════════════════════════════════════════════════════════════════╝
 */

'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import {
  Upload,
  FileSpreadsheet,
  AlertCircle,
  CheckCircle,
  Loader2,
  HelpCircle,
} from 'lucide-react'
import toast from 'react-hot-toast'

import type { IngestionResult, ParsedTrade } from '@/types'
import { uploadFile, uploadFileWithMapping } from '@/lib/api'

interface FileUploaderProps {
  onUploadComplete: (trades: ParsedTrade[]) => void
}

export function FileUploader({ onUploadComplete }: FileUploaderProps) {
  const [isUploading, setIsUploading] = useState(false)
  const [result, setResult] = useState<IngestionResult | null>(null)
  const [showMapping, setShowMapping] = useState(false)
  const [columnMapping, setColumnMapping] = useState<Record<string, string>>({})

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return

    const file = acceptedFiles[0]
    setIsUploading(true)
    setResult(null)

    try {
      const ingestionResult = await uploadFile(file)
      setResult(ingestionResult)

      if (ingestionResult.success && ingestionResult.trades.length > 0) {
        toast.success(`Parsed ${ingestionResult.parsed_rows} trades!`)
        onUploadComplete(ingestionResult.trades)
      } else if (ingestionResult.requires_user_input) {
        setShowMapping(true)
        setColumnMapping(ingestionResult.column_mapping || {})
        toast.error('Need clarification on some columns')
      } else {
        toast.error('Failed to parse trades')
      }
    } catch (error) {
      toast.error(`Upload failed: ${error}`)
    } finally {
      setIsUploading(false)
    }
  }, [onUploadComplete])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/pdf': ['.pdf'],
    },
    multiple: false,
    disabled: isUploading,
  })

  const handleMappingSubmit = async () => {
    if (!result) return

    setIsUploading(true)
    try {
      // Re-upload with explicit mapping
      // In a real implementation, you'd have the file cached
      toast.error('Please re-upload the file with the corrected mapping')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="card">
      {/* Header */}
      <div className="p-4 border-b border-iron-800">
        <div className="flex items-center gap-3">
          <Upload className="w-5 h-5 text-blue-500" />
          <div>
            <h2 className="font-semibold">Upload Trading Data</h2>
            <p className="text-sm text-gray-400">
              Import broker statements or trade exports
            </p>
          </div>
        </div>
      </div>

      {/* Dropzone */}
      <div className="p-6">
        <div
          {...getRootProps()}
          className={`
            border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
            transition-all duration-200
            ${isDragActive
              ? 'border-blue-500 bg-blue-500/10'
              : 'border-iron-700 hover:border-iron-600 hover:bg-iron-800/50'
            }
            ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}
          `}
        >
          <input {...getInputProps()} />

          {isUploading ? (
            <div className="flex flex-col items-center">
              <Loader2 className="w-12 h-12 text-blue-500 animate-spin" />
              <p className="mt-4 text-gray-300">Processing file...</p>
            </div>
          ) : isDragActive ? (
            <div className="flex flex-col items-center">
              <FileSpreadsheet className="w-12 h-12 text-blue-500" />
              <p className="mt-4 text-gray-300">Drop the file here</p>
            </div>
          ) : (
            <div className="flex flex-col items-center">
              <Upload className="w-12 h-12 text-gray-500" />
              <p className="mt-4 text-gray-300">
                Drag & drop your file here, or click to browse
              </p>
              <p className="mt-2 text-sm text-gray-500">
                Supports CSV, Excel (.xlsx, .xls), and PDF
              </p>
            </div>
          )}
        </div>

        {/* Result Display */}
        {result && (
          <div className="mt-6 space-y-4">
            {/* Success */}
            {result.success && result.trades.length > 0 && (
              <div className="p-4 bg-success-500/10 border border-success-500/30 rounded-lg">
                <div className="flex items-center gap-2 text-success-500">
                  <CheckCircle className="w-5 h-5" />
                  <span className="font-medium">
                    Successfully parsed {result.parsed_rows} of {result.total_rows} trades
                  </span>
                </div>
              </div>
            )}

            {/* Warnings */}
            {result.warnings.length > 0 && (
              <div className="p-4 bg-warning-500/10 border border-warning-500/30 rounded-lg">
                <div className="flex items-start gap-2 text-warning-500">
                  <AlertCircle className="w-5 h-5 mt-0.5" />
                  <div>
                    <span className="font-medium">Warnings:</span>
                    <ul className="mt-1 text-sm list-disc list-inside">
                      {result.warnings.map((w, i) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* User Questions */}
            {result.requires_user_input && result.user_questions.length > 0 && (
              <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                <div className="flex items-start gap-2 text-blue-400">
                  <HelpCircle className="w-5 h-5 mt-0.5" />
                  <div>
                    <span className="font-medium">Need clarification:</span>
                    <ul className="mt-1 text-sm list-disc list-inside">
                      {result.user_questions.map((q, i) => (
                        <li key={i}>{q}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Errors */}
            {result.errors.length > 0 && (
              <div className="p-4 bg-danger-500/10 border border-danger-500/30 rounded-lg">
                <div className="flex items-start gap-2 text-danger-500">
                  <AlertCircle className="w-5 h-5 mt-0.5" />
                  <div>
                    <span className="font-medium">Errors:</span>
                    <ul className="mt-1 text-sm">
                      {result.errors.slice(0, 5).map((e, i) => (
                        <li key={i} className="mt-1">
                          <span className="font-medium">{e.type}:</span> {e.message}
                          {e.suggestion && (
                            <span className="text-gray-400 block ml-4">
                              Suggestion: {e.suggestion}
                            </span>
                          )}
                        </li>
                      ))}
                      {result.errors.length > 5 && (
                        <li className="text-gray-400">
                          ...and {result.errors.length - 5} more errors
                        </li>
                      )}
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Supported Formats */}
        <div className="mt-6 text-sm text-gray-500">
          <p className="font-medium text-gray-400">Supported formats:</p>
          <ul className="mt-2 grid grid-cols-2 gap-2">
            <li className="flex items-center gap-2">
              <FileSpreadsheet className="w-4 h-4" />
              CSV (comma-separated)
            </li>
            <li className="flex items-center gap-2">
              <FileSpreadsheet className="w-4 h-4" />
              Excel (.xlsx, .xls)
            </li>
            <li className="flex items-center gap-2">
              <FileSpreadsheet className="w-4 h-4" />
              PDF (broker statements)
            </li>
          </ul>
          <p className="mt-3">
            We support exports from Interactive Brokers, TD Ameritrade, Robinhood,
            Fidelity, E*TRADE, and generic CSV formats.
          </p>
        </div>
      </div>
    </div>
  )
}
