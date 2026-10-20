import React, { useState, useEffect } from 'react'
import { Navbar } from './components/Navbar'
import { DesignsGallery } from './components/DesignsGallery'
import { Workspace } from './components/Workspace'
import { LiveDashboardPreview } from './components/LiveDashboardPreview'
import { StudentGuideView } from './components/StudentGuideView'
import { UploadModal } from './components/UploadModal'
import {
  fetchBackendStatus,
  fetchDesigns,
  fetchDesignDetails,
  runGeneration,
  runNormalize,
  runClassify,
  getDownloadPageUrl
} from './services/api'
import { BackendStatus, DesignSummary, PackageDetails, PipelineResult } from './types'
import { AlertCircle, CheckCircle2, X } from 'lucide-react'

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'designs' | 'workspace' | 'preview' | 'guide'>('designs')
  const [designs, setDesigns] = useState<DesignSummary[]>([])
  const [backendStatus, setBackendStatus] = useState<BackendStatus | null>(null)
  const [isConnecting, setIsConnecting] = useState(true)

  // Active workspace state
  const [currentResult, setCurrentResult] = useState<PipelineResult | null>(null)
  const [currentFigmaJson, setCurrentFigmaJson] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [processingStage, setProcessingStage] = useState('')

  // Modals & Notifications
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const showNotification = (message: string, type: 'success' | 'error' = 'success') => {
    setNotification({ type, message })
    setTimeout(() => setNotification(null), 5000)
  }

  // Load backend status and initial designs
  useEffect(() => {
    const initialize = async () => {
      try {
        setIsConnecting(true)
        const status = await fetchBackendStatus()
        setBackendStatus(status)

        const designList = await fetchDesigns()
        setDesigns(designList)

        // Load active/default design into workspace
        if (designList.length > 0) {
          try {
            const initial = await fetchDesignDetails(designList[0].id)
            setCurrentResult(initial)
          } catch (e) {
            console.warn('Could not load initial design details:', e)
          }
        }
      } catch (err: any) {
        console.error('Backend connection failed:', err)
        showNotification('Could not connect to FastAPI backend on port 8000. Ensure server.py is running.', 'error')
      } finally {
        setIsConnecting(false)
      }
    }

    initialize()
  }, [])

  // Open design from gallery
  const handleOpenDesign = async (designId: string) => {
    setIsLoading(true)
    setProcessingStage('Loading design artifacts...')
    try {
      const details = await fetchDesignDetails(designId)
      setCurrentResult(details)
      setActiveTab('workspace')
      showNotification(`Loaded ${details.designName}`)
    } catch (err: any) {
      showNotification(err.message || 'Failed to open design', 'error')
    } finally {
      setIsLoading(false)
      setProcessingStage('')
    }
  }

  // Handle uploaded Figma file
  const handleUploadSuccess = async (figmaJson: any, filename: string, docName: string) => {
    setCurrentFigmaJson(figmaJson)
    setIsLoading(true)
    setProcessingStage('Running full XGBoost pipeline on uploaded design...')
    setActiveTab('workspace')

    try {
      const result = await runGeneration({
        figmaJson,
        packageDetails: {
          title: docName,
          slideName: filename.replace('.json', ''),
        }
      })
      setCurrentResult(result)
      showNotification(`Successfully generated dashboard for ${docName}!`)

      // Refresh designs list
      const updated = await fetchDesigns()
      setDesigns(updated)
    } catch (err: any) {
      showNotification(err.message || 'Generation failed', 'error')
    } finally {
      setIsLoading(false)
      setProcessingStage('')
    }
  }

  // Run full generation in workspace
  const handleGenerate = async (packageDetails?: Partial<PackageDetails>, reclassify: boolean = false) => {
    setIsLoading(true)
    setProcessingStage('Running XGBoost classification and 12x12 grid layout...')

    try {
      const result = await runGeneration({
        figmaJson: currentFigmaJson,
        packageDetails,
        reclassify
      })
      setCurrentResult(result)
      showNotification(`Generated ${result.designName} in ${result.executionTimeMs} ms`)
    } catch (err: any) {
      showNotification(err.message || 'Generation failed', 'error')
    } finally {
      setIsLoading(false)
      setProcessingStage('')
    }
  }

  // Run Normalize (candidates only)
  const handleNormalize = async () => {
    setIsLoading(true)
    setProcessingStage('Extracting Figma components and generating candidates...')
    try {
      const normRes = await runNormalize({ figmaJson: currentFigmaJson })
      if (currentResult) {
        setCurrentResult({
          ...currentResult,
          normalizedJson: normRes.normalizedJson,
          candidateCount: normRes.candidateCount
        })
      }
      showNotification(`Normalized ${normRes.candidateCount} component candidates`)
    } catch (err: any) {
      showNotification(err.message || 'Normalization failed', 'error')
    } finally {
      setIsLoading(false)
      setProcessingStage('')
    }
  }

  // Run Classify (XGBoost only)
  const handleClassify = async () => {
    setIsLoading(true)
    setProcessingStage('Running XGBoost model inference and prediction cleaning...')
    try {
      const classRes = await runClassify({ figmaJson: currentFigmaJson })
      if (currentResult) {
        setCurrentResult({
          ...currentResult,
          classifierJson: classRes.classifierJson
        })
      }
      showNotification(`Classified ${classRes.candidateCount} components with XGBoost`)
    } catch (err: any) {
      showNotification(err.message || 'Classification failed', 'error')
    } finally {
      setIsLoading(false)
      setProcessingStage('')
    }
  }

  // Batch actions from Gallery
  const handleBatchAction = async (action: string) => {
    if (action === 'generate') {
      await handleGenerate()
      setActiveTab('workspace')
    } else if (action === 'normalize') {
      await handleNormalize()
      setActiveTab('workspace')
    } else if (action === 'classify') {
      await handleClassify()
      setActiveTab('workspace')
    } else if (action === 'download_zip' || action === 'score') {
      window.open(getDownloadPageUrl(), '_blank')
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      {/* Top Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        status={backendStatus}
        isConnecting={isConnecting}
        onAddDesign={() => setIsUploadModalOpen(true)}
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
        {activeTab === 'designs' && (
          <DesignsGallery
            designs={designs}
            onOpenDesign={handleOpenDesign}
            onAddDesign={() => setIsUploadModalOpen(true)}
            onBatchAction={handleBatchAction}
            isLoading={isLoading}
          />
        )}

        {activeTab === 'workspace' && (
          <Workspace
            result={currentResult}
            isLoading={isLoading}
            processingStage={processingStage}
            onGenerate={handleGenerate}
            onNormalize={handleNormalize}
            onClassify={handleClassify}
            onBackToGallery={() => setActiveTab('designs')}
            onOpenUpload={() => setIsUploadModalOpen(true)}
          />
        )}

        {activeTab === 'preview' && (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <LiveDashboardPreview
              pageJson={currentResult?.pageJson || null}
              onRefresh={() => handleGenerate()}
            />
          </div>
        )}

        {activeTab === 'guide' && <StudentGuideView />}
      </main>

      {/* Upload Modal */}
      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadSuccess={handleUploadSuccess}
        onSelectSample={handleOpenDesign}
      />
    </div>
  )
}

export default App
