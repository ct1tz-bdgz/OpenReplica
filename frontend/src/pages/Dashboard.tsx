import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import {
  PlusIcon,
  RocketLaunchIcon,
  CodeBracketIcon,
  ChatBubbleLeftRightIcon,
  ClockIcon,
  CpuChipIcon,
} from '@heroicons/react/24/outline'
import { useQuery } from '@tanstack/react-query'
import { sessionAPI, agentAPI } from '@/lib/api'
import { useSessionStore } from '@/store/sessionStore'
import { formatDistanceToNow } from 'date-fns'

const stats = [
  {
    name: 'Total Sessions',
    value: '0',
    icon: ChatBubbleLeftRightIcon,
    color: 'text-primary-600',
    bgColor: 'bg-primary-100',
  },
  {
    name: 'Code Executions',
    value: '0',
    icon: CodeBracketIcon,
    color: 'text-success-600',
    bgColor: 'bg-success-100',
  },
  {
    name: 'Active Agents',
    value: '0',
    icon: CpuChipIcon,
    color: 'text-accent-600',
    bgColor: 'bg-accent-100',
  },
  {
    name: 'Time Saved',
    value: '0h',
    icon: ClockIcon,
    color: 'text-warning-600',
    bgColor: 'bg-warning-100',
  },
]

