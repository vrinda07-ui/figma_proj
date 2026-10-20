import React, { useState } from 'react'
import {
  Search,
  Plus,
  ArrowUpDown,
  Download,
  Play,
  Layers,
  Sparkles,
  ExternalLink,
  ChevronRight,
  Info,
  CheckCircle2,
  AlertCircle
} from 'lucide-react'
import { DesignSummary } from '../types'

interface DesignsGalleryProps {
  designs: DesignSummary[]
  onOpenDesign: (designId: string) => void
  onAddDesign: () => void
  onBatchAction: (action: string) => void
  isLoading?: boolean
}

export const DesignsGallery: React.FC<DesignsGalleryProps> = ({
  designs,
  onOpenDesign,
  onAddDesign,
  onBatchAction,
  isLoading = false,
}) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState<'newest' | 'name' | 'tiles'>('newest')
  const [selectedIds, setSelectedIds] = useState<string[]>(designs.map(d => d.id))

  // Keyboard shortcut '/' to focus search
  const searchInputRef = React.useRef<HTMLInputElement>(null)
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === '/' && document.activeElement !== searchInputRef.current) {
        e.preventDefault()
        searchInputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // Sync selected IDs if designs change
  React.useEffect(() => {
    if (selectedIds.length === 0 && designs.length > 0) {
      setSelectedIds(designs.map(d => d.id))
    }
  }, [designs])

  const filteredDesigns = designs
    .filter(
      d =>
        d.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        d.subtitle.toLowerCase().includes(searchTerm.toLowerCase()) ||
        d.id.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .sort((a, b) => {
      if (sortBy === 'name') return a.name.localeCompare(b.name)
      if (sortBy === 'tiles') return b.tiles - a.tiles
      return 0
    })

  const generatedCount = designs.filter(d => d.status.toLowerCase().includes('generated')).length
  const attentionCount = designs.filter(d => d.status.toLowerCase().includes('attention')).length
  const failedCount = designs.filter(d => d.status.toLowerCase().includes('fail')).length
  const notGeneratedCount = designs.length - generatedCount - attentionCount - failedCount

  const toggleSelectAll = () => {
    if (selectedIds.length === filteredDesigns.length) {
      setSelectedIds([])
    } else {
      setSelectedIds(filteredDesigns.map(d => d.id))
    }
  }

  const toggleSelectOne = (id: string) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(i => i !== id))
    } else {
      setSelectedIds([...selectedIds, id])
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <h1 className="font-heading text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
            Designs
          </h1>
          <span className="text-xl sm:text-2xl font-bold text-slate-400">
            {designs.length}
          </span>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <button
            onClick={() => onBatchAction('score')}
            className="px-4 py-2 text-sm font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg shadow-2xs transition"
          >
            Score all
          </button>
          <button
            onClick={onAddDesign}
            className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition"
          >
            <Plus className="w-4 h-4" />
            Add design
          </button>
        </div>
      </div>

      {/* Progress / Status Bar */}
      <div className="space-y-2">
        <div className="h-2.5 w-full bg-slate-200 rounded-full overflow-hidden flex">
          <div
            style={{ width: `${(generatedCount / Math.max(designs.length, 1)) * 100}%` }}
            className="bg-emerald-600 h-full transition-all duration-500"
          />
          <div
            style={{ width: `${(attentionCount / Math.max(designs.length, 1)) * 100}%` }}
            className="bg-amber-600 h-full transition-all duration-500"
          />
          <div
            style={{ width: `${(failedCount / Math.max(designs.length, 1)) * 100}%` }}
            className="bg-rose-600 h-full transition-all duration-500"
          />
        </div>

        {/* Legend */}
        <div className="flex flex-wrap items-center gap-6 text-xs text-slate-600">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-2xs bg-slate-300" />
            <span>Not generated</span>
            <strong className="text-slate-900">{notGeneratedCount}</strong>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-2xs bg-emerald-600" />
            <span>Generated</span>
            <strong className="text-slate-900">{generatedCount}</strong>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-2xs bg-amber-600" />
            <span>Needs attention</span>
            <strong className="text-slate-900">{attentionCount}</strong>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-2xs bg-rose-600" />
            <span>Failed</span>
            <strong className="text-slate-900">{failedCount}</strong>
          </div>
        </div>
      </div>

      {/* Standing Caveat */}
      <div className="text-xs text-slate-500 bg-slate-50 border border-slate-200 rounded-lg p-3">
        <strong className="text-slate-700 font-semibold">Standing caveat.</strong> About Vista, not about any design, so it is in no count: the pages use 12 × vertical bar chart, 7 × table, 6 × image placeholder, templates that Vista has not rendered yet.
      </div>

      {/* Controls: Search & Sort */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            ref={searchInputRef}
            type="text"
            placeholder="Search by name or id"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-8 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition shadow-2xs"
          />
          <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 px-1.5 py-0.5 text-[10px] font-semibold text-slate-400 bg-slate-100 border border-slate-200 rounded">
            /
          </kbd>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto text-sm text-slate-600">
          <span>Sort</span>
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value as any)}
            className="px-3 py-1.5 text-sm font-medium bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition shadow-2xs cursor-pointer"
          >
            <option value="newest">Newest</option>
            <option value="name">Name</option>
            <option value="tiles">Tile Count</option>
          </select>
        </div>
      </div>

      {/* Designs Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50 text-slate-500 font-semibold text-xs uppercase tracking-wider">
              <tr>
                <th scope="col" className="w-12 px-4 py-3.5">
                  <input
                    type="checkbox"
                    checked={selectedIds.length === filteredDesigns.length && filteredDesigns.length > 0}
                    onChange={toggleSelectAll}
                    className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 border-slate-300"
                  />
                </th>
                <th scope="col" className="px-4 py-3.5">Name</th>
                <th scope="col" className="px-4 py-3.5">Status</th>
                <th scope="col" className="px-4 py-3.5">Tiles</th>
                <th scope="col" className="px-4 py-3.5">Last run</th>
                <th scope="col" className="px-4 py-3.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredDesigns.map(design => {
                const isSelected = selectedIds.includes(design.id)
                const isAttention = design.status.toLowerCase().includes('attention')

                return (
                  <tr
                    key={design.id}
                    className="hover:bg-slate-50/80 transition cursor-pointer group"
                    onClick={() => onOpenDesign(design.id)}
                  >
                    <td
                      className="px-4 py-4"
                      onClick={e => {
                        e.stopPropagation()
                        toggleSelectOne(design.id)
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => {}}
                        className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 border-slate-300"
                      />
                    </td>

                    <td className="px-4 py-4">
                      <div className="flex items-center gap-3">
                        {/* Mini wireframe thumbnail */}
                        <div className="w-12 h-9 rounded bg-slate-100 border border-slate-200 p-1 flex flex-col justify-between shrink-0">
                          <div className="h-1.5 w-full bg-slate-300 rounded-2xs" />
                          <div className="grid grid-cols-3 gap-0.5 h-3">
                            <div className="bg-blue-200 rounded-2xs" />
                            <div className="bg-slate-200 rounded-2xs" />
                            <div className="bg-emerald-200 rounded-2xs" />
                          </div>
                          <div className="h-1.5 w-2/3 bg-slate-300 rounded-2xs" />
                        </div>

                        <div>
                          <div className="font-semibold text-slate-900 group-hover:text-blue-600 transition">
                            {design.name}
                          </div>
                          <div className="text-xs text-slate-500 font-mono">
                            {design.subtitle}
                          </div>
                        </div>
                      </div>
                    </td>

                    <td className="px-4 py-4">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
                          isAttention
                            ? 'bg-amber-50 text-amber-700 border border-amber-200'
                            : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        }`}
                      >
                        {isAttention ? (
                          <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
                        ) : (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        )}
                        {design.status}
                      </span>
                    </td>

                    <td className="px-4 py-4 text-slate-600 font-medium">
                      {design.tiles} tiles
                    </td>

                    <td className="px-4 py-4 text-slate-500 text-xs">
                      {design.lastRun}
                    </td>

                    <td
                      className="px-4 py-4 text-right"
                      onClick={e => e.stopPropagation()}
                    >
                      <button
                        onClick={() => onOpenDesign(design.id)}
                        className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-100 border border-slate-300 rounded-md shadow-2xs transition"
                      >
                        Open
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Floating Bottom Batch Action Bar */}
      {selectedIds.length > 0 && (
        <div className="sticky bottom-6 z-30 bg-white border border-slate-200 shadow-lg rounded-xl p-3 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button className="flex items-center gap-1 text-xs font-semibold text-slate-700 hover:text-slate-900">
              <ChevronRight className="w-3.5 h-3.5" />
              Package
            </button>
            <Info className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-xs text-slate-500">
              <strong className="text-slate-800">{selectedIds.length}</strong> selected ·{' '}
              {selectedIds.length} of {designs.length} done
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setSelectedIds([])}
              className="px-3 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-md transition"
            >
              Clear
            </button>
            <button
              onClick={() => onBatchAction('normalize')}
              className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-md shadow-2xs transition"
            >
              Normalize
            </button>
            <button
              onClick={() => onBatchAction('classify')}
              className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-md shadow-2xs transition"
            >
              Classify
            </button>
            <button
              onClick={() => onBatchAction('generate')}
              className="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md shadow-xs transition"
            >
              Generate
            </button>
            <button
              onClick={() => onBatchAction('download_zip')}
              className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-700 hover:bg-blue-800 rounded-md shadow-xs transition"
            >
              <Download className="w-3.5 h-3.5" />
              Download zip
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
