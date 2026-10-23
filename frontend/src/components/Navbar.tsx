import React from 'react'
import { LayoutGrid, Sparkles, BookOpen, Layers, Activity, Clock } from 'lucide-react'
import { BackendStatus } from '../types'

interface NavbarProps {
  activeTab: 'workspace' | 'preview' | 'guide' | 'history'
  setActiveTab: (tab: 'workspace' | 'preview' | 'guide' | 'history') => void
  status: BackendStatus | null
  isConnecting: boolean
  onAddDesign: () => void
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  status,
  isConnecting,
  onAddDesign,
}) => {
  const isConnected = status?.status === 'connected'

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-slate-200 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          {/* Logo & Brand */}
          <div className="flex items-center gap-6">
            <div
              onClick={() => setActiveTab('workspace')}
              className="flex items-center gap-2 cursor-pointer group"
            >
              <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-xs group-hover:bg-blue-700 transition">
                <LayoutGrid className="w-4 h-4" />
              </div>
              <div className="flex items-center gap-2">
                <span className="font-heading font-bold text-lg tracking-tight text-slate-900">
                  Vista
                </span>
                <span className="px-1.5 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-600 border border-slate-200 rounded">
                  POC
                </span>
              </div>
            </div>

            {/* Nav Tabs */}
            <nav className="flex space-x-1">
              <button
                onClick={() => setActiveTab('workspace')}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition ${
                  activeTab === 'workspace'
                    ? 'text-blue-600 bg-blue-50 font-semibold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                Workspace
              </button>

              <button
                onClick={() => setActiveTab('history')}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition ${
                  activeTab === 'history'
                    ? 'text-blue-600 bg-blue-50 font-semibold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                History
              </button>

              <button
                onClick={() => setActiveTab('preview')}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition ${
                  activeTab === 'preview'
                    ? 'text-blue-600 bg-blue-50 font-semibold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                Live Preview
              </button>

              <button
                onClick={() => setActiveTab('guide')}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition ${
                  activeTab === 'guide'
                    ? 'text-blue-600 bg-blue-50 font-semibold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                Student Guide
              </button>
            </nav>
          </div>

          {/* Right Status Indicator */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-xs">
              <span
                className={`inline-block w-2.5 h-2.5 rounded-full ${
                  isConnected
                    ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]'
                    : isConnecting
                    ? 'bg-amber-400 animate-pulse'
                    : 'bg-rose-500'
                }`}
              />
              <span className="font-medium text-slate-700">
                {isConnected ? 'Connected' : isConnecting ? 'Connecting...' : 'Offline'}
              </span>
              {isConnected && status?.modelLoaded && (
                <span className="hidden sm:inline-block text-[11px] text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                  XGBoost Active
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}
