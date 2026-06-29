export default function RiskGauge({ score, size = 100 }) {
  const r = (size - 20) / 2
  const circ = 2 * Math.PI * r
  const offset = circ * (1 - Math.min(100, Math.max(0, score)) / 100)
  const color = score < 20 ? '#16A34A' : score < 60 ? '#D97706' : '#DC2626'

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#F0F0EE" strokeWidth="8" />
      <circle
        cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth="8"
        strokeDasharray={circ} strokeDashoffset={offset}
        strokeLinecap="round" transform={`rotate(-90 ${size / 2} ${size / 2})`}
        style={{ transition: 'stroke-dashoffset 0.8s ease-in-out' }}
      />
      <text x="50%" y="50%" textAnchor="middle" dy="0.35em"
        fill="currentColor" fontSize={size * 0.22} fontFamily="JetBrains Mono, monospace"
        fontWeight="700" className="text-text-primary"
      >
        {score}
      </text>
    </svg>
  )
}