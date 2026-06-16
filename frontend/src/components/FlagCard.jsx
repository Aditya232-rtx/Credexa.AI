export default function FlagCard({ layer, finding, severity, score }) {
  const colorMap = {
    high:   { dot: '#DC2626', bar: '#DC2626', text: '#DC2626' },
    medium: { dot: '#D97706', bar: '#D97706', text: '#D97706' },
    low:    { dot: '#16A34A', bar: '#16A34A', text: '#16A34A' },
  }
  const c = colorMap[severity] || colorMap.low

  return (
    <div className="flex items-center gap-[10px] px-[15px] py-[11px] border-b border-raised last:border-b-0">
      <div className="w-[7px] h-[7px] rounded-sm shrink-0" style={{ background: c.dot }} />
      <div className="text-label text-text-muted font-medium w-[120px] shrink-0">{layer}</div>
      <div className="text-data-sm text-text-ghost flex-1 leading-[1.4]">{finding}</div>
      <div className="shrink-0 flex items-center gap-[7px]">
        <div className="w-[72px] h-[3px] bg-[#EEEEEC] rounded-sm overflow-hidden">
          <div className="h-full rounded-sm" style={{ width: `${score}%`, background: c.bar }} />
        </div>
        <span className="text-data-sm font-mono min-w-[46px] text-right" style={{ color: c.text }}>
          {score} / 100
        </span>
      </div>
    </div>
  )
}
