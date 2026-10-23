import React, { useState } from 'react'
import { X, Download, Copy, CheckCircle2, AlertCircle } from 'lucide-react'

interface JsonViewerModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  jsonData: any
  onDownload?: () => void
  downloadFilename?: string
}

export const JsonViewerModal: React.FC<JsonViewerModalProps> = ({
  isOpen,
  onClose,
  title,
  jsonData,
  onDownload,
  downloadFilename
}) => {
  const [copied, setCopied] = useState(false)
  const [copyError, setCopyError] = useState<string | null>(null)

  const handleCopy = async () => {
    try {
      const jsonString = JSON.stringify(jsonData, null, 2)
      await navigator.clipboard.writeText(jsonString)
      setCopied(true)
      setCopyError(null)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      setCopyError('Failed to copy to clipboard')
      setTimeout(() => setCopyError(null), 3000)
    }
  }

  const handleDownload = () => {
    if (onDownload) {
      onDownload()
    } else if (downloadFilename) {
      const jsonString = JSON.stringify(jsonData, null, 2)
      const blob = new Blob([jsonString], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = downloadFilename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col m-4">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800">{title}</h3>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 p-4 border-b border-slate-200 bg-slate-50">
          <button
            onClick={handleCopy}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-300 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors"
          >
            {copied ? (
              <>
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="w-4 h-4 text-slate-600" />
                Copy JSON
              </>
            )}
          </button>
          <button
            onClick={handleDownload}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 text-white rounded-lg text-sm font-medium hover:bg-slate-900 transition-colors"
          >
            <Download className="w-4 h-4" />
            Download JSON
          </button>
          {copyError && (
            <div className="flex items-center gap-2 text-sm text-rose-600 ml-auto">
              <AlertCircle className="w-4 h-4" />
              {copyError}
            </div>
          )}
        </div>

        {/* JSON Content */}
        <div className="flex-1 overflow-auto p-4 bg-slate-900">
          <pre className="text-sm text-slate-100 font-mono whitespace-pre-wrap">
            {JSON.stringify(jsonData, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  )
}
