import { Link, useLocation } from 'react-router-dom'
import { Microscope } from 'lucide-react'

export default function Navbar() {
  const location = useLocation()

  const isActive = (path) => location.pathname === path

  return (
    <header className="relative z-10 border-b" style={{ borderColor: 'var(--border)' }}>
      <div className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-3 cursor-pointer hover:opacity-80 transition-opacity">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #4361ee, #8b5cf6)' }}>
            <Microscope size={18} color="white" />
          </div>
          <div>
            <span className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>Talaash</span>
            <span className="text-xs ml-2 font-normal" style={{ color: 'var(--text-muted)' }}>Research Lab Finder</span>
          </div>
        </Link>

        {/* Navigation Links */}
        <nav className="flex items-center gap-6">
          <Link
            to="/"
            className="text-sm font-medium transition-colors"
            style={{
              color: isActive('/') ? 'var(--brand)' : 'var(--text-secondary)',
              borderBottom: isActive('/') ? '2px solid var(--brand)' : 'none',
              paddingBottom: '4px'
            }}
          >
            Home
          </Link>
          <Link
            to="/about"
            className="text-sm font-medium transition-colors"
            style={{
              color: isActive('/about') ? 'var(--brand)' : 'var(--text-secondary)',
              borderBottom: isActive('/about') ? '2px solid var(--brand)' : 'none',
              paddingBottom: '4px'
            }}
          >
            About
          </Link>
        </nav>
      </div>
    </header>
  )
}