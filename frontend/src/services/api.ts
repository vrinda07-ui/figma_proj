import { BackendStatus, DesignSummary, PackageDetails, PipelineResult, HistoryEntry, HistoryRunDetails } from '../types'

const API_BASE = '/api'

export async function fetchBackendStatus(): Promise<BackendStatus> {
  const res = await fetch(`${API_BASE}/status`)
  if (!res.ok) {
    throw new Error(`Backend unavailable (${res.status})`)
  }
  return res.json()
}

export async function loadPluginData(): Promise<{
  success: boolean
  documentName: string
  nodeCount: number
  dimensions: { width: number; height: number }
  figmaJson: any
}> {
  const res = await fetch(`${API_BASE}/load-plugin-data`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to load plugin data' }))
    throw new Error(error.detail || 'Failed to load plugin data')
  }
  return res.json()
}

export async function fetchDesigns(): Promise<DesignSummary[]> {
  const res = await fetch(`${API_BASE}/designs`)
  if (!res.ok) {
    throw new Error('Failed to fetch designs list')
  }
  const data = await res.json()
  return data.designs || []
}

export async function fetchDesignDetails(designId: string): Promise<PipelineResult> {
  const res = await fetch(`${API_BASE}/designs/${designId}`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to load design' }))
    throw new Error(error.detail || 'Failed to load design')
  }
  return res.json()
}

export async function uploadFigmaFile(file: File): Promise<{
  filename: string
  documentName: string
  nodeCount: number
  dimensions: { width: number; height: number }
  figmaJson: any
}> {
  const formData = new FormData()
  formData.append('file', file)

  const res = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(error.detail || 'Upload failed')
  }
  return res.json()
}

export async function runGeneration(params: {
  figmaJson?: any
  designId?: string
  packageDetails?: Partial<PackageDetails>
  reclassify?: boolean
  includeChrome?: boolean
}): Promise<PipelineResult> {
  const res = await fetch(`${API_BASE}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Generation failed' }))
    throw new Error(error.detail || 'Pipeline generation failed')
  }
  return res.json()
}

export async function runNormalize(params: {
  figmaJson?: any
  designId?: string
}): Promise<any> {
  const res = await fetch(`${API_BASE}/normalize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Normalization failed' }))
    throw new Error(error.detail || 'Candidate normalization failed')
  }
  return res.json()
}

export async function runClassify(params: {
  figmaJson?: any
  designId?: string
}): Promise<any> {
  const res = await fetch(`${API_BASE}/classify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Classification failed' }))
    throw new Error(error.detail || 'Classification failed')
  }
  return res.json()
}

export async function runPreprocess(params: {
  figmaJson?: any
  designId?: string
}): Promise<any> {
  const res = await fetch(`${API_BASE}/preprocess`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Preprocessing failed' }))
    throw new Error(error.detail || 'Preprocessing failed')
  }
  return res.json()
}

export async function runGenerateLayout(params: {
  figmaJson?: any
  designId?: string
  packageDetails?: Partial<PackageDetails>
  runId?: string
}): Promise<any> {
  const res = await fetch(`${API_BASE}/generate-layout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Layout generation failed' }))
    throw new Error(error.detail || 'Layout generation failed')
  }
  return res.json()
}

export async function fetchHistory(): Promise<{ runs: HistoryEntry[] }> {
  const res = await fetch(`${API_BASE}/history`)
  if (!res.ok) {
    throw new Error('Failed to fetch history')
  }
  return res.json()
}

export async function fetchHistoryRun(runId: string): Promise<HistoryRunDetails> {
  const res = await fetch(`${API_BASE}/history/${runId}`)
  if (!res.ok) {
    throw new Error('Failed to fetch run details')
  }
  return res.json()
}

export async function fetchHistoryJson(runId: string, jsonType: string): Promise<any> {
  const res = await fetch(`${API_BASE}/history/${runId}/json/${jsonType}`)
  if (!res.ok) {
    throw new Error('Failed to fetch JSON')
  }
  return res.json()
}

export function getHistoryDownloadUrl(runId: string, jsonType: string): string {
  return `${API_BASE}/history/${runId}/download/${jsonType}`
}

export function getDownloadPageUrl(): string {
  return `${API_BASE}/download/page.json`
}

export function getDownloadPredictionsUrl(): string {
  return `${API_BASE}/download/predictions.json`
}
