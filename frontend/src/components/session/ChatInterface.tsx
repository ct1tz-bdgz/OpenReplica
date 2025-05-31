import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  PaperAirplaneIcon,
  MicrophoneIcon,
  PhotoIcon,
  PaperClipIcon,
} from '@heroicons/react/24/outline'
import { useSessionStore, Conversation, Message } from '@/store/sessionStore'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { useAppStore } from '@/store/appStore'
import { formatDistanceToNow } from 'date-fns'

interface ChatInterfaceProps {
  sessionId?: string
  conversation?: Conversation | null
  onSendMessage: (message: any) => boolean
  isConnected: boolean
}

export default function ChatInterface({
  sessionId,
  conversation,
  onSendMessage,
  isConnected,
}: ChatInterfaceProps) {
  const [message, setMessage] = useState('')
  const [isComposing, setIsComposing] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const { theme } = useAppStore()
  const { agentStatus, currentResponse } = useSessionStore()

  const messages = conversation?.messages || []

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, currentResponse])

  const handleSend = () => {
    if (!message.trim() || !isConnected || agentStatus !== 'idle') return

    const success = onSendMessage({
      type: 'message',
      content: message.trim(),
      conversation_id: conversation?.id,
    })

    if (success) {
      setMessage('')
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value)
    
    // Auto-resize textarea
    const textarea = e.target
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`
  }

  const renderMessage = (msg: Message) => (
    <motion.div
      key={msg.id}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} mb-4`}
    >
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          msg.role === 'user'
            ? 'message-user'
            : msg.role === 'system'
            ? 'message-system'
            : 'message-assistant'
        }`}
      >
        {msg.role === 'assistant' && (
          <div className="flex items-center space-x-2 mb-2">
            <div className="w-6 h-6 bg-gradient-to-br from-primary-500 to-accent-500 rounded-full flex items-center justify-center">
              <span className="text-white text-xs font-bold">AI</span>
            </div>
            <span className="text-xs text-secondary-500">Assistant</span>
          </div>
        )}
        
        <div className="prose prose-sm max-w-none dark:prose-invert">
          <ReactMarkdown
            components={{
              code({ node, inline, className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '')
                return !inline && match ? (
                  <SyntaxHighlighter
                    style={theme === 'dark' ? oneDark : oneLight}
                    language={match[1]}
                    PreTag="div"
                    className="rounded-lg"
                    {...props}
                  >
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                ) : (
                  <code className={className} {...props}>
                    {children}
                  </code>
                )
              },
            }}
          >
            {msg.content}
          </ReactMarkdown>
        </div>
        
        <div className="flex items-center justify-between mt-2 text-xs text-secondary-400">
          <span>
            {formatDistanceToNow(new Date(msg.created_at), { addSuffix: true })}
          </span>
          {msg.tokens_used > 0 && (
            <span>{msg.tokens_used} tokens</span>
          )}
        </div>
      </div>
    </motion.div>
  )

  return (
    <div className="flex flex-col h-full bg-secondary-50 dark:bg-secondary-900">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto">
          {messages.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center py-12"
            >
              <div className="w-16 h-16 bg-gradient-to-br from-primary-500 to-accent-500 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <span className="text-white text-xl font-bold">AI</span>
              </div>
              <h3 className="text-lg font-semibold text-secondary-900 dark:text-white mb-2">
                Start a conversation
              </h3>
              <p className="text-secondary-600 dark:text-secondary-300">
                Ask me anything about coding, and I'll help you write, debug, and improve your code.
              </p>
            </motion.div>
          ) : (
            <div className="space-y-4">
              {messages.map(renderMessage)}
              
              {/* Current streaming response */}
              {currentResponse && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex justify-start mb-4"
                >
                  <div className="max-w-[80%] message-assistant">
                    <div className="flex items-center space-x-2 mb-2">
                      <div className="w-6 h-6 bg-gradient-to-br from-primary-500 to-accent-500 rounded-full flex items-center justify-center">
                        <span className="text-white text-xs font-bold">AI</span>
                      </div>
                      <span className="text-xs text-secondary-500">Assistant</span>
                      <div className="flex space-x-1">
                        <div className="w-1 h-1 bg-primary-500 rounded-full animate-bounce" />
                        <div className="w-1 h-1 bg-primary-500 rounded-full animate-bounce animation-delay-100" />
                        <div className="w-1 h-1 bg-primary-500 rounded-full animate-bounce animation-delay-200" />
                      </div>
                    </div>
                    <div className="prose prose-sm max-w-none dark:prose-invert">
                      <ReactMarkdown>{currentResponse}</ReactMarkdown>
                    </div>
                  </div>
                </motion.div>
              )}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-secondary-200 dark:border-secondary-700 bg-white dark:bg-secondary-800 p-6">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-end space-x-4">
            <div className="flex-1">
              <div className="relative">
                <textarea
                  ref={textareaRef}
                  value={message}
                  onChange={handleTextareaChange}
                  onKeyDown={handleKeyDown}
                  placeholder={
                    isConnected
                      ? agentStatus === 'idle'
                        ? "Ask me anything about code..."
                        : "AI is thinking..."
                      : "Connecting..."
                  }
                  disabled={!isConnected || agentStatus !== 'idle'}
                  className="w-full resize-none rounded-xl border border-secondary-300 dark:border-secondary-600 bg-white dark:bg-secondary-700 px-4 py-3 pr-12 focus:border-primary-500 focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
                  rows={1}
                  style={{ minHeight: '48px' }}
                />
                
                <div className="absolute right-2 bottom-2 flex items-center space-x-1">
                  <button
                    type="button"
                    className="p-1.5 rounded-lg hover:bg-secondary-100 dark:hover:bg-secondary-600 transition-colors"
                    title="Attach file"
                  >
                    <PaperClipIcon className="w-4 h-4 text-secondary-400" />
                  </button>
                  
                  <button
                    type="button"
                    className="p-1.5 rounded-lg hover:bg-secondary-100 dark:hover:bg-secondary-600 transition-colors"
                    title="Add image"
                  >
                    <PhotoIcon className="w-4 h-4 text-secondary-400" />
                  </button>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                className="p-3 rounded-xl hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors"
                title="Voice input"
              >
                <MicrophoneIcon className="w-5 h-5 text-secondary-600 dark:text-secondary-400" />
              </button>
              
              <motion.button
                onClick={handleSend}
                disabled={!message.trim() || !isConnected || agentStatus !== 'idle'}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="p-3 bg-primary-600 text-white rounded-xl hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title="Send message"
              >
                <PaperAirplaneIcon className="w-5 h-5" />
              </motion.button>
            </div>
          </div>
          
          <div className="flex items-center justify-between mt-3 text-xs text-secondary-500">
            <div className="flex items-center space-x-4">
              <span>Press Enter to send, Shift+Enter for new line</span>
              {!isConnected && (
                <span className="flex items-center space-x-1 text-error-500">
                  <div className="w-2 h-2 bg-error-500 rounded-full" />
                  <span>Disconnected</span>
                </span>
              )}
            </div>
            
            {message.length > 0 && (
              <span>{message.length} characters</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
