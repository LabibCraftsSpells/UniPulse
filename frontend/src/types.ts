/**
 * UniPulse 2.0 TypeScript Interfaces
 */

export interface UserProfile {
  id: string
  email: string
  name: string | null
  picture: string | null
  has_profile?: boolean
}

export interface ExtractedActionItem {
  title: string
  deadline: string | null
  deadline_confidence: 'explicit' | 'ambiguous' | 'inferred' | 'none'
  completed: boolean
}

export interface ExtractedDeadline {
  date: string | null
  time: string | null
  source_text: string | null
  confidence: 'explicit' | 'ambiguous' | 'inferred' | 'none'
}

export interface ExtractedLink {
  label: string
  url: string
}

export interface EmailAnalysisResult {
  summary: string
  priority: 'high' | 'medium' | 'low'
  priority_reason: string
  category: string
  course: string | null
  what_this_means: string
  action_items: ExtractedActionItem[]
  deadlines: ExtractedDeadline[]
  important_links: ExtractedLink[]
}

export interface EmailListItem {
  gmail_message_id: string
  thread_id?: string | null
  sender: string
  sender_name?: string | null
  subject: string
  received_at: string | null
  snippet: string
  body_preview: string
  gmail_link: string
  is_unread: boolean
  has_attachments: boolean
  status: 'pending' | 'analyzing' | 'completed' | 'failed'
  priority?: 'high' | 'medium' | 'low' | null
  priority_reason?: string | null
  category?: string | null
  course?: string | null
  summary?: string | null
  deadline_count: number
  action_item_count: number
  next_deadline?: string | null
}

export interface EmailDetailResponse {
  gmail_message_id: string
  thread_id?: string | null
  sender: string
  sender_name?: string | null
  subject: string
  received_at: string | null
  snippet: string
  gmail_link: string
  is_unread: boolean
  has_attachments: boolean
  body_text: string
  body_html: string
  status: 'pending' | 'analyzing' | 'completed' | 'failed'
  analysis?: EmailAnalysisResult | null
  analyzed_at?: string | null
}

export interface TaskItem {
  id: number
  gmail_message_id?: string | null
  email_subject?: string | null
  email_sender?: string | null
  title: string
  deadline_date?: string | null
  deadline_time?: string | null
  deadline_confidence: string
  completed: boolean
  completed_at?: string | null
  course?: string | null
  priority: string
  created_at?: string | null
}

export interface InboxCounts {
  all: number
  unread: number
  high: number
  medium: number
  low: number
  pending: number
  deadlines: number
  tasks_pending: number
  tasks_overdue: number
}

export interface SyncState {
  status: 'idle' | 'syncing' | 'error'
  last_synced_at: string | null
  total_synced: number
  total_available: number
  is_initial_sync_complete: boolean
  sync_progress: number
  error?: string | null
}

export interface SyncTimingStats {
  status: string
  sync_type: string
  new_messages: number
  total_synced: number
  total_available: number
  is_initial_sync_complete: boolean
  gmail_api_ms: number
  db_ms: number
  total_sync_ms: number
  history_id?: string | null
  last_synced_at?: string | null
}

export interface InboxResponse {
  emails: EmailListItem[]
  total: number
  limit: number
  offset: number
  counts: InboxCounts
  sync_state: SyncState
}

export interface DailyBriefingData {
  unread_requiring_attention: number
  upcoming_deadlines_count: number
  overdue_tasks_count: number
  high_priority_count: number
  new_since_last_sync: number
  last_synced_at: string | null
  upcoming_deadlines: TaskItem[]
  recent_high_priority: EmailListItem[]
}
