import React from 'react'
import { ExternalLink, RefreshCw, Layers } from 'lucide-react'
import { VistaPageJson, VistaWidget } from '../types'
import { AbsoluteLayoutViewer } from './AbsoluteLayoutViewer'

interface LiveDashboardPreviewProps {
  pageJson: VistaPageJson | null
  onRefresh?: () => void
}

export const LiveDashboardPreview: React.FC<LiveDashboardPreviewProps> = ({
  pageJson,
  onRefresh,
}) => {
  if (!pageJson || !pageJson.widgets || pageJson.widgets.length === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-12 text-center">
        <Layers className="w-12 h-12 text-slate-300 mx-auto mb-3" />
        <h3 className="font-heading font-semibold text-slate-800 text-base">No dashboard generated yet</h3>
        <p className="text-sm text-slate-500 mt-1">Upload a Figma design or select an existing design to preview the dashboard.</p>
      </div>
    )
  }

  const widgets = pageJson.widgets
  const tiles = pageJson.tiles
  const dashboardSize = {
    width: pageJson.dashboard?.sourceWidth || 1440,
    height: pageJson.dashboard?.sourceHeight || 1024,
  }

  return (
    <div className="space-y-6">
      {/* Preview Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="font-heading text-xl font-bold text-slate-900">
              {pageJson.title || 'Generated Dashboard'}
            </h2>
            <span className="px-2 py-0.5 text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 rounded">
              Figma Geometry
            </span>
          </div>
          <div className="flex items-center gap-4 text-xs text-slate-500 mt-1 font-mono">
            <span>Slide ID: {pageJson.slideId}</span>
            <span>Content ID: {pageJson.contentId}</span>
            <span>{widgets.length} widgets</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg shadow-2xs transition"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh
            </button>
          )}
          <a
            href="/dashboard_preview.html"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Standalone Vista Preview
          </a>
        </div>
      </div>

      {/* Absolute Layout Viewer */}
      <AbsoluteLayoutViewer
        tiles={tiles}
        widgets={widgets}
        dashboardSize={dashboardSize}
      />
    </div>
  )
}
