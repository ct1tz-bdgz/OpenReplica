import { Routes, Route, Navigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import Layout from '@/components/layout/Layout'
import Dashboard from '@/pages/Dashboard'
import SessionPage from '@/pages/SessionPage'
import SettingsPage from '@/pages/SettingsPage'
import { useAppStore } from '@/store/appStore'
import { useEffect } from 'react'

function App() {
  const { theme, initializeApp } = useAppStore()

  useEffect(() => {
    initializeApp()
  }, [initializeApp])

  return (
    <div className={`min-h-screen ${theme === 'dark' ? 'dark' : ''}`}>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="min-h-screen bg-gradient-to-br from-secondary-50 via-white to-primary-50 dark:from-secondary-900 dark:via-secondary-800 dark:to-secondary-900"
      >
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="session/:sessionId" element={<SessionPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </motion.div>
    </div>
  )
}

export default App
