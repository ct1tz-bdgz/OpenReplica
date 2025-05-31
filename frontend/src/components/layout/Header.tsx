import { motion } from 'framer-motion'
import {
  Bars3Icon,
  SunIcon,
  MoonIcon,
  Cog6ToothIcon,
  UserCircleIcon,
} from '@heroicons/react/24/outline'
import { useAppStore } from '@/store/appStore'
import { useSessionStore } from '@/store/sessionStore'
import { Link } from 'react-router-dom'

export default function Header() {
  const { theme, toggleTheme, sidebarOpen, setSidebarOpen, isConnected } = useAppStore()
  const { currentSession, agentStatus } = useSessionStore()

  const getStatusColor = () => {
    if (!isConnected) return 'bg-error-500'
    switch (agentStatus) {
      case 'thinking':
      case 'responding':
        return 'bg-primary-500 animate-pulse'
      case 'executing':
        return 'bg-warning-500 animate-pulse'
      case 'error':
        return 'bg-error-500'
      default:
        return 'bg-success-500'
    }
  }

  const getStatusText = () => {
    if (!isConnected) return 'Disconnected'
    switch (agentStatus) {
      case 'thinking':
        return 'Thinking...'
      case 'responding':
        return 'Responding...'
      case 'executing':
        return 'Executing Code...'
      case 'error':
        return 'Error'
      default:
        return 'Ready'
    }
  }

  return (
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="bg-white/80 dark:bg-secondary-800/80 backdrop-blur-sm border-b border-secondary-200 dark:border-secondary-700 sticky top-0 z-50"
    >
      <div className="flex items-center justify-between px-4 py-3">
        {/* Left section */}
        <div className="flex items-center space-x-4">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 rounded-lg hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors"
          >
            <Bars3Icon className="w-5 h-5" />
          </button>

          <Link to="/" className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-accent-500 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">OR</span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-gradient">OpenReplica</h1>
              <p className="text-xs text-secondary-500 -mt-1">Code Less, Make More</p>
            </div>
          </Link>
        </div>

        {/* Center section - Current session info */}
        {currentSession && (
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="flex items-center space-x-3 bg-secondary-50 dark:bg-secondary-700 rounded-lg px-4 py-2"
          >
            <div className={`w-2 h-2 rounded-full ${getStatusColor()}`} />
            <div>
              <p className="font-medium text-sm truncate max-w-48">
                {currentSession.title}
              </p>
              <p className="text-xs text-secondary-500">
                {getStatusText()}
              </p>
            </div>
          </motion.div>
        )}

        {/* Right section */}
        <div className="flex items-center space-x-2">
          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors"
            title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
          >
            {theme === 'light' ? (
              <MoonIcon className="w-5 h-5" />
            ) : (
              <SunIcon className="w-5 h-5" />
            )}
          </button>

          {/* Settings */}
          <Link
            to="/settings"
            className="p-2 rounded-lg hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors"
            title="Settings"
          >
            <Cog6ToothIcon className="w-5 h-5" />
          </Link>

          {/* User menu */}
          <button
            className="p-2 rounded-lg hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors"
            title="User profile"
          >
            <UserCircleIcon className="w-5 h-5" />
          </button>
        </div>
      </div>
    </motion.header>
  )
}
