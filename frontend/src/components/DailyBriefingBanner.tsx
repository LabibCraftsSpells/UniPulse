import React from 'react'
import {
  Sparkles,
  AlertTriangle,
  Calendar,
  Mail,
  ArrowRight,
  Clock,
} from 'lucide-react'
import type { DailyBriefingData, EmailListItem } from '../types'

interface DailyBriefingProps {
  briefing: DailyBriefingData | null
  loading: boolean
  onSelectEmail: (email: EmailListItem) => void
  onViewTasks: () => void
}

export const DailyBriefingBanner: React.FC<DailyBriefingProps> = ({
  briefing,
  loading,
  onSelectEmail,
  onViewTasks,
}) => {
  if (loading && !briefing) {
    return (
      <div className="p-8 max-w-4xl mx-auto space-y-4">
        <div className="h-32 bg-surface rounded-2xl border border-border animate-pulse" />
      </div>
    )
  }

  if (!briefing) return null

  return (
    <div className="flex-1 flex flex-col h-screen bg-surface-muted/40 overflow-y-auto">
      {/* Header */}
      <div className="h-16 px-8 bg-surface border-b border-border flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-amber-50 text-amber-600 border border-amber-200/60 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-900/60">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-text tracking-tight">Daily Academic Briefing</h1>
            <p className="text-xs text-text-secondary">Synthesized from your verified email intelligence and action tasks.</p>
          </div>
        </div>
      </div>

      <div className="p-8 max-w-4xl w-full mx-auto space-y-6">
        {/* Metric Cards Row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-surface p-5 rounded-2xl border border-border shadow-xs">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-danger dark:text-red-400 uppercase tracking-wider">High Priority</span>
              <AlertTriangle className="w-4 h-4 text-danger dark:text-red-400" />
            </div>
            <p className="text-2xl font-bold text-text">{briefing.high_priority_count}</p>
            <p className="text-xs text-text-secondary mt-1">Requiring immediate student attention</p>
          </div>

          <div className="bg-surface p-5 rounded-2xl border border-border shadow-xs">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-primary dark:text-blue-400 uppercase tracking-wider">Upcoming Deadlines</span>
              <Calendar className="w-4 h-4 text-primary dark:text-blue-400" />
            </div>
            <p className="text-2xl font-bold text-text">{briefing.upcoming_deadlines_count}</p>
            <p className="text-xs text-text-secondary mt-1">Due within the next 7 days</p>
          </div>

          <div className="bg-surface p-5 rounded-2xl border border-border shadow-xs">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-amber-700 dark:text-amber-400 uppercase tracking-wider">Overdue Tasks</span>
              <Clock className="w-4 h-4 text-amber-600 dark:text-amber-400" />
            </div>
            <p className="text-2xl font-bold text-text">{briefing.overdue_tasks_count}</p>
            <p className="text-xs text-text-secondary mt-1">Pending past deadline</p>
          </div>
        </div>

        {/* Urgent Deadlines Agenda */}
        <div className="bg-surface rounded-2xl border border-border p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-bold text-text uppercase tracking-wide">Upcoming Academic Calendar</h3>
            </div>
            <button
              onClick={onViewTasks}
              className="text-xs font-semibold text-primary hover:underline flex items-center gap-1"
            >
              <span>View All Tasks</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {briefing.upcoming_deadlines.length === 0 ? (
            <div className="p-6 text-center text-xs text-text-secondary bg-surface-dark/40 rounded-xl">
              No upcoming deadlines detected for the next 7 days.
            </div>
          ) : (
            <div className="space-y-2.5">
              {briefing.upcoming_deadlines.map((t) => (
                <div
                  key={t.id}
                  className="p-3.5 bg-surface-dark/40 rounded-xl border border-border/70 flex items-center justify-between gap-4"
                >
                  <div>
                    <p className="text-xs font-bold text-text">{t.title}</p>
                    <div className="flex items-center gap-2 mt-1 text-[11px] text-text-secondary">
                      {t.course && (
                        <span className="font-bold text-indigo-700 dark:text-indigo-300 uppercase tracking-wider">{t.course}</span>
                      )}
                      <span>Due: {t.deadline_date} {t.deadline_time ? `at ${t.deadline_time}` : ''}</span>
                    </div>
                  </div>
                  <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-red-50 text-danger border border-red-200 dark:bg-red-950/40 dark:text-red-300 dark:border-red-900/60">
                    {t.priority}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* High Priority Messages */}
        <div className="bg-surface rounded-2xl border border-border p-6 shadow-xs space-y-4">
          <div className="flex items-center gap-2">
            <Mail className="w-4 h-4 text-danger" />
            <h3 className="text-sm font-bold text-text uppercase tracking-wide">Urgent Official Announcements</h3>
          </div>

          {briefing.recent_high_priority.length === 0 ? (
            <div className="p-6 text-center text-xs text-text-secondary bg-surface-dark/40 rounded-xl">
              No high-priority announcements pending.
            </div>
          ) : (
            <div className="space-y-2.5">
              {briefing.recent_high_priority.map((email) => (
                <div
                  key={email.gmail_message_id}
                  onClick={() => onSelectEmail(email)}
                  role="button"
                  tabIndex={0}
                  className="p-4 bg-surface-dark/40 hover:bg-surface-dark/70 rounded-xl border border-border/70 cursor-pointer transition-colors space-y-1"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-text">{email.sender_name || email.sender}</span>
                    <span className="text-[10px] uppercase font-bold text-danger dark:text-red-300 bg-red-50 dark:bg-red-950/40 px-2 py-0.5 rounded border border-red-200 dark:border-red-900/60">
                      🔴 High Priority
                    </span>
                  </div>
                  <h4 className="text-xs font-semibold text-text">{email.subject}</h4>
                  <p className="text-xs text-text-secondary line-clamp-2 leading-relaxed">{email.summary || email.snippet}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
