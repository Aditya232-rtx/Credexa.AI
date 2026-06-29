import { Search, Plus, FileSearch, TrendingUp, AlertTriangle, Shield, RefreshCw } from 'lucide-react'
import { useState, useMemo } from 'react'

function SkeletonRow() {
  return (
    <div className="w-full h-[52px] flex items-center px-5 gap-4 animate-skeleton">
      <div className="w-[100px] h-3 bg-raised rounded" />
      <div className="flex-1 h-3 bg-raised rounded max-w-[200px]" />
      <div className="w-[120px] h-3 bg-raised rounded" />
      <div className="w-[80px] h-3 bg-raised rounded" />
      <div className="w-[60px] h-3 bg-raised rounded ml-auto" />
    </div>
  )
}

function SkeletonMetric() {
  return (
    <div className="bg-sheet border border-border p-5 rounded-lg animate-skeleton">
      <div className="h-3 w-20 bg-raised rounded mb-3" />
      <div className="h-8 w-16 bg-raised rounded" />
    </div>
  )
}

function MetricCard({ label, value, icon: Icon, accent, delay }) {
  return (
    <div
      className="bg-sheet border border-border p-5 rounded-lg shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 animate-slide-up"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="text-caption text-text-muted tracking-wide">{label}</div>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${accent}`}>
          <Icon size={16} />
        </div>
      </div>
      <div className="text-data-lg text-text-primary font-mono">{value}</div>
    </div>
  )
}

export default function Dashboard({ cases, loading, error, onSelectCase, onNewCase, onRetry }) {
  const [searchQuery, setSearchQuery] = useState('')

  const pending = cases.filter(c => c.status === 'review' || c.status === 'pending' || c.status === 'processing').length
  const anomalies = cases.filter(c => c.status === 'flagged' || c.risk_score >= 60).length
  const cleared = cases.filter(c => c.status !== 'flagged' && c.risk_score < 60).length

  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return cases
    const q = searchQuery.toLowerCase()
    return cases.filter(c =>
      c.id?.toLowerCase().includes(q) ||
      c.applicant_name?.toLowerCase().includes(q) ||
      c.application_type?.toLowerCase().includes(q)
    )
  }, [cases, searchQuery])

  return (
    <div className="flex-1 flex flex-col h-full bg-paper overflow-hidden">
      {/* Header */}
      <header className="h-[60px] border-b border-border bg-sheet flex items-center justify-between px-4 sm:px-6 shrink-0">
        <div>
          <h1 className="text-title text-text-primary">Cases</h1>
          <p className="text-caption text-text-muted mt-[2px] tracking-wide">CREDEXA AI ENGINE</p>
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          <div className="relative hidden sm:block">
            <Search className="absolute left-[10px] top-1/2 -translate-y-1/2 text-text-ghost" size={14} />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search cases..."
              className="h-[32px] w-[180px] lg:w-[240px] rounded-md border border-border bg-paper pl-[32px] pr-[10px] text-body text-text-primary placeholder:text-text-ghost outline-none focus:border-indigo-mid focus:ring-1 focus:ring-indigo-surface transition-all"
            />
          </div>
          <button
            onClick={onNewCase}
            className="h-[32px] bg-indigo hover:bg-indigo-mid text-white px-3 sm:px-4 rounded-md text-label flex items-center gap-2 transition-all duration-200 shadow-[0_2px_4px_rgba(79,70,229,0.15)] hover:shadow-[0_4px_12px_rgba(79,70,229,0.25)] active:scale-[0.97]"
          >
            <Plus size={14} strokeWidth={2.5} />
            <span className="hidden sm:inline">New Case</span>
          </button>
        </div>
      </header>

      <div className="p-4 sm:p-6 overflow-y-auto flex-1">
        {/* Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6">
          {loading && cases.length === 0 ? (
            <>
              <SkeletonMetric />
              <SkeletonMetric />
              <SkeletonMetric />
              <SkeletonMetric />
            </>
          ) : (
            <>
              <MetricCard label="TOTAL CASES" value={cases.length} icon={FileSearch} accent="bg-indigo-surface text-indigo" delay={0} />
              <MetricCard label="PENDING REVIEW" value={pending} icon={TrendingUp} accent="bg-caution-surface text-caution" delay={60} />
              <MetricCard label="ANOMALIES DETECTED" value={anomalies} icon={AlertTriangle} accent="bg-alarm-surface text-alarm" delay={120} />
              <MetricCard label="CLEARED" value={cleared} icon={Shield} accent="bg-clear-surface text-clear" delay={180} />
            </>
          )}
        </div>

        {/* Table */}
        <div className="bg-sheet border border-border rounded-lg shadow-sm overflow-hidden animate-fade-in">
          {/* Table header */}
          <div className="h-[44px] border-b border-border bg-paper flex items-center px-5 text-label text-text-muted">
            <div className="w-[100px] lg:w-[120px] shrink-0">CASE ID</div>
            <div className="flex-1 min-w-0">APPLICANT</div>
            <div className="w-[120px] lg:w-[160px] shrink-0 hidden sm:block">APPLICATION TYPE</div>
            <div className="w-[90px] lg:w-[120px] shrink-0">STATUS</div>
            <div className="w-[80px] lg:w-[100px] shrink-0 text-right">RISK</div>
          </div>

          {/* Table body */}
          <div className="divide-y divide-border">
            {error ? (
              <div className="p-12 flex flex-col items-center justify-center text-center animate-fade-in">
                <div className="w-16 h-16 rounded-2xl bg-alarm-surface border border-alarm-border flex items-center justify-center mb-4">
                  <AlertTriangle size={28} className="text-alarm" />
                </div>
                <div className="text-heading text-text-primary mb-2">Failed to load cases</div>
                <div className="text-body text-text-muted mb-5 max-w-[320px]">{error}</div>
                <button onClick={onRetry} className="h-[36px] bg-indigo hover:bg-indigo-mid text-white px-5 rounded-md text-label flex items-center gap-2 transition-all">
                  <RefreshCw size={14} /> Retry
                </button>
              </div>
            ) : loading ? (
              <>
                <SkeletonRow />
                <SkeletonRow />
                <SkeletonRow />
                <SkeletonRow />
              </>
            ) : filtered.length === 0 ? (
              <div className="p-12 flex flex-col items-center justify-center text-center animate-fade-in">
                <div className="w-16 h-16 rounded-2xl bg-indigo-surface border border-indigo-border flex items-center justify-center mb-4">
                  <FileSearch size={28} className="text-indigo" />
                </div>
                <div className="text-heading text-text-primary mb-2">
                  {cases.length === 0 ? 'No cases yet' : 'No matching cases'}
                </div>
                <div className="text-body text-text-muted mb-5 max-w-[320px]">
                  {cases.length === 0
                    ? 'Upload documents to create your first fraud analysis case.'
                    : `No cases match "${searchQuery}". Try a different search term.`}
                </div>
                {cases.length === 0 && (
                  <button
                    onClick={onNewCase}
                    className="h-[36px] bg-indigo hover:bg-indigo-mid text-white px-5 rounded-md text-label flex items-center gap-2 transition-all duration-200 shadow-[0_2px_4px_rgba(79,70,229,0.15)]"
                  >
                    <Plus size={14} strokeWidth={2.5} /> Create First Case
                  </button>
                )}
              </div>
            ) : (
              filtered.map((c, idx) => {
                const isFlagged = c.status === 'flagged' || c.risk_score >= 60
                const isProcessing = c.status === 'processing'
                return (
                  <button
                    key={c.id}
                    onClick={() => onSelectCase(c.id)}
                    className="w-full h-[52px] flex items-center px-5 text-left hover:bg-[#F9FAFB] transition-all duration-200 hover:shadow-[inset_3px_0_0_#4F46E5] group animate-fade-in"
                    style={{ animationDelay: `${idx * 30}ms` }}
                  >
                    <div className="w-[100px] lg:w-[120px] shrink-0 font-mono text-data-md text-text-secondary group-hover:text-indigo transition-colors">{c.id}</div>
                    <div className="flex-1 min-w-0 text-heading text-text-primary truncate pr-2">{c.applicant_name}</div>
                    <div className="w-[120px] lg:w-[160px] shrink-0 text-body text-text-secondary hidden sm:block truncate">{c.application_type}{c.application_subtype ? ` · ${c.application_subtype}` : ''}</div>
                    <div className="w-[90px] lg:w-[120px] shrink-0">
                      {isProcessing ? (
                        <span className="inline-flex items-center px-[8px] py-[2px] rounded-[4px] bg-indigo-surface text-indigo text-caption border border-indigo-border font-semibold gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-indigo animate-pulse" />
                          PROCESSING
                        </span>
                      ) : isFlagged ? (
                        <span className="inline-flex items-center px-[8px] py-[2px] rounded-[4px] bg-alarm-surface text-alarm text-caption border border-alarm-border font-semibold">
                          FLAGGED
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-[8px] py-[2px] rounded-[4px] bg-clear-surface text-clear text-caption border border-clear-border font-semibold">
                          CLEARED
                        </span>
                      )}
                    </div>
                    <div className="w-[80px] lg:w-[100px] shrink-0 text-right font-mono text-data-md">
                      <span className={isFlagged ? 'text-alarm' : 'text-clear'}>{c.risk_score ?? '—'}</span>
                      <span className="text-text-ghost">/100</span>
                    </div>
                  </button>
                )
              })
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
