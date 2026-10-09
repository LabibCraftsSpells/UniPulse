import { Mail, ArrowRight, Shield, Zap, Brain } from 'lucide-react'

/**
 * Landing page — the first thing users see.
 *
 * Shows:
 * - Hero section with value proposition
 * - How it works (3-step flow)
 * - Feature highlights
 * - Connect Gmail button
 */
export default function LandingPage() {
  const handleConnect = () => {
    // This will redirect to our backend OAuth endpoint
    // which then redirects to Google's consent screen
    window.location.href = '/auth/google'
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Navigation */}
      <nav className="border-b border-border">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <img src="/favicon.svg" alt="UniPulse Logo" className="w-6 h-6" />
            <span className="font-semibold text-text tracking-tight">UniPulse</span>
          </div>
          <button
            onClick={handleConnect}
            className="text-sm text-primary hover:text-primary-dark font-medium transition-colors"
          >
            Sign in
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-3xl mx-auto px-6 pt-24 pb-16 text-center">
        <h1 className="text-4xl sm:text-5xl font-bold text-text leading-tight tracking-tight">
          Your university inbox is noisy.
          <br />
          <span className="text-primary">Your deadlines shouldn't be.</span>
        </h1>
        <p className="mt-6 text-lg text-text-secondary max-w-2xl mx-auto leading-relaxed">
          UniPulse connects to your university Gmail and turns
          important academic emails into clear actions, deadlines, and summaries.
        </p>
        <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
          <button
            onClick={handleConnect}
            className="inline-flex items-center justify-center gap-2 bg-primary hover:bg-primary-dark text-white font-medium px-8 py-3 rounded-lg transition-colors text-base"
          >
            <Mail className="w-4 h-4" />
            Connect Gmail
          </button>
          <a
            href="#how-it-works"
            className="inline-flex items-center justify-center gap-2 border border-border hover:bg-surface text-text font-medium px-8 py-3 rounded-lg transition-colors text-base"
          >
            See how it works
            <ArrowRight className="w-4 h-4" />
          </a>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="bg-surface border-y border-border">
        <div className="max-w-4xl mx-auto px-6 py-20">
          <h2 className="text-2xl font-bold text-text text-center mb-12">
            How it works
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <Step
              number={1}
              title="Connect Gmail"
              description="Sign in with your university Google account. We only request read-only access."
            />
            <Step
              number={2}
              title="AI analyzes your inbox"
              description="Important emails are identified and analyzed for deadlines, actions, and relevance to your courses."
            />
            <Step
              number={3}
              title="See what matters"
              description="Get a clean dashboard of what actually needs your attention — no noise."
            />
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-4xl mx-auto px-6 py-20">
        <h2 className="text-2xl font-bold text-text text-center mb-12">
          Built for students
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <Feature
            icon={<Brain className="w-5 h-5" />}
            title="Course-aware AI"
            description="Tell it your courses and major — it knows which emails matter to you."
          />
          <Feature
            icon={<Zap className="w-5 h-5" />}
            title="Deadline extraction"
            description="Deadlines, exam dates, and registration windows — pulled from your emails automatically."
          />
          <Feature
            icon={<Shield className="w-5 h-5" />}
            title="Privacy-first"
            description="Read-only Gmail access. No passwords stored. Disconnect anytime."
          />
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border">
        <div className="max-w-5xl mx-auto px-6 py-8 text-center text-sm text-text-secondary">
          <p>
            UniPulse — Open source on{' '}
            <a href="#" className="text-primary hover:underline">
              GitHub
            </a>
          </p>
          <p className="mt-2">
            Your email data never leaves your session. We don't store email content permanently.
          </p>
        </div>
      </footer>
    </div>
  )
}

/* ─── Sub-components ─── */

function Step({
  number,
  title,
  description,
}: {
  number: number
  title: string
  description: string
}) {
  return (
    <div className="text-center">
      <div className="w-10 h-10 rounded-full bg-primary text-white font-bold text-sm flex items-center justify-center mx-auto mb-4">
        {number}
      </div>
      <h3 className="font-semibold text-text mb-2">{title}</h3>
      <p className="text-sm text-text-secondary leading-relaxed">{description}</p>
    </div>
  )
}

function Feature({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <div className="p-6 rounded-xl border border-border bg-white">
      <div className="w-10 h-10 rounded-lg bg-surface flex items-center justify-center text-primary mb-4">
        {icon}
      </div>
      <h3 className="font-semibold text-text mb-2">{title}</h3>
      <p className="text-sm text-text-secondary leading-relaxed">{description}</p>
    </div>
  )
}
