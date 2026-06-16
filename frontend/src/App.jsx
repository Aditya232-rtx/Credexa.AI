import { useEffect, useState, useCallback } from 'react'
import Sidebar from './components/Sidebar'
import { ToastProvider, useToast } from './components/Toast'
import Dashboard from './views/Dashboard'
import CaseDetail from './views/CaseDetail'
import Upload from './views/Upload'
import { fetchCases, fetchCase, analyzeCase, uploadCase, fetchHealth } from './api'

function AppShell() {
  const toast = useToast()
  const [activeView, setActiveView] = useState('dash')
  const [cases, setCases] = useState([])
  const [selectedCaseId, setSelectedCaseId] = useState(null)
  const [selectedCase, setSelectedCase] = useState(null)
  const [loadingCases, setLoadingCases] = useState(true)
  const [loadingCase, setLoadingCase] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [backendReady, setBackendReady] = useState(false)

  // Poll for backend readiness
  useEffect(() => {
    let cancelled = false
    let attempts = 0
    const maxAttempts = 30

    async function checkBackend() {
      while (!cancelled && attempts < maxAttempts) {
        try {
          await fetchHealth()
          if (!cancelled) {
            setBackendReady(true)
            return
          }
        } catch {
          attempts++
          await new Promise(r => setTimeout(r, 1500))
        }
      }
      if (!cancelled) {
        toast.error('Backend server is not responding. Please restart the application.', 'Connection Failed')
      }
    }

    checkBackend()
    return () => { cancelled = true }
  }, [])

  const loadCases = useCallback(async (silent = false) => {
    if (!backendReady) return
    if (!silent) setLoadingCases(true)
    try {
      const res = await fetchCases()
      setCases(res.cases || [])
    } catch (e) {
      console.error(e)
      toast.error('Could not load cases from the backend.', 'Fetch Error')
    } finally {
      if (!silent) setLoadingCases(false)
    }
  }, [backendReady, toast])

  useEffect(() => {
    if (backendReady) {
      loadCases()
      toast.success('Backend connected and ready.', 'System Online')

      const interval = setInterval(() => {
        loadCases(true)
      }, 5000)
      return () => clearInterval(interval)
    }
  }, [backendReady])

  useEffect(() => {
    if (!selectedCaseId) return
    let cancelled = false
    setLoadingCase(true)
    fetchCase(selectedCaseId).then(data => {
      if (!cancelled) {
        setSelectedCase(data)
        setActiveView('cases')
      }
    }).catch(e => {
      console.error(e)
      if (!cancelled) toast.error(`Failed to load case ${selectedCaseId}`, 'Fetch Error')
    }).finally(() => {
      if (!cancelled) setLoadingCase(false)
    })
    return () => { cancelled = true }
  }, [selectedCaseId, toast])

  function handleNavigate(view) {
    if (view === 'cases' && !selectedCaseId && cases.length > 0) {
      setSelectedCaseId(cases[0].id)
    }
    setActiveView(view)
  }

  function handleSelectCase(id) {
    setSelectedCaseId(id)
  }

  async function handleAnalyze(id) {
    setLoadingCase(true)
    try {
      toast.info('Running document analysis pipeline...', 'Analysis Started')
      await analyzeCase(id)
      await loadCases()
      const fresh = await fetchCase(id)
      setSelectedCase(fresh)
      const score = fresh?.case?.risk_score || 0
      if (score >= 60) {
        toast.error(`Risk score: ${score}/100 — anomalies detected.`, 'High Risk')
      } else if (score >= 20) {
        toast.warning(`Risk score: ${score}/100 — some concerns found.`, 'Moderate Risk')
      } else {
        toast.success(`Risk score: ${score}/100 — documents appear clean.`, 'Low Risk')
      }
    } catch (e) {
      console.error(e)
      toast.error('Analysis pipeline encountered an error.', 'Analysis Failed')
    } finally {
      setLoadingCase(false)
    }
  }

  async function handleCreateCase(e, formData) {
    e.preventDefault()
    setSubmitting(true)
    try {
      const fd = formData || new FormData(e.currentTarget)
      // 1. Create case and upload documents
      const res = await uploadCase(fd)
      if (e.currentTarget?.reset) e.currentTarget.reset()
      
      // 2. Show toast and run analysis while staying in the upload tab
      toast.info(`Case ${res.case_id} created. Running forensic analysis layers...`, 'Processing')
      await analyzeCase(res.case_id)
      
      // 3. Analysis complete, load fresh data and transition to case detail tab
      await loadCases()
      setSelectedCaseId(res.case_id)
      toast.success('Analysis complete! Viewing case details.', 'Success')
    } catch (err) {
      console.error(err)
      toast.error(err.message || 'Failed to create or analyze case.', 'Process Error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex h-screen w-screen bg-paper overflow-hidden text-text-primary">
      <Sidebar activeView={activeView} onNavigate={handleNavigate} />

      <main className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        {!backendReady ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-4 animate-fade-in">
            <div className="w-10 h-10 border-3 border-indigo border-t-transparent rounded-full animate-spin" />
            <div className="text-heading text-text-muted">Connecting to backend...</div>
            <div className="text-body text-text-ghost">Loading ML models and initializing database</div>
          </div>
        ) : (
          <>
            {activeView === 'dash' && (
              <Dashboard
                cases={cases}
                loading={loadingCases}
                onSelectCase={handleSelectCase}
                onNewCase={() => handleNavigate('upload')}
              />
            )}

            {activeView === 'cases' && (
              <CaseDetail
                caseData={selectedCase}
                loading={loadingCase}
                onAnalyze={handleAnalyze}
                onBack={() => handleNavigate('dash')}
              />
            )}

            {activeView === 'upload' && (
              <Upload
                onSubmit={handleCreateCase}
                submitting={submitting}
                onCancel={() => handleNavigate('dash')}
              />
            )}
          </>
        )}
      </main>
    </div>
  )
}

export default function App() {
  return (
    <ToastProvider>
      <AppShell />
    </ToastProvider>
  )
}
