export default function RiskGauge({ score = 0, size = 96 }) {
  const r = 36
  const circumference = 2 * Math.PI * r
  const offset = circumference * (1 - score / 100)

  let color = '#16A34A' // clear
  if (score >= 60) color = '#DC2626' // alarm
  else if (score >= 20) color = '#D97706' // caution

  return (
    <svg width={size} height={size} viewBox="0 0 96 96" className="shrink-0">
      {/* Track */}
      <circle cx="48" cy="48" r={r} fill="none" stroke="#EBEBEA" strokeWidth="7" />
      {/* Fill */}
      <circle
        cx="48" cy="48" r={r}
        fill="none"
        stroke={color}
        strokeWidth="7"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform="rotate(-90 48 48)"
        opacity="0.9"
        className="gauge-arc"
        style={{ '--target-offset': offset }}
      />
      {/* Score */}
      <text
        x="48" y="44"
        textAnchor="middle"
        fill={color}
        fontSize="22"
        fontWeight="700"
        fontFamily="'JetBrains Mono', monospace"
      >
        {score}
      </text>
      {/* Label */}
      <text
        x="48" y="57"
        textAnchor="middle"
        fill="#BBBBBB"
        fontSize="8.5"
        fontFamily="'Inter', sans-serif"
        letterSpacing="0.08em"
      >
        RISK
      </text>
    </svg>
  )
}
