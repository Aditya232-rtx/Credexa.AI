export function getDocInfo(d, status, flags) {
  const isPdf = d.file_name.toLowerCase().endsWith('.pdf')
  const ext = isPdf ? 'PDF' : 'IMG'
  
  // Format file size correctly
  let sizeStr = '0 B'
  if (d.file_size) {
    if (d.file_size < 1024) sizeStr = `${d.file_size} B`
    else if (d.file_size < 1024 * 1024) sizeStr = `${(d.file_size / 1024).toFixed(0)} KB`
    else sizeStr = `${(d.file_size / 1024 / 1024).toFixed(1)} MB`
  }

  let cat = d.doc_category || 'Unknown'
  const fname = d.file_name.toLowerCase()
  if (fname.includes('bank') || fname.includes('statement')) cat = 'Financial'
  else if (fname.includes('itr') || fname.includes('tax') || fname.includes('pnl')) cat = 'Tax Document'
  else if (fname.includes('aadhaar') || fname.includes('pan') || fname.includes('passport')) cat = 'Identity Document'
  else if (fname.includes('deed') || fname.includes('poa')) cat = 'Legal Document'

  const isProcessing = status === 'processing' || status === 'uploaded'

  // Calculate score based on actual backend flags for this document
  const docFlags = flags.filter(f => f.document_id === d.id || f.finding.includes(d.file_name))
  let score = 0
  if (!isProcessing) {
    // If no flags, it's 0. Otherwise sum up to 100.
    score = Math.min(100, docFlags.reduce((acc, f) => acc + (f.score || 20), 0))
  }

  let scoreColor = ''
  let lineClass = ''
  if (!isProcessing) {
    if (score >= 60) {
      scoreColor = 'bg-[#FEF2F2] text-[#DC2626]' // Light red bg, red text
      lineClass = 'bg-[#DC2626]'
    } else if (score > 0) {
      scoreColor = 'bg-[#FFFBEB] text-[#D97706]' // Light amber bg, amber text
      lineClass = 'bg-[#D97706]'
    } else {
      scoreColor = 'bg-[#F0FDF4] text-[#16A34A]' // Usually not shown if safe, but if needed
      lineClass = 'bg-[#16A34A]' // Green line
    }
  } else {
    lineClass = 'bg-indigo'
  }

  let layers = []
  if (isProcessing) {
    layers = [
      { name: 'OCR ✓', type: 'done' },
      { name: 'Metadata ✓', type: 'done' },
      { name: isPdf ? 'Math Analysis...' : 'PRNU Analysis...', type: 'processing' },
      { name: isPdf ? 'TRACES API' : 'DCT Check', type: 'pending' },
      { name: 'Gov Source API', type: 'pending' }
    ]
  } else {
    // We derive layers, but if a layer was flagged, we mark it as alert
    const flaggedLayers = docFlags.map(f => f.layer)
    const addLayer = (name, rawName) => {
      if (flaggedLayers.includes(rawName)) {
        layers.push({ name: name.replace('✓', '✗'), type: 'alert' })
      } else {
        layers.push({ name, type: 'done' })
      }
    }

    addLayer('OCR ✓', 'OCR')
    addLayer('Metadata ✓', 'Metadata')
    
    if (cat === 'Financial') {
      addLayer('ELA ✓', 'ELA')
      addLayer('Math ✓', 'Math')
    } else if (cat === 'Tax Document') {
      addLayer('Math ✓', 'Math')
      addLayer('TRACES API ✓', 'TRACES API')
    } else {
      addLayer('PRNU Check ✓', 'PRNU Check')
      addLayer('DCT Check ✓', 'DCT Check')
      addLayer('Gov Source API ✓', 'Gov Source API')
    }
    layers.push({ name: 'Complete', type: 'complete' })
  }

  return { ext, cat, sizeStr, score, scoreColor, lineClass, isProcessing, layers }
}

export function DocumentCard({ doc, caseStatus, flags, delay }) {
  const info = getDocInfo(doc, caseStatus, flags)

  return (
    <div className="bg-white border border-border rounded-[8px] p-3 flex flex-col gap-2.5 shadow-sm animate-fade-in w-full max-w-full overflow-hidden" style={{ animationDelay: `${delay}ms` }}>
      {/* Top Row */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-8 h-8 rounded border border-border bg-[#F9FAFB] flex items-center justify-center shrink-0 text-[10px] font-mono text-text-muted font-semibold">
            {info.ext}
          </div>
          <div className="min-w-0">
            <div className="text-[13px] font-semibold text-text-primary truncate">{doc.file_name}</div>
            <div className="text-[11px] text-text-muted mt-0.5 flex items-center gap-1 flex-wrap">
              <span>{info.sizeStr}</span>
              <span>·</span>
              <span>{info.cat}</span>
            </div>
          </div>
        </div>
        <div className="shrink-0">
          {info.isProcessing ? (
            <span className="text-[12px] text-text-ghost font-medium">Processing...</span>
          ) : (
            <span className={`px-2 py-0.5 rounded-[4px] text-[11px] font-bold ${info.scoreColor}`}>
              Score {info.score}
            </span>
          )}
        </div>
      </div>

      {/* Progress Line */}
      <div className="w-full h-[2px] bg-[#EEEEEC] overflow-hidden">
        {info.isProcessing ? (
          <div className="h-full bg-indigo w-[60%] animate-pulse" />
        ) : (
          <div className={`h-full w-full ${info.lineClass}`} />
        )}
      </div>

      {/* Layers */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {info.layers.map((layer, idx) => {
          let badgeClass = ''
          if (layer.type === 'done') {
            badgeClass = 'text-[#16A34A] bg-[#F0FDF4] border border-[#DCFCE7]'
          } else if (layer.type === 'complete') {
            badgeClass = 'text-white bg-[#16A34A] border border-[#16A34A]'
          } else if (layer.type === 'processing') {
            badgeClass = 'text-indigo bg-[#EEF2FF] border border-[#E0E7FF] animate-pulse'
          } else if (layer.type === 'alert') {
            badgeClass = 'text-[#DC2626] bg-[#FEF2F2] border border-[#FEE2E2]'
          } else {
            badgeClass = 'text-[#9CA3AF] bg-[#F3F4F6] border border-[#E5E7EB]'
          }

          return (
            <span key={idx} className={`px-1.5 py-[1px] rounded text-[10px] font-semibold tracking-wide ${badgeClass}`}>
              {layer.name}
            </span>
          )
        })}
      </div>
    </div>
  )
}
