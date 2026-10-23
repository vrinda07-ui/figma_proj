
import React from 'react'
import { VistaTile, VistaWidget } from '../types'

interface AbsoluteLayoutViewerProps {
  tiles: VistaTile[]
  widgets: VistaWidget[]
  dashboardSize: { width: number; height: number }
}

export const AbsoluteLayoutViewer: React.FC<AbsoluteLayoutViewerProps> = ({
  tiles,
  widgets,
  dashboardSize,
}) => {
  const widgetMap = React.useMemo(() => {
    const map = new Map<string, VistaWidget>()
    widgets.forEach(w => {
      map.set(w.id, w)
      if (w.widgetId) map.set(w.widgetId, w)
    })
    return map
  }, [widgets])

  const containerRef = React.useRef<HTMLDivElement>(null)
  const [scale, setScale] = React.useState(1)
  const [selectedWidget, setSelectedWidget] = React.useState<VistaWidget | null>(null)

  React.useEffect(() => {
    const updateScale = () => {
      if (containerRef.current) {
        const containerWidth = containerRef.current.clientWidth - 32
        setScale(Math.min(1, containerWidth / dashboardSize.width))
      }
    }

    updateScale()
    window.addEventListener('resize', updateScale)
    return () => window.removeEventListener('resize', updateScale)
  }, [dashboardSize.width])

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-col h-full min-h-[500px]">
      <div className="flex items-center justify-between pb-2 mb-2 text-xs text-slate-500">
        <span className="font-semibold text-slate-800">Absolute Layout (Figma Geometry)</span>
        <span className="font-medium text-slate-700">{tiles.length} tiles</span>
      </div>

      <div ref={containerRef} className="flex-1 overflow-auto mt-3">
        <div
          className="relative bg-white border border-slate-300 rounded-lg"
          style={{
            width: dashboardSize.width,
            height: dashboardSize.height,
            transform: `scale(${scale})`,
            transformOrigin: 'top left',
          }}
        >
          {tiles.map((tile, idx) => {
            const widgetId = tile.widgetId || (tile.widgetIds && tile.widgetIds[0])
            const widget = widgetId ? widgetMap.get(widgetId) : undefined

            const position = widget?.position
            const componentType = widget?.componentType || widget?.type || 'OTHER'
            const semanticLabel = widget?.semanticLabel || widget?.title || 'Untitled widget'
            const kpiLabel = widget?.kpiLabel || semanticLabel
            const kpiVal = widget?.kpiValue
            const supportingText = widget?.supportingText
            const trend = widget?.trend
            const chartData = widget?.chartData
            const texts = widget?.text || []
            const isKpi = componentType === 'KPI_CARD'

            const x = position?.x ?? 0
            const y = position?.y ?? 0
            const width = position?.width ?? 100
            const height = position?.height ?? 100

            return (
              <div
                key={tile.tileId || tile.id || idx}
                className="absolute bg-white border border-slate-300 rounded-lg p-2 shadow-sm hover:border-blue-400 hover:shadow-md transition overflow-hidden cursor-pointer"
                style={{ left: x, top: y, width, height }}
                onClick={() => setSelectedWidget(widget || null)}
              >
                <div className="flex flex-col h-full">
                  <div className="flex items-center justify-between gap-1 mb-1 flex-shrink-0">
                    <span className="px-1.5 py-0.5 text-[9px] font-mono font-medium text-slate-600 bg-slate-100 rounded border border-slate-200">
                      {componentType}
                    </span>
                    <span className="text-[9px] text-slate-400 font-mono">
                      {Math.round(width)}×{Math.round(height)}
                    </span>
                  </div>

                  {isKpi ? (
                    <div className="mt-1 flex-shrink-0 space-y-1">
                      <div className="text-xs font-medium text-slate-600 line-clamp-2">
                        {kpiLabel}
                      </div>

                      <div className="text-lg font-bold text-slate-900 tracking-tight">
                        {kpiVal || '—'}
                      </div>

                      {supportingText && (
                        <div className="text-[10px] text-slate-500 leading-snug line-clamp-2">
                          {supportingText}
                        </div>
                      )}

                      {trend && (
                        <div className={`text-[9px] font-medium line-clamp-1 ${
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
                      {chartData && chartData.length > 0 ? (
                        <div className="space-y-0.5 mt-1 flex-shrink-0 overflow-hidden">
                          {chartData.slice(0, 3).map((d, i) => (
                            <div key={i} className="flex justify-between text-[9px] text-slate-600">
                              <span className="truncate">{d.label}</span>
                              <span className="font-semibold text-slate-800 ml-1">{d.value}</span>
                            </div>
                          ))}
                        </div>
                      ) : texts.length > 0 ? (
                        <div className="text-[9px] text-slate-500 font-mono line-clamp-3 mt-1 flex-shrink-0">
                          {texts.slice(0, 4).join(', ')}
                        </div>
                      ) : null}
                    </>
                  )}

                  {widget?.needsReview && (
                    <div className="text-[8px] text-amber-700 font-medium mt-auto flex-shrink-0">
                      Needs review
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="mt-2 text-[10px] text-slate-400 font-mono">
        Original: {Math.round(dashboardSize.width)}×{Math.round(dashboardSize.height)} px | Scale: {(scale * 100).toFixed(0)}%
      </div>

      {selectedWidget && (
        <div className="mt-4 bg-white border border-slate-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm text-slate-800">Component Inspector</h3>
            <button
              onClick={() => setSelectedWidget(null)}
              className="text-xs text-slate-500 hover:text-slate-700"
            >
              Close
            </button>
          </div>

          <div className="space-y-2 text-xs">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <span className="text-slate-500">Component Type:</span>
                <span className="ml-2 font-medium text-slate-800">{selectedWidget.componentType}</span>
              </div>
              <div>
                <span className="text-slate-500">Vista Type:</span>
                <span className="ml-2 font-medium text-slate-800">{selectedWidget.type}</span>
              </div>
              <div>
                <span className="text-slate-500">Semantic Label:</span>
                <span className="ml-2 font-medium text-slate-800">{selectedWidget.semanticLabel || '—'}</span>
              </div>
              <div>
                <span className="text-slate-500">Source ID:</span>
                <span className="ml-2 font-mono text-slate-600">{selectedWidget.sourceComponentId?.substring(0, 12)}...</span>
              </div>
            </div>

            {selectedWidget.position && (
              <div className="mt-2 p-2 bg-slate-50 rounded">
                <div className="text-slate-500 mb-1">Layout (Figma Coordinates):</div>
                <div className="font-mono text-slate-700">
                  x: {selectedWidget.position.x.toFixed(0)}, y: {selectedWidget.position.y.toFixed(0)}, w: {selectedWidget.position.width.toFixed(0)}, h: {selectedWidget.position.height.toFixed(0)}
                </div>
              </div>
            )}

            {selectedWidget.text && selectedWidget.text.length > 0 && (
              <div className="mt-2">
                <div className="text-slate-500 mb-1">Extracted Content:</div>
                <div className="text-slate-700 bg-slate-50 p-2 rounded max-h-32 overflow-auto">
                  {selectedWidget.text.slice(0, 10).join(', ')}
                  {selectedWidget.text.length > 10 && '...'}
                </div>
              </div>
            )}

            {selectedWidget.kpiLabel && (
              <div className="mt-2">
                <div className="text-slate-500 mb-1">KPI Label:</div>
                <div className="font-medium text-slate-800">{selectedWidget.kpiLabel}</div>
              </div>
            )}

            {selectedWidget.kpiValue && (
              <div className="mt-2">
                <div className="text-slate-500 mb-1">KPI Value:</div>
                <div className="font-bold text-slate-800">{selectedWidget.kpiValue}</div>
              </div>
            )}

            {selectedWidget.supportingText && (
              <div className="mt-2">
                <div className="text-slate-500 mb-1">Supporting Information:</div>
                <div className="text-slate-700">{selectedWidget.supportingText}</div>
              </div>
            )}

            {selectedWidget.trend && (
              <div className="mt-2">
                <div className="text-slate-500 mb-1">Trend:</div>
                <div className="font-medium text-slate-800">{selectedWidget.trend}</div>
              </div>
            )}

            {selectedWidget.chartData && selectedWidget.chartData.length > 0 && (
              <div className="mt-2">
                <div className="text-slate-500 mb-1">Chart Data:</div>
                <div className="text-slate-700 bg-slate-50 p-2 rounded max-h-32 overflow-auto">
                  {selectedWidget.chartData.map((d, i) => (
                    <div key={i}>{d.label}: {d.value}</div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
