import { useEffect, useState, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  fetchCurrentUser,
  logoutUser,
  fetchInbox,
  triggerSync,
  fetchEmailDetail,
  analyzeEmail,
  fetchTasks,
  createTask,
  updateTask,
  deleteTask,
  fetchDailyBriefing,
} from '../api'
import type {
  UserProfile,
  EmailListItem,
  EmailDetailResponse,
  TaskItem,
  DailyBriefingData,
  InboxCounts,
  SyncState,
} from '../types'
import { Sidebar } from '../components/Sidebar'
import { EmailList } from '../components/EmailList'
import { EmailDetailPanel } from '../components/EmailDetailPanel'
import { ActionCenter } from '../components/ActionCenter'
import { DailyBriefingBanner } from '../components/DailyBriefingBanner'

export default function DashboardPage() {
  const navigate = useNavigate()

  // User & Global state
  const [user, setUser] = useState<UserProfile | null>(null)
  const [loadingUser, setLoadingUser] = useState(true)

  // Navigation & View state
  const [activeView, setActiveView] = useState<'inbox' | 'action_center' | 'briefing'>('inbox')
  const [activeFilter, setActiveFilter] = useState('all')
  const [activeCourse, setActiveCourse] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortMode, setSortMode] = useState<'priority' | 'newest'>('priority')

  // Inbox data state
  const [emails, setEmails] = useState<EmailListItem[]>([])
  const [inboxLoading, setInboxLoading] = useState(true)
  const [counts, setCounts] = useState<InboxCounts>({
    all: 0,
    unread: 0,
    high: 0,
    medium: 0,
    low: 0,
    pending: 0,
    deadlines: 0,
    tasks_pending: 0,
    tasks_overdue: 0,
  })
  const [syncState, setSyncState] = useState<SyncState>({
    status: 'idle',
    last_synced_at: null,
    total_synced: 0,
    total_available: 0,
    is_initial_sync_complete: false,
    sync_progress: 0,
  })
  const [limit, setLimit] = useState(100)
  const [totalMatching, setTotalMatching] = useState(0)
  const [loadingMore, setLoadingMore] = useState(false)

  // Detail panel state
  const [selectedEmailId, setSelectedEmailId] = useState<string | null>(null)
  const [selectedEmailDetail, setSelectedEmailDetail] = useState<EmailDetailResponse | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [analyzingId, setAnalyzingId] = useState<string | null>(null)

  // Tasks & Briefing state
  const [tasks, setTasks] = useState<TaskItem[]>([])
  const [tasksLoading, setTasksLoading] = useState(false)
  const [briefing, setBriefing] = useState<DailyBriefingData | null>(null)
  const [briefingLoading, setBriefingLoading] = useState(false)

  // Mobile navigation helper
  const [mobileShowDetail, setMobileShowDetail] = useState(false)

  // 1. Initial Authentication Check
  useEffect(() => {
    fetchCurrentUser()
      .then((data) => {
        setUser(data)
        setLoadingUser(false)
      })
      .catch(() => {
        navigate('/')
      })
  }, [navigate])

  // 2. Load Inbox emails based on current filters and search
  const loadInbox = useCallback(async (isLoadMore = false) => {
    try {
      if (isLoadMore) setLoadingMore(true)
      const res = await fetchInbox({
        priority:
          activeFilter === 'high' || activeFilter === 'medium' || activeFilter === 'low' || activeFilter === 'pending'
            ? activeFilter
            : null,
        unread: activeFilter === 'unread' ? true : null,
        has_deadline: activeFilter === 'deadlines' ? true : null,
        course: activeCourse,
        search: searchQuery || null,
        sort: sortMode,
        limit,
      })

      setEmails(res.emails)
      setTotalMatching(res.total)
      setCounts(res.counts)
      setSyncState(res.sync_state)
    } catch (err) {
      console.error('Failed loading inbox:', err)
    } finally {
      setInboxLoading(false)
      setLoadingMore(false)
    }
  }, [activeFilter, activeCourse, searchQuery, sortMode, limit])

  const handleLoadMore = () => {
    setLimit((prev) => prev + 50)
  }

  useEffect(() => {
    if (!loadingUser) {
      loadInbox()
    }
  }, [loadingUser, loadInbox])

  // 3. Load Tasks for Action Center
  const loadTasks = useCallback(async () => {
    try {
      setTasksLoading(true)
      const data = await fetchTasks('all')
      setTasks(data)
    } catch (err) {
      console.error('Failed loading tasks:', err)
    } finally {
      setTasksLoading(false)
    }
  }, [])

  // 4. Load Daily Briefing
  const loadBriefing = useCallback(async () => {
    try {
      setBriefingLoading(true)
      const data = await fetchDailyBriefing()
      setBriefing(data)
    } catch (err) {
      console.error('Failed loading briefing:', err)
    } finally {
      setBriefingLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!loadingUser) {
      loadTasks()
      loadBriefing()
    }
  }, [loadingUser, loadTasks, loadBriefing])

  // 5. Background Sync Polling
  // When synchronization is in progress, poll every 3 seconds to reflect new emails seamlessly
  useEffect(() => {
    if (syncState.status === 'syncing') {
      const interval = setInterval(() => {
        loadInbox()
        loadTasks()
        loadBriefing()
      }, 3500)
      return () => clearInterval(interval)
    }
  }, [syncState.status, loadInbox, loadTasks, loadBriefing])

  // 6. Handle Email Selection
  const handleSelectEmail = async (email: EmailListItem) => {
    setSelectedEmailId(email.gmail_message_id)
    setMobileShowDetail(true)
    setDetailLoading(true)

    // Mark as read in local list state immediately
    setEmails((prev) =>
      prev.map((e) => (e.gmail_message_id === email.gmail_message_id ? { ...e, is_unread: false } : e))
    )

    try {
      const detail = await fetchEmailDetail(email.gmail_message_id)
      setSelectedEmailDetail(detail)

      // If email is currently unanalyzed / pending, automatically trigger priority analysis
      if (detail.status === 'pending') {
        handleAnalyzeOnDemand(detail.gmail_message_id)
      }
    } catch (err) {
      console.error('Failed fetching email detail:', err)
    } finally {
      setDetailLoading(false)
    }
  }

  // 7. On-demand AI analysis trigger
  const handleAnalyzeOnDemand = async (messageId: string) => {
    setAnalyzingId(messageId)
    try {
      const updatedDetail = await analyzeEmail(messageId)
      setSelectedEmailDetail(updatedDetail)

      // Update in email list
      setEmails((prev) =>
        prev.map((e) =>
          e.gmail_message_id === messageId
            ? {
                ...e,
                status: updatedDetail.status,
                priority: updatedDetail.analysis?.priority || null,
                priority_reason: updatedDetail.analysis?.priority_reason || null,
                category: updatedDetail.analysis?.category || null,
                course: updatedDetail.analysis?.course || null,
                summary: updatedDetail.analysis?.summary || null,
                deadline_count: updatedDetail.analysis?.deadlines.length || 0,
                action_item_count: updatedDetail.analysis?.action_items.length || 0,
              }
            : e
        )
      )

      // Refresh tasks and briefing
      loadTasks()
      loadBriefing()
    } catch (err) {
      console.error('On-demand analysis error:', err)
    } finally {
      setAnalyzingId(null)
    }
  }

  // 8. Manual Sync Trigger
  const handleManualSync = async () => {
    try {
      setSyncState((prev) => ({ ...prev, status: 'syncing' }))
      const stats = await triggerSync()
      setSyncState({
        status: stats.is_initial_sync_complete ? 'idle' : 'syncing',
        last_synced_at: stats.last_synced_at || new Date().toISOString(),
        total_synced: stats.total_synced,
        total_available: stats.total_available,
        is_initial_sync_complete: stats.is_initial_sync_complete,
        sync_progress: stats.total_synced,
      })
      await loadInbox()
      await loadTasks()
      await loadBriefing()
    } catch (err) {
      console.error('Manual sync failed:', err)
      setSyncState((prev) => ({ ...prev, status: 'idle' }))
    }
  }

  // 9. Task Management Handlers
  const handleToggleTask = async (taskId: number, completed: boolean) => {
    try {
      setTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, completed } : t)))
      await updateTask(taskId, { completed })
      loadInbox()
    } catch (err) {
      console.error('Failed updating task:', err)
      loadTasks()
    }
  }

  const handleCreateTask = async (data: {
    title: string
    deadline_date?: string | null
    course?: string | null
    priority?: string
  }) => {
    try {
      const newTask = await createTask(data)
      setTasks((prev) => [newTask, ...prev])
      loadInbox()
    } catch (err) {
      console.error('Failed creating task:', err)
    }
  }

  const handleCreateTaskFromDeadline = async (text: string, date: string | null) => {
    if (!selectedEmailDetail) return
    await handleCreateTask({
      title: text,
      deadline_date: date,
      course: selectedEmailDetail.analysis?.course || null,
      priority: selectedEmailDetail.analysis?.priority || 'medium',
    })
  }

  const handleUpdateTask = async (taskId: number, updates: Partial<TaskItem>) => {
    try {
      const updated = await updateTask(taskId, updates)
      setTasks((prev) => prev.map((t) => (t.id === taskId ? updated : t)))
    } catch (err) {
      console.error('Failed updating task:', err)
    }
  }

  const handleDeleteTask = async (taskId: number) => {
    try {
      setTasks((prev) => prev.filter((t) => t.id !== taskId))
      await deleteTask(taskId)
      loadInbox()
    } catch (err) {
      console.error('Failed deleting task:', err)
      loadTasks()
    }
  }

  // 10. Open Email from Action Center
  const handleOpenEmailFromTask = async (messageId: string) => {
    setActiveView('inbox')
    const existing = emails.find((e) => e.gmail_message_id === messageId)
    if (existing) {
      handleSelectEmail(existing)
    } else {
      setSelectedEmailId(messageId)
      setDetailLoading(true)
      try {
        const detail = await fetchEmailDetail(messageId)
        setSelectedEmailDetail(detail)
      } catch (err) {
        console.error(err)
      } finally {
        setDetailLoading(false)
      }
    }
  }

  // Extract distinct course tags dynamically from emails
  const availableCourses = useMemo(() => {
    const set = new Set<string>()
    emails.forEach((e) => {
      if (e.course) set.add(e.course.trim().toUpperCase())
    })
    tasks.forEach((t) => {
      if (t.course) set.add(t.course.trim().toUpperCase())
    })
    return Array.from(set).sort()
  }, [emails, tasks])

  const activeFilterTitle = useMemo(() => {
    if (activeCourse) return `Course: ${activeCourse}`
    switch (activeFilter) {
      case 'unread':
        return 'Unread Messages'
      case 'high':
        return '🔴 High Priority'
      case 'medium':
        return '🟡 Medium Priority'
      case 'low':
        return '🟢 Low Priority'
      case 'deadlines':
        return '⏰ Messages with Deadlines'
      case 'pending':
        return '⏳ In Analysis Queue'
      default:
        return 'All Mail'
    }
  }, [activeFilter, activeCourse])

  if (loadingUser) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
            Loading UniPulse 2.0...
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-surface font-sans">
      {/* 1. Left Sidebar Navigation Pane */}
      <Sidebar
        user={user}
        activeView={activeView}
        setActiveView={setActiveView}
        activeFilter={activeFilter}
        setActiveFilter={setActiveFilter}
        counts={counts}
        syncState={syncState}
        onSync={handleManualSync}
        onLogout={async () => {
          await logoutUser()
          navigate('/')
        }}
        availableCourses={availableCourses}
        activeCourse={activeCourse}
        setActiveCourse={setActiveCourse}
      />

      {/* 2. Middle & Right Workspace Area */}
      <div className="flex-1 flex overflow-hidden">
        {activeView === 'inbox' ? (
          <>
            {/* Middle Pane: Central Email List */}
            <div
              className={`w-full md:w-[420px] lg:w-[460px] shrink-0 h-full ${
                mobileShowDetail ? 'hidden md:flex' : 'flex'
              }`}
            >
              <EmailList
                emails={emails}
                selectedId={selectedEmailId}
                onSelectEmail={handleSelectEmail}
                loading={inboxLoading}
                syncState={syncState}
                onManualSync={handleManualSync}
                sortMode={sortMode}
                setSortMode={setSortMode}
                searchQuery={searchQuery}
                setSearchQuery={setSearchQuery}
                activeFilterTitle={activeFilterTitle}
                totalMatching={totalMatching}
                onLoadMore={handleLoadMore}
                hasMore={emails.length < totalMatching}
                loadingMore={loadingMore}
              />
            </div>

            {/* Right Pane: Email Detail & AI Analysis Panel */}
            <div
              className={`flex-1 h-full bg-surface ${
                mobileShowDetail ? 'flex' : 'hidden md:flex'
              }`}
            >
              <EmailDetailPanel
                email={selectedEmailDetail}
                loading={detailLoading}
                onClose={() => {
                  setSelectedEmailId(null)
                  setSelectedEmailDetail(null)
                  setMobileShowDetail(false)
                }}
                onAnalyzeOnDemand={handleAnalyzeOnDemand}
                analyzingId={analyzingId}
                onCreateTaskFromDeadline={handleCreateTaskFromDeadline}
              />
            </div>
          </>
        ) : activeView === 'action_center' ? (
          <ActionCenter
            tasks={tasks}
            loading={tasksLoading}
            onToggleComplete={handleToggleTask}
            onCreateTask={handleCreateTask}
            onUpdateTask={handleUpdateTask}
            onDeleteTask={handleDeleteTask}
            onOpenEmail={handleOpenEmailFromTask}
            availableCourses={availableCourses}
          />
        ) : (
          <DailyBriefingBanner
            briefing={briefing}
            loading={briefingLoading}
            onSelectEmail={(email) => {
              setActiveView('inbox')
              handleSelectEmail(email)
            }}
            onViewTasks={() => setActiveView('action_center')}
          />
        )}
      </div>
    </div>
  )
}
