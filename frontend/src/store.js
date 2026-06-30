import { create } from 'zustand'

export const useStore = create((set) => ({
  activeView: 'dash',
  cases: [],
  selectedCaseId: null,
  selectedCase: null,
  loadingCases: true,
  loadingCase: false,
  submitting: false,
  backendReady: false,
  casesError: null,
  caseError: null,
  caseRefresh: 0,

  setActiveView: (view) => set({ activeView: view }),
  setCases: (cases) => set({ cases }),
  setSelectedCaseId: (id) => set({ selectedCaseId: id }),
  setSelectedCase: (data) => set({ selectedCase: data }),
  setLoadingCases: (loading) => set({ loadingCases: loading }),
  setLoadingCase: (loading) => set({ loadingCase: loading }),
  setSubmitting: (submitting) => set({ submitting }),
  setBackendReady: (ready) => set({ backendReady: ready }),
  setCasesError: (error) => set({ casesError: error }),
  setCaseError: (error) => set({ caseError: error }),
  refreshCase: () => set((s) => ({ caseRefresh: s.caseRefresh + 1 })),
}))
