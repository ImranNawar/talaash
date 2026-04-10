import { useEffect, useState } from 'react'

export default function ScoreBar({ score }) {
  const [width, setWidth] = useState(0)

  useEffect(() => {
    const t = setTimeout(() => setWidth(score), 100)
    return () => clearTimeout(t)
  }, [score])

  const getColor = (s) => {
    if (s >= 70) return 'linear-gradient(90deg, #059669, #10b981)'
    if (s >= 40) return 'linear-gradient(90deg, #b45309, #f59e0b)'
    return 'linear-gradient(90deg, #b91c1c, #ef4444)'
  }

  const getTextColor = (s) => {
    if (s >= 70) return '#34d399'
    if (s >= 40) return '#fbbf24'
    return '#f87171'
  }

  const getLabel = (s) => {
    if (s >= 80) return 'Excellent Match'
    if (s >= 65) return 'Strong Match'
    if (s >= 50) return 'Good Match'
    if (s >= 35) return 'Moderate Match'
    return 'Weak Match'
  }

  return (
    <div className="w-full">
      <div className="flex justify-between items-baseline mb-2">
        <span className="text-xs font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
          Match Score
        </span>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-extrabold" style={{ color: getTextColor(score) }}>
            {Math.round(score)}
          </span>
          <span className="text-sm" style={{ color: 'var(--text-muted)' }}>/100</span>
          <span className="text-xs font-medium px-2 py-0.5 rounded-full" style={{
            background: getTextColor(score) + '20',
            color: getTextColor(score),
          }}>
            {getLabel(score)}
          </span>
        </div>
      </div>
      <div className="score-bar-track">
        <div
          className="score-bar-fill"
          style={{
            width: `${width}%`,
            background: getColor(score),
          }}
        />
      </div>
    </div>
  )
}
