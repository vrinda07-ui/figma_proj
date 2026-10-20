import React from 'react'

interface SourceComponent {
  id: string
  name: string
  type: string
  x: number
  y: number
  width: number
  height: number
  textPreview: string[]
}

interface SourceWireframeProps {
  components: SourceComponent[]
  dimensions: { width: number; height: number }
}

export const SourceWireframe: React.FC<SourceWireframeProps> = ({
  components,
  dimensions,
}) => {
  const docW = dimensions.width || 1440
  const docH = dimensions.height || 900

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-col h-full min-h-[500px]">
      <div className="flex items-center justify-between pb-3 border-b border-slate-200 mb-3 text-xs text-slate-500">
        <div>
          <span className="font-semibold text-slate-800">Source</span>
          <span className="ml-2 font-mono">Figma frame · {Math.round(docW)} × {Math.round(docH)}</span>
        </div>
        <span className="font-medium text-slate-700">{components.length} components</span>
      </div>

      {/* Spatial Wireframe Preview */}
      <div className="relative w-full flex-1 bg-white border border-slate-200 rounded-lg overflow-hidden shadow-2xs p-3">
        <div className="w-full h-full flex flex-col gap-2 overflow-y-auto pr-1">
          {components.length === 0 ? (
            <div className="flex items-center justify-center h-48 text-slate-400 text-sm">
              No components extracted
            </div>
          ) : (
            components.map((comp, idx) => {
              const nameLower = comp.name.toLowerCase()
              let badgeColor = 'bg-slate-100 text-slate-700 border-slate-200'
              let badgeLabel = comp.type || 'FRAME'

              if (nameLower.includes('kpi') || nameLower.includes('metric')) {
                badgeColor = 'bg-blue-50 text-blue-700 border-blue-200'
                badgeLabel = 'kpi_card'
              } else if (nameLower.includes('chart') || nameLower.includes('donut') || nameLower.includes('plot')) {
                badgeColor = 'bg-indigo-50 text-indigo-700 border-indigo-200'
                badgeLabel = 'donut_chart'
              } else if (nameLower.includes('table')) {
                badgeColor = 'bg-purple-50 text-purple-700 border-purple-200'
                badgeLabel = 'table'
              } else if (nameLower.includes('nav') || nameLower.includes('sidebar')) {
                badgeColor = 'bg-slate-100 text-slate-600 border-slate-300'
                badgeLabel = 'sidebar_nav'
              } else if (nameLower.includes('header') || nameLower.includes('heading')) {
                badgeColor = 'bg-sky-50 text-sky-700 border-sky-200'
                badgeLabel = 'header'
              } else if (nameLower.includes('filter')) {
                badgeColor = 'bg-amber-50 text-amber-700 border-amber-200'
                badgeLabel = 'filter_bar'
              }

              return (
                <div
                  key={comp.id || idx}
                  className="group relative border border-slate-300 hover:border-blue-400 bg-white hover:bg-blue-50/20 rounded-md p-2.5 transition shadow-2xs"
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className={`px-1.5 py-0.5 text-[10px] font-mono font-medium rounded border ${badgeColor}`}>
                      {badgeLabel}
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">
                      {Math.round(comp.width)} × {Math.round(comp.height)}
                    </span>
                  </div>

                  <div className="font-semibold text-xs text-slate-800 truncate">
                    {comp.name}
                  </div>

                  {comp.textPreview && comp.textPreview.length > 0 && (
                    <div className="text-[11px] text-slate-500 mt-1 truncate font-mono">
                      {comp.textPreview.join(' · ')}
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
