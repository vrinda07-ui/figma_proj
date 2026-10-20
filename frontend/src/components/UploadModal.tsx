import React, { useState } from 'react'
import { UploadCloud, FileText, X, CheckCircle, AlertTriangle, Sparkles, Folder } from 'lucide-react'

interface UploadModalProps {
  isOpen: boolean
  onClose: () => void
  onUploadSuccess: (figmaJson: any, filename: string, docName: string) => void
  onSelectSample: (sampleId: string) => void
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
  onSelectSample,
}) => {
  const [isDragging, setIsDragging] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [parsedJson, setParsedJson] = useState<any>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [docInfo, setDocInfo] = useState<{ name: string; nodeCount: number } | null>(null)

  if (!isOpen) return null

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const validateAndParse = (text: string, file: File) => {
    setErrorMsg(null)
    try {
      const data = JSON.parse(text)
      if (!data || typeof data !== 'object') {
        throw new Error('File does not contain a valid JSON object.')
      }

      let name = 'Figma Design'
      let count = 0

      if (data.document) {
        name = data.document.name || data.pageName || 'Figma Document'
        const countNodes = (n: any): number => 1 + (n.children ? n.children.reduce((acc: number, c: any) => acc + countNodes(c), 0) : 0)
        count = countNodes(data.document)
      } else if (data.nodes && Array.isArray(data.nodes)) {
        name = data.file_name || data.name || 'Figma Nodes'
        count = data.nodes.length
      } else {
        throw new Error("Invalid Figma JSON: Expected a 'document' or 'nodes' structure. Export from Figma REST API or the Figma plugin.")
      }

      setParsedJson(data)
      setSelectedFile(file)
      setDocInfo({ name, nodeCount: count })
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to parse JSON file.')
      setSelectedFile(null)
      setParsedJson(null)
      setDocInfo(null)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0]
      if (!file.name.endsWith('.json')) {
        setErrorMsg('Please upload a .json file exported from Figma.')
        return
      }
      const reader = new FileReader()
      reader.onload = ev => {
        validateAndParse(ev.target?.result as string, file)
      }
      reader.readAsText(file)
    }
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0]
      const reader = new FileReader()
      reader.onload = ev => {
        validateAndParse(ev.target?.result as string, file)
      }
      reader.readAsText(file)
    }
  }

  const handleProceed = () => {
    if (parsedJson && selectedFile) {
      onUploadSuccess(parsedJson, selectedFile.name, docInfo?.name || 'Uploaded Design')
      onClose()
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white border border-slate-200 rounded-2xl max-w-xl w-full shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <UploadCloud className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-heading font-bold text-slate-900 text-base">Add Figma Design</h3>
              <p className="text-xs text-slate-500">Upload exported Figma JSON or select a reference sample</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5">
          {/* Drag & Drop Area */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-xl p-8 text-center transition flex flex-col items-center justify-center cursor-pointer ${
              isDragging
                ? 'border-blue-500 bg-blue-50/50'
                : selectedFile
                ? 'border-emerald-400 bg-emerald-50/20'
                : 'border-slate-300 hover:border-slate-400 bg-slate-50/50'
            }`}
          >
            <input
              type="file"
              accept=".json"
              onChange={handleFileInput}
              className="hidden"
              id="figma-file-input"
            />
            <label htmlFor="figma-file-input" className="cursor-pointer space-y-2">
              <div className="w-12 h-12 rounded-full bg-blue-100 text-blue-600 mx-auto flex items-center justify-center">
                <UploadCloud className="w-6 h-6" />
              </div>
              <div className="text-sm font-semibold text-slate-800">
                Click to browse or drag and drop Figma JSON
              </div>
              <div className="text-xs text-slate-500">
                Exported from Figma REST API or the provided Figma plugin
              </div>
            </label>
          </div>

          {/* Validation Status / Selected File Info */}
          {errorMsg && (
            <div className="flex items-start gap-2.5 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs">
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <div>
                <strong className="font-semibold">Validation Error:</strong> {errorMsg}
              </div>
            </div>
          )}

          {selectedFile && docInfo && (
            <div className="flex items-center justify-between p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs">
              <div className="flex items-center gap-2.5">
                <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
                <div>
                  <div className="font-semibold text-slate-900">{docInfo.name}</div>
                  <div className="text-slate-500 font-mono">
                    {selectedFile.name} · {docInfo.nodeCount} nodes · {Math.round(selectedFile.size / 1024)} KB
                  </div>
                </div>
              </div>
              <span className="px-2 py-0.5 text-[11px] font-semibold bg-emerald-100 text-emerald-800 rounded">
                Valid Figma JSON
              </span>
            </div>
          )}

          {/* Quick Select Presets */}
          <div className="pt-2 border-t border-slate-100">
            <div className="text-xs font-semibold text-slate-600 mb-2">Or load an existing benchmark design:</div>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => {
                  onSelectSample('design-03-appointment-operations')
                  onClose()
                }}
                className="flex items-center gap-2 p-2.5 text-left rounded-lg border border-slate-200 hover:border-blue-400 hover:bg-blue-50/30 transition text-xs group"
              >
                <Folder className="w-4 h-4 text-blue-600 group-hover:scale-110 transition" />
                <div>
                  <div className="font-semibold text-slate-800">Design 03 — Appointment Operations</div>
                  <div className="text-[10px] text-slate-400 font-mono">1607:2230 #03 · 12 tiles</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => {
                  onSelectSample('design-02-pharmacy')
                  onClose()
                }}
                className="flex items-center gap-2 p-2.5 text-left rounded-lg border border-slate-200 hover:border-blue-400 hover:bg-blue-50/30 transition text-xs group"
              >
                <Folder className="w-4 h-4 text-indigo-600 group-hover:scale-110 transition" />
                <div>
                  <div className="font-semibold text-slate-800">Design 02 — Pharmacy Prescriptions</div>
                  <div className="text-[10px] text-slate-400 font-mono">6:157 #12 · 9 tiles</div>
                </div>
              </button>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200 rounded-lg transition"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={!parsedJson}
            onClick={handleProceed}
            className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg shadow-xs transition"
          >
            Generate Dashboard
          </button>
        </div>
      </div>
    </div>
  )
}
