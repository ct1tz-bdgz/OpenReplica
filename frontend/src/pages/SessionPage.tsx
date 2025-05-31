import { useEffect, useState } from 'react'
import { useParams, Navigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { sessionAPI, conversationAPI } from '@/lib/api'
import { useSessionStore } from '@/store/sessionStore'
import { useWebSocket } from '@/hooks/useWebSocket'
import ChatInterface from '@/components/session/ChatInterface'
import CodeEditor from '@/components/session/CodeEditor'
import FileExplorer from '@/components/session/FileExplorer'
import Terminal from '@/components/session/Terminal'
import SessionHeader from '@/components/session/SessionHeader'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'

export default function SessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [activeTab, setActiveTab] = useState('chat')
  
  const {
    currentSession,
    setCurrentSession,
    currentConversation,
    setCurrentConversation,
    setConversations,
  } = useSessionStore()

  // Initialize WebSocket connection
  const { isConnected, sendMessage } = useWebSocket(sessionId || null)

  // Load session data
  const { data: sessionData, isLoading: sessionLoading, error: sessionError } = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => sessionAPI.get(sessionId!),
    enabled: !!sessionId && sessionId !== 'new',
    onSuccess: (response) => {
      setCurrentSession(response.data)
    },
  })

  // Load conversations for the session
  const { data: conversationsData } = useQuery({
    queryKey: ['conversations', sessionId],
    queryFn: () => conversationAPI.list(sessionId!),
    enabled: !!sessionId && sessionId !== 'new',
    onSuccess: (response) => {
      const conversations = response.data
      setConversations(sessionId!, conversations)
      
      // Set the first conversation as current
      if (conversations.length > 0 && !currentConversation) {
        setCurrentConversation(conversations[0])
      }
    },
  })

  // Handle new session creation
  useEffect(() => {
    if (sessionId === 'new') {
      // Create a new session
      handleCreateNewSession()
    }
  }, [sessionId])

  const handleCreateNewSession = async () => {
    try {
      const response = await sessionAPI.create({
        title: `Session ${new Date().toLocaleString()}`,
        description: 'New coding session',
        llm_provider: 'openai',
        llm_model: 'gpt-4',
      })
      
      const newSession = response.data
      setCurrentSession(newSession)
      
      // Redirect to the new session
      window.history.replaceState({}, '', `/session/${newSession.id}`)
      
    } catch (error) {
      console.error('Error creating session:', error)
    }
  }

  if (sessionId !== 'new' && sessionError) {
    return <Navigate to="/" replace />
  }

  if (sessionLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="loading-spinner w-8 h-8" />
      </div>
    )
  }

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col">
      {/* Session Header */}
      {currentSession && (
        <SessionHeader session={currentSession} isConnected={isConnected} />
      )}

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - File Explorer */}
        <motion.div
          initial={{ x: -20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          className="w-64 border-r border-secondary-200 dark:border-secondary-700 bg-white dark:bg-secondary-800"
        >
          <FileExplorer sessionId={sessionId} />
        </motion.div>

        {/* Center Panel - Chat/Code Editor */}
        <div className="flex-1 flex flex-col">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
            <TabsList className="border-b border-secondary-200 dark:border-secondary-700 bg-transparent p-0 h-auto">
              <TabsTrigger
                value="chat"
                className="px-4 py-3 data-[state=active]:bg-primary-50 data-[state=active]:text-primary-700 data-[state=active]:border-b-2 data-[state=active]:border-primary-500"
              >
                Chat
              </TabsTrigger>
              <TabsTrigger
                value="editor"
                className="px-4 py-3 data-[state=active]:bg-primary-50 data-[state=active]:text-primary-700 data-[state=active]:border-b-2 data-[state=active]:border-primary-500"
              >
                Code Editor
              </TabsTrigger>
            </TabsList>

            <TabsContent value="chat" className="flex-1 p-0 m-0">
              <ChatInterface
                sessionId={sessionId}
                conversation={currentConversation}
                onSendMessage={sendMessage}
                isConnected={isConnected}
              />
            </TabsContent>

            <TabsContent value="editor" className="flex-1 p-0 m-0">
              <CodeEditor sessionId={sessionId} />
            </TabsContent>
          </Tabs>
        </div>

        {/* Right Panel - Terminal */}
        <motion.div
          initial={{ x: 20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          className="w-80 border-l border-secondary-200 dark:border-secondary-700 bg-white dark:bg-secondary-800"
        >
          <Terminal sessionId={sessionId} />
        </motion.div>
      </div>
    </div>
  )
}
