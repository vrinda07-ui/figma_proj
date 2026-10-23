import React, { useState, useEffect } from 'react'
import { Clock, FileText, Eye, ChevronRight, AlertCircle } from 'lucide-react'
import { HistoryEntry, HistoryRunDetails } from '../types'
import { fetchHistory, fetchHistoryRun, fetchHistoryJson, getHistoryDownloadUrl } from '../services/api'
import { JsonViewerModal } from './JsonViewerModal'

type JsonType = 'figma_data' | 'raw_predictions' | 'clean_predictions' | 'grid_layout' | 'page_json'

const jsonTypeLabels: Record<JsonType, string> = {
  figma_data: 'Figma Data',
  raw_predictions: 'Raw Predictions',
  clean_predictions: 'Clean Predictions',
  grid_layout: 'Grid Layout',
  page_json: 'Page JSON'
}

export const HistoryView: React.FC = () => {
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedRun, setSelectedRun] = useState<HistoryRunDetails | null>(null)
  const [jsonModalOpen, setJsonModalOpen] = useState(false)
  const [jsonModalData, setJsonModalData] = useState<any>(null)
  const [jsonModalTitle, setJsonModalTitle] = useState('')
  const [jsonModalFilename, setJsonModalFilename] = useState('')

  useEffect(() => {
    loadHistory()
  }, [])

  const loadHistory = async () => {
    try {
      setIsLoading(true)
      const data = await fetchHistory()
      setHistory(data.runs)
      setError(null)
    } catch (err: any) {
      setError('Failed to load history')
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleString()
  }

  const handleViewRun = async (runId: string) => {
    try {
      const details = await fetchHistoryRun(runId)
      setSelectedRun(details)
    } catch (err: any) {
      console.error('Failed to load run details', err)
    }
  }

  const handleViewJson = async (runId: string, jsonType: JsonType) => {
    try {
      const data = await fetchHistoryJson(runId, jsonType)
      setJsonModalData(data)
      setJsonModalTitle(`${jsonTypeLabels[jsonType]} - ${runId}`)
      setJsonModalFilename(`${runId}_${jsonType}.json`)
      setJsonModalOpen(true)
    } catch (err: any) {
      console.error('Failed to load JSON', err)
    }
  }

  const handleDownloadJson = (runId: string, jsonType: JsonType) => {
    const url = getHistoryDownloadUrl(runId, jsonType)
    window.open(url, '_blank')
  }

  const handleJsonModalDownload = () => {
    const jsonString = JSON.stringify(jsonModalData, null, 2)
    const blob = new Blob([jsonString], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = jsonModalFilename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-slate-500">Loading history...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex items-center gap-2 text-rose-600">
          <AlertCircle className="w-5 h-5" />
          {error}
        </div>
      </div>
    )
  }

  if (history.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Clock className="w-12 h-12 text-slate-300 mb-4" />
        <h3 className="text-lg font-medium text-slate-700 mb-2">No history yet</h3>
        <p className="text-sm text-slate-500">
          Process a design to see it appear here.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* History List */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200">
        <div className="p-6 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-800">Processing History</h2>
          <p className="text-sm text-slate-500 mt-1">
            {history.length} {history.length === 1 ? 'run' : 'runs'} recorded
          </p>
        </div>
        <div className="divide-y divide-slate-200">
          {history.map((entry) => (
            <div
              key={entry.runId}
              className="p-4 hover:bg-slate-50 transition-colors cursor-pointer"
              onClick={() => handleViewRun(entry.runId)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                    <FileText className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="font-medium text-slate-800">{entry.designName}</h3>
                    <p className="text-sm text-slate-500">{formatDate(entry.timestamp)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <p className="text-sm font-medium text-slate-700">{entry.widgetCount} widgets</p>
                    <p className="text-xs text-slate-500">{entry.tileCount} tiles</p>
                  </div>
                  {entry.needAttention > 0 && (
                    <div className="text-right">
                      <p className="text-sm font-medium text-amber-600">{entry.needAttention}</p>
                      <p className="text-xs text-slate-500">need review</p>
                    </div>
                  )}
                  <ChevronRight className="w-5 h-5 text-slate-400" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Selected Run Details */}
      {selectedRun && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200">
          <div className="p-6 border-b border-slate-200">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-slate-800">{selectedRun.designName}</h2>
                <p className="text-sm text-slate-500">Run ID: {selectedRun.runId}</p>
              </div>
              <button
                onClick={() => setSelectedRun(null)}
                className="text-sm text-slate-500 hover:text-slate-700"
              >
                Close
              </button>
            </div>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-4 gap-4 mb-6">
              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-2xl font-bold text-slate-800">{selectedRun.componentCount}</p>
                <p className="text-xs text-slate-500">Components</p>
              </div>
              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-2xl font-bold text-slate-800">{selectedRun.widgetCount}</p>
                <p className="text-xs text-slate-500">Widgets</p>
              </div>
              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-2xl font-bold text-slate-800">{selectedRun.tileCount}</p>
                <p className="text-xs text-slate-500">Tiles</p>
              </div>
              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-2xl font-bold text-slate-800">{selectedRun.needAttention}</p>
                <p className="text-xs text-slate-500">Need Review</p>
              </div>
            </div>

            <h3 className="text-sm font-medium text-slate-700 mb-4">Available Outputs</h3>
            <div className="grid grid-cols-2 gap-3">
              {(Object.keys(selectedRun.availableOutputs) as JsonType[]).map((jsonType) => {
                const available = selectedRun.availableOutputs[jsonType]
                return (
                  <div
                    key={jsonType}
                    className={`flex items-center justify-between p-3 rounded-lg border ${
                      available
                        ? 'bg-white border-slate-200'
                        : 'bg-slate-50 border-slate-200 opacity-50'
                    }`}
                  >
                    <span className="text-sm font-medium text-slate-700">
                      {jsonTypeLabels[jsonType]}
                    </span>
                    {available ? (
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleViewJson(selectedRun.runId, jsonType)}
                          className="flex items-center gap-1 px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        >
                          <Eye className="w-4 h-4" />
                          View
                        </button>
                        <button
                          onClick={() => handleDownloadJson(selectedRun.runId, jsonType)}
                          className="flex items-center gap-1 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                        >
                          Download
                        </button>
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400">Not available</span>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* JSON Viewer Modal */}
      <JsonViewerModal
        isOpen={jsonModalOpen}
        onClose={() => setJsonModalOpen(false)}
        title={jsonModalTitle}
        jsonData={jsonModalData}
        onDownload={handleJsonModalDownload}
        downloadFilename={jsonModalFilename}
      />
    </div>
  )
}
