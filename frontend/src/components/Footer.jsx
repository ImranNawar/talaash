import { Github, Linkedin, Mail } from 'lucide-react'

export default function Footer() {
  const currentYear = new Date().getFullYear()

  return (
    <footer className="relative z-10 border-t mt-20" style={{ borderColor: 'var(--border)' }}>
      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
          {/* Brand Section */}
          <div>
            <h3 className="text-lg font-bold mb-3" style={{ color: 'var(--text-primary)' }}>Talaash</h3>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Discover research labs worldwide using AI-powered matching and comprehensive data extraction.
            </p>
          </div>

          {/* Links Section */}
          <div>
            <h4 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Navigation</h4>
            <ul className="space-y-2 text-sm" style={{ color: 'var(--text-secondary)' }}>
              <li><a href="/" className="hover:opacity-75 transition-opacity">Home</a></li>
              <li><a href="/about" className="hover:opacity-75 transition-opacity">About</a></li>
            </ul>
          </div>

          {/* Contact Section */}
          <div>
            <h4 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Connect</h4>
            <div className="flex items-center gap-4">
              <a href="https://github.com/ImranNawar" className="p-2 rounded-lg transition-colors"
                style={{ background: '#e0e9ff', color: '#4361ee' }}
                title="GitHub">
                <Github size={18} />
              </a>
              <a href="https://www.linkedin.com/in/imran-nawar/" className="p-2 rounded-lg transition-colors"
                style={{ background: '#e0e9ff', color: '#4361ee' }}
                title="LinkedIn">
                <Linkedin size={18} />
              </a>
              <a href="imran1nawar@gmail.com" className="p-2 rounded-lg transition-colors"
                style={{ background: '#e0e9ff', color: '#4361ee' }}
                title="Email">
                <Mail size={18} />
              </a>
            </div>
          </div>
        </div>

        {/* Divider */}
        <div style={{ borderTop: '1px solid var(--border)', marginBottom: '16px' }} />

        {/* Bottom Section */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-sm" style={{ color: 'var(--text-muted)' }}>
          <p>&copy; {currentYear} Talaash. All rights reserved.</p>
          <div className="flex items-center gap-6">
            <a href="#" className="hover:opacity-75 transition-opacity">Privacy Policy</a>
            <a href="#" className="hover:opacity-75 transition-opacity">Terms of Service</a>
          </div>
        </div>
      </div>
    </footer>
  )
}