export default function Dashboard() {
  const { sessions, setSessions } = useSessionStore()

  const { data: sessionsData, isLoading } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => sessionAPI.list({ limit: 10 }),
    onSuccess: (response) => {
      setSessions(response.data)
    },
  })

  const { data: agentTypes } = useQuery({
    queryKey: ['agent-types'],
    queryFn: () => agentAPI.getTypesDetailed(),
  })

  const recentSessions = sessions.slice(0, 5)

  return (
    <div className="max-w-7xl mx-auto">
      {/* Hero Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-12"
      >
        <div className="flex items-center justify-center mb-6">
          <div className="w-16 h-16 bg-gradient-to-br from-primary-500 to-accent-500 rounded-2xl flex items-center justify-center shadow-lg shadow-primary-500/25">
            <RocketLaunchIcon className="w-8 h-8 text-white" />
          </div>
        </div>
        <h1 className="text-4xl font-bold text-gradient mb-4">
          Welcome to OpenReplica
        </h1>
        <p className="text-xl text-secondary-600 dark:text-secondary-300 max-w-2xl mx-auto mb-8">
          Your AI-powered coding assistant that helps you write, debug, and improve code faster than ever before.
        </p>
        
        <motion.div
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Link
            to="/session/new"
            className="inline-flex items-center space-x-2 btn-primary text-lg px-8 py-4 shadow-lg shadow-primary-500/25"
          >
            <PlusIcon className="w-5 h-5" />
            <span>Start New Session</span>
          </Link>
        </motion.div>
      </motion.div>

      {/* Stats Grid */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12"
      >
        {stats.map((stat, index) => (
          <motion.div
            key={stat.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + index * 0.05 }}
            className="card hover:shadow-lg transition-shadow"
          >
            <div className="flex items-center">
              <div className={`p-3 rounded-lg ${stat.bgColor}`}>
                <stat.icon className={`w-6 h-6 ${stat.color}`} />
              </div>
              <div className="ml-4">
                <p className="text-2xl font-bold text-secondary-900 dark:text-white">
                  {stat.value}
                </p>
                <p className="text-sm text-secondary-500">{stat.name}</p>
              </div>
            </div>
          </motion.div>
        ))}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Sessions */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
          className="card"
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold">Recent Sessions</h2>
            <Link
              to="/sessions"
              className="text-sm text-primary-600 hover:text-primary-700 font-medium"
            >
              View all
            </Link>
          </div>

          {isLoading ? (
            <div className="space-y-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="animate-pulse">
                  <div className="h-4 bg-secondary-200 rounded w-3/4 mb-2" />
                  <div className="h-3 bg-secondary-100 rounded w-1/2" />
                </div>
              ))}
            </div>
          ) : recentSessions.length > 0 ? (
            <div className="space-y-4">
              {recentSessions.map((session, index) => (
                <motion.div
                  key={session.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 + index * 0.05 }}
                >
                  <Link
                    to={`/session/${session.id}`}
                    className="block p-4 rounded-lg border border-secondary-200 hover:border-primary-300 hover:bg-primary-50/50 transition-all"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-secondary-900 dark:text-white">
                          {session.title}
                        </p>
                        <p className="text-sm text-secondary-500 mt-1">
                          {session.description || 'No description'}
                        </p>
                      </div>
                      <div className="text-xs text-secondary-400">
                        {formatDistanceToNow(new Date(session.created_at), {
                          addSuffix: true,
                        })}
                      </div>
                    </div>
                  </Link>
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-secondary-500">
              <ChatBubbleLeftRightIcon className="w-12 h-12 mx-auto mb-3 text-secondary-300" />
              <p>No sessions yet</p>
              <p className="text-sm mt-1">Create your first session to get started</p>
            </div>
          )}
        </motion.div>

        {/* Available Agents */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
          className="card"
        >
          <h2 className="text-lg font-semibold mb-6">Available AI Agents</h2>

          <div className="space-y-4">
            {agentTypes?.data?.map((agent: any, index: number) => (
              <motion.div
                key={agent.name}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + index * 0.05 }}
                className="p-4 rounded-lg border border-secondary-200 hover:border-primary-300 transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-accent-500 rounded-lg flex items-center justify-center">
                    <CpuChipIcon className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <p className="font-medium text-secondary-900 dark:text-white capitalize">
                      {agent.name} Agent
                    </p>
                    <p className="text-sm text-secondary-500">
                      {agent.description}
                    </p>
                  </div>
                </div>
              </motion.div>
            )) || (
              <div className="text-center py-4 text-secondary-500">
                <CpuChipIcon className="w-8 h-8 mx-auto mb-2 text-secondary-300" />
                <p className="text-sm">Loading agents...</p>
              </div>
            )}
          </div>
        </motion.div>
      </div>

      {/* Quick Actions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="mt-12 card"
      >
        <h2 className="text-lg font-semibold mb-6">Quick Actions</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            to="/session/new"
            className="p-6 rounded-lg border border-secondary-200 hover:border-primary-300 hover:bg-primary-50/50 transition-all text-center group"
          >
            <PlusIcon className="w-8 h-8 mx-auto mb-3 text-primary-600 group-hover:scale-110 transition-transform" />
            <p className="font-medium text-secondary-900 dark:text-white">New Session</p>
            <p className="text-sm text-secondary-500 mt-1">Start a new coding session</p>
          </Link>

          <Link
            to="/templates"
            className="p-6 rounded-lg border border-secondary-200 hover:border-primary-300 hover:bg-primary-50/50 transition-all text-center group"
          >
            <CodeBracketIcon className="w-8 h-8 mx-auto mb-3 text-primary-600 group-hover:scale-110 transition-transform" />
            <p className="font-medium text-secondary-900 dark:text-white">Browse Templates</p>
            <p className="text-sm text-secondary-500 mt-1">Explore project templates</p>
          </Link>

          <Link
            to="/settings"
            className="p-6 rounded-lg border border-secondary-200 hover:border-primary-300 hover:bg-primary-50/50 transition-all text-center group"
          >
            <CpuChipIcon className="w-8 h-8 mx-auto mb-3 text-primary-600 group-hover:scale-110 transition-transform" />
            <p className="font-medium text-secondary-900 dark:text-white">Configure AI</p>
            <p className="text-sm text-secondary-500 mt-1">Set up your AI preferences</p>
          </Link>
        </div>
      </motion.div>
    </div>
  )
}
