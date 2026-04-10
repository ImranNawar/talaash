import { useState } from 'react'
import { Search, ChevronDown } from 'lucide-react'

const ACADEMIC_LEVELS = ['Undergrad', "Master's", 'PhD', 'Postdoc', 'Faculty']
const GOALS = ['Join a lab', 'Collaborate', 'Apply for PhD', 'Find internship']
const REGIONS = ['North America', 'Europe', 'Asia', 'Middle East', 'Latin America', 'Global']

export default function SearchForm({ onSearch }) {
  const [formData, setFormData] = useState({
    research_interests: '',
    technical_skills: '',
    academic_level: 'PhD',
    goal: 'Join a lab',
    keywords: '',
    preferred_region: '',
  })
  const [selectedRegions, setSelectedRegions] = useState([])
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState({})

  const toggleRegion = (region) => {
    setSelectedRegions(prev => {
      const next = prev.includes(region)
        ? prev.filter(r => r !== region)
        : [...prev, region]
      return next
    })
  }

  const validate = () => {
    const e = {}
    if (!formData.research_interests.trim()) e.research_interests = 'Required'
    if (!formData.technical_skills.trim()) e.technical_skills = 'Required'
    return e
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const e2 = validate()
    if (Object.keys(e2).length > 0) { setErrors(e2); return }
    setErrors({})
    setLoading(true)
    const payload = {
      ...formData,
      preferred_region: selectedRegions.length > 0 ? selectedRegions.join(', ') : 'Global',
    }
    await onSearch(payload)
    setLoading(false)
  }

  const set = (key) => (e) => {
    setFormData(prev => ({ ...prev, [key]: e.target.value }))
    if (errors[key]) setErrors(prev => ({ ...prev, [key]: undefined }))
  }

  return (
    <form onSubmit={handleSubmit} className="glass-card p-8 max-w-3xl mx-auto">
      {/* Research Interests */}
      <div className="mb-6">
        <label className="form-label">
          Research Interests <span style={{ color: '#ef4444' }}>*</span>
        </label>
        <textarea
          id="research_interests"
          className={`form-input ${errors.research_interests ? 'border-red-500' : ''}`}
          rows={3}
          placeholder="e.g. federated learning, privacy-preserving ML, autonomous navigation"
          value={formData.research_interests}
          onChange={set('research_interests')}
        />
        {errors.research_interests && (
          <p className="mt-1 text-xs" style={{ color: '#f87171' }}>{errors.research_interests}</p>
        )}
      </div>

      {/* Technical Skills */}
      <div className="mb-6">
        <label className="form-label">
          Technical Skills <span style={{ color: '#ef4444' }}>*</span>
        </label>
        <textarea
          id="technical_skills"
          className={`form-input ${errors.technical_skills ? 'border-red-500' : ''}`}
          rows={2}
          placeholder="e.g. Python, PyTorch, CUDA, FPGA, ROS"
          value={formData.technical_skills}
          onChange={set('technical_skills')}
        />
        {errors.technical_skills && (
          <p className="mt-1 text-xs" style={{ color: '#f87171' }}>{errors.technical_skills}</p>
        )}
      </div>

      {/* Academic Level + Goal (2 columns) */}
      <div className="grid grid-cols-2 gap-5 mb-6">
        <div>
          <label className="form-label">Academic Level</label>
          <div className="relative">
            <select
              id="academic_level"
              className="form-input pr-10 appearance-none"
              value={formData.academic_level}
              onChange={set('academic_level')}
            >
              {ACADEMIC_LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
            </select>
            <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none"
              style={{ color: 'var(--text-muted)' }} />
          </div>
        </div>
        <div>
          <label className="form-label">Goal</label>
          <div className="relative">
            <select
              id="goal"
              className="form-input pr-10 appearance-none"
              value={formData.goal}
              onChange={set('goal')}
            >
              {GOALS.map(g => <option key={g} value={g}>{g}</option>)}
            </select>
            <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none"
              style={{ color: 'var(--text-muted)' }} />
          </div>
        </div>
      </div>

      {/* Keywords */}
      <div className="mb-6">
        <label className="form-label">
          Keywords / Buzzwords <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>(optional)</span>
        </label>
        <input
          id="keywords"
          type="text"
          className="form-input"
          placeholder="e.g. differential privacy, LLM alignment, neuromorphic"
          value={formData.keywords}
          onChange={set('keywords')}
        />
      </div>

      {/* Preferred Region */}
      <div className="mb-8">
        <label className="form-label">
          Preferred Region <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>(optional, multi-select)</span>
        </label>
        <div className="flex flex-wrap gap-2">
          {REGIONS.map(region => (
            <div
              key={region}
              id={`region-${region.replace(/\s+/g, '-').toLowerCase()}`}
              className={`region-check ${selectedRegions.includes(region) ? 'selected' : ''}`}
              onClick={() => toggleRegion(region)}
            >
              <div className={`w-3.5 h-3.5 rounded flex items-center justify-center flex-shrink-0`}
                style={{
                  border: selectedRegions.includes(region) ? 'none' : '1.5px solid #cbd5e0',
                  background: selectedRegions.includes(region) ? 'var(--brand)' : 'transparent',
                }}>
                {selectedRegions.includes(region) && (
                  <svg width="8" height="6" viewBox="0 0 8 6" fill="none">
                    <path d="M1 3L3 5L7 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                )}
              </div>
              {region}
            </div>
          ))}
        </div>
      </div>

      {/* Submit */}
      <button
        id="search-submit"
        type="submit"
        disabled={loading}
        className="btn-primary w-full flex items-center justify-center gap-3"
      >
        {loading ? (
          <>
            <div className="spinner" />
            Initiating Pipeline…
          </>
        ) : (
          <>
            <Search size={18} />
            Find Research Labs
          </>
        )}
      </button>

      <p className="text-center mt-4 text-xs" style={{ color: 'var(--text-muted)' }}>
        Takes 1-3 minutes · Runs a 7-phase AI pipeline · Results vary based on API quotas
      </p>
    </form>
  )
}
