import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import MainLayout from '@/components/layout/MainLayout'
import HomePage from '@/pages/HomePage'
import WorkspacePage from '@/pages/WorkspacePage'
import SettingsPage from '@/pages/SettingsPage'
import { useAppStore } from '@/stores/appStore'

function App() {
  const { theme } = useAppStore()

  return (
    <div className={`app ${theme}`}>
      <AnimatePresence mode="wait">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/workspace/:sessionId?" element={
            <MainLayout>
              <WorkspacePage />
            </MainLayout>
          } />
          <Route path="/settings" element={
            <MainLayout>
              <SettingsPage />
            </MainLayout>
          } />
        </Routes>
      </AnimatePresence>
    </div>
  )
}

export default App
