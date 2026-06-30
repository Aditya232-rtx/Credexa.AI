import { ArrowLeft, Clock, RefreshCw, AlertTriangle, Phone, MapPin, Calendar, FileText, Shield, ChevronRight, Eye, Search, Fingerprint, Brain, Gauge, Upload, CheckCircle, ScanLine, Layers } from 'lucide-react'
import RiskGauge from '../components/RiskGauge'
import FlagCard from '../components/FlagCard'

function DetailSkeleton() {
  return (
    <div className="flex-1 flex flex-col h-full bg-paper overflow-hidden animate-skeleton">
      <header className="h-[60px] border-b border-border bg-sheet flex items-center px-6 shrink-0">
        <div className="w-8 h-8 rounded bg-raised mr-4" />
        <div className="flex-1">
          <div className="h-4 w-48 bg-raised rounded mb-2" />
          <div className="h-3 w-32 bg-raised rounded" />
        </div>
      </header>
      <div className="p-6 flex-1 overflow-y-auto">
        <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-6 mb-6">
          <div className="h-[200px] bg-raised rounded-lg" />
          <div className="h-[300px] bg-raised rounded-lg" />
        </div>
        <div className="space-y-4">
          <div className="h-[100px] bg-raised rounded-lg" />
          <div className="h-[100px] bg-raised rounded-lg" />
        </div>
      </div>
    </div>
  )
}

