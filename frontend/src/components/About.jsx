export default function About() {
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

      <main className="relative z-10 max-w-4xl mx-auto px-6 pb-20 min-h-[60vh]">
        <div className="animate-fade-in pt-16">
          {/* Page Title */}
          <div className="text-center mb-12">
            <h1 className="text-5xl font-extrabold mb-4 leading-tight" style={{ color: 'var(--text-primary)' }}>
              About Talaash
            </h1>
          </div>

          {/* Description Sections */}
          <div className="space-y-8">
            {/* Overview Section */}
            <section className="p-8 rounded-xl transition-all hover:shadow-lg"
              style={{
                background: '#ffffff',
                border: '1px solid #e0e4e8',
                backdropFilter: 'blur(10px)'
              }}>
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--brand)' }}>What is Talaash?</h2>
              <p className="text-base leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                Talaash is an intelligent research lab discovery platform that combines artificial intelligence, 
                web scraping, and machine learning to help you find the perfect research lab matching your 
                academic interests and research profile. Whether you're looking for collaboration opportunities, 
                internships, or exploring potential research partnerships, Talaash streamlines the discovery process.
              </p>
            </section>

            {/* 7-Phase Pipeline */}
            <section className="p-8 rounded-xl transition-all hover:shadow-lg"
              style={{
                background: '#ffffff',
                border: '1px solid #e0e4e8',
                backdropFilter: 'blur(10px)'
              }}>
              <h2 className="text-2xl font-bold mb-6" style={{ color: 'var(--brand)' }}>Our 7-Phase AI Pipeline</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  { num: 1, title: 'Analyzing Your Profile', desc: 'Understanding your research interests and academic background' },
                  { num: 2, title: 'Expanding Search Queries', desc: 'Generating comprehensive search variations for better coverage' },
                  { num: 3, title: 'Discovering Research Labs', desc: 'Identifying relevant laboratories across global databases' },
                  { num: 4, title: 'Scraping Lab Data', desc: 'Extracting detailed information from lab websites and profiles' },
                  { num: 5, title: 'Building Knowledge Base', desc: 'Creating a comprehensive vectorized knowledge base' },
                  { num: 6, title: 'Matching & Ranking', desc: 'AI-powered matching algorithm to rank labs by compatibility' },
                  { num: 7, title: 'Preparing Results', desc: 'Formatting and presenting results with detailed analytics' },
                ].map((phase) => (
                  <div key={phase.num} className="p-4 rounded-lg"
                    style={{
                      background: '#f0f2f5',
                      border: '1px solid #e0e4e8'
                    }}>
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold"
                        style={{
                          background: 'linear-gradient(135deg, #4361ee, #8b5cf6)',
                          color: 'white'
                        }}>
                        {phase.num}
                      </div>
                      <div>
                        <h3 className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                          {phase.title}
                        </h3>
                        <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
                          {phase.desc}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* Key Features */}
            <section className="p-8 rounded-xl transition-all hover:shadow-lg"
              style={{
                background: '#ffffff',
                border: '1px solid #e0e4e8',
                backdropFilter: 'blur(10px)'
              }}>
              <h2 className="text-2xl font-bold mb-6" style={{ color: 'var(--brand)' }}>Key Features</h2>
              <ul className="space-y-4">
                {[
                  'AI-Powered Matching: Our machine learning algorithms analyze your profile to find labs with optimal compatibility',
                  'Global Coverage: Search across research institutions worldwide with comprehensive data extraction',
                  'Fast Discovery: Get results in minutes instead of hours of manual research',
                  'Detailed Analytics: Comprehensive matching scores and lab information for informed decisions',
                  'Smart Ranking: Laboratories ranked by relevance and alignment with your research interests',
                  'Real-Time Updates: Fresh data from multiple sources ensures accurate and current information'
                ].map((feature, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-5 h-5 rounded-full mt-1" style={{
                      background: 'linear-gradient(135deg, #4361ee, #8b5cf6)'
                    }}></span>
                    <span style={{ color: 'var(--text-secondary)' }}>{feature}</span>
                  </li>
                ))}
              </ul>
            </section>

            {/* How It Works */}
            <section className="p-8 rounded-xl transition-all hover:shadow-lg"
              style={{
                background: '#ffffff',
                border: '1px solid #e0e4e8',
                backdropFilter: 'blur(10px)'
              }}>
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--brand)' }}>How It Works</h2>
              <ol className="space-y-3">
                {[
                  'Fill out your research profile describing your interests, skills, and research focus',
                  'Our AI analyzes your profile and generates optimized search queries',
                  'The system discovers and scrapes relevant research laboratories',
                  'A knowledge base is built from the collected data',
                  'Advanced matching algorithms rank labs by compatibility',
                  'Review detailed results with matching scores and lab information',
                  'Connect with the perfect research lab for your next opportunity'
                ].map((step, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-sm font-semibold"
                      style={{
                        background: 'linear-gradient(135deg, #4361ee, #8b5cf6)',
                        color: 'white'
                      }}>
                      {i + 1}
                    </span>
                    <span style={{ color: 'var(--text-secondary)' }}>{step}</span>
                  </li>
                ))}
              </ol>
            </section>

            {/* CTA Section */}
            <section className="p-8 rounded-xl text-center"
              style={{
                background: 'linear-gradient(135deg, #e0e9ff, #f0ebff)',
                border: '1px solid #d0d8e0',
                backdropFilter: 'blur(10px)'
              }}>
              <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--text-primary)' }}>Ready to Find Your Lab?</h2>
              <p className="mb-6" style={{ color: 'var(--text-secondary)' }}>
                Start your research lab discovery journey today and connect with the perfect laboratory for your academic goals.
              </p>
              <a href="/"
                className="inline-block px-6 py-3 rounded-lg font-semibold transition-all"
                style={{
                  background: 'linear-gradient(135deg, #4361ee, #8b5cf6)',
                  color: 'white'
                }}>
                Begin Your Search
              </a>
            </section>
          </div>
        </div>
      </main>
    </>
  )
}