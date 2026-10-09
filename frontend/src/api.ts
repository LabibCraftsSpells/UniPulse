/**
 * UniPulse 2.0 API Client
 */

import type {
  UserProfile,
  InboxResponse,
  EmailDetailResponse,
  TaskItem,
  DailyBriefingData,
  SyncTimingStats,
} from './types'

export async function fetchCurrentUser(): Promise<UserProfile> {
  const res = await fetch('/auth/me')
  if (!res.ok) throw new Error('Not authenticated')
  return res.json()
}

export async function logoutUser(): Promise<void> {
  await fetch('/auth/disconnect', { method: 'POST' })
}

export async function fetchInbox(params: {
  priority?: string | null
  unread?: boolean | null
  has_deadline?: boolean | null
  course?: string | null
  category?: string | null
  search?: string | null
  sort?: 'priority' | 'newest'
  limit?: number
  offset?: number
}): Promise<InboxResponse> {
  const query = new URLSearchParams()
  if (params.priority && params.priority !== 'all') query.set('priority', params.priority)
  if (params.unread !== undefined && params.unread !== null) query.set('unread', String(params.unread))
  if (params.has_deadline) query.set('has_deadline', 'true')
  if (params.course) query.set('course', params.course)
  if (params.category) query.set('category', params.category)
  if (params.search) query.set('search', params.search)
  if (params.sort) query.set('sort', params.sort)
  if (params.limit) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))

  const res = await fetch(`/api/emails?${query.toString()}`)
  if (!res.ok) throw new Error('Failed to load inbox')
  return res.json()
}

export async function triggerSync(): Promise<SyncTimingStats> {
  const res = await fetch('/api/sync', { method: 'POST' })
  if (!res.ok) throw new Error('Failed to trigger synchronization')
  return res.json()
}

export async function fetchEmailDetail(messageId: string): Promise<EmailDetailResponse> {
  const res = await fetch(`/api/emails/${messageId}`)
  if (!res.ok) throw new Error('Failed to load email details')
  return res.json()
}

export async function analyzeEmail(messageId: string): Promise<EmailDetailResponse> {
  const res = await fetch(`/api/emails/${messageId}/analyze`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to analyze email')
  return res.json()
}

export async function toggleEmailRead(messageId: string, isUnread: boolean): Promise<{ is_unread: boolean }> {
  const res = await fetch(`/api/emails/${messageId}?is_unread=${isUnread}`, { method: 'PATCH' })
  if (!res.ok) throw new Error('Failed to update email status')
  return res.json()
}

export async function fetchTasks(filter: string = 'all', course?: string): Promise<TaskItem[]> {
  const query = new URLSearchParams({ filter })
  if (course) query.set('course', course)
  const res = await fetch(`/api/tasks?${query.toString()}`)
  if (!res.ok) throw new Error('Failed to load tasks')
  return res.json()
}

export async function createTask(data: {
  title: string
  gmail_message_id?: string | null
  deadline_date?: string | null
  deadline_time?: string | null
  course?: string | null
  priority?: string
}): Promise<TaskItem> {
  const res = await fetch('/api/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to create task')
  return res.json()
}

export async function updateTask(taskId: number, updates: Partial<TaskItem>): Promise<TaskItem> {
  const res = await fetch(`/api/tasks/${taskId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  })
  if (!res.ok) throw new Error('Failed to update task')
  return res.json()
}

export async function deleteTask(taskId: number): Promise<void> {
  const res = await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Failed to delete task')
}

export async function fetchDailyBriefing(): Promise<DailyBriefingData> {
  const res = await fetch('/api/briefing')
  if (!res.ok) throw new Error('Failed to load briefing')
  return res.json()
}
