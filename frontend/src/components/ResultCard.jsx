import { useState } from 'react'
import {
  ExternalLink, Mail, Github, BookOpen,
  FlaskConical, ChevronDown, ChevronUp, User
} from 'lucide-react'
import ScoreBar from './ScoreBar.jsx'

function AcceptingBadge({ value }) {
  if (value === true)  return <span className="badge badge-green">✓ Accepting Students</span>
  if (value === false) return <span className="badge badge-red">✗ Not Accepting</span>
  return <span className="badge badge-grey">? Status Unknown</span>
}

function TagList({ items, max = 6 }) {
  if (!items || items.length === 0) return null
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.slice(0, max).map((item, i) => (
        <span key={i} className="tag">{item}</span>
      ))}
      {items.length > max && (
        <span className="tag" style={{ opacity: 0.6 }}>+{items.length - max} more</span>
      )}
    </div>
  )
}

export default function ResultCard({ result, rank }) {
  const { profile, final_score, match_reasons, gaps, has_recent_publication } = result
  const [expanded, setExpanded] = useState(false)

  const displayName = profile.lab_name || `${profile.pi_name || 'Research Group'}'s Lab`
  const displayInstitution = [profile.university, profile.department].filter(Boolean).join(' · ')

  return (
    <div className="result-card glass-card p-6">
      {/* ── Top row: rank + name + badge ─────────────────────────────────── */}
      <div className="flex items-start gap-4 mb-5">
        {/* Rank */}
        <div className="flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold"
          style={{
            background: rank <= 3
              ? 'linear-gradient(135deg, #4361ee, #8b5cf6)'
              : '#f0f2f5',
            color: rank <= 3 ? 'white' : '#718096',
          }}>
          #{rank}
        </div>

        {/* Name block */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3 flex-wrap">
            <div>
              {profile.lab_url ? (
                <a
                  href={profile.lab_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-lg font-bold hover:underline flex items-center gap-1.5 group"
                  style={{ color: 'var(--text-primary)' }}
                >
                  {displayName}
                  <ExternalLink size={13} style={{ color: 'var(--brand-light)', opacity: 0.7 }}
                    className="group-hover:opacity-100 transition-opacity" />
                </a>
              ) : (
                <span className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
                  {displayName}
                </span>
              )}
              {profile.pi_name && (
                <div className="flex items-center gap-1.5 mt-0.5">
                  <User size={12} style={{ color: 'var(--text-muted)' }} />
                  <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                    PI: {profile.pi_name}
                  </span>
                </div>
              )}
              {displayInstitution && (
                <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  {displayInstitution}
                </p>
              )}
            </div>
            <div className="flex flex-col items-end gap-2">
              <AcceptingBadge value={profile.is_accepting_students} />
              {has_recent_publication && (
                <span className="badge badge-green" style={{ fontSize: '0.65rem' }}>
                  📄 Recent Publications
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── Score bar ────────────────────────────────────────────────────── */}
      <div className="mb-5">
        <ScoreBar score={final_score} />
      </div>

      {/* ── Match Reasons ────────────────────────────────────────────────── */}
      {match_reasons && match_reasons.length > 0 && (
        <div className="mb-4 p-4 rounded-xl"
          style={{ background: '#e0e9ff', border: '1px solid #c2d3ff' }}>
          <p className="text-xs font-semibold uppercase tracking-widest mb-2.5"
            style={{ color: '#4361ee' }}>
            ✦ Why This Lab Matches
          </p>
          <ul className="space-y-1.5">
            {match_reasons.map((reason, i) => (
              <li key={i} className="flex items-start gap-2 text-sm"
                style={{ color: 'var(--text-secondary)' }}>
                <span className="mt-0.5 text-xs flex-shrink-0" style={{ color: 'var(--brand-light)' }}>●</span>
                {reason}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Gaps ─────────────────────────────────────────────────────────── */}
      {gaps && gaps.length > 0 && (
        <div className="mb-4 p-4 rounded-xl"
          style={{ background: '#fef3c7', border: '1px solid #fde68a' }}>
          <p className="text-xs font-semibold uppercase tracking-widest mb-2.5"
            style={{ color: '#ca8a04' }}>
            △ Skills Gap / You'd Learn
          </p>
          <ul className="space-y-1.5">
            {gaps.map((gap, i) => (
              <li key={i} className="flex items-start gap-2 text-sm"
                style={{ color: 'var(--text-secondary)' }}>
                <span className="mt-0.5 text-xs flex-shrink-0" style={{ color: '#f59e0b' }}>▸</span>
                {gap}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Research Areas ───────────────────────────────────────────────── */}
      {profile.research_areas && profile.research_areas.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>
            Research Areas
          </p>
          <TagList items={profile.research_areas} max={8} />
        </div>
      )}

      {/* ── Expand / Collapse ────────────────────────────────────────────── */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs font-medium mt-3 mb-1 transition-colors"
        style={{ color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}
        onMouseEnter={e => e.currentTarget.style.color = 'var(--brand-light)'}
        onMouseLeave={e => e.currentTarget.style.color = 'var(--text-muted)'}
      >
        {expanded ? <ChevronUp size={14}/> : <ChevronDown size={14}/>}
        {expanded ? 'Show less' : 'Show more details'}
      </button>

      {expanded && (
        <div className="mt-4 space-y-4 animate-fade-in">
          <div className="divider" />

          {/* Current Projects */}
          {profile.current_projects && profile.current_projects.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <FlaskConical size={13} style={{ color: 'var(--accent)' }} />
                <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                  Current Projects
                </p>
              </div>
              <ul className="space-y-1.5">
                {profile.current_projects.slice(0, 5).map((proj, i) => (
                  <li key={i} className="text-sm flex items-start gap-2" style={{ color: 'var(--text-secondary)' }}>
                    <span className="flex-shrink-0 mt-1.5 w-1 h-1 rounded-full"
                      style={{ background: 'var(--accent)', display: 'inline-block', minWidth: 4 }} />
                    {proj}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Recent Publications */}
          {profile.recent_publications && profile.recent_publications.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <BookOpen size={13} style={{ color: '#f59e0b' }} />
                <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                  Recent Publications
                </p>
              </div>
              <ul className="space-y-2">
                {profile.recent_publications.slice(0, 4).map((pub, i) => (
                  <li key={i} className="text-sm flex items-start gap-2" style={{ color: 'var(--text-secondary)' }}>
                    <span className="flex-shrink-0 text-xs font-bold mt-0.5 px-1.5 py-0.5 rounded"
                      style={{ background: 'rgba(245,158,11,0.1)', color: '#f59e0b' }}>
                      {pub.year}
                    </span>
                    <span>{pub.title}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Methods */}
          {profile.methods_used && profile.methods_used.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>
                Methods & Tools
              </p>
              <TagList items={profile.methods_used} max={10} />
            </div>
          )}

          {/* Student requirements */}
          {profile.student_requirements && (
            <div className="p-3 rounded-lg" style={{ background: '#f8f9fa' }}>
              <p className="text-xs font-semibold uppercase tracking-widest mb-1" style={{ color: 'var(--text-muted)' }}>
                Student Requirements
              </p>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                {profile.student_requirements}
              </p>
            </div>
          )}

          {/* Links row */}
          <div className="flex items-center flex-wrap gap-3 pt-1">
            {profile.contact_email && (
              <a
                href={`mailto:${profile.contact_email}`}
                className="flex items-center gap-1.5 text-sm font-medium transition-opacity hover:opacity-80"
                style={{ color: 'var(--brand-light)' }}
              >
                <Mail size={14} />
                {profile.contact_email}
              </a>
            )}
            {profile.github_url && (
              <a
                href={profile.github_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-sm font-medium transition-opacity hover:opacity-80"
                style={{ color: 'var(--text-secondary)' }}
              >
                <Github size={14} />
                GitHub
              </a>
            )}
            {profile.lab_url && (
              <a
                href={profile.lab_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-sm font-medium transition-opacity hover:opacity-80"
                style={{ color: 'var(--brand-light)' }}
              >
                <ExternalLink size={14} />
                Visit Lab Page
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
