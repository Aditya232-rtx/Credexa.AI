import { useState, useRef, useCallback } from 'react'
import { Upload as UploadIcon, User, Phone, MapPin, Briefcase, ChevronDown } from 'lucide-react'
import { DocumentCard } from '../components/DocumentCard'

const APPLICATION_TYPES = {
  'Loan': ['Home Loan', 'Business Loan', 'Mortgage Loan', 'Vehicle Loan', 'Crop Loan', 'Gold Loan', 'Personal Loan', 'Education Loan'],
  'Insurance': ['Life Insurance', 'Health Insurance', 'Vehicle Insurance', 'Property Insurance', 'Crop Insurance'],
  'KYC Verification': ['Individual KYC', 'Business KYC', 'Enhanced Due Diligence'],
  'Account Opening': ['Savings Account', 'Current Account', 'Fixed Deposit', 'Demat Account'],
  'Property Registration': ['Sale Deed', 'Gift Deed', 'Mortgage Registration', 'Lease Registration'],
  'Tax Filing': ['ITR Filing', 'GST Registration', 'TDS Return', 'Corporate Tax'],
}

export default function Upload({ onSubmit, submitting, onCancel }) {
  const [dragging, setDragging] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState([])
  const [applicationType, setApplicationType] = useState('')
  const [applicationSubtype, setApplicationSubtype] = useState('')
  const fileInputRef = useRef(null)
  const dragCounter = useRef(0)

  function handleFiles(fileList) {
    const arr = Array.from(fileList)
    setSelectedFiles(prev => {
      const existing = new Set(prev.map(f => f.name + f.size))
      const newFiles = arr.filter(f => !existing.has(f.name + f.size))
      return [...prev, ...newFiles]
    })
  }

  const handleDragEnter = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    dragCounter.current++
    setDragging(true)
  }, [])

  const handleDragLeave = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    dragCounter.current--
    if (dragCounter.current <= 0) {
      dragCounter.current = 0
      setDragging(false)
    }
  }, [])

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    dragCounter.current = 0
    setDragging(false)
    if (e.dataTransfer.files?.length) {
      handleFiles(e.dataTransfer.files)
    }
  }, [])

  function handleNativeSubmit(e) {
    e.preventDefault()
    if (selectedFiles.length === 0) return

    const form = e.currentTarget
    const formData = new FormData()
    formData.append('applicant_name', form.applicant_name.value)
    formData.append('mobile_no', form.mobile_no.value)
    formData.append('address', form.address.value)
    formData.append('application_type', form.application_type.value)
    formData.append('application_subtype', form.application_subtype.value)
    selectedFiles.forEach(f => formData.append('files', f))

    const syntheticEvent = {
      preventDefault: () => {},
      currentTarget: {
        reset: () => {
          form.reset()
          setSelectedFiles([])
          setApplicationType('')
          setApplicationSubtype('')
        },
      },
    }

    onSubmit(syntheticEvent, formData)
  }

  const subtypes = APPLICATION_TYPES[applicationType] || []

  const inputClass = "h-[40px] px-3 rounded-[8px] border border-[#E5E7EB] bg-white text-[13px] text-text-primary outline-none focus:border-[#818CF8] focus:ring-2 focus:ring-[#EEF2FF] transition-all placeholder:text-[#C4C5C9] disabled:opacity-50"
  const labelClass = "text-[11px] font-semibold text-[#8B8D98] tracking-wider uppercase"

  return (
    <div className="flex-1 flex flex-col h-full bg-paper overflow-hidden">
      <div className="p-4 sm:p-6 overflow-y-auto flex-1 flex justify-center w-full">
        <form id="upload-form" onSubmit={handleNativeSubmit} className="w-full max-w-[800px] flex flex-col gap-6 animate-fade-in pb-8">

          {/* Applicant Information Card */}
          <div className="bg-white border border-[#E5E7EB] rounded-[12px] shadow-sm overflow-hidden">
            <div className="h-[44px] border-b border-[#F0F0EE] bg-[#FAFAFA] flex items-center px-5 gap-2">
              <User size={14} className="text-[#8B8D98]" />
              <span className="text-[11px] font-semibold text-[#8B8D98] tracking-wider">APPLICANT INFORMATION</span>
            </div>
            <div className="p-5 flex flex-col gap-5">
              {/* Row 1: Name + Mobile */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="applicant_name" className={labelClass}>FULL NAME *</label>
                  <div className="relative">
                    <User size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#C4C5C9]" />
                    <input
                      id="applicant_name"
                      name="applicant_name"
                      required
                      disabled={submitting}
                      className={`${inputClass} pl-9 w-full`}
                      placeholder="e.g. Rajesh Kumar Mehta"
                    />
                  </div>
                </div>
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="mobile_no" className={labelClass}>MOBILE NUMBER</label>
                  <div className="relative">
                    <Phone size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#C4C5C9]" />
                    <input
                      id="mobile_no"
                      name="mobile_no"
                      type="tel"
                      disabled={submitting}
                      className={`${inputClass} pl-9 w-full`}
                      placeholder="+91 98765 43210"
                    />
                  </div>
                </div>
              </div>

              {/* Row 2: Application Type + Subtype */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="application_type" className={labelClass}>APPLICATION TYPE *</label>
                  <div className="relative">
                    <Briefcase size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#C4C5C9]" />
                    <select
                      id="application_type"
                      name="application_type"
                      required
                      disabled={submitting}
                      value={applicationType}
                      onChange={e => { setApplicationType(e.target.value); setApplicationSubtype('') }}
                      className={`${inputClass} pl-9 w-full appearance-none cursor-pointer`}
                    >
                      <option value="">Select type...</option>
                      {Object.keys(APPLICATION_TYPES).map(t => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                    <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#C4C5C9] pointer-events-none" />
                  </div>
                </div>
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="application_subtype" className={labelClass}>SUB-CATEGORY</label>
                  <div className="relative">
                    <select
                      id="application_subtype"
                      name="application_subtype"
                      disabled={submitting || !applicationType}
                      value={applicationSubtype}
                      onChange={e => setApplicationSubtype(e.target.value)}
                      className={`${inputClass} pl-3 w-full appearance-none cursor-pointer ${!applicationType ? 'opacity-50' : ''}`}
                    >
                      <option value="">{applicationType ? 'Select sub-category...' : 'Select type first'}</option>
                      {subtypes.map(s => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                    <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#C4C5C9] pointer-events-none" />
                  </div>
                </div>
              </div>

              {/* Row 3: Address */}
              <div className="flex flex-col gap-1.5">
                <label htmlFor="address" className={labelClass}>ADDRESS</label>
                <div className="relative">
                  <MapPin size={14} className="absolute left-3 top-3 text-[#C4C5C9]" />
                  <textarea
                    id="address"
                    name="address"
                    disabled={submitting}
                    rows={2}
                    className="w-full pl-9 px-3 py-2.5 rounded-[8px] border border-[#E5E7EB] bg-white text-[13px] text-text-primary outline-none focus:border-[#818CF8] focus:ring-2 focus:ring-[#EEF2FF] transition-all placeholder:text-[#C4C5C9] resize-none disabled:opacity-50"
                    placeholder="Flat 402, Wing B, Sai Residency, Baner Road, Pune 411045"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Document Upload Drop Zone */}
          <div
            className={`bg-sheet border-2 border-dashed rounded-[12px] p-10 flex flex-col items-center justify-center transition-all duration-200 ${
              dragging ? 'border-indigo bg-[#EEF2FF]' : 'border-[#E5E7EB] hover:border-[#C4C5C9]'
            }`}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
          >
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-3 transition-all duration-200 ${dragging ? 'bg-indigo text-white scale-110' : 'text-[#8B8D98]'}`}>
              <UploadIcon size={32} />
            </div>
            <div className="text-[16px] font-semibold text-text-primary mb-1">
              Drop documents here or click to browse
            </div>
            <div className="text-[13px] text-text-muted mb-6">
              All processing happens locally — no data leaves your machine
            </div>
            <div className="flex flex-wrap gap-2 justify-center">
              {['.pdf', '.jpg', '.png', '.tiff'].map(ext => (
                <button
                  key={ext}
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="px-3 py-1 rounded-[6px] bg-white border border-[#E5E7EB] hover:bg-raised text-[11px] font-mono font-semibold text-[#8B8D98] transition-colors"
                >
                  {ext}
                </button>
              ))}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              onChange={e => handleFiles(e.target.files)}
            />
          </div>

          {/* Processing Queue List */}
          {selectedFiles.length > 0 && (
            <div className="flex flex-col gap-3 animate-slide-up">
              <div className="text-[11px] font-semibold text-[#8B8D98] tracking-wider uppercase mb-1">
                PROCESSING QUEUE — {selectedFiles.length} DOCUMENT{selectedFiles.length > 1 ? 'S' : ''}
              </div>
              <div className="flex flex-col gap-3">
                {selectedFiles.map((file, i) => {
                  const docMock = {
                    id: file.name,
                    file_name: file.name,
                    file_size: file.size,
                    doc_category: 'Unknown'
                  }
                  const caseStatus = submitting ? 'processing' : 'uploaded'
                  return (
                    <DocumentCard
                      key={`${file.name}-${i}`}
                      doc={docMock}
                      caseStatus={caseStatus}
                      flags={[]}
                      delay={i * 60}
                    />
                  )
                })}
              </div>

              <div className="mt-6 flex items-center justify-between">
                <button
                  type="button"
                  onClick={onCancel}
                  className="h-[40px] px-5 rounded-[8px] text-[13px] font-medium text-text-secondary hover:bg-raised border border-[#E5E7EB] transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="h-[40px] bg-indigo hover:bg-indigo-mid text-white px-6 rounded-[8px] text-[13px] font-semibold flex items-center gap-2 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_2px_4px_rgba(79,70,229,0.15)] hover:shadow-[0_4px_12px_rgba(79,70,229,0.25)]"
                >
                  {submitting ? (
                    <>
                      <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    'Run Analysis →'
                  )}
                </button>
              </div>
            </div>
          )}
        </form>
      </div>
    </div>
  )
}
