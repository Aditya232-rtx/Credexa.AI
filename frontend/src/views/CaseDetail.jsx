import { ArrowLeft, File as FileIcon, Clock, RefreshCw } from 'lucide-react'
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



export default function CaseDetail({ caseData, onBack, onAnalyze, loading }) {
  if (loading) return <DetailSkeleton />
  if (!caseData) return (
    <div className="flex-1 flex flex-col items-center justify-center gap-3 text-text-muted animate-fade-in">
      <div className="w-12 h-12 rounded-xl bg-indigo-surface border border-indigo-border flex items-center justify-center">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#4F46E5" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
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

  const isFlagged = c.risk_score >= 60 || c.status === 'flagged'
  const isProcessing = c.status === 'processing'

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

          {/* Left Column */}
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

            {/* Documents */}
            <div className="bg-sheet border border-border rounded-lg shadow-sm overflow-hidden animate-slide-up" style={{ animationDelay: '80ms' }}>
              <div className="h-[40px] border-b border-border bg-paper flex items-center px-4 text-[11px] font-semibold text-[#8B8D98] tracking-wider uppercase">
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

                    let cat = d.doc_category || 'Unknown'
                    let extra = ''
                    const fname = d.file_name.toLowerCase()
                    if (fname.includes('bank') || fname.includes('statement')) { cat = 'Financial'; extra = 'HDFC · 3 months' }
                    else if (fname.includes('itr') || fname.includes('tax') || fname.includes('pnl')) { cat = 'Tax Document'; extra = 'Income Tax' }
                    else if (fname.includes('aadhaar') || fname.includes('pan') || fname.includes('passport')) { cat = 'Identity'; extra = 'Identity' }
                    else if (fname.includes('deed') || fname.includes('poa')) { cat = 'Legal'; extra = 'Legal' }

                    const docFlags = flags.filter(f => f.document_id === d.id || f.finding.includes(d.file_name))
                    const score = Math.min(100, docFlags.reduce((acc, f) => acc + (f.score || 20), 0))
                    const isProc = c.status === 'processing' || c.status === 'uploaded'
                    
                    let dotColor = 'bg-[#16A34A]' // Green
                    if (isProc) dotColor = 'bg-indigo animate-pulse'
                    else if (score >= 60) dotColor = 'bg-[#DC2626]' // Red
                    else if (score > 0) dotColor = 'bg-[#D97706]' // Orange

                    const isActive = i === 0;

                    return (
                      <div key={d.id} className={`flex items-center gap-3 p-2 rounded-[8px] border transition-colors animate-fade-in ${isActive ? 'bg-[#EEF2FF] border-[#C7D2FE]' : 'bg-transparent border-transparent hover:bg-raised'}`} style={{ animationDelay: `${i * 40}ms` }}>
                        <div className={`w-10 h-10 rounded-[6px] border flex items-center justify-center shrink-0 text-[10px] font-mono font-semibold ${isActive ? 'border-[#C7D2FE] bg-white text-indigo' : 'border-border bg-paper text-text-muted'}`}>
                          {ext}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-[13px] font-semibold text-text-primary truncate">{d.file_name}</div>
                          <div className="text-[12px] text-[#8B8D98] mt-0.5 truncate">
                            {extra ? `${extra} · ${sizeStr}` : `${cat} · ${sizeStr}`}
                          </div>
                        </div>
                        <div className="shrink-0 px-2 flex items-center justify-center">
                          <div className={`w-2 h-2 rounded-full ${dotColor}`} />
                        </div>
                      </div>
                    )
                  })
                )}
              </div>
            </div>

            {/* Audit Log */}
            {auditLog.length > 0 && (
              <div className="bg-sheet border border-border rounded-lg shadow-sm overflow-hidden animate-slide-up" style={{ animationDelay: '160ms' }}>
                <div className="h-[40px] border-b border-border bg-paper flex items-center px-4 text-caption text-text-muted tracking-wide">
                  AUDIT LOG
                </div>
                <div className="divide-y divide-border max-h-[200px] overflow-y-auto">
                  {auditLog.map((entry, i) => (
                    <div key={i} className="px-4 py-2.5 flex items-start gap-2">
                      <Clock size={12} className="text-text-ghost mt-0.5 shrink-0" />
                      <div className="min-w-0">
                        <div className="text-data-sm text-text-secondary">{entry.action}</div>
                        <div className="text-caption text-text-ghost mt-0.5">{entry.created_at}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right Column */}
          <div className="flex flex-col gap-4 sm:gap-6">

            {/* Flags Panel */}
            <div className="bg-sheet border border-border rounded-lg shadow-sm overflow-hidden animate-slide-up" style={{ animationDelay: '40ms' }}>
              <div className="h-[40px] border-b border-border bg-paper flex items-center px-5 text-caption text-text-muted tracking-wide">
                DETECTION LAYERS ({flags.length})
              </div>
              <div>
                {flags.length === 0 ? (
                  <div className="p-8 sm:p-12 text-center animate-fade-in">
                    <div className="w-12 h-12 rounded-xl bg-clear-surface border border-clear-border flex items-center justify-center mx-auto mb-3">
                      <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm3.5-9.5L9 13l-2.5-2.5" stroke="#16A34A" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
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

            {/* Explainability Panel */}
            {flags.length > 0 && (
              <div className="bg-sheet border border-border rounded-lg shadow-sm overflow-hidden animate-slide-up" style={{ animationDelay: '120ms' }}>
                <div className="h-[40px] border-b border-border bg-paper flex items-center px-4 sm:px-5 gap-2 sm:gap-3 flex-wrap">
                  <div className="text-caption text-text-muted tracking-wide bg-raised border border-border px-2 py-[2px] rounded-[3px]">AI ANALYSIS</div>
                  <div className="text-label text-text-secondary">Explainability Report — Qwen2.5 Local</div>
                </div>
                <div className="p-4 sm:p-6">
                  <p className="text-body text-text-primary leading-relaxed mb-4">
                    The analysis identified <span className="font-semibold text-alarm">{flags.length} independent forensic signal{flags.length > 1 ? 's' : ''}</span> that require{flags.length === 1 ? 's' : ''} attention.
                    These signals indicate potential inconsistencies or modifications in the submitted documents.
                  </p>
                  <ul className="space-y-3">
                    {flags.map((f, i) => (
                      <li key={i} className="flex gap-3 text-body text-text-secondary animate-fade-in" style={{ animationDelay: `${i * 80}ms` }}>
                        <span className={`mt-[2px] shrink-0 ${f.severity === 'high' ? 'text-alarm' : f.severity === 'medium' ? 'text-caution' : 'text-clear'}`}>●</span>
                        <span dangerouslySetInnerHTML={{ __html: f.finding?.replace(/(₹[\d,]+|\d+%|Adobe Acrobat Pro)/g, '<span class="font-semibold text-text-primary bg-raised px-1 rounded-[2px]">$1</span>') || '' }} />
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

          </div>
        </div>


      </div>
    </div>
  )
}
