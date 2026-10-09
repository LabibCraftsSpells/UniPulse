import React, { useState } from 'react'
import {
  X,
  ExternalLink,
  Copy,
  Check,
  Calendar,
  ListTodo,
  Sparkles,
  Info,
  ChevronDown,
  ChevronUp,
  FileText,
  Clock,
  Plus,
  ShieldCheck,
} from 'lucide-react'
import type { EmailDetailResponse, TaskItem } from '../types'

interface EmailDetailPanelProps {
  email: EmailDetailResponse | null
  loading: boolean
  onClose: () => void
  onAnalyzeOnDemand: (messageId: string) => void
  analyzingId: string | null
  onToggleTaskComplete?: (taskId: number, completed: boolean) => void
  onCreateTaskFromDeadline?: (deadlineText: string, date: string | null) => void
  userTasks?: TaskItem[]
}

export const EmailDetailPanel: React.FC<EmailDetailPanelProps> = ({
  email,
  loading,
  onClose,
  onAnalyzeOnDemand,
  analyzingId,
  onCreateTaskFromDeadline,
}) => {
  const [copied, setCopied] = useState(false)
  const [showOriginal, setShowOriginal] = useState(false)
  const [viewHtml, setViewHtml] = useState(true)

  if (!email && !loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 bg-surface text-center">
        <div className="w-12 h-12 rounded-full bg-surface-dark border border-border flex items-center justify-center mb-3">
          <FileText className="w-6 h-6 text-text-secondary/50" />
        </div>
        <h3 className="text-sm font-semibold text-text mb-1">Select an email</h3>
        <p className="text-xs text-text-secondary max-w-xs leading-relaxed">
          Choose a message from your priority inbox to view its AI summary, deadlines, action items, and original content.
        </p>
      </div>
    )
  }

  if (loading && !email) {
    return (
      <div className="flex-1 p-8 bg-surface space-y-6 animate-pulse">
        <div className="h-6 bg-surface-dark rounded w-3/4" />
        <div className="h-4 bg-surface-dark rounded w-1/3" />
        <div className="h-28 bg-surface-dark rounded-xl" />
        <div className="h-32 bg-surface-dark rounded-xl" />
      </div>
    )
  }

  if (!email) return null

  const isAnalyzing = analyzingId === email.gmail_message_id || email.status === 'analyzing'
  const analysis = email.analysis

  const handleCopySummary = () => {
    if (!analysis?.summary) return
    navigator.clipboard.writeText(analysis.summary)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const formatFullDate = (isoString?: string | null) => {
    if (!isoString) return ''
    try {
      const date = new Date(isoString)
      return date.toLocaleDateString(undefined, {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: 'numeric',
      })
    } catch {
      return ''
    }
  }

  return (
    <div className="flex-1 flex flex-col h-screen bg-surface overflow-hidden">
      {/* Top Header Actions */}
      <div className="h-16 px-6 border-b border-border flex items-center justify-between shrink-0 bg-surface">
        <div className="flex items-center gap-3">
          <button
            onClick={onClose}
            className="p-1.5 text-text-secondary hover:text-text hover:bg-surface-dark rounded-lg transition-colors"
            title="Close panel"
          >
            <X className="w-5 h-5" />
          </button>
          <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Email Details</span>
        </div>

        <div className="flex items-center gap-2">
          {analysis?.summary && (
            <button
              onClick={handleCopySummary}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-xs font-medium text-text-secondary hover:text-text hover:bg-surface-dark transition-all active:scale-95"
              title="Copy AI summary to clipboard"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-success" />
                  <span className="text-success font-semibold">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy Summary</span>
                </>
              )}
            </button>
          )}

          <a
            href={email.gmail_link}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-white text-xs font-medium hover:bg-primary-dark transition-all active:scale-95 shadow-2xs"
            title="Open original thread in official Gmail"
          >
            <span>Open in Gmail</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Email Header Info */}
        <div className="space-y-3 pb-5 border-b border-border">
          <div className="flex flex-wrap items-center gap-2">
            {analysis?.priority === 'high' && (
              <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-red-50 text-danger border border-red-200/80 dark:bg-red-950/40 dark:text-red-300 dark:border-red-900/60">
                🔴 High Priority
              </span>
            )}
            {analysis?.priority === 'medium' && (
              <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200/80 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-900/60">
                🟡 Medium Priority
              </span>
            )}
            {analysis?.priority === 'low' && (
              <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200/80 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700">
                🟢 Low Priority
              </span>
            )}

            {analysis?.course && (
              <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200/80 dark:bg-indigo-950/40 dark:text-indigo-300 dark:border-indigo-900/60">
                {analysis.course}
              </span>
            )}

            {analysis?.category && (
              <span className="text-xs font-medium uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-surface-dark text-text-secondary border border-border">
                {analysis.category}
              </span>
            )}
          </div>

          <h2 className="text-xl font-bold text-text leading-snug">{email.subject}</h2>

          <div className="flex items-center justify-between text-xs text-text-secondary pt-1">
            <div className="min-w-0">
              <span className="font-semibold text-text">{email.sender_name || email.sender}</span>
              {email.sender_name && <span className="text-text-secondary/70 ml-1.5">&lt;{email.sender}&gt;</span>}
            </div>
            <span className="shrink-0">{formatFullDate(email.received_at)}</span>
          </div>

          {analysis?.priority_reason && (
            <p className="text-xs text-text-secondary bg-surface-dark/70 p-3 rounded-xl border border-border italic leading-relaxed">
              💡 {analysis.priority_reason}
            </p>
          )}
        </div>

        {/* AI Analysis Section */}
        {analysis ? (
          <div className="space-y-5">
            {/* AI Summary Card */}
            <div className="bg-surface-elevated rounded-2xl p-5 border border-border shadow-xs space-y-3">
              <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-wider">
                <Sparkles className="w-4 h-4" />
                <span>AI Intelligence Summary</span>
              </div>
              <p className="text-sm text-text leading-relaxed font-normal whitespace-pre-line">{analysis.summary}</p>

              {analysis.what_this_means && (
                <div className="pt-3 border-t border-border">
                  <div className="flex items-center gap-1.5 text-text-secondary text-xs font-semibold mb-1">
                    <Info className="w-3.5 h-3.5 text-primary" />
                    <span>What this means for you:</span>
                  </div>
                  <p className="text-xs text-text-secondary italic leading-relaxed">{analysis.what_this_means}</p>
                </div>
              )}
            </div>

            {/* Action Items List */}
            {analysis.action_items.length > 0 && (
              <div className="bg-blue-50/40 dark:bg-blue-950/20 rounded-2xl p-5 border border-blue-100/70 dark:border-blue-900/40 space-y-3">
                <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-wider">
                  <ListTodo className="w-4 h-4" />
                  <span>Required Actions ({analysis.action_items.length})</span>
                </div>
                <div className="space-y-2">
                  {analysis.action_items.map((item, idx) => (
                    <div
                      key={idx}
                      className="bg-surface p-3.5 rounded-xl border border-blue-100 dark:border-blue-900/50 text-xs text-text flex items-start gap-2.5 shadow-2xs"
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-primary shrink-0 mt-1.5" />
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-text">{item.title}</p>
                        {item.deadline && (
                          <p className="text-[11px] text-danger font-medium mt-0.5">Due: {item.deadline}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Extracted Deadlines Section */}
            {analysis.deadlines.length > 0 && (
              <div className="bg-red-50/40 dark:bg-red-950/20 rounded-2xl p-5 border border-red-100/70 dark:border-red-900/40 space-y-3">
                <div className="flex items-center gap-2 text-danger font-bold text-xs uppercase tracking-wider">
                  <Calendar className="w-4 h-4" />
                  <span>Extracted Deadlines</span>
                </div>
                <div className="space-y-2.5">
                  {analysis.deadlines.map((dl, idx) => (
                    <div
                      key={idx}
                      className="bg-surface p-3.5 rounded-xl border border-red-100 dark:border-red-900/50 text-xs flex items-center justify-between gap-3 shadow-2xs"
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <strong className="text-danger font-bold text-sm">{dl.date || 'Unspecified date'}</strong>
                          {dl.time && <span className="text-text-secondary text-[11px]">at {dl.time}</span>}
                          <span
                            className={`text-[9px] uppercase font-bold px-1.5 py-0.2 rounded border ${
                              dl.confidence === 'explicit'
                                ? 'bg-green-50 text-success border-green-200 dark:bg-green-950/50 dark:text-green-300 dark:border-green-800'
                                : 'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-800'
                            }`}
                          >
                            {dl.confidence}
                          </span>
                        </div>
                        {dl.source_text && (
                          <p className="text-[11px] text-text-secondary italic mt-0.5 line-clamp-1">
                            "{dl.source_text}"
                          </p>
                        )}
                      </div>

                      {onCreateTaskFromDeadline && (
                        <button
                          onClick={() => onCreateTaskFromDeadline(dl.source_text || 'Exam/Assignment', dl.date)}
                          className="shrink-0 p-1.5 text-danger hover:bg-red-50 dark:hover:bg-red-950/50 rounded-lg transition-colors border border-red-200/60 dark:border-red-900/60 text-xs flex items-center gap-1 font-medium"
                          title="Save as task in Action Center"
                        >
                          <Plus className="w-3.5 h-3.5" />
                          <span>Add Task</span>
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Extracted Important Links */}
            {analysis.important_links.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider">Extracted Links</h4>
                <div className="space-y-1.5">
                  {analysis.important_links.map((link, idx) => (
                    <a
                      key={idx}
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center justify-between p-2.5 rounded-xl border border-border bg-surface hover:bg-surface-dark transition-colors group"
                    >
                      <span className="truncate pr-2">{link.label || link.url}</span>
                      <ExternalLink className="w-3.5 h-3.5 text-text-secondary group-hover:text-primary shrink-0" />
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Unanalyzed / Analyzing State */
          <div className="p-6 bg-surface-dark/40 rounded-2xl border border-border text-center space-y-3">
            <Clock className="w-8 h-8 text-primary mx-auto animate-pulse" />
            <h4 className="text-sm font-semibold text-text">
              {isAnalyzing ? 'Analyzing with Gemini...' : 'Not Analyzed Yet'}
            </h4>
            <p className="text-xs text-text-secondary max-w-sm mx-auto leading-relaxed">
              {isAnalyzing
                ? 'Gemini is reading this email to identify academic priority, extracted deadlines, and required actions.'
                : 'This email is queued for background processing, or you can analyze it immediately.'}
            </p>
            {!isAnalyzing && (
              <button
                onClick={() => onAnalyzeOnDemand(email.gmail_message_id)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-white text-xs font-semibold hover:bg-primary-dark transition-all active:scale-95 shadow-sm"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Analyze Now</span>
              </button>
            )}
          </div>
        )}

        {/* Collapsible Original Email Content (Sanitized) */}
        <div className="pt-4 border-t border-border">
          <div className="flex items-center justify-between mb-3">
            <button
              onClick={() => setShowOriginal(!showOriginal)}
              className="flex items-center gap-2 text-xs font-bold text-text uppercase tracking-wider hover:text-primary transition-colors"
            >
              <span>Original Message Content</span>
              {showOriginal ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>

            {showOriginal && email.body_html && (
              <div className="flex items-center gap-1 text-[11px] bg-surface-dark p-0.5 rounded-lg border border-border/70">
                <button
                  onClick={() => setViewHtml(true)}
                  className={`px-2.5 py-0.5 rounded ${viewHtml ? 'bg-surface text-primary shadow-xs font-semibold' : 'text-text-secondary hover:text-text'}`}
                >
                  HTML
                </button>
                <button
                  onClick={() => setViewHtml(false)}
                  className={`px-2.5 py-0.5 rounded ${!viewHtml ? 'bg-surface text-primary shadow-xs font-semibold' : 'text-text-secondary hover:text-text'}`}
                >
                  Plain Text
                </button>
              </div>
            )}
          </div>

          {showOriginal && (
            <div className="bg-surface-muted rounded-2xl p-4 border border-border text-xs overflow-x-auto space-y-3">
              <div className="flex items-center gap-1.5 text-[11px] text-success font-medium pb-2 border-b border-border">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Sanitized & secured content — scripts blocked</span>
              </div>

              {viewHtml && email.body_html ? (
                <div
                  className="p-4 rounded-xl bg-white text-slate-900 dark:bg-slate-900/90 dark:text-slate-100 border border-border/80 overflow-x-auto shadow-2xs max-w-none text-xs leading-relaxed"
                  dangerouslySetInnerHTML={{ __html: email.body_html }}
                />
              ) : (
                <pre className="whitespace-pre-wrap font-sans text-xs text-text leading-relaxed p-3 bg-surface rounded-xl border border-border/60">
                  {email.body_text || email.snippet || '(No content body)'}
                </pre>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
