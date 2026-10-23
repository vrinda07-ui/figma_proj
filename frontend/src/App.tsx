import React, { useState, useEffect } from 'react'
import { Navbar } from './components/Navbar'
import { LiveDashboardPreview } from './components/LiveDashboardPreview'
import { StudentGuideView } from './components/StudentGuideView'
import { HistoryView } from './components/HistoryView'
import { JsonViewerModal } from './components/JsonViewerModal'
import {
  fetchBackendStatus,
  loadPluginData,
  runNormalize,
  runPreprocess,
  runClassify,
  runGenerateLayout,
  getDownloadPageUrl
} from './services/api'
import { BackendStatus, PackageDetails, PipelineResult } from './types'
import { AlertCircle, CheckCircle2, X, Upload, Play, Download, RefreshCw, Eye } from 'lucide-react'

type StageStatus = 'pending' | 'in_progress' | 'completed' | 'error'

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'workspace' | 'preview' | 'guide' | 'history'>('workspace')
  const [backendStatus, setBackendStatus] = useState<BackendStatus | null>(null)
  const [isConnecting, setIsConnecting] = useState(true)

  // Pipeline stage statuses
  const [stageStatus, setStageStatus] = useState<Record<string, StageStatus>>({
    plugin_received: 'pending',
    normalize: 'pending',
    preprocess: 'pending',
    classify: 'pending',
    layout: 'pending'
  })

  // Active workspace state
  const [currentResult, setCurrentResult] = useState<PipelineResult | null>(null)
  const [currentFigmaJson, setCurrentFigmaJson] = useState<any>(null)
  const [designName, setDesignName] = useState<string>('')
  const [isLoading, setIsLoading] = useState(false)
  const [processingStage, setProcessingStage] = useState('')

  // Notifications
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  // JSON Viewer Modal
  const [jsonModalOpen, setJsonModalOpen] = useState(false)
  const [jsonModalData, setJsonModalData] = useState<any>(null)
  const [jsonModalTitle, setJsonModalTitle] = useState('')
  const [jsonModalFilename, setJsonModalFilename] = useState('')

  const showNotification = (message: string, type: 'success' | 'error' = 'success') => {
    setNotification({ type, message })
    setTimeout(() => setNotification(null), 5000)
  }

  // Load backend status and check plugin data
  useEffect(() => {
    const initialize = async () => {
      try {
        setIsConnecting(true)
        const status = await fetchBackendStatus()
        setBackendStatus(status)

        // Check if plugin has sent data
        if (status.pluginDataReceived) {
          setStageStatus(prev => ({ ...prev, plugin_received: 'completed' }))
          setDesignName(status.designName || 'Unknown Design')
        }
      } catch (err: any) {
        console.error('Backend connection failed:', err)
        showNotification('Could not connect to FastAPI backend. Ensure server.py is running.', 'error')
      } finally {
        setIsConnecting(false)
      }
    }

    initialize()
  }, [])

  // Load plugin data into workspace
  const handleLoadPluginData = async () => {
    setIsLoading(true)
    setProcessingStage('Loading design from Figma plugin...')
    try {
      const data = await loadPluginData()
      setCurrentFigmaJson(data.figmaJson)
      setDesignName(data.documentName)
      setStageStatus(prev => ({ ...prev, plugin_received: 'completed' }))
      showNotification(`Loaded design: ${data.documentName}`)
    } catch (err: any) {
      showNotification(err.message || 'Failed to load plugin data', 'error')
      setStageStatus(prev => ({ ...prev, plugin_received: 'error' }))
    } finally {
      setIsLoading(false)
      setProcessingStage('')
    }
  }

  // Run Normalize
  const handleNormalize = async () => {
    setIsLoading(true)
    setProcessingStage('Normalizing design data...')
    setStageStatus(prev => ({ ...prev, normalize: 'in_progress' }))
    try {
      const normRes = await runNormalize({ figmaJson: currentFigmaJson })
      setStageStatus(prev => ({ ...prev, normalize: 'completed' }))
      setDesignName(normRes.documentName)
      showNotification(`Normalized ${normRes.candidateCount} component candidates`)
    } catch (err: any) {
      setStageStatus(prev => ({ ...prev, normalize: 'error' }))
      showNotification(err.message || 'Normalization failed', 'error')
    } finally {
      setIsLoading(false)
      setProcessingStage('')
    }
  }

  // Run Preprocess
  const handlePreprocess = async () => {
    setIsLoading(true)
    setProcessingStage('Extracting features...')
    setStageStatus(prev => ({ ...prev, preprocess: 'in_progress' }))
    try {
      const prepRes = await runPreprocess({ figmaJson: currentFigmaJson })
      setStageStatus(prev => ({ ...prev, preprocess: 'completed' }))
      showNotification(`Extracted features for ${prepRes.candidateCount} components`)
    } catch (err: any) {
      setStageStatus(prev => ({ ...prev, preprocess: 'error' }))
      showNotification(err.message || 'Preprocessing failed', 'error')
    } finally {
      setIsLoading(false)
      setProcessingStage('')
    }
  }

  // Run Classify (XGBoost)
  const handleClassify = async () => {
    setIsLoading(true)
    setProcessingStage('Running XGBoost model...')
    setStageStatus(prev => ({ ...prev, classify: 'in_progress' }))
    try {
      const classRes = await runClassify({ figmaJson: currentFigmaJson })
      setStageStatus(prev => ({ ...prev, classify: 'completed' }))
      showNotification(`Classified ${classRes.candidateCount} components with XGBoost`)
    } catch (err: any) {
      setStageStatus(prev => ({ ...prev, classify: 'error' }))
      showNotification(err.message || 'Classification failed', 'error')
    } finally {
      setIsLoading(false)
      setProcessingStage('')
    }
  }

  // Generate Layout
  const handleGenerateLayout = async () => {
    setIsLoading(true)
    setProcessingStage('Generating 12x12 grid layout...')
    setStageStatus(prev => ({ ...prev, layout: 'in_progress' }))
    try {
      const layoutRes = await runGenerateLayout({ figmaJson: currentFigmaJson })
      setStageStatus(prev => ({ ...prev, layout: 'completed' }))
      setCurrentResult({
        success: true,
        designName: layoutRes.pageJson.title,
        contentId: layoutRes.pageJson.contentId,
        slideId: layoutRes.pageJson.slideId,
        pageId: layoutRes.pageJson.pageId,
        executionTimeMs: 0,
        sourceDimensions: { width: 0, height: 0 },
        nodeCount: 0,
        candidateCount: 0,
        sourceComponents: [],
        normalizedJson: { dashboard: '', candidate_count: 0, candidates: [] },
        classifierJson: { candidate_count: 0, predictions: [] },
        gridLayout: layoutRes.gridLayout,
        pageJson: layoutRes.pageJson,
        stats: layoutRes.stats,
        runId: layoutRes.runId
      })
      showNotification(`Generated dashboard with ${layoutRes.stats.widgets} widgets`)
    } catch (err: any) {
      setStageStatus(prev => ({ ...prev, layout: 'error' }))
      showNotification(err.message || 'Layout generation failed', 'error')
    } finally {
      setIsLoading(false)
      setProcessingStage('')
    }
  }

  // Download page.json
  const handleDownload = () => {
    window.open(getDownloadPageUrl(), '_blank')
  }

  // View JSON from current results
  const handleViewJson = (jsonData: any, title: string, filename: string) => {
    setJsonModalData(jsonData)
    setJsonModalTitle(title)
    setJsonModalFilename(filename)
    setJsonModalOpen(true)
  }

  // Handle JSON modal download
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

  // Check if stage can be executed
  const canRunStage = (stage: string) => {
    if (stage === 'normalize') return stageStatus.plugin_received === 'completed'
    if (stage === 'preprocess') return stageStatus.normalize === 'completed'
    if (stage === 'classify') return stageStatus.preprocess === 'completed'
    if (stage === 'layout') return stageStatus.classify === 'completed'
    return false
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      {/* Top Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        status={backendStatus}
        isConnecting={isConnecting}
        onAddDesign={() => {}}
      />

      {/* Floating Notification */}
      {notification && (
        <div className="fixed top-16 right-6 z-50 animate-in slide-in-from-top-2 duration-200">
          <div
            className={`flex items-center gap-2.5 px-4 py-3 rounded-xl shadow-lg border text-sm font-medium ${
              notification.type === 'error'
                ? 'bg-rose-50 border-rose-200 text-rose-800'
                : 'bg-emerald-50 border-emerald-200 text-emerald-800'
            }`}
          >
            {notification.type === 'error' ? (
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            ) : (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            )}
            <span>{notification.message}</span>
            <button
              onClick={() => setNotification(null)}
              className="ml-2 text-slate-400 hover:text-slate-600"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Main Tab Content */}
      <main className="flex-1 pb-16">
        {activeTab === 'workspace' && (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {/* Plugin Data Status */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-slate-800">Design Reception</h2>
                <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${
                  stageStatus.plugin_received === 'completed'
                    ? 'bg-emerald-100 text-emerald-700'
                    : stageStatus.plugin_received === 'error'
                    ? 'bg-rose-100 text-rose-700'
                    : 'bg-slate-100 text-slate-600'
                }`}>
                  {stageStatus.plugin_received === 'completed' && <CheckCircle2 className="w-4 h-4" />}
                  {stageStatus.plugin_received === 'error' && <AlertCircle className="w-4 h-4" />}
                  {stageStatus.plugin_received === 'completed'
                    ? 'Design received'
                    : stageStatus.plugin_received === 'error'
                    ? 'Error'
                    : 'Waiting for plugin'}
                </div>
              </div>
              {designName && (
                <p className="text-sm text-slate-600 mb-4">Current design: <span className="font-medium">{designName}</span></p>
              )}
              <button
                onClick={handleLoadPluginData}
                disabled={isLoading || stageStatus.plugin_received === 'completed'}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  stageStatus.plugin_received === 'completed'
                    ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                    : 'bg-blue-600 text-white hover:bg-blue-700 disabled:bg-slate-300 disabled:text-slate-500'
                }`}
              >
                <Upload className="w-4 h-4" />
                {stageStatus.plugin_received === 'completed' ? 'Design Loaded' : 'Load Plugin Data'}
              </button>
              {stageStatus.plugin_received === 'pending' && (
                <p className="text-xs text-slate-500 mt-2">Please send a design from the Figma plugin first</p>
              )}
            </div>

            {/* Pipeline Stages */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
              <h2 className="text-lg font-semibold text-slate-800 mb-6">Processing Pipeline</h2>
              
              <div className="space-y-4">
                {/* Normalize */}
                <div className="flex items-center justify-between p-4 rounded-lg border border-slate-200">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      stageStatus.normalize === 'completed' ? 'bg-emerald-100 text-emerald-600' :
                      stageStatus.normalize === 'in_progress' ? 'bg-blue-100 text-blue-600' :
                      stageStatus.normalize === 'error' ? 'bg-rose-100 text-rose-600' :
                      'bg-slate-100 text-slate-400'
                    }`}>
                      {stageStatus.normalize === 'completed' && <CheckCircle2 className="w-4 h-4" />}
                      {stageStatus.normalize === 'in_progress' && <RefreshCw className="w-4 h-4 animate-spin" />}
                      {stageStatus.normalize === 'error' && <AlertCircle className="w-4 h-4" />}
                      {stageStatus.normalize === 'pending' && <span className="text-sm font-medium">1</span>}
                    </div>
                    <div>
                      <p className="font-medium text-slate-800">Normalize</p>
                      <p className="text-xs text-slate-500">Extract component candidates</p>
                    </div>
                  </div>
                  <button
                    onClick={handleNormalize}
                    disabled={!canRunStage('normalize') || isLoading}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      canRunStage('normalize') && !isLoading
                        ? 'bg-blue-600 text-white hover:bg-blue-700'
                        : 'bg-slate-100 text-slate-400 cursor-not-allowed'
                    }`}
                  >
                    <Play className="w-4 h-4" />
                    Run
                  </button>
                </div>

                
                {/* Preprocess */}
                <div className="flex items-center justify-between p-4 rounded-lg border border-slate-200">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      stageStatus.preprocess === 'completed' ? 'bg-emerald-100 text-emerald-600' :
                      stageStatus.preprocess === 'in_progress' ? 'bg-blue-100 text-blue-600' :
                      stageStatus.preprocess === 'error' ? 'bg-rose-100 text-rose-600' :
                      'bg-slate-100 text-slate-400'
                    }`}>
                      {stageStatus.preprocess === 'completed' && <CheckCircle2 className="w-4 h-4" />}
                      {stageStatus.preprocess === 'in_progress' && <RefreshCw className="w-4 h-4 animate-spin" />}
                      {stageStatus.preprocess === 'error' && <AlertCircle className="w-4 h-4" />}
                      {stageStatus.preprocess === 'pending' && <span className="text-sm font-medium">2</span>}
                    </div>
                    <div>
                      <p className="font-medium text-slate-800">Preprocess</p>
                      <p className="text-xs text-slate-500">Extract features for ML model</p>
                    </div>
                  </div>
                  <button
                    onClick={handlePreprocess}
                    disabled={!canRunStage('preprocess') || isLoading}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      canRunStage('preprocess') && !isLoading
                        ? 'bg-blue-600 text-white hover:bg-blue-700'
                        : 'bg-slate-100 text-slate-400 cursor-not-allowed'
                    }`}
                  >
                    <Play className="w-4 h-4" />
                    Run
                  </button>
                </div>

                {/* Classify */}
                <div className="flex items-center justify-between p-4 rounded-lg border border-slate-200">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      stageStatus.classify === 'completed' ? 'bg-emerald-100 text-emerald-600' :
                      stageStatus.classify === 'in_progress' ? 'bg-blue-100 text-blue-600' :
                      stageStatus.classify === 'error' ? 'bg-rose-100 text-rose-600' :
                      'bg-slate-100 text-slate-400'
                    }`}>
                      {stageStatus.classify === 'completed' && <CheckCircle2 className="w-4 h-4" />}
                      {stageStatus.classify === 'in_progress' && <RefreshCw className="w-4 h-4 animate-spin" />}
                      {stageStatus.classify === 'error' && <AlertCircle className="w-4 h-4" />}
                      {stageStatus.classify === 'pending' && <span className="text-sm font-medium">3</span>}
                    </div>
                    <div>
                      <p className="font-medium text-slate-800">Run Model</p>
                      <p className="text-xs text-slate-500">XGBoost classification</p>
                    </div>
                  </div>
                  <button
                    onClick={handleClassify}
                    disabled={!canRunStage('classify') || isLoading}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      canRunStage('classify') && !isLoading
                        ? 'bg-blue-600 text-white hover:bg-blue-700'
                        : 'bg-slate-100 text-slate-400 cursor-not-allowed'
                    }`}
                  >
                    <Play className="w-4 h-4" />
                    Run
                  </button>
                </div>

                {/* Generate Layout */}
                <div className="flex items-center justify-between p-4 rounded-lg border border-slate-200">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      stageStatus.layout === 'completed' ? 'bg-emerald-100 text-emerald-600' :
                      stageStatus.layout === 'in_progress' ? 'bg-blue-100 text-blue-600' :
                      stageStatus.layout === 'error' ? 'bg-rose-100 text-rose-600' :
                      'bg-slate-100 text-slate-400'
                    }`}>
                      {stageStatus.layout === 'completed' && <CheckCircle2 className="w-4 h-4" />}
                      {stageStatus.layout === 'in_progress' && <RefreshCw className="w-4 h-4 animate-spin" />}
                      {stageStatus.layout === 'error' && <AlertCircle className="w-4 h-4" />}
                      {stageStatus.layout === 'pending' && <span className="text-sm font-medium">4</span>}
                    </div>
                    <div>
                      <p className="font-medium text-slate-800">Generate Layout</p>
                      <p className="text-xs text-slate-500">12x12 grid and Vista page.json</p>
                    </div>
                  </div>
                  <button
                    onClick={handleGenerateLayout}
                    disabled={!canRunStage('layout') || isLoading}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      canRunStage('layout') && !isLoading
                        ? 'bg-blue-600 text-white hover:bg-blue-700'
                        : 'bg-slate-100 text-slate-400 cursor-not-allowed'
                    }`}
                  >
                    <Play className="w-4 h-4" />
                    Run
                  </button>
                </div>
              </div>

              {processingStage && (
                <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-center gap-2 text-sm text-blue-700">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    {processingStage}
                  </div>
                </div>
              )}
            </div>

            {/* Results Section */}
            {currentResult && (
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-slate-800">Generated Dashboard</h2>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleViewJson(currentResult.pageJson, 'Vista page.json', 'page.json')}
                      className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-300 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors"
                    >
                      <Eye className="w-4 h-4 text-slate-600" />
                      View JSON
                    </button>
                    <button
                      onClick={handleDownload}
                      className="flex items-center gap-2 px-4 py-2 bg-slate-800 text-white rounded-lg text-sm font-medium hover:bg-slate-900 transition-colors"
                    >
                      <Download className="w-4 h-4" />
                      Download page.json
                    </button>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div className="p-4 bg-slate-50 rounded-lg">
                    <p className="text-2xl font-bold text-slate-800">{currentResult.stats.widgets}</p>
                    <p className="text-xs text-slate-500">Widgets</p>
                  </div>
                  <div className="p-4 bg-slate-50 rounded-lg">
                    <p className="text-2xl font-bold text-slate-800">{currentResult.stats.tiles}</p>
                    <p className="text-xs text-slate-500">Tiles</p>
                  </div>
                  <div className="p-4 bg-slate-50 rounded-lg">
                    <p className="text-2xl font-bold text-slate-800">{currentResult.stats.needAttention}</p>
                    <p className="text-xs text-slate-500">Need Review</p>
                  </div>
                </div>
                <button
                  onClick={() => setActiveTab('preview')}
                  className="w-full py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
                >
                  View Dashboard Preview
                </button>
              </div>
            )}
          </div>
        )}

        {activeTab === 'preview' && (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <LiveDashboardPreview
              pageJson={currentResult?.pageJson || null}
              onRefresh={() => handleGenerateLayout()}
            />
          </div>
        )}

        {activeTab === 'history' && (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <HistoryView />
          </div>
        )}

        {activeTab === 'guide' && <StudentGuideView />}
      </main>

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

export default App