function formatDate(raw) {
  if (!raw) return ''
  const d = new Date(raw)
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const h = d.getHours().toString().padStart(2, '0')
  const m = d.getMinutes().toString().padStart(2, '0')
  return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}, ${h}:${m}`
}

function timeAgo(raw) {
  if (!raw) return ''
  const diff = Date.now() - new Date(raw).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

function SeverityDonut({ high, medium, low }) {
  const total = high + medium + low
  if (!total) return null

  const segments = []
  if (high) segments.push({ count: high, color: '#DC2626', label: 'High' })
  if (medium) segments.push({ count: medium, color: '#D97706', label: 'Medium' })
  if (low) segments.push({ count: low, color: '#16A34A', label: 'Low' })

  const r = 44
  const cx = 60
  const cy = 60
  const circumference = 2 * Math.PI * r

  let offset = 0
  const arcs = segments.map(seg => {
    const pct = seg.count / total
    const length = circumference * pct
    const arc = { ...seg, dashArray: `${length} ${circumference - length}`, dashOffset: -offset, pct }
    offset += length
    return arc
  })

  return (
    <div className="flex items-center gap-3 sm:gap-5">
      <div className="relative shrink-0" style={{ width: 120, height: 120 }}>
        <svg width="120" height="120" viewBox="0 0 120 120" className="transform -rotate-90">
          <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--color-border-ghost)" strokeWidth="18" />
          {arcs.map((arc, i) => (
            <circle
              key={i}
              cx={cx}
              cy={cy}
              r={r}
              fill="none"
              stroke={arc.color}
              strokeWidth="18"
              strokeLinecap="butt"
              strokeDasharray={arc.dashArray}
              strokeDashoffset={arc.dashOffset}
              className="transition-all duration-700"
            />
          ))}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-[22px] font-bold text-text-primary leading-none">{total}</span>
          <span className="text-[10px] text-text-ghost tracking-wide mt-0.5">FLAGS</span>
        </div>
      </div>
      <div className="flex flex-col gap-1.5">
        {arcs.map((seg, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="w-[10px] h-[10px] rounded-full shrink-0" style={{ backgroundColor: seg.color }} />
            <span className="text-[12px] text-text-secondary min-w-[44px]">{seg.label}</span>
            <span className="text-[12px] font-semibold text-text-primary font-mono">{seg.count}</span>
            <span className="text-[11px] text-text-ghost">({(seg.pct * 100).toFixed(0)}%)</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ArchitectureFlow() {
  const steps = [
    { icon: Upload, label: 'Upload', color: 'text-[#6366F1]', bg: 'bg-[#EEF2FF]', border: 'border-[#C7D2FE]' },
    { icon: ScanLine, label: 'OCR / VLM', color: 'text-[#8B5CF6]', bg: 'bg-[#F5F3FF]', border: 'border-[#DDD6FE]' },
    { icon: Search, label: 'Classify', color: 'text-[#06B6D4]', bg: 'bg-[#ECFEFF]', border: 'border-[#A5F3FC]' },
    { icon: Layers, label: 'Forensic\nLayers', color: 'text-[#F59E0B]', bg: 'bg-[#FFFBEB]', border: 'border-[#FDE68A]' },
    { icon: Brain, label: 'Score', color: 'text-[#10B981]', bg: 'bg-[#ECFDF5]', border: 'border-[#A7F3D0]' },
    { icon: CheckCircle, label: 'Result', color: 'text-text-primary', bg: 'bg-paper', border: 'border-border' },
  ]

  return (
    <div className="bg-sheet border border-border rounded-lg shadow-sm overflow-hidden animate-slide-up" style={{ animationDelay: '80ms' }}>
      <div className="h-[40px] border-b border-border bg-paper flex items-center px-5 text-caption text-text-muted tracking-wide gap-2">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-text-ghost"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="9" y1="21" x2="9" y2="9" /></svg>
        DETECTION PIPELINE
      </div>
      <div className="p-4 sm:p-5">
        <div className="flex items-center justify-center gap-0 overflow-x-auto py-2">
          {steps.map((step, i) => {
            const Icon = step.icon
            const isLast = i === steps.length - 1
            return (
              <div key={i} className="flex items-center animate-fade-in shrink-0" style={{ animationDelay: `${i * 80}ms` }}>
                <div className="flex flex-col items-center gap-1.5 px-2 sm:px-3">
                  <div className={`w-[38px] h-[38px] rounded-full ${step.bg} ${step.border} border flex items-center justify-center ${step.color} shadow-sm`}>
                    <Icon size={17} />
                  </div>
                  <span className="text-[11px] font-medium text-text-secondary whitespace-pre-line text-center leading-tight">
                    {step.label}
                  </span>
                </div>
                {!isLast && (
                  <ChevronRight size={18} className="text-text-ghost/30 shrink-0 mx-1" />
                )}
              </div>
            )
          })}
        </div>
        <div className="mt-3 pt-3 border-t border-border flex items-center justify-center gap-2 text-[11px] text-text-ghost">
          <Shield size={11} />
          <span>Credexa AI</span>
        </div>
      </div>
    </div>
  )
}

function KeyExtractions({ flags, caseData }) {
  const applicantFlags = flags.filter(f => f.layer === 'Applicant Data Check')
  if (!applicantFlags.length) return null

  const mismatches = applicantFlags.map(f => {
    const finding = f.finding || ''
    const fieldMatch = finding.match(/^(\w+)\s/)
    const field = fieldMatch ? fieldMatch[1] : 'Field'
    const submittedMatch = finding.match(/'([^']+)'/)
    const extractedMatch = finding.match(/e\.g\.,\s*'([^']+)'/)
    return {
      field,
      submitted: submittedMatch ? submittedMatch[1] : '—',
      extracted: extractedMatch ? extractedMatch[1] : '—',
      severity: f.severity,
      raw: finding,
    }
  })

  return (
    <div className="bg-sheet border border-border rounded-lg shadow-sm overflow-hidden animate-slide-up" style={{ animationDelay: '120ms' }}>
      <div className="h-[40px] border-b border-border bg-paper flex items-center px-5 text-caption text-text-muted tracking-wide gap-2">
        <FileText size={13} className="text-text-ghost" />
        KEY EXTRACTIONS
      </div>
      <div className="p-4">
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left font-medium text-text-ghost pb-2 pr-4">Field</th>
                <th className="text-left font-medium text-text-ghost pb-2 pr-4">Submitted</th>
                <th className="text-left font-medium text-text-ghost pb-2 pr-4">Extracted</th>
                <th className="text-left font-medium text-text-ghost pb-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {mismatches.map((m, i) => (
                <tr key={i} className="border-b border-border/50 last:border-0">
                  <td className="py-2.5 pr-4 font-medium text-text-primary capitalize">{m.field}</td>
                  <td className="py-2.5 pr-4 text-text-secondary">{m.submitted}</td>
                  <td className="py-2.5 pr-4 text-text-secondary">{m.extracted}</td>
                  <td className="py-2.5">
                    <span className={`inline-flex items-center gap-1 px-[5px] py-[1px] rounded-[3px] text-[11px] font-semibold ${m.severity === 'high' ? 'bg-alarm-surface text-alarm' :
                        m.severity === 'medium' ? 'bg-caution-surface text-caution' :
                          'bg-clear-surface text-clear'
                      }`}>
                      <span className="w-1.5 h-1.5 rounded-full bg-current" />
                      MISMATCH
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default function CaseDetail({ caseData, onBack, onAnalyze, loading, error, onRetry }) {
  if (loading) return <DetailSkeleton />
  if (error) return (
    <div className="flex-1 flex flex-col items-center justify-center gap-3 text-text-muted animate-fade-in">
      <div className="w-16 h-16 rounded-2xl bg-alarm-surface border border-alarm-border flex items-center justify-center mb-2">
        <AlertTriangle size={28} className="text-alarm" />
      </div>
      <div className="text-heading text-text-primary">Failed to load case</div>
      <div className="text-body text-text-muted max-w-[320px] text-center">{error}</div>
      <div className="flex gap-3 mt-2">
        <button onClick={onRetry} className="h-[36px] bg-indigo hover:bg-indigo-mid text-white px-5 rounded-md text-label flex items-center gap-2 transition-all">
          <RefreshCw size={14} /> Retry
        </button>
        <button onClick={onBack} className="h-[36px] px-4 rounded-md border border-border text-label text-text-secondary hover:bg-raised transition-all">← Back to Dashboard</button>
      </div>
    </div>
  )
  if (!caseData) return (
    <div className="flex-1 flex flex-col items-center justify-center gap-3 text-text-muted animate-fade-in">
      <div className="w-12 h-12 rounded-xl bg-indigo-surface border border-indigo-border flex items-center justify-center">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#4F46E5" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /></svg>
      </div>
      <div className="text-heading text-text-primary">No case selected</div>
      <div className="text-body text-text-muted">Select a case from the dashboard to view details.</div>
      <button onClick={onBack} className="mt-2 h-[32px] px-4 rounded-md border border-border text-label text-text-secondary hover:bg-raised transition-all">← Back to Dashboard</button>
    </div>
  )

  const c = caseData.case
  const docs = caseData.documents || []
  const flags = caseData.flags || []
  const auditLog = caseData.audit_log || []

  const isFlagged = c.risk_score >= 80 || c.status === 'flagged'
  const isReview = (c.risk_score >= 45 && c.risk_score < 80) || c.status === 'review'
  const isProcessing = c.status === 'processing'

  const highCount = flags.filter(f => f.severity === 'high').length
  const medCount = flags.filter(f => f.severity === 'medium').length
  const lowCount = flags.filter(f => f.severity === 'low').length
  const totalFlags = highCount + medCount + lowCount

  return (
    <div className="flex-1 flex flex-col h-full bg-paper overflow-hidden">
      {/* Header */}
      <header className="h-[60px] border-b border-border bg-sheet flex items-center justify-between px-4 sm:px-6 shrink-0">
        <div className="flex items-center gap-3 sm:gap-4 min-w-0">
          <button onClick={onBack} className="w-8 h-8 flex items-center justify-center rounded-md hover:bg-raised text-text-muted transition-all duration-200 border border-transparent hover:border-border shrink-0">
            <ArrowLeft size={16} />
          </button>
          <div className="min-w-0">
            <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
              <h1 className="text-title text-text-primary truncate">{c.applicant_name}</h1>
              {isProcessing ? (
                <span className="px-[6px] py-[2px] rounded-[4px] bg-indigo-surface text-indigo text-caption border border-indigo-border font-semibold flex items-center gap-1 shrink-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo animate-pulse" />
                  PROCESSING
                </span>
              ) : isFlagged ? (
                <span className="px-[6px] py-[2px] rounded-[4px] bg-alarm-surface text-alarm text-caption border border-alarm-border font-semibold shrink-0">FLAGGED</span>
              ) : isReview ? (
                <span className="px-[6px] py-[2px] rounded-[4px] bg-caution-surface text-caution text-caption border border-caution-border font-semibold shrink-0">REVIEW</span>
              ) : (
                <span className="px-[6px] py-[2px] rounded-[4px] bg-clear-surface text-clear text-caption border border-clear-border font-semibold shrink-0">CLEARED</span>
              )}
            </div>
            <div className="text-caption text-text-muted mt-[2px] tracking-wide flex items-center gap-2">
              <span className="font-mono">{c.id}</span>
              <span className="w-1 h-1 rounded-full bg-border-strong" />
              <span>{c.application_type}{c.application_subtype ? ` · ${c.application_subtype}` : ''}</span>
            </div>
          </div>
        </div>
        <div className="shrink-0 ml-3">
          <button
            onClick={() => onAnalyze(c.id)}
            disabled={loading}
            className="h-[32px] bg-indigo hover:bg-indigo-mid text-white px-3 sm:px-4 rounded-md text-label flex items-center gap-2 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_2px_4px_rgba(79,70,229,0.15)] hover:shadow-[0_4px_12px_rgba(79,70,229,0.25)] active:scale-[0.97]"
          >
            {loading ? (
              <>
                <RefreshCw size={14} className="animate-spin" />
                <span className="hidden sm:inline">Analyzing...</span>
              </>
            ) : (
              <>
                <span className="hidden sm:inline">Run Analysis →</span>
                <span className="sm:hidden">Analyze</span>
              </>
            )}
          </button>
        </div>
      </header>

      <div className="p-4 sm:p-6 overflow-y-auto flex-1">
        <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] xl:grid-cols-[300px_1fr] gap-4 sm:gap-6 items-start">

          {/* ──────── LEFT COLUMN ──────── */}
          <div className="flex flex-col gap-4 sm:gap-6">

            {/* Score Card */}
            <div className="bg-sheet border border-border rounded-lg p-5 sm:p-6 flex flex-col items-center shadow-sm animate-slide-up">
              <div className="text-caption text-text-muted mb-4 tracking-wide w-full text-left">OVERALL RISK SCORE</div>
              <RiskGauge score={c.risk_score || 0} size={120} />
              <div className="mt-4 w-full flex items-center justify-between text-caption text-text-ghost">
                <span>0 — Safe</span>
                <span>100 — Critical</span>
              </div>
            </div>

            {/* Applicant Details */}
            <div className="bg-sheet border border-border rounded-lg shadow-sm overflow-hidden animate-slide-up" style={{ animationDelay: '40ms' }}>
              <div className="h-[40px] border-b border-border bg-paper flex items-center px-4 text-caption text-text-muted tracking-wide">
                APPLICANT DETAILS
              </div>
              <div className="p-4 space-y-3">
                <div className="flex items-start gap-3">
                  <Phone size={14} className="text-text-ghost mt-0.5 shrink-0" />
                  <div className="min-w-0">
                    <div className="text-body text-text-primary">{c.mobile_no || '—'}</div>
                    <div className="text-caption text-text-ghost">Mobile</div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <MapPin size={14} className="text-text-ghost mt-0.5 shrink-0" />
                  <div className="min-w-0">
                    <div className="text-body text-text-primary">{c.address || '—'}</div>
                    <div className="text-caption text-text-ghost">Address</div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Calendar size={14} className="text-text-ghost mt-0.5 shrink-0" />
                  <div className="min-w-0">
                    <div className="text-body text-text-primary">{formatDate(c.submitted_at)}</div>
                    <div className="text-caption text-text-ghost">Submitted</div>
                  </div>
                </div>
                <div className="pt-1 border-t border-border">
                  <div className="flex items-center justify-between text-body">
                    <span className="text-text-secondary">{c.application_type}</span>
                    {c.application_subtype && (
                      <span className="text-caption text-text-ghost">{c.application_subtype}</span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Documents */}
            <div className="bg-sheet border border-border rounded-lg shadow-sm overflow-hidden animate-slide-up" style={{ animationDelay: '80ms' }}>
              <div className="h-[40px] border-b border-border bg-paper flex items-center px-4 text-caption text-text-muted tracking-wide">
                DOCUMENTS ({docs.length})
              </div>
              <div className="flex flex-col p-2 gap-1.5">
                {docs.length === 0 ? (
                  <div className="p-4 text-center text-body text-text-muted">No documents uploaded</div>
                ) : (
                  docs.map((d, i) => {
                    const isPdf = d.file_name.toLowerCase().endsWith('.pdf')
                    const ext = isPdf ? 'PDF' : 'IMG'

                    let sizeStr = '0 B'
                    if (d.file_size) {
                      if (d.file_size < 1024) sizeStr = `${d.file_size} B`
                      else if (d.file_size < 1024 * 1024) sizeStr = `${(d.file_size / 1024).toFixed(0)} KB`
                      else sizeStr = `${(d.file_size / 1024 / 1024).toFixed(1)} MB`
                    }

                    const docFlags = flags.filter(f => f.document_id === d.id || f.finding.includes(d.file_name))
                    const score = Math.min(100, docFlags.reduce((acc, f) => acc + (f.score || 20), 0))
                    const isProc = c.status === 'processing' || c.status === 'uploaded'

                    let dotColor = 'bg-[#16A34A]'
                    if (isProc) dotColor = 'bg-indigo animate-pulse'
                    else if (score >= 60) dotColor = 'bg-[#DC2626]'
                    else if (score > 0) dotColor = 'bg-[#D97706]'

                    const isActive = i === 0

                    return (
                      <div key={d.id} className={`flex items-center gap-3 p-2 rounded-[8px] border transition-colors animate-fade-in ${isActive ? 'bg-[#EEF2FF] border-[#C7D2FE]' : 'bg-transparent border-transparent hover:bg-raised'}`} style={{ animationDelay: `${i * 40}ms` }}>
                        <div className={`w-10 h-10 rounded-[6px] border flex items-center justify-center shrink-0 text-[10px] font-mono font-semibold ${isActive ? 'border-[#C7D2FE] bg-white text-indigo' : 'border-border bg-paper text-text-muted'}`}>
                          {ext}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-[13px] font-semibold text-text-primary truncate">{d.file_name}</div>
                          <div className="text-[12px] text-[#8B8D98] mt-0.5 truncate">
                            {d.doc_category || 'Unknown'} · {sizeStr}
                          </div>
                        </div>
                        <div className="shrink-0 flex items-center gap-1.5">
                          {docFlags.length > 0 && (
                            <span className="text-[10px] font-mono text-alarm font-semibold">{docFlags.length}</span>
                          )}
                          <div className={`w-2 h-2 rounded-full ${dotColor}`} />
                        </div>
                      </div>
                    )
                  })
                )}
              </div>
            </div>

            {/* Timeline (back on left column) */}
            {auditLog.length > 0 && (
              <div className="bg-sheet border border-border rounded-lg shadow-sm overflow-hidden animate-slide-up" style={{ animationDelay: '120ms' }}>
                <div className="h-[40px] border-b border-border bg-paper flex items-center px-4 text-caption text-text-muted tracking-wide gap-2">
                  <Clock size={13} className="text-text-ghost" />
                  TIMELINE
                </div>
                <div className="p-4 max-h-[260px] overflow-y-auto">
                  <div className="relative">
                    <div className="absolute left-[7px] top-[6px] bottom-[6px] w-[2px] bg-border-strong/40" />
                    <div className="space-y-3.5">
                      {auditLog.map((entry, i) => {
                        const isAnalyze = entry.action?.toLowerCase().includes('analysis') || entry.action?.toLowerCase().includes('completed')
                        const isCreate = entry.action?.toLowerCase().includes('create') || entry.action?.toLowerCase().includes('upload')
                        const isError = entry.action?.toLowerCase().includes('fail') || entry.action?.toLowerCase().includes('error')
                        let dotColor = 'bg-indigo'
                        if (isError) dotColor = 'bg-alarm'
                        else if (isAnalyze) dotColor = 'bg-clear'
                        else if (isCreate) dotColor = 'bg-caution'
                        return (
                          <div key={i} className="relative pl-7 animate-fade-in" style={{ animationDelay: `${i * 60}ms` }}>
                            <div className={`absolute left-0 top-[5px] w-[16px] h-[16px] rounded-full border-2 border-sheet ${dotColor} z-10 flex items-center justify-center`} />
                            <div className="flex items-baseline gap-2">
                              <span className="text-[13px] font-medium text-text-primary">{entry.action || 'Event'}</span>
                              <span className="text-[10px] text-text-ghost font-mono">{timeAgo(entry.created_at)}</span>
                            </div>
                            {entry.details && (
                              <div className="text-[12px] text-text-muted mt-0.5 line-clamp-2 leading-relaxed">{entry.details}</div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* ──────── RIGHT COLUMN ──────── */}
          <div className="flex flex-col gap-4 sm:gap-6">

            {/* Detection Layers */}
            <div className="bg-sheet border border-border rounded-lg shadow-sm overflow-hidden animate-slide-up" style={{ animationDelay: '40ms' }}>
              <div className="h-[40px] border-b border-border bg-paper flex items-center px-5 text-caption text-text-muted tracking-wide">
                DETECTION LAYERS ({flags.length})
              </div>
              <div>
                {flags.length === 0 ? (
                  <div className="p-8 sm:p-12 text-center animate-fade-in">
                    <div className="w-12 h-12 rounded-xl bg-clear-surface border border-clear-border flex items-center justify-center mx-auto mb-3">
                      <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm3.5-9.5L9 13l-2.5-2.5" stroke="#16A34A" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    </div>
                    <div className="text-heading text-text-primary mb-1">No anomalies detected</div>
                    <div className="text-body text-text-muted">All documents passed forensic analysis layers.</div>
                  </div>
                ) : (
                  flags.map((f, i) => (
                    <div key={i} className="animate-fade-in" style={{ animationDelay: `${i * 60}ms` }}>
                      <FlagCard layer={f.layer} finding={f.finding} severity={f.severity} score={f.score} />
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Severity + Explainability side by side */}
            {flags.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
                <div className="bg-sheet border border-border rounded-lg shadow-sm overflow-hidden animate-slide-up" style={{ animationDelay: '60ms' }}>
                  <div className="h-[40px] border-b border-border bg-paper flex items-center px-5 text-caption text-text-muted tracking-wide">
                    SEVERITY BREAKDOWN
                  </div>
                  <div className="p-5">
                    <SeverityDonut high={highCount} medium={medCount} low={lowCount} />
                  </div>
                </div>

                <div className="bg-sheet border border-border rounded-lg shadow-sm overflow-hidden animate-slide-up" style={{ animationDelay: '80ms' }}>
                  <div className="h-[40px] border-b border-border bg-paper flex items-center px-4 sm:px-5 gap-2 sm:gap-3 flex-wrap">
                    <div className="text-caption text-text-muted tracking-wide bg-raised border border-border px-2 py-[2px] rounded-[3px]">AI ANALYSIS</div>
                    <div className="text-label text-text-secondary">Explainability Report</div>
                  </div>
                  <div className="p-4 sm:p-5 space-y-3">
                    <p className="text-body text-text-primary leading-relaxed">
                      The analysis identified <span className="font-semibold text-alarm">{flags.length} independent forensic signal{flags.length > 1 ? 's' : ''}</span> across <span className="font-semibold text-text-primary">{docs.length} document{docs.length > 1 ? 's' : ''}</span>
                      {docs.filter(d => d.doc_category).length > 0 && (
                        <>: <span className="font-medium text-text-secondary">{docs.filter(d => d.doc_category).map(d => d.doc_category).join(', ')}</span></>
                      )}.
                    </p>
                    <p className="text-[13px] text-text-secondary leading-relaxed">
                      These signals indicate potential inconsistencies, digital modifications, or data mismatches in the submitted documents
                      that require{flags.length === 1 ? 's' : ''} underwriting review before proceeding with the application.
                    </p>
                    <ul className="space-y-2 pt-1">
                      {flags.map((f, i) => {
                        const findingText = f.finding || 'No specific finding recorded'
                        return (
                          <li key={i} className="flex gap-2 text-[13px] text-text-secondary animate-fade-in" style={{ animationDelay: `${i * 80}ms` }}>
                            <span className={`mt-[3px] shrink-0 ${f.severity === 'high' ? 'text-alarm' : f.severity === 'medium' ? 'text-caution' : 'text-clear'}`}>●</span>
                            <span>
                              <span className="font-medium text-text-primary capitalize">{f.layer}</span>
                              {': '}
                              <span dangerouslySetInnerHTML={{ __html: findingText.replace(/(₹[\d,]+|[\d.]+%|Adobe Acrobat Pro)/g, '<span class="font-semibold text-text-primary bg-raised px-1 rounded-[2px]">$1</span>') }} />
                            </span>
                          </li>
                        )
                      })}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Applicant Data Check */}
            {flags.some(f => f.layer === 'Applicant Data Check') && (
              <div className="bg-sheet border border-border rounded-lg shadow-sm overflow-hidden animate-slide-up" style={{ animationDelay: '100ms' }}>
                <div className="h-[40px] border-b border-border bg-paper flex items-center px-5 text-caption text-text-muted tracking-wide">
                  APPLICANT DATA CHECK
                </div>
                <div className="p-4 space-y-2">
                  {flags.filter(f => f.layer === 'Applicant Data Check').map((f, i) => (
                    <div key={i} className="flex items-start gap-3 p-2 rounded-md bg-paper border border-border animate-fade-in" style={{ animationDelay: `${i * 60}ms` }}>
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 text-[10px] font-bold ${f.severity === 'high' ? 'bg-alarm-surface text-alarm' :
                          f.severity === 'medium' ? 'bg-caution-surface text-caution' :
                            'bg-clear-surface text-clear'
                        }`}>!</div>
                      <div className="min-w-0">
                        <div className="text-body text-text-primary">{f.finding}</div>
                        <div className="text-caption text-text-ghost mt-0.5">Severity: {f.severity}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Architecture Flow */}
            <ArchitectureFlow />

            {/* Key Extractions */}
            <KeyExtractions flags={flags} caseData={c} />

          </div>
        </div>
      </div>
    </div>
  )
}
