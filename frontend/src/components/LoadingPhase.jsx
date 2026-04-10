import { CheckCircle, Circle, Loader } from 'lucide-react'

const PHASE_ICONS = ['👤', '🔍', '🌐', '📄', '🧠', '⚖️', '✨']

export default function LoadingPhase({ phases }) {
  const completedCount = phases.filter(p => p.status === 'done').length
  const progress = (completedCount / phases.length) * 100

  return (
    <div className="max-w-xl mx-auto">
      {/* Overall progress bar */}
      <div className="mb-8 glass-card p-5">
        <div className="flex justify-between items-center mb-3">
          <span className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
            Overall Progress
          </span>
          <span className="text-sm font-bold" style={{ color: 'var(--brand-light)' }}>
            {completedCount} / {phases.length} phases
          </span>
        </div>
        <div className="score-bar-track">
          <div
            className="score-bar-fill"
            style={{
              width: `${progress}%`,
              background: 'linear-gradient(90deg, #4361ee, #8b5cf6)',
              transition: 'width 0.6s ease',
            }}
          />
        </div>
      </div>

      {/* Phase list */}
      <div className="glass-card overflow-hidden divide-y" style={{ borderColor: 'var(--border)' }}>
        {phases.map((phase, i) => (
          <div
            key={phase.phase}
            className="phase-item"
            style={{
              background: phase.status === 'running' ? '#f0f2f5' : 'transparent',
            }}
          >
            {/* Icon */}
            <div className="text-lg w-7 text-center flex-shrink-0">
              {PHASE_ICONS[i]}
            </div>

            {/* Status dot */}
            <div className={`phase-dot ${phase.status}`} />

            {/* Label + detail */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span
                  className="text-sm font-medium"
                  style={{
                    color: phase.status === 'done'
                      ? 'var(--text-secondary)'
                      : phase.status === 'running'
                      ? 'var(--text-primary)'
                      : 'var(--text-muted)'
                  }}
                >
                  Phase {phase.phase}: {phase.label}
                </span>
                {phase.status === 'running' && (
                  <div className="spinner" style={{ width: 14, height: 14 }} />
                )}
              </div>
              {phase.detail && phase.status !== 'pending' && (
                <p className="text-xs mt-0.5 truncate" style={{ color: 'var(--text-muted)' }}>
                  {phase.detail}
                </p>
              )}
            </div>

            {/* Right icon */}
            <div className="flex-shrink-0">
              {phase.status === 'done' && (
                <CheckCircle size={16} style={{ color: '#10b981' }} />
              )}
              {phase.status === 'pending' && (
                <Circle size={16} style={{ color: 'var(--text-muted)', opacity: 0.4 }} />
              )}
              {phase.status === 'running' && (
                <Loader size={16} style={{ color: 'var(--brand-light)' }}
                  className="animate-spin" />
              )}
            </div>
          </div>
        ))}
      </div>

      <p className="text-center mt-6 text-sm" style={{ color: 'var(--text-muted)' }}>
        Talaash is scraping and analyzing research groups worldwide…
      </p>
    </div>
  )
}
