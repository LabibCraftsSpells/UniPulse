/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useEffect, useState } from 'react'

type Theme = 'light' | 'dark'

interface ThemeContextType {
  theme: Theme
  isDark: boolean
  toggleTheme: () => void
  setTheme: (theme: Theme) => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

const STORAGE_KEY = 'unipulse_theme'

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<Theme>(() => {
    // Check localStorage first
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(STORAGE_KEY) as Theme | null
      if (saved === 'light' || saved === 'dark') {
        return saved
      }
      // Fallback to system preference
      if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return 'dark'
      }
    }
    return 'light'
  })

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'dark') {
      root.classList.add('dark')
      root.style.colorScheme = 'dark'
    } else {
      root.classList.remove('dark')
      root.style.colorScheme = 'light'
    }
    localStorage.setItem(STORAGE_KEY, theme)
  }, [theme])

  // Listen to OS system theme changes if user hasn't explicitly set one or to keep responsive
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = (e: MediaQueryListEvent) => {
      const saved = localStorage.getItem(STORAGE_KEY)
      // Only auto-switch if user hasn't manually set a theme in localStorage
      if (!saved) {
        setThemeState(e.matches ? 'dark' : 'light')
      }
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])

  const toggleTheme = () => {
    setThemeState((prev) => (prev === 'dark' ? 'light' : 'dark'))
  }

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme)
  }

  return (
    <ThemeContext.Provider
      value={{
        theme,
        isDark: theme === 'dark',
        toggleTheme,
        setTheme,
      }}
    >
      {children}
    </ThemeContext.Provider>
  )
}

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
