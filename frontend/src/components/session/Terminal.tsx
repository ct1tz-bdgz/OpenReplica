import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  CommandLineIcon,
  TrashIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'

interface TerminalProps {
  sessionId?: string
}

interface TerminalLine {
  id: string
  type: 'command' | 'output' | 'error'
  content: string
  timestamp: Date
}

export default function Terminal({ sessionId }: TerminalProps) {
  const [lines, setLines] = useState<TerminalLine[]>([
    {
      id: '1',
      type: 'output',
      content: 'Welcome to OpenReplica Terminal',
      timestamp: new Date(),
    },
    {
      id: '2',
      type: 'output',
      content: 'Type commands to interact with your workspace',
      timestamp: new Date(),
    },
  ])
  const [currentCommand, setCurrentCommand] = useState('')
  const [commandHistory, setCommandHistory] = useState<string[]>([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  
  const terminalRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight
    }
  }, [lines])

  const addLine = (type: TerminalLine['type'], content: string) => {
    const newLine: TerminalLine = {
      id: Date.now().toString(),
      type,
      content,
      timestamp: new Date(),
    }
    setLines((prev) => [...prev, newLine])
  }

  const executeCommand = async (command: string) => {
    if (!command.trim()) return

    // Add command to history
    setCommandHistory((prev) => [...prev, command])
    setHistoryIndex(-1)

    // Add command line
    addLine('command', `$ ${command}`)

    // Simulate command execution
    try {
      if (command === 'clear') {
        setLines([])
        return
      }

      if (command === 'help') {
        addLine('output', 'Available commands:')
        addLine('output', '  clear - Clear the terminal')
        addLine('output', '  help - Show this help message')
        addLine('output', '  ls - List files')
        addLine('output', '  pwd - Print working directory')
        return
      }

      if (command === 'pwd') {
        addLine('output', '/workspace')
        return
      }

      if (command === 'ls') {
        addLine('output', 'script.py  README.md  requirements.txt')
        return
      }

      // For other commands, simulate a response
      addLine('output', `Command '${command}' executed`)
      
    } catch (error) {
      addLine('error', `Error: ${error}`)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      executeCommand(currentCommand)
      setCurrentCommand('')
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (commandHistory.length > 0) {
        const newIndex = Math.min(historyIndex + 1, commandHistory.length - 1)
        setHistoryIndex(newIndex)
        setCurrentCommand(commandHistory[commandHistory.length - 1 - newIndex])
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1
        setHistoryIndex(newIndex)
        setCurrentCommand(commandHistory[commandHistory.length - 1 - newIndex])
      } else if (historyIndex === 0) {
        setHistoryIndex(-1)
        setCurrentCommand('')
      }
    }
  }

  const clearTerminal = () => {
    setLines([])
  }

  const getLineColor = (type: TerminalLine['type']) => {
    switch (type) {
      case 'command':
        return 'text-blue-400'
      case 'error':
        return 'text-red-400'
      case 'output':
      default:
        return 'text-green-400'
    }
  }

  return (
    <div className="h-full flex flex-col bg-secondary-900 text-green-400 font-mono">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-secondary-700 bg-secondary-800">
        <div className="flex items-center space-x-2">
          <CommandLineIcon className="w-4 h-4" />
          <span className="text-sm font-medium text-white">Terminal</span>
        </div>
        
        <div className="flex space-x-1">
          <button
            onClick={clearTerminal}
            className="p-1 rounded hover:bg-secondary-700 transition-colors"
            title="Clear terminal"
          >
            <TrashIcon className="w-4 h-4 text-secondary-400" />
          </button>
          
          <button
            className="p-1 rounded hover:bg-secondary-700 transition-colors"
            title="Restart terminal"
          >
            <ArrowPathIcon className="w-4 h-4 text-secondary-400" />
          </button>
        </div>
      </div>

      {/* Terminal Content */}
      <div
        ref={terminalRef}
        className="flex-1 overflow-y-auto p-4 space-y-1 text-sm"
      >
        {lines.map((line, index) => (
          <motion.div
            key={line.id}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.01 }}
            className={`${getLineColor(line.type)} font-mono whitespace-pre-wrap`}
          >
            {line.content}
          </motion.div>
        ))}

        {/* Current input line */}
        <div className="flex items-center space-x-2">
          <span className="text-blue-400">$</span>
          <input
            ref={inputRef}
            type="text"
            value={currentCommand}
            onChange={(e) => setCurrentCommand(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 bg-transparent border-none outline-none text-green-400 font-mono"
            placeholder="Type a command..."
            autoFocus
          />
          <div className="terminal-cursor" />
        </div>
      </div>

      {/* Status Bar */}
      <div className="px-4 py-2 border-t border-secondary-700 bg-secondary-800 text-xs">
        <div className="flex items-center justify-between text-secondary-400">
          <span>Ready</span>
          <span>{lines.length} lines</span>
        </div>
      </div>
    </div>
  )
}
