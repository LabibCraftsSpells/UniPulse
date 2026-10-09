import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Mail, LogOut, RefreshCcw, ExternalLink, 
  Calendar, Info, ListTodo, Sparkles, User, ShieldAlert, AlertCircle 
} from 'lucide-react'

// Matches our Pydantic UserResponse schema
interface UserProfile {
  id: string
  email: string
  name: string
  picture: string
}

// Matches our Pydantic EmailCardResponse schema
interface EmailCard {
  gmail_message_id: string
  subject: string
  sender: string
  received_at: string
  body_preview: string
  gmail_link: string
  analysis?: {
    priority: 'high' | 'medium' | 'low'
    category: string
    summary: string
    what_this_means: string
    action_required: boolean
    action_items: string[]
    deadlines: Array<{date: string, time: string, description: string}>
  }
}

export default function DashboardPage() {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [emails, setEmails] = useState<EmailCard[]>([])
  const [loading, setLoading] = useState(true)
  const [fetchingEmails, setFetchingEmails] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'high' | 'medium' | 'low'>('all')
  const navigate = useNavigate()

  const filteredEmails = emails.filter(email => {
    if (filter === 'all') return true
    return email.analysis?.priority === filter
  })

  useEffect(() => {
    fetch('/auth/me')
      .then(res => {
        if (!res.ok) throw new Error('Not logged in')
        return res.json()
      })
      .then(data => {
        setUser(data)
        setLoading(false)
      })
      .catch(() => {
        navigate('/')
      })
  }, [navigate])

  const handleLogout = async () => {
    await fetch('/auth/disconnect', { method: 'POST' })
    navigate('/')
  }

  const fetchRecentEmails = async () => {
    setFetchingEmails(true)
    setError(null)
    try {
      const res = await fetch('/api/emails/analyze', { method: 'POST' })
      if (res.status === 401) {
        await handleLogout()
        return
      }
      if (!res.ok) throw new Error('Failed to fetch and analyze emails')
      const data = await res.json()
      setEmails(data)
    } catch (err: any) {
      setError(err.message || 'An error occurred while analyzing emails')
    } finally {
      setFetchingEmails(false)
    }
  }

  const getInitials = (sender: string) => {
    const clean = sender.split('<')[0].replace(/["']/g, '').trim()
    const words = clean.split(' ')
    if (words.length >= 2) return (words[0][0] + words[words.length-1][0]).toUpperCase()
    return clean.slice(0, 2).toUpperCase() || '?'
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface">
        <div className="flex flex-col items-center gap-3">
          <RefreshCcw className="w-6 h-6 text-primary animate-spin" />
          <p className="text-sm font-medium text-text-secondary">Loading your workspace...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-surface pb-24 font-sans">
      {/* Navbar */}
      <nav className="bg-white border-b border-border/60 sticky top-0 z-20 shadow-sm">
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <img src="/favicon.svg" alt="UniPulse Logo" className="w-7 h-7" />
            <span className="font-bold text-text tracking-tight">UniPulse</span>
          </div>
          <div className="flex items-center gap-5">
            <div className="flex items-center gap-3 border-r border-border/60 pr-5">
              {user?.picture ? (
                <img src={user.picture} alt="Profile" className="w-8 h-8 rounded-full border border-border/50 shadow-sm" />
              ) : (
                <div className="w-8 h-8 rounded-full bg-surface-dark flex items-center justify-center border border-border">
                  <User className="w-4 h-4 text-text-secondary" />
                </div>
              )}
              <span className="text-sm font-medium text-text hidden sm:block">{user?.name}</span>
            </div>
            <button 
              onClick={handleLogout}
              className="text-sm font-medium text-text-secondary hover:text-danger flex items-center gap-1.5 transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Sign out
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-6 py-10">
        
        {/* Header Section */}
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-10">
          <div>
            <h1 className="text-3xl font-bold text-text tracking-tight mb-2">Your Inbox</h1>
            <p className="text-text-secondary text-sm max-w-md">
              AI-powered analysis of your recent university emails, helping you focus on what actually matters.
            </p>
          </div>
          <button 
            onClick={fetchRecentEmails}
            disabled={fetchingEmails}
            className="flex items-center justify-center gap-2 bg-primary hover:bg-primary-dark text-white px-5 py-2.5 rounded-xl text-sm font-semibold transition-all shadow-sm hover:shadow active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed disabled:active:scale-100"
          >
            {fetchingEmails ? (
              <>
                <RefreshCcw className="w-4 h-4 animate-spin" />
                Analyzing Inbox...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Fetch & Analyze
              </>
            )}
          </button>
        </div>

        {/* Error State */}
        {error && (
          <div className="bg-red-50 text-danger p-4 rounded-xl mb-8 border border-red-100 flex items-start gap-3 shadow-sm">
            <ShieldAlert className="w-5 h-5 shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-semibold mb-1">Analysis Failed</h3>
              <p className="text-sm opacity-90">{error}</p>
            </div>
          </div>
        )}

        {/* Empty State */}
        {emails.length === 0 && !fetchingEmails && !error && (
          <div className="text-center bg-white p-16 rounded-2xl border border-border/60 shadow-sm mt-8">
            <div className="bg-surface w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-5 border border-border">
              <Mail className="w-8 h-8 text-text-secondary/50" />
            </div>
            <h2 className="text-xl font-semibold text-text mb-2 tracking-tight">Inbox clear</h2>
            <p className="text-text-secondary max-w-sm mx-auto text-sm leading-relaxed">
              Connect to Gmail and fetch your recent messages to see your AI-analyzed priority dashboard.
            </p>
          </div>
        )}

        {/* Loading Skeletons */}
        {fetchingEmails && emails.length === 0 && (
          <div className="space-y-5">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white p-6 rounded-2xl border border-border/60 shadow-sm animate-pulse flex gap-4">
                 <div className="w-10 h-10 rounded-full bg-surface-dark shrink-0"></div>
                 <div className="flex-1 space-y-3 py-1">
                   <div className="h-4 bg-surface-dark rounded w-1/4"></div>
                   <div className="h-5 bg-surface-dark rounded w-3/4"></div>
                   <div className="h-4 bg-surface-dark rounded w-full mt-4"></div>
                   <div className="h-4 bg-surface-dark rounded w-5/6"></div>
                 </div>
              </div>
            ))}
          </div>
        )}

        {/* Priority Filter */}
        {emails.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 mb-6">
            <span className="text-sm font-semibold text-text-secondary mr-2 shrink-0">Priority:</span>
            {(['all', 'high', 'medium', 'low'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 border ${
                  filter === f
                    ? 'bg-primary text-white border-primary shadow-sm'
                    : 'bg-white text-text-secondary border-border/60 hover:bg-surface-dark hover:text-text'
                }`}
              >
                {f === 'all' ? 'All' :
                 f === 'high' ? '🔴 High' :
                 f === 'medium' ? '🟡 Medium' : '🟢 Low'}
              </button>
            ))}
          </div>
        )}

        {/* Filtered Empty State */}
        {emails.length > 0 && filteredEmails.length === 0 && !fetchingEmails && (
          <div className="text-center bg-white p-12 rounded-2xl border border-border/60 shadow-sm">
            <p className="text-text-secondary font-medium">No {filter}-priority emails found.</p>
          </div>
        )}

        {/* Email Cards */}
        <div className="space-y-5">
          {filteredEmails.map((email) => (
            <div 
              key={email.gmail_message_id} 
              className="group bg-white rounded-2xl border border-border/60 shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden flex flex-col"
            >
              <div className="p-6">
                {/* Header (Sender, Date, Link) */}
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div className="flex items-center gap-3 overflow-hidden">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary/10 to-primary/5 text-primary font-bold text-sm flex items-center justify-center shrink-0 border border-primary/10">
                      {getInitials(email.sender)}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-text truncate pr-4">{email.sender.split('<')[0].trim()}</p>
                      <p className="text-xs text-text-secondary truncate mt-0.5">
                        {new Date(email.received_at).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: 'numeric' })}
                      </p>
                    </div>
                  </div>
                  <a 
                    href={email.gmail_link} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="p-2 text-text-secondary/50 hover:text-primary hover:bg-primary/5 rounded-lg transition-colors shrink-0"
                    title="Open in Gmail"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </div>

                {/* Subject & Preview */}
                <h3 className="text-lg font-semibold text-text leading-snug mb-2">{email.subject || '(No Subject)'}</h3>
                <p className="text-sm text-text-secondary line-clamp-2 leading-relaxed">
                  {email.body_preview || '(Empty body)'}
                </p>

                {/* AI Analysis Section */}
                {email.analysis && (
                  <div className="mt-6 pt-5 border-t border-border/50">
                    
                    {/* Badges */}
                    <div className="flex flex-wrap items-center gap-2 mb-5">
                      <span className={`text-[10px] font-bold tracking-wide uppercase px-2.5 py-1 rounded-md border ${
                        email.analysis.priority === 'high' ? 'bg-red-50 text-red-700 border-red-200/60' :
                        email.analysis.priority === 'medium' ? 'bg-amber-50 text-amber-700 border-amber-200/60' :
                        'bg-slate-50 text-slate-600 border-slate-200/60'
                      }`}>
                        {email.analysis.priority} Priority
                      </span>
                      <span className="text-[10px] font-bold tracking-wide uppercase px-2.5 py-1 rounded-md bg-surface-dark text-text-secondary border border-border/60">
                        {email.analysis.category.replace('_', ' ')}
                      </span>
                      {email.analysis.action_required && (
                        <span className="flex items-center gap-1.5 text-[10px] font-bold tracking-wide uppercase px-2.5 py-1 rounded-md bg-blue-50 text-blue-700 border border-blue-200/60">
                          <AlertCircle className="w-3 h-3" />
                          Action Required
                        </span>
                      )}
                    </div>

                    <div className="space-y-4">
                      {/* Summary */}
                      <div className="bg-surface/50 rounded-xl p-4 border border-border/40">
                        <div className="flex items-start gap-2.5">
                          <Sparkles className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                          <div>
                            <h4 className="text-xs font-bold text-text uppercase tracking-wide mb-1">AI Summary</h4>
                            <p className="text-sm text-text-secondary leading-relaxed">{email.analysis.summary}</p>
                          </div>
                        </div>
                        
                        {email.analysis.what_this_means && (
                          <div className="flex items-start gap-2.5 mt-4 pt-4 border-t border-border/40">
                            <Info className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                            <div>
                              <h4 className="text-xs font-bold text-text uppercase tracking-wide mb-1">What this means</h4>
                              <p className="text-sm text-text-secondary leading-relaxed italic">{email.analysis.what_this_means}</p>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Action Items & Deadlines Row */}
                      {(email.analysis.action_items.length > 0 || email.analysis.deadlines.length > 0) && (
                        <div className="grid sm:grid-cols-2 gap-4">
                          {email.analysis.action_items.length > 0 && (
                            <div className="bg-blue-50/40 p-4 rounded-xl border border-blue-100/50">
                              <div className="flex items-center gap-2 mb-2.5">
                                <ListTodo className="w-4 h-4 text-primary" />
                                <h4 className="text-xs font-bold text-primary uppercase tracking-wide">Action Items</h4>
                              </div>
                              <ul className="space-y-2">
                                {email.analysis.action_items.map((item, idx) => (
                                  <li key={idx} className="text-sm text-text-secondary flex items-start gap-2">
                                    <span className="w-1.5 h-1.5 rounded-full bg-primary/40 shrink-0 mt-1.5"></span>
                                    <span className="leading-snug">{item}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {email.analysis.deadlines.length > 0 && (
                            <div className="bg-red-50/40 p-4 rounded-xl border border-red-100/50">
                              <div className="flex items-center gap-2 mb-2.5">
                                <Calendar className="w-4 h-4 text-danger" />
                                <h4 className="text-xs font-bold text-danger uppercase tracking-wide">Deadlines</h4>
                              </div>
                              <ul className="space-y-2">
                                {email.analysis.deadlines.map((dl, idx) => (
                                  <li key={idx} className="text-sm text-text-secondary flex items-start gap-2">
                                    <span className="w-1.5 h-1.5 rounded-full bg-danger/40 shrink-0 mt-1.5"></span>
                                    <div className="leading-snug">
                                      <strong className="text-danger/90 font-semibold">{dl.date}</strong>
                                      {dl.time && <span className="text-danger/80 text-xs ml-1">at {dl.time}</span>}
                                      <span className="block mt-0.5">{dl.description}</span>
                                    </div>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}
