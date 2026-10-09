import React from 'react'
import {
  Inbox,
  CheckSquare,
  Sparkles,
  LogOut,
  RefreshCw,
  Clock,
  Mail,
  Bookmark,
  Calendar,
} from 'lucide-react'
import type { UserProfile, InboxCounts, SyncState } from '../types'
import { ThemeToggle } from './ThemeToggle'

interface SidebarProps {
  user: UserProfile | null
  activeView: 'inbox' | 'action_center' | 'briefing'
  setActiveView: (view: 'inbox' | 'action_center' | 'briefing') => void
  activeFilter: string
  setActiveFilter: (filter: string) => void
  counts: InboxCounts
  syncState: SyncState
  onSync: () => void
  onLogout: () => void
  availableCourses: string[]
  activeCourse: string | null
  setActiveCourse: (course: string | null) => void
}

export const Sidebar: React.FC<SidebarProps> = ({
  user,
  activeView,
  setActiveView,
  activeFilter,
  setActiveFilter,
  counts,
  syncState,
  onSync,
  onLogout,
  availableCourses,
  activeCourse,
  setActiveCourse,
}) => {
  const formatSyncTime = (isoString: string | null) => {
    if (!isoString) return 'Never'
    try {
      const date = new Date(isoString)
      const diffMins = Math.round((Date.now() - date.getTime()) / 60000)
      if (diffMins < 1) return 'Just now'
      if (diffMins === 1) return '1m ago'
      if (diffMins < 60) return `${diffMins}m ago`
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } catch {
      return 'Recently'
    }
  }

  return (
    <aside className="w-64 bg-surface border-r border-border flex flex-col h-screen shrink-0 select-none">
      {/* Brand Header */}
      <div className="h-16 px-5 border-b border-border/80 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <img src="/favicon.svg" alt="UniPulse" className="w-7 h-7" />
          <div>
            <span className="font-bold text-base text-text tracking-tight">UniPulse</span>
            <span className="text-[10px] uppercase font-semibold text-primary block tracking-wider leading-none">2.0 Copilot</span>
          </div>
        </div>
        <button
          onClick={onSync}
          disabled={syncState.status === 'syncing'}
          title="Synchronize Gmail inbox"
          className="p-1.5 text-text-secondary hover:text-primary hover:bg-surface-dark rounded-lg transition-all active:scale-95 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${syncState.status === 'syncing' ? 'animate-spin text-primary' : ''}`} />
        </button>
      </div>

      {/* Main Navigation Views */}
      <div className="p-3 space-y-1">
        <button
          onClick={() => {
            setActiveView('inbox')
            setActiveCourse(null)
          }}
          className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
            activeView === 'inbox' && !activeCourse && activeFilter === 'all'
              ? 'bg-primary text-white shadow-sm'
              : 'text-text hover:bg-surface-dark'
          }`}
        >
          <div className="flex items-center gap-2.5">
            <Inbox className="w-4 h-4" />
            <span>Priority Inbox</span>
          </div>
          {counts.unread > 0 && (
            <span
              className={`text-xs px-2 py-0.5 rounded-full font-bold ${
                activeView === 'inbox' && !activeCourse && activeFilter === 'all'
                  ? 'bg-white/20 text-white'
                  : 'bg-primary/10 text-primary'
              }`}
            >
              {counts.unread}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveView('action_center')}
          className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
            activeView === 'action_center'
              ? 'bg-primary text-white shadow-sm'
              : 'text-text hover:bg-surface-dark'
          }`}
        >
          <div className="flex items-center gap-2.5">
            <CheckSquare className="w-4 h-4" />
            <span>Action Center</span>
          </div>
          {counts.tasks_pending > 0 && (
            <span
              className={`text-xs px-2 py-0.5 rounded-full font-bold ${
                activeView === 'action_center'
                  ? 'bg-white/20 text-white'
                  : counts.tasks_overdue > 0
                  ? 'bg-red-100 text-danger dark:bg-red-950/50 dark:text-red-300 dark:border dark:border-red-900/50'
                  : 'bg-amber-100 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300 dark:border dark:border-amber-900/50'
              }`}
            >
              {counts.tasks_pending}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveView('briefing')}
          className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
            activeView === 'briefing'
              ? 'bg-primary text-white shadow-sm'
              : 'text-text hover:bg-surface-dark'
          }`}
        >
          <div className="flex items-center gap-2.5">
            <Sparkles className="w-4 h-4 text-amber-500" />
            <span>Daily Briefing</span>
          </div>
          {counts.high > 0 && (
            <span
              className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider ${
                activeView === 'briefing'
                  ? 'bg-white/20 text-white'
                  : 'bg-red-50 text-danger border border-red-200/50 dark:bg-red-950/50 dark:text-red-300 dark:border-red-900/60'
              }`}
            >
              {counts.high} Urgent
            </span>
          )}
        </button>
      </div>

      <div className="h-px bg-border/60 mx-4 my-1" />

      {/* Smart Filters List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        <div className="px-3 pt-2 pb-1 text-[11px] font-bold text-text-secondary uppercase tracking-wider">
          Priority Filters
        </div>

        <button
          onClick={() => {
            setActiveView('inbox')
            setActiveFilter('all')
            setActiveCourse(null)
          }}
          className={`w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            activeView === 'inbox' && activeFilter === 'all' && !activeCourse
              ? 'bg-surface-dark font-semibold text-text'
              : 'text-text-secondary hover:text-text hover:bg-surface-dark/60'
          }`}
        >
          <span className="flex items-center gap-2">
            <Mail className="w-3.5 h-3.5" />
            All Mail
          </span>
          <span className="text-[11px] text-text-secondary/70">{counts.all}</span>
        </button>

        <button
          onClick={() => {
            setActiveView('inbox')
            setActiveFilter('unread')
            setActiveCourse(null)
          }}
          className={`w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            activeView === 'inbox' && activeFilter === 'unread'
              ? 'bg-surface-dark font-semibold text-text'
              : 'text-text-secondary hover:text-text hover:bg-surface-dark/60'
          }`}
        >
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-primary" />
            Unread
          </span>
          <span className="text-[11px] font-semibold text-primary">{counts.unread}</span>
        </button>

        <button
          onClick={() => {
            setActiveView('inbox')
            setActiveFilter('high')
            setActiveCourse(null)
          }}
          className={`w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            activeView === 'inbox' && activeFilter === 'high'
              ? 'bg-red-50 text-danger dark:bg-red-950/50 dark:text-red-300 font-semibold'
              : 'text-text-secondary hover:text-text hover:bg-surface-dark/60'
          }`}
        >
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-danger" />
            High Priority
          </span>
          <span className="text-[11px] font-semibold text-danger dark:text-red-400">{counts.high}</span>
        </button>

        <button
          onClick={() => {
            setActiveView('inbox')
            setActiveFilter('medium')
            setActiveCourse(null)
          }}
          className={`w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            activeView === 'inbox' && activeFilter === 'medium'
              ? 'bg-amber-50 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300 font-semibold'
              : 'text-text-secondary hover:text-text hover:bg-surface-dark/60'
          }`}
        >
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            Medium Priority
          </span>
          <span className="text-[11px] text-text-secondary/80 dark:text-text-secondary">{counts.medium}</span>
        </button>

        <button
          onClick={() => {
            setActiveView('inbox')
            setActiveFilter('low')
            setActiveCourse(null)
          }}
          className={`w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            activeView === 'inbox' && activeFilter === 'low'
              ? 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200 font-semibold'
              : 'text-text-secondary hover:text-text hover:bg-surface-dark/60'
          }`}
        >
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-slate-400" />
            Low Priority
          </span>
          <span className="text-[11px] text-text-secondary/70">{counts.low}</span>
        </button>

        <button
          onClick={() => {
            setActiveView('inbox')
            setActiveFilter('deadlines')
            setActiveCourse(null)
          }}
          className={`w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            activeView === 'inbox' && activeFilter === 'deadlines'
              ? 'bg-surface-dark font-semibold text-text'
              : 'text-text-secondary hover:text-text hover:bg-surface-dark/60'
          }`}
        >
          <span className="flex items-center gap-2">
            <Calendar className="w-3.5 h-3.5 text-danger" />
            Has Deadlines
          </span>
          <span className="text-[11px] text-text-secondary/70">{counts.deadlines}</span>
        </button>

        {counts.pending > 0 && (
          <button
            onClick={() => {
              setActiveView('inbox')
              setActiveFilter('pending')
              setActiveCourse(null)
            }}
            className={`w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeView === 'inbox' && activeFilter === 'pending'
                ? 'bg-blue-50 text-primary dark:bg-blue-950/50 dark:text-blue-300 font-semibold'
                : 'text-text-secondary hover:text-text hover:bg-surface-dark/60'
            }`}
          >
            <span className="flex items-center gap-2">
              <Clock className="w-3.5 h-3.5 animate-pulse text-primary" />
              Analyzing Queue
            </span>
            <span className="text-[11px] font-semibold text-primary">{counts.pending}</span>
          </button>
        )}

        {/* Academic Course Filters */}
        {availableCourses.length > 0 && (
          <>
            <div className="px-3 pt-4 pb-1 text-[11px] font-bold text-text-secondary uppercase tracking-wider flex items-center gap-1.5">
              <Bookmark className="w-3 h-3" />
              Courses
            </div>
            {availableCourses.map((c) => (
              <button
                key={c}
                onClick={() => {
                  setActiveView('inbox')
                  setActiveCourse(activeCourse === c ? null : c)
                }}
                className={`w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  activeCourse === c
                    ? 'bg-primary/10 text-primary dark:bg-primary/20 dark:text-blue-300 font-semibold'
                    : 'text-text-secondary hover:text-text hover:bg-surface-dark/60'
                }`}
              >
                <span>{c}</span>
                {activeCourse === c && <span className="w-1.5 h-1.5 rounded-full bg-primary" />}
              </button>
            ))}
          </>
        )}
      </div>

      {/* User Footer & Sync Status */}
      <div className="p-3 border-t border-border bg-surface-elevated/60 space-y-2.5">
        {/* Sync Info */}
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-1.5 text-[11px] text-text-secondary">
            <span
              className={`w-2 h-2 rounded-full ${
                syncState.status === 'syncing'
                  ? 'bg-primary animate-ping'
                  : syncState.status === 'error'
                  ? 'bg-danger'
                  : 'bg-success'
              }`}
            />
            <span className="truncate">
              {syncState.status === 'syncing'
                ? (!syncState.is_initial_sync_complete && syncState.total_available > 0
                    ? `Importing (${syncState.total_synced}/${syncState.total_available})...`
                    : 'Syncing...')
                : `Synced ${formatSyncTime(syncState.last_synced_at)}`}
            </span>
          </div>
          <span className="text-[10px] text-text-secondary/80 shrink-0">
            {syncState.total_available > 0 && syncState.total_available > counts.all
              ? `${counts.all} of ${syncState.total_available}`
              : `${counts.all} emails`}
          </span>
        </div>

        {/* Theme Switcher */}
        <ThemeToggle />

        {/* User Profile */}
        <div className="flex items-center justify-between pt-2 border-t border-border/60">
          <div className="flex items-center gap-2 overflow-hidden pr-2">
            {user?.picture ? (
              <img src={user.picture} alt="Avatar" className="w-7 h-7 rounded-full border border-border" />
            ) : (
              <div className="w-7 h-7 rounded-full bg-primary/10 text-primary font-bold text-xs flex items-center justify-center">
                {user?.name?.[0] || 'U'}
              </div>
            )}
            <div className="min-w-0">
              <p className="text-xs font-semibold text-text truncate leading-tight">{user?.name || 'Student'}</p>
              <p className="text-[10px] text-text-secondary truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={onLogout}
            title="Sign out of UniPulse"
            className="p-1.5 text-text-secondary hover:text-danger hover:bg-red-50 dark:hover:bg-red-950/50 rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  )
}
