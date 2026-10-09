import React from 'react'
import { Sun, Moon } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'

interface ThemeToggleProps {
  compact?: boolean
  className?: string
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({ compact = false, className = '' }) => {
  const { theme, toggleTheme, setTheme } = useTheme()

  if (compact) {
    return (
      <button
        onClick={toggleTheme}
        className={`p-1.5 rounded-lg text-text-secondary hover:text-text hover:bg-surface-dark transition-all active:scale-95 ${className}`}
        title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} mode`}
        aria-label="Toggle theme"
      >
        {theme === 'dark' ? (
          <Sun className="w-4 h-4 text-amber-400 transition-transform duration-200 hover:rotate-45" />
        ) : (
          <Moon className="w-4 h-4 text-slate-600 transition-transform duration-200 hover:-rotate-12" />
        )}
      </button>
    )
  }

  return (
    <div
      className={`flex items-center p-0.5 rounded-xl bg-surface-dark/80 border border-border/80 text-xs ${className}`}
      role="radiogroup"
      aria-label="Theme toggle"
    >
      <button
        type="button"
        onClick={() => setTheme('light')}
        role="radio"
        aria-checked={theme === 'light'}
        className={`flex-1 flex items-center justify-center gap-1.5 py-1 px-2.5 rounded-lg font-medium transition-all duration-150 ${
          theme === 'light'
            ? 'bg-surface text-primary shadow-xs font-semibold'
            : 'text-text-secondary hover:text-text'
        }`}
      >
        <Sun className="w-3.5 h-3.5 text-amber-500" />
        <span>Light</span>
      </button>
      <button
        type="button"
        onClick={() => setTheme('dark')}
        role="radio"
        aria-checked={theme === 'dark'}
        className={`flex-1 flex items-center justify-center gap-1.5 py-1 px-2.5 rounded-lg font-medium transition-all duration-150 ${
          theme === 'dark'
            ? 'bg-surface text-primary shadow-xs font-semibold'
            : 'text-text-secondary hover:text-text'
        }`}
      >
        <Moon className="w-3.5 h-3.5 text-blue-400" />
        <span>Dark</span>
      </button>
    </div>
  )
}
