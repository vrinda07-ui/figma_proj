import React from 'react'
import { ExternalLink, RefreshCw, BarChart2, TrendingUp, Layers, CheckCircle2 } from 'lucide-react'
import { VistaPageJson, VistaWidget } from '../types'

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

  const widgetMap = React.useMemo(() => {
    const map = new Map<string, VistaWidget>()
    widgets.forEach(w => {
      map.set(w.id, w)
      if (w.widgetId) map.set(w.widgetId, w)
    })
    return map
  }, [widgets])

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
              12×12 Grid
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

      {/* Rendered 12-Column Grid Dashboard */}
      <div className="bg-slate-100/70 border border-slate-200 rounded-xl p-5 shadow-2xs">
        <div className="grid grid-cols-12 gap-3.5 auto-rows-[minmax(120px,auto)]">
          {tiles.map((tile, idx) => {
            const widgetId = tile.widgetId || (tile.widgetIds && tile.widgetIds[0])
            const widget = widgetId ? widgetMap.get(widgetId) : undefined

            const colStart = (tile.colOffset ?? tile.grid?.colOffset ?? 0) + 1
            const colSpan = tile.cols ?? tile.grid?.colSpan ?? 12
            const rowSpan = tile.rows ?? tile.grid?.rowSpan ?? 2

            const isKpi = widget?.componentType === 'KPI_CARD' || Boolean(widget?.kpiValue)
            const isChart = widget?.componentType === 'CHART' || (widget?.chartData && widget.chartData.length > 0)
            const isTable = widget?.componentType === 'TABLE' || widget?.type === 'table'

            return (
              <div
                key={tile.tileId || idx}
                style={{
                  gridColumn: `${colStart} / span ${Math.min(colSpan, 12)}`,
                }}
                className="bg-white border border-slate-200/90 rounded-xl p-4 shadow-xs flex flex-col justify-between hover:shadow-md transition"
              >
                <div>
                  {/* Top Badge & Title */}
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      {widget?.kpiLabel || widget?.title || 'Component'}
                    </span>
                    <span className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                      {widget?.type || 'card'}
                    </span>
                  </div>

                  {/* KPI Card Rendering */}
                  {isKpi && (
                    <div className="mt-2 space-y-1">
                      <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 font-heading tracking-tight">
                        {widget?.kpiValue || '—'}
                      </div>
                      {widget?.trend && (
                        <div className="flex items-center gap-1 text-xs font-medium text-emerald-600">
                          <TrendingUp className="w-3.5 h-3.5" />
                          <span>{widget.trend}</span>
                        </div>
                      )}
                      {widget?.text && widget.text.length > 1 && (
                        <div className="text-[11px] text-slate-400 mt-2 truncate">
                          {widget.text.slice(1, 4).join(' · ')}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Chart Rendering */}
                  {isChart && !isKpi && (
                    <div className="mt-3 space-y-2.5">
                      <div className="font-semibold text-xs text-slate-700">
                        {widget?.title}
                      </div>
                      {widget?.chartData && widget.chartData.length > 0 ? (
                        <div className="space-y-2">
                          {widget.chartData.slice(0, 5).map((item, i) => {
                            const maxVal = Math.max(...widget.chartData!.map(d => d.value), 1)
                            const pct = Math.min(100, Math.max(10, (item.value / maxVal) * 100))
                            return (
                              <div key={i} className="space-y-1">
                                <div className="flex justify-between text-xs">
                                  <span className="text-slate-600 truncate">{item.label}</span>
                                  <span className="font-semibold text-slate-900">{item.value}</span>
                                </div>
                                <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                                  <div
                                    style={{ width: `${pct}%` }}
                                    className="h-full bg-blue-600 rounded-full transition-all duration-500"
                                  />
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      ) : (
                        <div className="text-xs text-slate-400 py-3 text-center bg-slate-50 rounded-lg">
                          Dynamic chart visualization configured
                        </div>
                      )}
                    </div>
                  )}

                  {/* Table Rendering */}
                  {isTable && (
                    <div className="mt-2 overflow-x-auto">
                      <div className="text-xs font-semibold text-slate-700 mb-2">
                        {widget?.title || 'Data Table'}
                      </div>
                      <div className="border border-slate-200 rounded-lg overflow-hidden text-xs">
                        <table className="min-w-full divide-y divide-slate-200">
                          <thead className="bg-slate-50">
                            <tr>
                              {(widget?.tableConfig?.columns || widget?.text?.slice(0, 4) || ['Col 1', 'Col 2', 'Status']).map((col, cIdx) => (
                                <th key={cIdx} className="px-3 py-2 text-left font-semibold text-slate-600 text-[11px]">
                                  {col}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 bg-white">
                            <tr>
                              <td className="px-3 py-2 text-slate-700 font-medium">Sample A</td>
                              <td className="px-3 py-2 text-slate-500">Record #1024</td>
                              <td className="px-3 py-2">
                                <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-emerald-50 text-emerald-700 rounded border border-emerald-200">
                                  Active
                                </span>
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Fallback generic view */}
                  {!isKpi && !isChart && !isTable && (
                    <div className="mt-2 text-xs text-slate-600 font-mono">
                      {widget?.text && widget.text.length > 0 ? (
                        <ul className="list-disc list-inside space-y-0.5">
                          {widget.text.slice(0, 3).map((t, idx) => (
                            <li key={idx} className="truncate">{t}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-slate-400">Annotation block</p>
                      )}
                    </div>
                  )}
                </div>

                <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-400">
                  <span>Cols: {colSpan} · Rows: {rowSpan}</span>
                  <span className="font-mono text-slate-500">{widget?.widgetId ? widget.widgetId.substring(0, 8) : ''}</span>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
