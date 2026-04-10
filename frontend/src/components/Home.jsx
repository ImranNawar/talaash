import { useState } from 'react'
import SearchForm from './SearchForm.jsx'
import LoadingPhase from './LoadingPhase.jsx'
import ResultCard from './ResultCard.jsx'
import { Search, Microscope } from 'lucide-react'

const PHASE_LABELS = [
  'Analyzing your profile',
  'Expanding search queries',
  'Discovering research labs',
  'Scraping and extracting lab data',
  'Building knowledge base',
  'Matching and ranking labs',
  'Preparing your results',
]

const INITIAL_PHASES = PHASE_LABELS.map((label, i) => ({
  phase: i + 1,
  label,
  status: 'pending',
  detail: '',
}))

export default function Home() {
  const [view, setView] = useState('form')
  const [phases, setPhases] = useState(INITIAL_PHASES)
  const [results, setResults] = useState([])
  const [totalFound, setTotalFound] = useState(0)
  const [error, setError] = useState(null)

  const handleSearch = async (formData) => {
    setPhases(INITIAL_PHASES)
    setResults([])
    setError(null)
    setView('loading')

    try {
      const response = await fetch('/api/search/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      })

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop()

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue
          try {
            const data = JSON.parse(raw)

            if (data.type === 'results') {
              setTotalFound(data.total_candidates || 0)
              setResults(data.results || [])
              setView('results')
            } else if (data.type === 'error') {
              setView('results')
            } else if (data.phase) {
              setPhases(prev => prev.map(p =>
                p.phase === data.phase
                  ? { ...p, status: data.status, detail: data.detail || '' }
                  : p
              ))
            }
          } catch (e) {
            // ignore parse errors
          }
        }
      }
    } catch (err) {
      setResults([])
      setView('results')
    }
  }

  const handleReset = () => {
    setView('form')
    setResults([])
    setPhases(INITIAL_PHASES)
    setError(null)
  }

  return (
    <>
      {/* Decorative orbs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -left-40 w-96 h-96 rounded-full opacity-10"
          style={{ background: 'radial-gradient(circle, #4361ee, transparent)' }} />
        <div className="absolute top-1/3 -right-40 w-80 h-80 rounded-full opacity-8"
          style={{ background: 'radial-gradient(circle, #8b5cf6, transparent)' }} />
        <div className="absolute -bottom-40 left-1/3 w-72 h-72 rounded-full opacity-5"
          style={{ background: 'radial-gradient(circle, #4361ee, transparent)' }} />
      </div>

      <main className="relative z-10 max-w-6xl mx-auto px-6 pb-20 min-h-[60vh]">
        {/* FORM VIEW */}
        {view === 'form' && (
          <div className="animate-fade-in">
            <div className="text-center pt-16 pb-12">
              <h1 className="text-5xl font-extrabold mb-4 leading-tight" style={{ color: 'var(--text-primary)' }}>
                Find Your Perfect{' '}
                <span style={{
                  background: 'linear-gradient(135deg, #4361ee, #8b5cf6)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}>
                  Research Lab
                </span>
              </h1>
              <p className="text-lg max-w-2xl mx-auto" style={{ color: 'var(--text-secondary)' }}>
                Describe your research profile and let Talaash discover, scrape, and rank
                matching labs worldwide using a 7-phase AI pipeline.
              </p>
            </div>

            <SearchForm onSearch={handleSearch} />
          </div>
        )}

        {/* LOADING VIEW */}
        {view === 'loading' && (
          <div className="animate-fade-in pt-16">
            <div className="text-center mb-10">
              <h2 className="text-3xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>
                Searching the world&apos;s research labs…
              </h2>
              <p style={{ color: 'var(--text-secondary)' }}>
                Running a 7-phase AI pipeline. This may take a minute.
              </p>
            </div>
            <LoadingPhase phases={phases} />
          </div>
        )}

        {/* RESULTS VIEW */}
        {view === 'results' && (
          <div className="animate-fade-in pt-10">
            <div className="flex items-center justify-between mb-8">
              <div>
                <h2 className="text-3xl font-bold" style={{ color: 'var(--text-primary)' }}>
                  {results.length > 0 ? `${results.length} Matched Labs` : 'No Matches Found'}
                </h2>
                {totalFound > 0 && (
                  <p className="mt-1 text-sm" style={{ color: 'var(--text-muted)' }}>
                    Scanned {totalFound} candidate pages · Showing top {results.length} by match score
                  </p>
                )}
              </div>
              <button onClick={handleReset} className="btn-primary flex items-center gap-2 text-sm py-3 px-5">
                <Search size={15} />
                New Search
              </button>
            </div>

            {results.length === 0 ? (
              <div className="text-center py-20 glass-card">
                <div className="text-5xl mb-4">🔬</div>
                <p className="text-lg font-medium mb-2" style={{ color: 'var(--text-primary)' }}>No matching labs found</p>
                <p style={{ color: 'var(--text-muted)' }}>
                  Try broadening your research interests or check your API keys.
                </p>
              </div>
            ) : (
              <div className="space-y-5">
                {results.map((result, i) => (
                  <ResultCard key={result.profile?.lab_url || i} result={result} rank={i + 1} />
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </>
  )
}