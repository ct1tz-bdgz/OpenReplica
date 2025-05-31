import { motion } from 'framer-motion'
import {
  PlayIcon,
  PauseIcon,
  StopIcon,
  Cog6ToothIcon,
  ShareIcon,
} from '@heroicons/react/24/outline'
import { Session } from '@/store/sessionStore'
import { formatDistanceToNow } from 'date-fns'

interface SessionHeaderProps {
  session: Session
  isConnected: boolean
}

export default function SessionHeader({ session, isConnected }: SessionHeaderProps) {
  const getStatusColor = () => {
    if (!isConnected) return 'bg-error-500'
    switch (session.status) {
      case 'active':
        return 'bg-success-500'
      case 'paused':
        return 'bg-warning-500'
      case 'error':
        return 'bg-error-500'
      default:
        return 'bg-secondary-400'
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-secondary-800 border-b border-secondary-200 dark:border-secondary-700 px-6 py-4"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className={`w-3 h-3 rounded-full ${getStatusColor()}`} />
          <div>
            <h1 className="text-xl font-semibold text-secondary-900 dark:text-white">
              {session.title}
            </h1>
            <p className="text-sm text-secondary-500">
              Created {formatDistanceToNow(new Date(session.created_at), { addSuffix: true })} • 
              {session.llm_provider} ({session.llm_model})
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            className="btn-ghost"
            title="Session settings"
          >
            <Cog6ToothIcon className="w-4 h-4" />
          </button>
          
          <button
            className="btn-ghost"
            title="Share session"
          >
            <ShareIcon className="w-4 h-4" />
          </button>

          <div className="h-4 w-px bg-secondary-300 dark:bg-secondary-600" />

          <button
            className="btn-secondary"
            title="Pause session"
          >
            <PauseIcon className="w-4 h-4" />
            <span className="ml-1">Pause</span>
          </button>
          
          <button
            className="btn-error"
            title="Stop session"
          >
            <StopIcon className="w-4 h-4" />
            <span className="ml-1">Stop</span>
          </button>
        </div>
      </div>
    </motion.div>
  )
}
