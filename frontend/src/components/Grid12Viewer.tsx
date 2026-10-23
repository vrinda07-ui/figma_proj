
import React from 'react'
import { VistaTile, VistaWidget } from '../types'

interface Grid12ViewerProps {
  tiles: VistaTile[]
  widgets: VistaWidget[]
}

export const Grid12Viewer: React.FC<Grid12ViewerProps> = ({ tiles, widgets }) => {
  const widgetMap = React.useMemo(() => {
    const map = new Map<string, VistaWidget>()
    widgets.forEach(w => {
      map.set(w.id, w)
      if (w.widgetId) map.set(w.widgetId, w)
    })
    return map
  }, [widgets])

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-col h-full min-h-[500px]">
      <div className="flex items-center justify-between pb-2 mb-2 text-xs text-slate-500">
        <span className="font-semibold text-slate-800">Generated (12 × 12)</span>
        <span className="font-medium text-slate-700">{tiles.length} tiles</span>
      </div>

      <div className="grid grid-cols-12 gap-2 text-center text-[11px] font-mono font-medium text-slate-400 pb-2 border-b border-slate-200">
        {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(col => (
          <div key={col} className="truncate">{col}</div>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto mt-3">
        <div className="grid grid-cols-12 gap-2.5 auto-rows-[minmax(90px,auto)]">
          {tiles.map((tile, idx) => {
            const widgetId = tile.widgetId || (tile.widgetIds && tile.widgetIds[0])
            const widget = widgetId ? widgetMap.get(widgetId) : undefined

            const colStart = (tile.colOffset ?? tile.grid?.colOffset ?? 0) + 1
            const colSpan = tile.cols ?? tile.grid?.colSpan ?? 12
            const rowSpan = tile.rows ?? tile.grid?.rowSpan ?? 2

            const widgetType = widget?.type || 'column2d'
            const componentType = widget?.componentType || widgetType
            const title = widget?.title || widget?.semanticLabel || 'Untitled widget'
            const kpiLabel = widget?.kpiLabel || widget?.semanticLabel || title
            const kpiVal = widget?.kpiValue
            const supportingText = widget?.supportingText
            const trend = widget?.trend
            const chartData = widget?.chartData
            const texts = widget?.text || []
            const isKpi = componentType === 'KPI_CARD'

            return (
              <div
                key={tile.tileId || tile.id || idx}
                style={{
                  gridColumn: `${colStart} / span ${Math.min(colSpan, 12)}`,
                }}
                className="bg-white border border-slate-300 rounded-lg p-3 shadow-sm flex flex-col justify-between hover:border-blue-400 hover:shadow-md transition"
              >
                <div>
                  <div className="flex items-center justify-between gap-1 mb-1.5">
                    <span className="px-1.5 py-0.5 text-[10px] font-mono font-medium text-slate-600 bg-slate-100 rounded border border-slate-200">
                      {componentType}
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">
                      {colSpan}×{rowSpan}
                    </span>
                  </div>

                  {isKpi ? (
                    <div className="mt-2 space-y-1">
                      <div className="text-xs font-medium text-slate-600 line-clamp-2">
                        {kpiLabel}
                      </div>

                      <div className="text-2xl font-bold text-slate-900 tracking-tight">
                        {kpiVal || '—'}
                      </div>

                      {supportingText && (
                        <div className="text-[10px] text-slate-500 leading-snug line-clamp-2">
                          {supportingText}
                        </div>
                      )}

                      {trend && (
                        <div className={`text-[10px] font-medium line-clamp-1 ${
                          /^[−-]|↓|↘/.test(trend.trim())
                            ? 'text-rose-600'
                            : 'text-emerald-600'
                        }`}>
                          {trend}
                        </div>
                      )}
                    </div>
                  ) : (
                    <>
                      <div className="font-semibold text-xs text-slate-900 line-clamp-1 mb-1">
                        {title}
                      </div>

                      {chartData && chartData.length > 0 ? (
                        <div className="space-y-1 mt-1.5">
                          {chartData.slice(0, 3).map((d, i) => (
                            <div key={i} className="flex justify-between text-[10px] text-slate-600">
                              <span className="truncate">{d.label}</span>
                              <span className="font-semibold text-slate-800 ml-1">{d.value}</span>
                            </div>
                          ))}
                        </div>
                      ) : texts.length > 0 ? (
                        <div className="text-[10px] text-slate-500 font-mono line-clamp-2 mt-1">
                          {texts.slice(0, 4).join(', ')}
                        </div>
                      ) : null}
                    </>
                  )}
                </div>

                {widget?.needsReview && (
                  <div className="text-[9px] text-amber-700 font-medium mt-1">
                    Needs review
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
