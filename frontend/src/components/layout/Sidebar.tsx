import { motion, AnimatePresence } from 'framer-motion'
import { Link, useLocation } from 'react-router-dom'
import {
  PlusIcon,
  ChatBubbleLeftRightIcon,
  ClockIcon,
  TrashIcon,
  PlayIcon,
  PauseIcon,
} from '@heroicons/react/24/outline'
import { useAppStore } from '@/store/appStore'
import { useSessionStore } from '@/store/sessionStore'
import { useQuery } from '@tanstack/react-query'
import { sessionAPI } from '@/lib/api'
import { formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'

export default function Sidebar() {
  const location = useLocation()
  const { sidebarOpen } = useAppStore()
  const { sessions, setSessions, currentSession, setCurrentSession } = useSessionStore()

  const { data: sessionsData, isLoading } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => sessionAPI.list({ limit: 50 }),
    onSuccess: (response) => {
      setSessions(response.data)
    },
  })

  const handleCreateSession = async () => {
    try {
      const response = await sessionAPI.create({
        title: `Session ${new Date().toLocaleString()}`,
        description: 'New coding session',
        llm_provider: 'openai',
        llm_model: 'gpt-4',
      })
      
      const newSession = response.data
      setSessions([newSession, ...sessions])
      toast.success('New session created!')
      
    } catch (error) {
      console.error('Error creating session:', error)
      toast.error('Failed to create session')
    }
  }

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    
    if (!confirm('Are you sure you want to delete this session?')) return
    
    try {
      await sessionAPI.delete(sessionId)
      setSessions(sessions.filter(s => s.id !== sessionId))
      
      if (currentSession?.id === sessionId) {
        setCurrentSession(null)
      }
      
      toast.success('Session deleted')
    } catch (error) {
      console.error('Error deleting session:', error)
      toast.error('Failed to delete session')
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <PlayIcon className="w-3 h-3 text-success-500" />
      case 'paused':
        return <PauseIcon className="w-3 h-3 text-warning-500" />
      default:
        return <ClockIcon className="w-3 h-3 text-secondary-400" />
    }
  }

  return (
    <motion.aside
      layout
      initial={{ x: -100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className={`fixed left-0 top-16 h-[calc(100vh-4rem)] bg-white dark:bg-secondary-800 border-r border-secondary-200 dark:border-secondary-700 transition-all duration-300 z-40 ${
        sidebarOpen ? 'w-64' : 'w-16'
      }`}
    >
      <div className="flex flex-col h-full">
        {/* Create session button */}
        <div className="p-4 border-b border-secondary-200 dark:border-secondary-700">
          <motion.button
            onClick={handleCreateSession}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className={`w-full btn-primary ${
              sidebarOpen ? 'px-4 py-2' : 'p-2 justify-center'
            }`}
            title="Create new session"
          >
            <PlusIcon className="w-5 h-5" />
            <AnimatePresence>
              {sidebarOpen && (
                <motion.span
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: 'auto' }}
                  exit={{ opacity: 0, width: 0 }}
                  className="ml-2 whitespace-nowrap"
                >
                  New Session
                </motion.span>
              )}
            </AnimatePresence>
          </motion.button>
        </div>

        {/* Sessions list */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-2">
            <AnimatePresence>
              {sidebarOpen && (
                <motion.h3
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="text-xs font-semibold text-secondary-500 uppercase tracking-wider mb-3 px-2"
                >
                  Recent Sessions
                </motion.h3>
              )}
            </AnimatePresence>

            {isLoading ? (
              <div className="space-y-2">
                {[...Array(5)].map((_, i) => (
                  <div
                    key={i}
                    className={`animate-pulse bg-secondary-100 dark:bg-secondary-700 rounded-lg ${
                      sidebarOpen ? 'h-16' : 'h-10 w-10'
                    }`}
                  />
                ))}
              </div>
            ) : (
              <div className="space-y-1">
                {sessions.map((session) => (
                  <motion.div
                    key={session.id}
                    layout
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <Link
                      to={`/session/${session.id}`}
                      className={`block p-3 rounded-lg transition-colors group ${
                        location.pathname === `/session/${session.id}`
                          ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                          : 'hover:bg-secondary-50 dark:hover:bg-secondary-700'
                      } ${!sidebarOpen && 'p-2'}`}
                    >
                      <div className="flex items-center justify-between">
                        <div className={`flex items-center space-x-3 ${!sidebarOpen && 'justify-center'}`}>
                          <ChatBubbleLeftRightIcon className="w-5 h-5 flex-shrink-0" />
                          <AnimatePresence>
                            {sidebarOpen && (
                              <motion.div
                                initial={{ opacity: 0, width: 0 }}
                                animate={{ opacity: 1, width: 'auto' }}
                                exit={{ opacity: 0, width: 0 }}
                                className="flex-1 min-w-0"
                              >
                                <p className="font-medium text-sm truncate">
                                  {session.title}
                                </p>
                                <div className="flex items-center space-x-2 mt-1">
                                  {getStatusIcon(session.status)}
                                  <span className="text-xs text-secondary-500">
                                    {formatDistanceToNow(new Date(session.created_at), {
                                      addSuffix: true,
                                    })}
                                  </span>
                                </div>
                              </motion.div>
                            )}
                          </AnimatePresence>
                        </div>

                        <AnimatePresence>
                          {sidebarOpen && (
                            <motion.button
                              initial={{ opacity: 0, scale: 0.8 }}
                              animate={{ opacity: 1, scale: 1 }}
                              exit={{ opacity: 0, scale: 0.8 }}
                              onClick={(e) => handleDeleteSession(session.id, e)}
                              className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-error-100 dark:hover:bg-error-900/30 text-error-600 transition-all"
                              title="Delete session"
                            >
                              <TrashIcon className="w-4 h-4" />
                            </motion.button>
                          )}
                        </AnimatePresence>
                      </div>
                    </Link>
                  </motion.div>
                ))}
              </div>
            )}

            {!isLoading && sessions.length === 0 && (
              <AnimatePresence>
                {sidebarOpen && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="text-center py-8 text-secondary-500"
                  >
                    <ChatBubbleLeftRightIcon className="w-12 h-12 mx-auto mb-3 text-secondary-300" />
                    <p className="text-sm">No sessions yet</p>
                    <p className="text-xs mt-1">Create your first session to get started</p>
                  </motion.div>
                )}
              </AnimatePresence>
            )}
          </div>
        </div>
      </div>
    </motion.aside>
  )
}
