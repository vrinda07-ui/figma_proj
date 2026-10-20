import React, { useState } from 'react'
import {
  ChevronRight,
  Download,
  Copy,
  Check,
  Play,
  RotateCw,
  Sliders,
  FileCode,
  Eye,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  Layers,
  ChevronDown,
  ChevronUp
} from 'lucide-react'
import { PipelineResult, PackageDetails } from '../types'
import { SourceWireframe } from './SourceWireframe'
import { Grid12Viewer } from './Grid12Viewer'
import { LiveDashboardPreview } from './LiveDashboardPreview'
import { JsonViewer } from './JsonViewer'

interface WorkspaceProps {
  result: PipelineResult | null
  isLoading: boolean
  processingStage?: string
  onGenerate: (packageDetails?: Partial<PackageDetails>, reclassify?: boolean) => void
  onNormalize: () => void
  onClassify: () => void
  onBackToGallery: () => void
  onOpenUpload: () => void
}

export const Workspace: React.FC<WorkspaceProps> = ({
  result,
  isLoading,
  processingStage,
  onGenerate,
  onNormalize,
  onClassify,
  onBackToGallery,
  onOpenUpload,
}) => {
  const [activeTab, setActiveTab] = useState<'split' | 'normalized' | 'classifier' | 'generated' | 'preview'>('split')
  const [reclassify, setReclassify] = useState(false)
  const [includeChrome, setIncludeChrome] = useState(false)
  const [showPackageDetails, setShowPackageDetails] = useState(false)
  const [copied, setCopied] = useState(false)

  // Package metadata form fields per student guide
  const [subjectArea, setSubjectArea] = useState('sales')
  const [topic, setTopic] = useState('ecommerce')
  const [slideName, setSlideName] = useState('revenue-summary')
  const [slideId, setSlideId] = useState(result?.slideId || 'CR001')
  const [customTitle, setCustomTitle] = useState('')

  // Sync slide ID when result updates
  React.useEffect(() => {
    if (result?.slideId) {
      setSlideId(result.slideId)
    }
  }, [result?.slideId])

  const handleCopyPageJson = () => {
    if (result?.pageJson) {
      navigator.clipboard.writeText(JSON.stringify(result.pageJson, null, 2))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleDownloadPageJson = () => {
    if (result?.pageJson) {
      const blob = new Blob([JSON.stringify(result.pageJson, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'page.json'
      a.click()
      URL.revokeObjectURL(url)
    }
  }

  const handleTriggerGenerate = () => {
    onGenerate(
      {
        subjectArea,
        topic,
        slideName,
        slideId: slideId.toUpperCase().slice(0, 5),
        title: customTitle || result?.designName || '',
      },
      reclassify
    )
  }

  if (!result && !isLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center space-y-4">
        <div className="w-16 h-16 rounded-2xl bg-blue-50 text-blue-600 mx-auto flex items-center justify-center">
          <Layers className="w-8 h-8" />
        </div>
        <h2 className="font-heading text-2xl font-bold text-slate-900">No Design Loaded in Workspace</h2>
        <p className="text-slate-500 text-sm max-w-md mx-auto">
          Upload a new Figma JSON file or select a design from the gallery to run candidate normalization and XGBoost classification.
        </p>
        <div className="flex justify-center gap-3 pt-2">
          <button
            onClick={onBackToGallery}
            className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition"
          >
            Browse Designs
          </button>
          <button
            onClick={onOpenUpload}
            className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 shadow-xs transition"
          >
            Upload Figma JSON
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
        <button
          onClick={onBackToGallery}
          className="hover:text-blue-600 transition"
        >
          Designs
        </button>
        <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
        <span className="text-slate-900 font-semibold truncate">
          {result?.designName || 'Loading Design...'}
        </span>
      </nav>

      {/* Design Header & Top Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            {result?.designName || 'Design Analysis'}
          </h1>
          <div className="flex items-center gap-4 text-xs text-slate-500 mt-1 font-mono">
            <span>Content ID: <strong className="text-slate-700">{result?.contentId || '—'}</strong></span>
            <span>Slide ID: <strong className="text-slate-700">{result?.slideId || '—'}</strong></span>
            <span>Node Count: <strong className="text-slate-700">{result?.nodeCount || 0}</strong></span>
          </div>
        </div>

        {/* Action Buttons (Normalize, Classify, Generate) */}
        <div className="flex items-center gap-2 self-start md:self-auto">
          <button
            disabled={isLoading}
            onClick={onNormalize}
            className="px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg shadow-2xs transition disabled:opacity-50"
          >
            Normalize
          </button>

          <button
            disabled={isLoading}
            onClick={onClassify}
            className="px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg shadow-2xs transition disabled:opacity-50"
          >
            Classify
          </button>

          <button
            disabled={isLoading}
            onClick={handleTriggerGenerate}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <RotateCw className="w-3.5 h-3.5 animate-spin" />
                <span>Running...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                <span>Generate</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Options & Collapsible Package Details */}
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-6 text-slate-700">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={reclassify}
                onChange={e => setReclassify(e.target.checked)}
                className="w-3.5 h-3.5 rounded text-blue-600 border-slate-300 focus:ring-blue-500"
              />
              <span>Re-classify (ignore the cached classifier result)</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={includeChrome}
                onChange={e => setIncludeChrome(e.target.checked)}
                className="w-3.5 h-3.5 rounded text-blue-600 border-slate-300 focus:ring-blue-500"
              />
              <span>Include page chrome (sidebar)</span>
            </label>
          </div>

          <button
            onClick={() => setShowPackageDetails(!showPackageDetails)}
            className="flex items-center gap-1 font-semibold text-blue-600 hover:text-blue-700 transition"
          >
            <span>{showPackageDetails ? 'Hide package details' : '+ Package details (optional)'}</span>
            {showPackageDetails ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>

        {/* Collapsible Package Metadata Accordion */}
        {showPackageDetails && (
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 animate-in fade-in duration-150">
            <div className="text-xs font-semibold text-slate-800 mb-3">
              Vista Slide Package Inputs (Student Guide Format):
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3 text-xs">
              <div>
                <label className="block text-slate-600 font-medium mb-1">Subject Area</label>
                <input
                  type="text"
                  value={subjectArea}
                  onChange={e => setSubjectArea(e.target.value)}
                  placeholder="e.g. sales, operations"
                  className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded text-slate-800 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-600 font-medium mb-1">Topic</label>
                <input
                  type="text"
                  value={topic}
                  onChange={e => setTopic(e.target.value)}
                  placeholder="e.g. ecommerce, appointments"
                  className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded text-slate-800 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-600 font-medium mb-1">Slide Name</label>
                <input
                  type="text"
                  value={slideName}
                  onChange={e => setSlideName(e.target.value)}
                  placeholder="kebab-case URL slug"
                  className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded text-slate-800 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-600 font-medium mb-1">Slide ID (5 Chars)</label>
                <input
                  type="text"
                  maxLength={5}
                  value={slideId}
                  onChange={e => setSlideId(e.target.value.toUpperCase())}
                  placeholder="CR001"
                  className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded text-slate-800 font-mono focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-600 font-medium mb-1">Custom Title</label>
                <input
                  type="text"
                  value={customTitle}
                  onChange={e => setCustomTitle(e.target.value)}
                  placeholder="Slide title"
                  className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded text-slate-800 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Output View Tabs & Status */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-2">
        <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-lg text-xs font-semibold">
          <button
            onClick={() => setActiveTab('split')}
            className={`px-3 py-1.5 rounded-md transition ${
              activeTab === 'split' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Grid Layout
          </button>
          <button
            onClick={() => setActiveTab('normalized')}
            className={`px-3 py-1.5 rounded-md transition ${
              activeTab === 'normalized' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Normalized JSON
          </button>
          <button
            onClick={() => setActiveTab('classifier')}
            className={`px-3 py-1.5 rounded-md transition ${
              activeTab === 'classifier' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Classifier JSON
          </button>
          <button
            onClick={() => setActiveTab('generated')}
            className={`px-3 py-1.5 rounded-md transition ${
              activeTab === 'generated' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Generated JSON
          </button>
          <button
            onClick={() => setActiveTab('preview')}
            className={`px-3 py-1.5 rounded-md transition ${
              activeTab === 'preview' ? 'bg-white text-blue-600 shadow-2xs font-bold' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Live Preview
          </button>
        </div>

        {/* Status / Timing Banner */}
        {result && (
          <div className="text-xs text-slate-500 font-mono bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-md">
            Generated page.json in <strong className="text-slate-900">{result.executionTimeMs} ms</strong>
          </div>
        )}
      </div>

      {/* Meta Stats Row (matching Screenshot 2 & 3) */}
      {result && (
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 py-2.5 px-4 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span><strong>{result.stats.widgets}</strong> widgets</span>
            <span>·</span>
            <span><strong>{result.stats.tiles}</strong> tiles</span>
            <span>·</span>
            <span><strong>{result.stats.needAttention}</strong> need attention</span>
            <span>·</span>
            <span><strong>{result.stats.infoNotes}</strong> info notes</span>
            <span>·</span>
            <span><strong>{result.stats.validationErrors}</strong> validation errors</span>
            <span>·</span>
            <span><strong>{result.executionTimeMs}</strong> ms</span>
            <span>·</span>
            <span>classifier: <strong className="text-slate-800">{result.stats.classifier}</strong></span>
          </div>

          <div className="flex items-center gap-2 self-end sm:self-auto shrink-0">
            <button
              onClick={handleCopyPageJson}
              className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-100 border border-slate-300 rounded-md shadow-2xs transition"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy page.json'}</span>
            </button>

            <button
              onClick={handleDownloadPageJson}
              className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-100 border border-slate-300 rounded-md shadow-2xs transition"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download page.json</span>
            </button>
          </div>
        </div>
      )}

      {/* Loading Progress State */}
      {isLoading && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-8 text-center space-y-3 animate-in fade-in">
          <RotateCw className="w-8 h-8 text-blue-600 animate-spin mx-auto" />
          <h3 className="font-heading font-semibold text-slate-900 text-sm">
            {processingStage || 'Processing Figma document through XGBoost pipeline...'}
          </h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Extracting candidate containers, computing 20 spatial & semantic features, and generating 12x12 grid positions.
          </p>
        </div>
      )}

      {/* Main Content Area based on Active Tab */}
      {!isLoading && result && (
        <div>
          {activeTab === 'split' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              {/* Left Column: Source Wireframe (5 cols) */}
              <div className="lg:col-span-5">
                <SourceWireframe
                  components={result.sourceComponents}
                  dimensions={result.sourceDimensions}
                />
              </div>

              {/* Right Column: Generated 12x12 Grid (7 cols) */}
              <div className="lg:col-span-7">
                <Grid12Viewer
                  tiles={result.pageJson.tiles}
                  widgets={result.pageJson.widgets}
                />
              </div>
            </div>
          )}

          {activeTab === 'normalized' && (
            <JsonViewer
              data={result.normalizedJson}
              title="Normalized Candidates JSON"
              filename="candidates.json"
            />
          )}

          {activeTab === 'classifier' && (
            <JsonViewer
              data={result.classifierJson}
              title="Classifier Predictions JSON (XGBoost)"
              filename="predictions.json"
            />
          )}

          {activeTab === 'generated' && (
            <JsonViewer
              data={result.pageJson}
              title="Generated Vista page.json"
              filename="page.json"
            />
          )}

          {activeTab === 'preview' && (
            <LiveDashboardPreview
              pageJson={result.pageJson}
              onRefresh={handleTriggerGenerate}
            />
          )}
        </div>
      )}
    </div>
  )
}
