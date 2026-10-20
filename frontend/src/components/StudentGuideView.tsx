import React from 'react'
import { BookOpen, CheckCircle, Code, Layers, Grid, FileJson } from 'lucide-react'

export const StudentGuideView: React.FC = () => {
  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div className="border-b border-slate-200 pb-6">
        <div className="flex items-center gap-2 text-blue-600 text-sm font-semibold mb-2">
          <BookOpen className="w-4 h-4" />
          <span>Vista Slide POC Guide</span>
        </div>
        <h1 className="font-heading text-3xl font-extrabold text-slate-900 tracking-tight">
          Figma-to-Dashboard Generator Guide & Specification
        </h1>
        <p className="text-slate-600 mt-2 text-base">
          Rule set, 12-column grid constraints, and widget architecture for generating valid Vista <code className="text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded font-mono text-sm">page.json</code> dashboard slides.
        </p>
      </div>

      {/* Grid Rules Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4">
        <div className="flex items-center gap-2 font-heading font-bold text-lg text-slate-900">
          <Grid className="w-5 h-5 text-blue-600" />
          <h2>The 12-Column × 12-Row Grid Mapping</h2>
        </div>
        <p className="text-sm text-slate-600">
          The dashboard slide is always <strong>12 columns wide</strong> and <strong>12 rows tall</strong>. Every horizontal row of tiles must add up to <strong>12</strong>.
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-center">
            <div className="font-bold text-slate-900 text-sm">~17% Width</div>
            <div className="text-blue-600 font-semibold mt-1">2 cols</div>
          </div>
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-center">
            <div className="font-bold text-slate-900 text-sm">~25% Width</div>
            <div className="text-blue-600 font-semibold mt-1">3 cols</div>
          </div>
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-center">
            <div className="font-bold text-slate-900 text-sm">~33% Width</div>
            <div className="text-blue-600 font-semibold mt-1">4 cols</div>
          </div>
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-center">
            <div className="font-bold text-slate-900 text-sm">~50% Width</div>
            <div className="text-blue-600 font-semibold mt-1">6 cols</div>
          </div>
        </div>

        <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-900 flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-blue-600 shrink-0" />
          <span>
            <strong>Formula:</strong> Left Sidebar (2 cols) + Main Chart (8 cols) + Right Panel (2 cols) = <strong>12 ✅</strong>
          </span>
        </div>
      </div>

      {/* Widget Types Table */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4">
        <div className="flex items-center gap-2 font-heading font-bold text-lg text-slate-900">
          <Layers className="w-5 h-5 text-indigo-600" />
          <h2>Figma Element → Vista Widget Mapping</h2>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold">
              <tr>
                <th className="px-4 py-2.5">Figma UI Element</th>
                <th className="px-4 py-2.5">Vista Widget Type</th>
                <th className="px-4 py-2.5">Configuration & Key Properties</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              <tr>
                <td className="px-4 py-2.5 font-sans font-medium text-slate-900">KPI Stat Card / Metric</td>
                <td className="px-4 py-2.5 text-blue-600 font-bold">column2d</td>
                <td className="px-4 py-2.5 text-slate-600">annotations group with text labels and bold values</td>
              </tr>
              <tr>
                <td className="px-4 py-2.5 font-sans font-medium text-slate-900">Bar / Column Chart</td>
                <td className="px-4 py-2.5 text-blue-600 font-bold">column2d / bar2d</td>
                <td className="px-4 py-2.5 text-slate-600">showValues: 1, theme: cigna-light / evernorth-light</td>
              </tr>
              <tr>
                <td className="px-4 py-2.5 font-sans font-medium text-slate-900">Pie / Donut Chart</td>
                <td className="px-4 py-2.5 text-blue-600 font-bold">doughnut2d / pie2d</td>
                <td className="px-4 py-2.5 text-slate-600">doughnutRadius: 55%, pieRadius: 85%</td>
              </tr>
              <tr>
                <td className="px-4 py-2.5 font-sans font-medium text-slate-900">Data Table</td>
                <td className="px-4 py-2.5 text-blue-600 font-bold">table</td>
                <td className="px-4 py-2.5 text-slate-600">tableConfig with column definitions</td>
              </tr>
              <tr>
                <td className="px-4 py-2.5 font-sans font-medium text-slate-900">Insights / Comments</td>
                <td className="px-4 py-2.5 text-blue-600 font-bold">comment</td>
                <td className="px-4 py-2.5 text-slate-600">headerText, bodyStyle, headerStyle</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Critical POC Checklist */}
      <div className="bg-slate-900 text-slate-100 rounded-xl p-6 shadow-md space-y-4">
        <div className="flex items-center gap-2 font-heading font-bold text-lg text-white">
          <FileJson className="w-5 h-5 text-blue-400" />
          <h2>Automated POC Validation Rules</h2>
        </div>

        <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-300">
          <li className="flex items-start gap-2 bg-slate-800/60 p-2.5 rounded-lg border border-slate-700">
            <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <span><strong>contentId</strong> &amp; <strong>slideId</strong> must match and be exactly 5 alphanumeric chars (e.g. CR001, EC001).</span>
          </li>
          <li className="flex items-start gap-2 bg-slate-800/60 p-2.5 rounded-lg border border-slate-700">
            <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <span><strong>pageId</strong>, <strong>tileId</strong>, and <strong>widgetId</strong> must be valid UUID v4 format.</span>
          </li>
          <li className="flex items-start gap-2 bg-slate-800/60 p-2.5 rounded-lg border border-slate-700">
            <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <span>Every <strong>widgetId</strong> in tiles[].widgetIds must exist in the widgets array.</span>
          </li>
          <li className="flex items-start gap-2 bg-slate-800/60 p-2.5 rounded-lg border border-slate-700">
            <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <span>All column spans in a row must add up to 12 without overlapping.</span>
          </li>
        </ul>
      </div>
    </div>
  )
}
