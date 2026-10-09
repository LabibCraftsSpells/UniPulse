import React, { useState, useEffect } from 'react'
import {
  Search,
  Calendar,
  Paperclip,
  Clock,
  RefreshCw,
  X,
  Mail,
} from 'lucide-react'
import type { EmailListItem, SyncState } from '../types'

interface EmailListProps {
  emails: EmailListItem[]
  selectedId: string | null
  onSelectEmail: (email: EmailListItem) => void
  loading: boolean
  syncState: SyncState
  onManualSync: () => void
  sortMode: 'priority' | 'newest'
  setSortMode: (mode: 'priority' | 'newest') => void
  searchQuery: string
  setSearchQuery: (query: string) => void
  activeFilterTitle: string
  totalMatching?: number
  onLoadMore?: () => void
  hasMore?: boolean
  loadingMore?: boolean
}

export const EmailList: React.FC<EmailListProps> = ({
  emails,
  selectedId,
  onSelectEmail,
  loading,
  syncState,
  onManualSync,
  sortMode,
  setSortMode,
  searchQuery,
  setSearchQuery,
  activeFilterTitle,
  totalMatching,
  onLoadMore,
  hasMore,
  loadingMore,
}) => {
  const [localSearch, setLocalSearch] = useState(searchQuery)

  // Debounce search input
  useEffect(() => {
    const handler = setTimeout(() => {
      setSearchQuery(localSearch)
    }, 250)
    return () => clearTimeout(handler)
  }, [localSearch, setSearchQuery])

  const getInitials = (senderName?: string | null, sender?: string) => {
    const name = senderName || sender || '?'
    const clean = name.replace(/["']/g, '').split('<')[0].trim()
    const words = clean.split(' ')
    if (words.length >= 2) return (words[0][0] + words[words.length - 1][0]).toUpperCase()
    return clean.slice(0, 2).toUpperCase() || '?'
  }

  const formatEmailDate = (isoString?: string | null) => {
    if (!isoString) return ''
    try {
      const date = new Date(isoString)
      const now = new Date()
      const isToday = date.toDateString() === now.toDateString()
      if (isToday) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
    } catch {
      return ''
    }
  }

  // Group emails by priority if sortMode === 'priority'
  const highPriority = emails.filter((e) => e.priority === 'high')
  const mediumPriority = emails.filter((e) => e.priority === 'medium')
  const lowPriority = emails.filter((e) => e.priority === 'low')
  const pendingEmails = emails.filter((e) => !e.priority || e.status === 'pending' || e.status === 'analyzing')

  const renderEmailRow = (email: EmailListItem) => {
    const isSelected = selectedId === email.gmail_message_id
    const isUnread = email.is_unread

    return (
      <div
        key={email.gmail_message_id}
        onClick={() => onSelectEmail(email)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            onSelectEmail(email)
          }
        }}
        className={`group relative p-3.5 border-b border-border/70 cursor-pointer transition-all duration-150 select-none ${
          isSelected
            ? 'bg-primary/10 border-l-4 border-l-primary shadow-xs'
            : isUnread
            ? 'bg-surface hover:bg-surface-dark'
            : 'bg-surface-muted/50 hover:bg-surface-dark/70 opacity-90'
        }`}
      >
        <div className="flex items-start justify-between gap-2.5 mb-1.5">
          <div className="flex items-center gap-2.5 min-w-0">
            {/* Unread indicator */}
            <span
              className={`w-2 h-2 rounded-full shrink-0 transition-opacity ${
                isUnread ? 'bg-primary opacity-100' : 'opacity-0'
              }`}
            />
            {/* Avatar initials */}
            <div
              className={`w-6 h-6 rounded-full font-bold text-[10px] flex items-center justify-center shrink-0 ${
                email.priority === 'high'
                  ? 'bg-red-100 text-danger dark:bg-red-950/60 dark:text-red-300 dark:border dark:border-red-900/50'
                  : email.priority === 'medium'
                  ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 dark:border dark:border-amber-900/50'
                  : 'bg-primary/10 text-primary dark:bg-primary/20 dark:text-blue-300'
              }`}
            >
              {getInitials(email.sender_name, email.sender)}
            </div>
            <span
              className={`text-xs truncate ${
                isUnread ? 'font-bold text-text' : 'font-medium text-text-secondary'
              }`}
            >
              {email.sender_name || email.sender}
            </span>
          </div>

          {/* Time & Badges */}
          <div className="flex items-center gap-1.5 shrink-0 text-[11px] text-text-secondary">
            {email.has_attachments && <Paperclip className="w-3 h-3 text-text-secondary/70" />}
            <span>{formatEmailDate(email.received_at)}</span>
          </div>
        </div>

        {/* Subject */}
        <h4
          className={`text-xs leading-snug line-clamp-1 mb-1 ${
            isUnread ? 'font-semibold text-text' : 'font-normal text-text-secondary'
          }`}
        >
          {email.subject}
        </h4>

        {/* Snippet / Summary preview */}
        <p className="text-[11px] text-text-secondary line-clamp-2 leading-relaxed">
          {email.summary || email.body_preview || email.snippet}
        </p>

        {/* Status Pills */}
        <div className="flex flex-wrap items-center gap-1.5 mt-2 pt-1">
          {email.priority === 'high' && (
            <span className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-red-50 text-danger border border-red-200/60 dark:bg-red-950/40 dark:text-red-300 dark:border-red-900/60">
              🔴 High
            </span>
          )}
          {email.priority === 'medium' && (
            <span className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200/60 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-900/60">
              🟡 Medium
            </span>
          )}
          {email.priority === 'low' && (
            <span className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200/60 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700">
              🟢 Low
            </span>
          )}
          {(!email.priority || email.status === 'pending' || email.status === 'analyzing') && (
            <span className="text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-blue-50 text-primary border border-blue-200/60 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-900/60 flex items-center gap-1">
              <Clock className="w-2.5 h-2.5 animate-spin" />
              Analyzing
            </span>
          )}

          {email.course && (
            <span className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200/60 dark:bg-indigo-950/40 dark:text-indigo-300 dark:border-indigo-900/60">
              {email.course}
            </span>
          )}

          {email.deadline_count > 0 && (
            <span className="text-[9px] font-medium px-1.5 py-0.5 rounded bg-red-50 text-danger dark:bg-red-950/40 dark:text-red-300 dark:border dark:border-red-900/50 flex items-center gap-1">
              <Calendar className="w-2.5 h-2.5" />
              {email.next_deadline || `${email.deadline_count} deadline`}
            </span>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col h-screen bg-surface overflow-hidden border-r border-border">
      {/* Header bar: Search & Controls */}
      <div className="p-3 border-b border-border bg-surface space-y-2.5 shrink-0">
        <div className="flex items-center justify-between gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-text-secondary absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search sender, subject, content..."
              value={localSearch}
              onChange={(e) => setLocalSearch(e.target.value)}
              className="w-full bg-surface-dark/70 text-text pl-9 pr-8 py-1.5 text-xs rounded-xl border border-border focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all placeholder:text-text-secondary/60"
            />
            {localSearch && (
              <button
                onClick={() => setLocalSearch('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text p-0.5"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Sync Button */}
          <button
            onClick={onManualSync}
            disabled={syncState.status === 'syncing'}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-border text-xs font-medium text-text-secondary hover:text-text hover:bg-surface-dark transition-all disabled:opacity-50"
            title="Check for new messages in Gmail"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncState.status === 'syncing' ? 'animate-spin text-primary' : ''}`} />
            <span className="hidden sm:inline">Sync</span>
          </button>
        </div>

        {/* Filter Title & Sort Mode Switcher */}
        <div className="flex items-center justify-between text-xs text-text-secondary pt-0.5">
          <div className="font-semibold text-text truncate max-w-[200px]">
            {activeFilterTitle} <span className="font-normal text-text-secondary text-[11px]">({emails.length})</span>
          </div>

          <div className="flex items-center gap-1 bg-surface-dark/80 p-0.5 rounded-lg border border-border/70">
            <button
              onClick={() => setSortMode('priority')}
              className={`px-2.5 py-0.5 rounded text-[11px] font-medium transition-all ${
                sortMode === 'priority'
                  ? 'bg-surface text-primary shadow-xs font-semibold'
                  : 'text-text-secondary hover:text-text'
              }`}
            >
              Priority
            </button>
            <button
              onClick={() => setSortMode('newest')}
              className={`px-2.5 py-0.5 rounded text-[11px] font-medium transition-all ${
                sortMode === 'newest'
                  ? 'bg-surface text-primary shadow-xs font-semibold'
                  : 'text-text-secondary hover:text-text'
              }`}
            >
              Newest
            </button>
          </div>
        </div>
      </div>

      {/* Progressive Mailbox Import Banner */}
      {!syncState.is_initial_sync_complete && (
        <div className="bg-primary/10 border-b border-primary/20 px-3.5 py-2 flex items-center justify-between text-xs text-primary">
          <div className="flex items-center gap-2 min-w-0">
            <RefreshCw className="w-3.5 h-3.5 animate-spin text-primary shrink-0" />
            <div className="truncate">
              <span className="font-semibold">Importing mailbox: </span>
              <span>
                {syncState.total_synced} imported{syncState.total_available > 0 ? ` of ${syncState.total_available}` : ''}...
              </span>
            </div>
          </div>
          <span className="text-[10px] text-primary/80 font-medium shrink-0 ml-2">Inbox ready</span>
        </div>
      )}

      {/* Email Rows List */}
      <div className="flex-1 overflow-y-auto divide-y divide-border/60">
        {loading && emails.length === 0 ? (
          // Skeleton Loaders
          <div className="p-4 space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="animate-pulse space-y-2 py-1">
                <div className="flex justify-between">
                  <div className="h-3 bg-surface-dark rounded w-1/3" />
                  <div className="h-3 bg-surface-dark rounded w-12" />
                </div>
                <div className="h-3.5 bg-surface-dark rounded w-3/4" />
                <div className="h-3 bg-surface-dark rounded w-full" />
              </div>
            ))}
          </div>
        ) : emails.length === 0 ? (
          <div className="p-12 text-center text-text-secondary">
            <Mail className="w-10 h-10 mx-auto text-text-secondary/40 mb-3" />
            <h3 className="text-sm font-semibold text-text mb-1">No emails found</h3>
            <p className="text-xs max-w-xs mx-auto leading-relaxed">
              {searchQuery
                ? `No emails match the search term "${searchQuery}".`
                : 'No messages match the currently selected filter.'}
            </p>
          </div>
        ) : sortMode === 'priority' ? (
          <div>
            {highPriority.length > 0 && (
              <div>
                <div className="sticky top-0 z-10 bg-red-50/90 dark:bg-red-950/80 backdrop-blur-md px-3.5 py-1.5 text-[10px] font-bold text-danger dark:text-red-300 uppercase tracking-wider border-b border-red-200/50 dark:border-red-900/50 flex items-center justify-between">
                  <span>🔴 High Priority ({highPriority.length})</span>
                </div>
                {highPriority.map(renderEmailRow)}
              </div>
            )}

            {mediumPriority.length > 0 && (
              <div>
                <div className="sticky top-0 z-10 bg-amber-50/90 dark:bg-amber-950/80 backdrop-blur-md px-3.5 py-1.5 text-[10px] font-bold text-amber-900 dark:text-amber-300 uppercase tracking-wider border-b border-amber-200/50 dark:border-amber-900/50 flex items-center justify-between">
                  <span>🟡 Medium Priority ({mediumPriority.length})</span>
                </div>
                {mediumPriority.map(renderEmailRow)}
              </div>
            )}

            {lowPriority.length > 0 && (
              <div>
                <div className="sticky top-0 z-10 bg-slate-100/90 dark:bg-slate-900/80 backdrop-blur-md px-3.5 py-1.5 text-[10px] font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider border-b border-slate-200/50 dark:border-slate-800 flex items-center justify-between">
                  <span>🟢 Low Priority ({lowPriority.length})</span>
                </div>
                {lowPriority.map(renderEmailRow)}
              </div>
            )}

            {pendingEmails.length > 0 && (
              <div>
                <div className="sticky top-0 z-10 bg-blue-50/90 dark:bg-blue-950/80 backdrop-blur-md px-3.5 py-1.5 text-[10px] font-bold text-primary dark:text-blue-300 uppercase tracking-wider border-b border-blue-200/50 dark:border-blue-900/50 flex items-center justify-between">
                  <span>⏳ Analyzing in Background ({pendingEmails.length})</span>
                </div>
                {pendingEmails.map(renderEmailRow)}
              </div>
            )}
          </div>
        ) : (
          emails.map(renderEmailRow)
        )}

        {/* Load More Emails Button */}
        {hasMore && (
          <div className="p-3 bg-surface-muted/30 text-center border-t border-border">
            <button
              onClick={onLoadMore}
              disabled={loadingMore}
              className="px-4 py-1.5 text-xs font-medium text-primary hover:bg-primary/10 rounded-lg border border-primary/20 transition-all disabled:opacity-50"
            >
              {loadingMore
                ? 'Loading more emails...'
                : `Load more emails (${emails.length} of ${totalMatching ?? syncState.total_synced})`}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
