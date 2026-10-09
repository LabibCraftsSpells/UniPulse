import React, { useState } from 'react'
import {
  CheckSquare,
  Square,
  Calendar,
  Plus,
  Trash2,
  ExternalLink,
  CheckCircle2,
  Mail,
  Edit2,
  Check,
  X,
} from 'lucide-react'
import type { TaskItem } from '../types'

interface ActionCenterProps {
  tasks: TaskItem[]
  loading: boolean
  onToggleComplete: (taskId: number, completed: boolean) => void
  onCreateTask: (data: { title: string; deadline_date?: string | null; course?: string | null; priority?: string }) => void
  onUpdateTask: (taskId: number, updates: Partial<TaskItem>) => void
  onDeleteTask: (taskId: number) => void
  onOpenEmail: (messageId: string) => void
  availableCourses: string[]
}

export const ActionCenter: React.FC<ActionCenterProps> = ({
  tasks,
  loading,
  onToggleComplete,
  onCreateTask,
  onUpdateTask,
  onDeleteTask,
  onOpenEmail,
  availableCourses,
}) => {
  const [activeFilter, setActiveFilter] = useState<'all' | 'upcoming' | 'overdue' | 'completed'>('upcoming')
  const [selectedCourse, setSelectedCourse] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newDeadline, setNewDeadline] = useState('')
  const [newCourse, setNewCourse] = useState('')
  const [newPriority, setNewPriority] = useState('medium')

  const [editingId, setEditingId] = useState<number | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [editDate, setEditDate] = useState('')

  const todayStr = new Date().toISOString().split('T')[0]

  // Filter tasks locally
  const filteredTasks = tasks.filter((task) => {
    if (selectedCourse && task.course !== selectedCourse) return false

    if (activeFilter === 'completed') return task.completed
    if (activeFilter === 'upcoming') {
      return !task.completed && (!task.deadline_date || task.deadline_date >= todayStr)
    }
    if (activeFilter === 'overdue') {
      return !task.completed && task.deadline_date && task.deadline_date < todayStr
    }
    return true
  })

  const handleStartEdit = (task: TaskItem) => {
    setEditingId(task.id)
    setEditTitle(task.title)
    setEditDate(task.deadline_date || '')
  }

  const handleSaveEdit = (taskId: number) => {
    onUpdateTask(taskId, { title: editTitle, deadline_date: editDate || null })
    setEditingId(null)
  }

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTitle.trim()) return
    onCreateTask({
      title: newTitle.trim(),
      deadline_date: newDeadline || null,
      course: newCourse || null,
      priority: newPriority,
    })
    setNewTitle('')
    setNewDeadline('')
    setNewCourse('')
    setShowCreateModal(false)
  }

  return (
    <div className="flex-1 flex flex-col h-screen bg-surface-muted/40 overflow-hidden">
      {/* Top Header */}
      <div className="h-16 px-8 bg-surface border-b border-border flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-xl font-bold text-text tracking-tight flex items-center gap-2">
            <CheckSquare className="w-5 h-5 text-primary" />
            <span>Academic Action Center</span>
          </h1>
          <p className="text-xs text-text-secondary">Track deadlines, assignments, and tasks extracted from your university emails.</p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-primary text-white text-xs font-semibold hover:bg-primary-dark transition-all active:scale-95 shadow-sm"
        >
          <Plus className="w-4 h-4" />
          <span>New Task</span>
        </button>
      </div>

      {/* Filter Tabs Bar */}
      <div className="px-8 py-3 bg-surface border-b border-border flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-1 bg-surface-dark/80 p-1 rounded-xl border border-border/70">
          {(['upcoming', 'overdue', 'completed', 'all'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveFilter(tab)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all capitalize ${
                activeFilter === tab
                  ? 'bg-surface text-primary shadow-xs'
                  : 'text-text-secondary hover:text-text'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Course Filter Dropdown */}
        {availableCourses.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-secondary font-medium">Course:</span>
            <select
              value={selectedCourse || ''}
              onChange={(e) => setSelectedCourse(e.target.value || null)}
              className="bg-surface-dark text-xs text-text font-medium px-2.5 py-1.5 rounded-lg border border-border focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="">All Courses</option>
              {availableCourses.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Task List Content */}
      <div className="flex-1 overflow-y-auto p-8 max-w-4xl w-full mx-auto space-y-3">
        {loading && tasks.length === 0 ? (
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-16 bg-surface rounded-xl border border-border animate-pulse" />
            ))}
          </div>
        ) : filteredTasks.length === 0 ? (
          <div className="bg-surface rounded-2xl border border-border p-12 text-center max-w-md mx-auto mt-8 shadow-sm">
            <div className="w-12 h-12 rounded-full bg-surface-dark flex items-center justify-center mx-auto mb-3">
              <CheckCircle2 className="w-6 h-6 text-success" />
            </div>
            <h3 className="text-base font-bold text-text mb-1">
              {activeFilter === 'completed'
                ? 'No completed tasks yet'
                : activeFilter === 'overdue'
                ? 'No overdue tasks!'
                : 'All caught up!'}
            </h3>
            <p className="text-xs text-text-secondary leading-relaxed mb-4">
              {activeFilter === 'overdue'
                ? 'Great job staying ahead of your academic calendar.'
                : 'Sync your Gmail inbox or create custom academic tasks above.'}
            </p>
          </div>
        ) : (
          filteredTasks.map((task) => {
            const isOverdue = !task.completed && task.deadline_date && task.deadline_date < todayStr
            const isEditing = editingId === task.id

            return (
              <div
                key={task.id}
                className={`bg-surface rounded-xl p-4 border transition-all duration-150 flex items-start justify-between gap-4 shadow-2xs hover:shadow-xs ${
                  task.completed
                    ? 'opacity-70 border-border bg-surface-muted/40'
                    : isOverdue
                    ? 'border-red-200 dark:border-red-900/60 bg-red-50/20 dark:bg-red-950/20'
                    : 'border-border hover:border-primary/40'
                }`}
              >
                <div className="flex items-start gap-3 min-w-0 flex-1">
                  <button
                    onClick={() => onToggleComplete(task.id, !task.completed)}
                    className="mt-0.5 text-text-secondary hover:text-primary transition-colors shrink-0"
                  >
                    {task.completed ? (
                      <CheckSquare className="w-5 h-5 text-primary" />
                    ) : (
                      <Square className="w-5 h-5 text-border hover:text-primary" />
                    )}
                  </button>

                  <div className="min-w-0 flex-1">
                    {isEditing ? (
                      <div className="space-y-2">
                        <input
                          type="text"
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          className="w-full text-sm font-medium px-2.5 py-1 bg-surface-dark text-text border border-primary rounded-lg focus:outline-none"
                        />
                        <div className="flex items-center gap-2">
                          <input
                            type="date"
                            value={editDate}
                            onChange={(e) => setEditDate(e.target.value)}
                            className="text-xs px-2 py-1 bg-surface-dark text-text border border-border rounded"
                          />
                          <button
                            onClick={() => handleSaveEdit(task.id)}
                            className="p-1 text-success hover:bg-green-50 dark:hover:bg-green-950/50 rounded"
                          >
                            <Check className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => setEditingId(null)}
                            className="p-1 text-danger hover:bg-red-50 dark:hover:bg-red-950/50 rounded"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <p
                          className={`text-sm font-semibold text-text leading-snug ${
                            task.completed ? 'line-through text-text-secondary' : ''
                          }`}
                        >
                          {task.title}
                        </p>

                        <div className="flex flex-wrap items-center gap-2 mt-1.5 text-xs text-text-secondary">
                          {task.course && (
                            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200/60 dark:bg-indigo-950/40 dark:text-indigo-300 dark:border-indigo-900/60">
                              {task.course}
                            </span>
                          )}

                          {task.deadline_date && (
                            <span
                              className={`flex items-center gap-1 font-medium ${
                                isOverdue ? 'text-danger dark:text-red-400 font-semibold' : 'text-text-secondary'
                              }`}
                            >
                              <Calendar className="w-3.5 h-3.5" />
                              <span>{task.deadline_date}</span>
                              {task.deadline_time && <span>at {task.deadline_time}</span>}
                              {isOverdue && <span className="text-[10px] uppercase font-bold">(Overdue)</span>}
                            </span>
                          )}

                          {task.email_subject && (
                            <span className="text-text-secondary/70 truncate max-w-xs flex items-center gap-1">
                              <Mail className="w-3 h-3 shrink-0" />
                              <span className="truncate">{task.email_subject}</span>
                            </span>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-1 shrink-0">
                  {task.gmail_message_id && (
                    <button
                      onClick={() => onOpenEmail(task.gmail_message_id!)}
                      className="p-1.5 text-text-secondary hover:text-primary hover:bg-surface-dark rounded-lg transition-colors"
                      title="View originating email"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </button>
                  )}

                  {!isEditing && (
                    <button
                      onClick={() => handleStartEdit(task)}
                      className="p-1.5 text-text-secondary hover:text-text hover:bg-surface-dark rounded-lg transition-colors"
                      title="Edit task"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                  )}

                  <button
                    onClick={() => onDeleteTask(task.id)}
                    className="p-1.5 text-text-secondary hover:text-danger hover:bg-red-50 dark:hover:bg-red-950/50 rounded-lg transition-colors"
                    title="Delete task"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* Create Task Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-surface rounded-2xl max-w-md w-full p-6 shadow-2xl border border-border space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-text">Create Academic Task</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-1 text-text-secondary hover:text-text rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-text mb-1">Task Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Complete CSE231 Lab Assignment 3"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full text-xs p-2.5 rounded-xl bg-surface-dark/70 text-text border border-border focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-text mb-1">Deadline Date</label>
                  <input
                    type="date"
                    value={newDeadline}
                    onChange={(e) => setNewDeadline(e.target.value)}
                    className="w-full text-xs p-2.5 rounded-xl bg-surface-dark/70 text-text border border-border focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-text mb-1">Course Code</label>
                  <input
                    type="text"
                    placeholder="e.g. CSE231"
                    value={newCourse}
                    onChange={(e) => setNewCourse(e.target.value.toUpperCase())}
                    className="w-full text-xs p-2.5 rounded-xl bg-surface-dark/70 text-text border border-border focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-text mb-1">Priority</label>
                <select
                  value={newPriority}
                  onChange={(e) => setNewPriority(e.target.value)}
                  className="w-full text-xs p-2.5 rounded-xl bg-surface-dark/70 text-text border border-border focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="high">High Priority</option>
                  <option value="medium">Medium Priority</option>
                  <option value="low">Low Priority</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-xs font-medium text-text-secondary hover:text-text rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-semibold bg-primary text-white hover:bg-primary-dark rounded-xl shadow-sm"
                >
                  Save Task
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
