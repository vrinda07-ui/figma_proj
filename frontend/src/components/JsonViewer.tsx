import React, { useState } from 'react'
import { Copy, Check, Search, Download } from 'lucide-react'

interface JsonViewerProps {
  data: any
  title?: string
  filename?: string
}

export const JsonViewer: React.FC<JsonViewerProps> = ({
  data,
  title = 'JSON Output',
  filename = 'output.json',
}) => {
  const [copied, setCopied] = useState(false)
  const [filterText, setFilterText] = useState('')

  const jsonString = React.useMemo(() => {
    return JSON.stringify(data, null, 2)
  }, [data])

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonString)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    const blob = new Blob([jsonString], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-md flex flex-col h-full min-h-[500px]">
      {/* Header */}
      <div className="bg-slate-950 px-4 py-3 border-b border-slate-800 flex items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <span className="font-mono font-medium text-slate-300">{title}</span>
          <span className="text-slate-500 font-mono">
            ({Math.round(jsonString.length / 1024)} KB)
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Filter JSON..."
              value={filterText}
              onChange={e => setFilterText(e.target.value)}
              className="pl-8 pr-3 py-1 bg-slate-900 border border-slate-700 rounded text-slate-200 text-xs focus:outline-none focus:border-blue-500 w-36 sm:w-48"
            />
          </div>

          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded font-medium transition"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>

          <button
            onClick={handleDownload}
            className="flex items-center gap-1.5 px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded font-medium transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download</span>
          </button>
        </div>
      </div>

      {/* Code body */}
      <div className="p-4 overflow-auto flex-1 font-mono text-xs leading-relaxed text-slate-300">
        <pre className="whitespace-pre-wrap break-words">
          {filterText
            ? jsonString
                .split('\n')
                .filter(line => line.toLowerCase().includes(filterText.toLowerCase()))
                .join('\n')
            : jsonString}
        </pre>
      </div>
    </div>
  )
}
