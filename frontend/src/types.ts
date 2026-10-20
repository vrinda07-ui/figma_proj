export interface GridPosition {
  colOffset: number
  colSpan: number
  rowOffset: number
  rowSpan: number
}

export interface CandidateComponent {
  candidate_id: string
  name: string
  type?: string
  x: number
  y: number
  width: number
  height: number
  text_preview?: string[]
  candidate_score?: number
}

export interface PredictedComponent extends CandidateComponent {
  predicted_type: 'CHART' | 'KPI_CARD' | 'TABLE' | 'FILTER' | 'HEADER' | 'OTHER'
  confidence?: number
}

export interface VistaTile {
  tileId: string
  id?: string
  contentId: string
  slideId: string
  cols: number
  rows: number
  colOffset?: number
  rowOffset?: number
  widgetIds: string[]
  widgetId?: string
  grid: GridPosition
}

export interface VistaWidget {
  id: string
  widgetId: string
  type: string
  componentType: string
  title: string
  sourceComponentId?: string
  grid: GridPosition
  text?: string[]
  chartData?: Array<{ label: string; value: number }>
  kpiValue?: string
  kpiLabel?: string
  trend?: string
  needsReview?: boolean
  chart?: Record<string, any>
  annotations?: Record<string, any>
  dataRequest?: Record<string, any>
  tableConfig?: {
    columns: string[]
    rows?: any[]
  }
}

export interface VistaPageJson {
  contentId: string
  slideId: string
  pageId: string
  id?: string
  title: string
  description: string
  subjectArea?: string
  topic?: string
  slideName?: string
  schemaVersion?: string
  format?: string
  dashboard?: {
    id: string
    name: string
    columns: number
    rows: number
    sourceWidth: number
    sourceHeight: number
  }
  tiles: VistaTile[]
  widgets: VistaWidget[]
  backgroundPaths?: any[]
  validation: {
    componentCount: number
    widgetCount: number
    tileCount: number
    reviewRequired: number
    validationErrors?: string[]
  }
}

export interface PackageDetails {
  subjectArea: string
  topic: string
  slideName: string
  slideId: string
  title: string
}

export interface PipelineResult {
  success: boolean
  designName: string
  contentId: string
  slideId: string
  pageId: string
  executionTimeMs: number
  sourceDimensions: { width: number; height: number }
  nodeCount: number
  candidateCount: number
  sourceComponents: Array<{
    id: string
    name: string
    type: string
    x: number
    y: number
    width: number
    height: number
    textPreview: string[]
  }>
  normalizedJson: {
    dashboard: string
    candidate_count: number
    candidates: CandidateComponent[]
  }
  classifierJson: {
    candidate_count: number
    predictions: PredictedComponent[]
  }
  gridLayout: {
    dashboard_id: string
    dashboard_name: string
    grid: { columns: number; rows: number }
    dashboard_size: { width: number; height: number }
    component_count: number
    components: Array<{
      candidate_id: string
      name: string
      predicted_type: string
      grid: GridPosition
      position_relative_to_dashboard: { x: number; y: number; width: number; height: number }
    }>
  }
  pageJson: VistaPageJson
  stats: {
    widgets: number
    tiles: number
    needAttention: number
    infoNotes: number
    validationErrors: number
    classifier: string
  }
}

export interface DesignSummary {
  id: string
  name: string
  subtitle: string
  status: string
  statusColor?: 'green' | 'orange' | 'red'
  tiles: number
  lastRun: string
  isSample?: boolean
  filePath?: string
}

export interface BackendStatus {
  status: string
  modelLoaded: boolean
  modelFile: string
  classes: string[]
  pipelineStages: string[]
  timestamp: number
}
