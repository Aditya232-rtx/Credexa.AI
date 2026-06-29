import { useState, useEffect, useRef, useMemo } from 'react'
import { BarChart2, Download, AlertTriangle, Shield, FileText, ChevronDown, Search, Layers, Clock } from 'lucide-react'
import { fetchCases, fetchCaseReport } from '../api'
import RiskGauge from '../components/RiskGauge'

function severityColor(s) {
  if (s === 'high') return 'text-alarm bg-alarm-surface border-alarm-border'
  if (s === 'medium') return 'text-caution bg-caution-surface border-caution-border'
  return 'text-clear bg-clear-surface border-clear-border'
}

function severityDot(s) {
  if (s === 'high') return 'bg-[#DC2626]'
  if (s === 'medium') return 'bg-[#D97706]'
  return 'bg-[#16A34A]'
}

function formatSize(bytes) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1048576).toFixed(1)} MB`
}

export default function Reports() {
  const [casesList, setCasesList] = useState([])
  const [selectedCaseId, setSelectedCaseId] = useState('')
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loadingCases, setLoadingCases] = useState(true)
  const [error, setError] = useState(null)
  const reportRef = useRef(null)

  useEffect(() => {
    fetchCases().then(res => {
      setCasesList(res.cases || [])
      if (res.cases?.length > 0) setSelectedCaseId(res.cases[0].id)
    }).catch(() => {}).finally(() => setLoadingCases(false))
  }, [])

  useEffect(() => {
    if (!selectedCaseId) return
    setLoading(true)
    setError(null)
    fetchCaseReport(selectedCaseId).then(data => {
      setReport(data)
    }).catch(e => {
      setError(e.message || 'Failed to load report')
    }).finally(() => setLoading(false))
  }, [selectedCaseId])

  const selectedCase = useMemo(() => {
    return casesList.find(c => c.id === selectedCaseId)
  }, [casesList, selectedCaseId])

  async function handleExportPdf() {
    const { default: html2canvas } = await import('html2canvas')
    const { jsPDF } = await import('jspdf')

    const el = reportRef.current
    if (!el) return

    const canvas = await html2canvas(el, {
      scale: 2,
      useCORS: true,
      backgroundColor: '#FFFFFF',
    })
    const imgData = canvas.toDataURL('image/png')
    const pdf = new jsPDF('p', 'mm', 'a4')
    const imgWidth = 190
    const pageHeight = 297
    const imgHeight = (canvas.height * imgWidth) / canvas.width

    let heightLeft = imgHeight
    let position = 10

    pdf.addImage(imgData, 'PNG', 10, position, imgWidth, imgHeight)
    heightLeft -= pageHeight - 20

    while (heightLeft > 0) {
      position = heightLeft - imgHeight + 10
      pdf.addPage()
      pdf.addImage(imgData, 'PNG', 10, position, imgWidth, imgHeight)
      heightLeft -= pageHeight - 20
    }

    pdf.save(`report-${selectedCaseId || 'case'}.pdf`)
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-paper overflow-hidden">
      <header className="h-[60px] border-b border-border bg-sheet flex items-center justify-between px-4 sm:px-6 shrink-0">
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 rounded-lg bg-indigo-surface text-indigo flex items-center justify-center">
            <BarChart2 size={16} />
          </div>
          <div>
            <h1 className="text-title text-text-primary">Fraud Analysis Report</h1>
            <p className="text-caption text-text-muted mt-[2px] tracking-wide">EXPORTABLE PDF REPORT</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-ghost" />
            <select
              value={selectedCaseId}
              onChange={e => setSelectedCaseId(e.target.value)}
              disabled={loadingCases}
              className="h-[34px] pl-9 pr-8 rounded-md border border-border bg-paper text-body text-text-primary appearance-none cursor-pointer outline-none focus:border-indigo-mid focus:ring-1 focus:ring-indigo-surface min-w-[200px] disabled:opacity-50"
            >
              {loadingCases ? (
                <option>Loading cases...</option>
              ) : casesList.length === 0 ? (
                <option>No cases found</option>
              ) : (
                casesList.map(c => (
                  <option key={c.id} value={c.id}>{c.id} — {c.applicant_name}</option>
                ))
              )}
            </select>
            <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-text-ghost pointer-events-none" />
          </div>
          {report && (
            <button onClick={handleExportPdf}
              className="h-[34px] bg-indigo hover:bg-indigo-mid text-white px-4 rounded-md text-label flex items-center gap-2 transition-all shadow-[0_2px_4px_rgba(79,70,229,0.15)] hover:shadow-[0_4px_12px_rgba(79,70,229,0.25)] active:scale-[0.97]"
            >
              <Download size={14} /> Export PDF
            </button>
          )}
        </div>
      </header>

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="flex flex-col items-center gap-3 animate-fade-in">
              <div className="w-8 h-8 border-3 border-indigo border-t-transparent rounded-full animate-spin" />
              <div className="text-body text-text-muted">Generating report...</div>
            </div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-full">
            <div className="flex flex-col items-center gap-3 animate-fade-in">
              <AlertTriangle size={28} className="text-alarm" />
              <div className="text-heading text-text-primary">Failed to load report</div>
              <div className="text-body text-text-muted">{error}</div>
            </div>
          </div>
        ) : !report ? (
          <div className="flex items-center justify-center h-full">
            <div className="flex flex-col items-center gap-3 animate-fade-in">
              <BarChart2 size={28} className="text-text-ghost" />
              <div className="text-heading text-text-muted">Select a case to view report</div>
            </div>
          </div>
        ) : (
          <div ref={reportRef} className="max-w-[900px] mx-auto p-6 sm:p-8 space-y-6">
            {/* ── Report Header ── */}
            <div className="bg-white border border-border rounded-xl shadow-sm overflow-hidden">
              <div className="h-[44px] border-b border-border bg-paper flex items-center px-5 gap-2">
                <Shield size={14} className="text-indigo" />
                <span className="text-caption text-text-muted tracking-wide">FRAUD ANALYSIS REPORT</span>
              </div>
              <div className="p-6 flex flex-col sm:flex-row gap-6">
                <div className="flex-1 space-y-4">
                  <div>
                    <div className="text-caption text-text-ghost mb-1">CASE ID</div>
                    <div className="text-heading font-mono text-text-primary">{report.case.id}</div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-caption text-text-ghost mb-1">APPLICANT</div>
                      <div className="text-body font-semibold text-text-primary">{report.case.applicant_name}</div>
                    </div>
                    <div>
                      <div className="text-caption text-text-ghost mb-1">TYPE</div>
                      <div className="text-body text-text-primary">{report.case.application_type}{report.case.application_subtype ? ` · ${report.case.application_subtype}` : ''}</div>
                    </div>
                    <div>
                      <div className="text-caption text-text-ghost mb-1">STATUS</div>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-caption font-semibold border ${
                        report.status === 'flagged' ? 'text-alarm bg-alarm-surface border-alarm-border' :
                        report.status === 'review' ? 'text-caution bg-caution-surface border-caution-border' :
                        'text-clear bg-clear-surface border-clear-border'
                      }`}>{report.status.toUpperCase()}</span>
                    </div>
                    <div>
                      <div className="text-caption text-text-ghost mb-1">DOCUMENTS</div>
                      <div className="text-body text-text-primary">{report.documents.length} file{report.documents.length !== 1 ? 's' : ''}</div>
                    </div>
                  </div>
                  <div className="pt-2">
                    <div className="text-caption text-text-ghost mb-1">SUBMITTED</div>
                    <div className="text-body text-text-secondary">{report.case.submitted_at || 'N/A'}</div>
                  </div>
                </div>
                <div className="flex flex-col items-center justify-center shrink-0">
                  <RiskGauge score={report.risk_score} size={110} />
                  <div className="text-caption text-text-ghost mt-2">RISK SCORE</div>
                </div>
              </div>
            </div>

            {/* ── Explainability ── */}
            <div className="bg-white border border-border rounded-xl shadow-sm overflow-hidden">
              <div className="h-[44px] border-b border-border bg-paper flex items-center px-5 gap-2">
                <FileText size={14} className="text-indigo" />
                <span className="text-caption text-text-muted tracking-wide">AI EXPLAINABILITY</span>
              </div>
              <div className="p-5">
                <p className="text-body text-text-primary leading-relaxed">{report.explanation}</p>
              </div>
            </div>

            {/* ── Severity Breakdown ── */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                { label: 'HIGH', key: 'high', color: 'text-alarm bg-alarm-surface border-alarm-border', dot: 'bg-[#DC2626]' },
                { label: 'MEDIUM', key: 'medium', color: 'text-caution bg-caution-surface border-caution-border', dot: 'bg-[#D97706]' },
                { label: 'LOW', key: 'low', color: 'text-clear bg-clear-surface border-clear-border', dot: 'bg-[#16A34A]' },
              ].map(s => (
                <div key={s.key} className="bg-white border border-border rounded-lg p-4 flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${s.dot}`} />
                  <div>
                    <div className="text-caption text-text-ghost">{s.label} FLAGS</div>
                    <div className="text-data-lg font-mono text-text-primary">{report.severity_counts[s.key] || 0}</div>
                  </div>
                </div>
              ))}
            </div>

            {/* ── Documents ── */}
            <div className="bg-white border border-border rounded-xl shadow-sm overflow-hidden">
              <div className="h-[44px] border-b border-border bg-paper flex items-center px-5 gap-2">
                <Layers size={14} className="text-indigo" />
                <span className="text-caption text-text-muted tracking-wide">DOCUMENT ANALYSIS ({report.documents.length})</span>
              </div>
              <div className="divide-y divide-border">
                {report.documents.length === 0 ? (
                  <div className="p-6 text-center text-body text-text-muted">No documents</div>
                ) : (
                  report.documents.map((doc, idx) => (
                    <div key={doc.id} className="p-5 animate-fade-in" style={{ animationDelay: `${idx * 30}ms` }}>
                      <div className="flex items-start justify-between mb-3">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-body font-semibold text-text-primary truncate">{doc.file_name}</span>
                            {doc.max_severity !== 'none' && (
                              <span className={`px-2 py-0.5 rounded text-caption font-semibold border ${severityColor(doc.max_severity)}`}>
                                {doc.max_severity.toUpperCase()}
                              </span>
                            )}
                          </div>
                          <div className="text-caption text-text-muted mt-0.5">
                            {doc.doc_category} · {formatSize(doc.file_size)} · {doc.flag_count} flag{doc.flag_count !== 1 ? 's' : ''}
                          </div>
                        </div>
                      </div>
                      {doc.flags.length > 0 && (
                        <div className="space-y-2 ml-0">
                          {doc.flags.map((f, fi) => (
                            <div key={fi} className="flex items-start gap-2.5 p-2.5 rounded-lg bg-paper border border-border">
                              <div className={`w-2 h-2 rounded-full mt-1 shrink-0 ${severityDot(f.severity)}`} />
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-2 mb-0.5">
                                  <span className="text-caption font-semibold text-text-muted">{f.layer}</span>
                                  <span className={`text-caption font-semibold ${severityColor(f.severity)}`}>{f.severity.toUpperCase()}</span>
                                </div>
                                <div className="text-body text-text-secondary">{f.finding}</div>
                              </div>
                              <div className="shrink-0 font-mono text-data-md text-text-ghost">{f.score}</div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* ── Detection Layers ── */}
            <div className="bg-white border border-border rounded-xl shadow-sm overflow-hidden">
              <div className="h-[44px] border-b border-border bg-paper flex items-center px-5 gap-2">
                <AlertTriangle size={14} className="text-indigo" />
                <span className="text-caption text-text-muted tracking-wide">DETECTION LAYERS</span>
              </div>
              <div className="divide-y divide-border">
                {Object.entries(report.layers || {}).length === 0 ? (
                  <div className="p-6 text-center text-body text-text-muted">No detection layers triggered</div>
                ) : (
                  Object.entries(report.layers || {}).map(([layerName, layerData], idx) => (
                    <div key={layerName} className="p-4 flex items-center justify-between animate-fade-in" style={{ animationDelay: `${idx * 30}ms` }}>
                      <div className="flex items-center gap-3">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-caption font-semibold ${
                          layerData.count > 3 ? 'bg-alarm-surface text-alarm' :
                          layerData.count > 0 ? 'bg-caution-surface text-caution' :
                          'bg-clear-surface text-clear'
                        }`}>
                          {layerData.count}
                        </div>
                        <div>
                          <div className="text-body font-semibold text-text-primary">{layerName}</div>
                          <div className="text-caption text-text-muted">{layerData.count} flag{layerData.count !== 1 ? 's' : ''}</div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* ── Audit Log ── */}
            {report.audit_log?.length > 0 && (
              <div className="bg-white border border-border rounded-xl shadow-sm overflow-hidden">
                <div className="h-[44px] border-b border-border bg-paper flex items-center px-5 gap-2">
                  <Clock size={14} className="text-indigo" />
                  <span className="text-caption text-text-muted tracking-wide">AUDIT LOG</span>
                </div>
                <div className="divide-y divide-border max-h-[200px] overflow-y-auto">
                  {report.audit_log.map((entry, i) => (
                    <div key={i} className="px-5 py-2.5 flex items-start gap-2">
                      <Clock size={12} className="text-text-ghost mt-0.5 shrink-0" />
                      <div>
                        <div className="text-data-sm text-text-secondary">{entry.action}</div>
                        <div className="text-caption text-text-ghost mt-0.5">{entry.created_at}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── Footer ── */}
            <div className="text-center text-caption text-text-ghost py-4 border-t border-border">
              Credexa AI — Document Fraud Detection Report · Generated {new Date().toLocaleString()}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
