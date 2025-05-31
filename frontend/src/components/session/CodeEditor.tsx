import { useState, useRef } from 'react'
import { motion } from 'framer-motion'
import Editor from '@monaco-editor/react'
import {
  PlayIcon,
  DocumentArrowDownIcon,
  FolderOpenIcon,
  Cog6ToothIcon,
} from '@heroicons/react/24/outline'
import { useAppStore } from '@/store/appStore'
import { runtimeAPI } from '@/lib/api'
import toast from 'react-hot-toast'

interface CodeEditorProps {
  sessionId?: string
}

export default function CodeEditor({ sessionId }: CodeEditorProps) {
  const [code, setCode] = useState('# Welcome to OpenReplica Code Editor\n# Start writing your code here!\n\nprint("Hello, OpenReplica!")')
  const [language, setLanguage] = useState('python')
  const [isExecuting, setIsExecuting] = useState(false)
  const [output, setOutput] = useState('')

  const { theme, preferences } = useAppStore()
  const editorRef = useRef<any>(null)

  const handleEditorDidMount = (editor: any, monaco: any) => {
    editorRef.current = editor

    // Configure editor theme
    monaco.editor.defineTheme('openreplica-light', {
      base: 'vs',
      inherit: true,
      rules: [],
      colors: {
        'editor.background': '#ffffff',
        'editor.foreground': '#1e293b',
      },
    })

    monaco.editor.defineTheme('openreplica-dark', {
      base: 'vs-dark',
      inherit: true,
      rules: [],
      colors: {
        'editor.background': '#1e293b',
        'editor.foreground': '#f1f5f9',
      },
    })

    monaco.editor.setTheme(theme === 'dark' ? 'openreplica-dark' : 'openreplica-light')
  }

  const executeCode = async () => {
    if (!sessionId || !code.trim()) return

    setIsExecuting(true)
    try {
      const response = await runtimeAPI.executeCode(sessionId, {
        code: code.trim(),
        language,
      })

      setOutput(response.data.output)
      
      if (response.data.success) {
        toast.success('Code executed successfully')
      } else {
        toast.error('Code execution failed')
      }
    } catch (error) {
      console.error('Code execution error:', error)
      setOutput('Error: Failed to execute code')
      toast.error('Failed to execute code')
    } finally {
      setIsExecuting(false)
    }
  }

  const saveFile = async () => {
    if (!sessionId) return

    try {
      const filename = `script.${language === 'python' ? 'py' : language === 'javascript' ? 'js' : 'txt'}`
      await runtimeAPI.writeFile(sessionId, {
        filepath: filename,
        content: code,
      })
      toast.success(`File saved as ${filename}`)
    } catch (error) {
      console.error('Save error:', error)
      toast.error('Failed to save file')
    }
  }

  return (
    <div className="flex flex-col h-full bg-white dark:bg-secondary-900">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-secondary-200 dark:border-secondary-700 bg-secondary-50 dark:bg-secondary-800">
        <div className="flex items-center space-x-4">
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="text-sm border border-secondary-300 dark:border-secondary-600 rounded-lg px-3 py-1 bg-white dark:bg-secondary-700"
          >
            <option value="python">Python</option>
            <option value="javascript">JavaScript</option>
            <option value="typescript">TypeScript</option>
            <option value="bash">Bash</option>
            <option value="json">JSON</option>
            <option value="markdown">Markdown</option>
          </select>

          <div className="h-4 w-px bg-secondary-300 dark:bg-secondary-600" />

          <span className="text-sm text-secondary-600 dark:text-secondary-400">
            {code.split('\n').length} lines
          </span>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={saveFile}
            className="btn-ghost text-sm"
            title="Save file"
          >
            <DocumentArrowDownIcon className="w-4 h-4" />
            <span className="ml-1">Save</span>
          </button>

          <button
            className="btn-ghost text-sm"
            title="Open file"
          >
            <FolderOpenIcon className="w-4 h-4" />
            <span className="ml-1">Open</span>
          </button>

          <div className="h-4 w-px bg-secondary-300 dark:bg-secondary-600" />

          <motion.button
            onClick={executeCode}
            disabled={isExecuting || !sessionId}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="btn-primary text-sm"
            title="Run code"
          >
            <PlayIcon className="w-4 h-4" />
            <span className="ml-1">
              {isExecuting ? 'Running...' : 'Run'}
            </span>
          </motion.button>

          <button
            className="btn-ghost text-sm"
            title="Editor settings"
          >
            <Cog6ToothIcon className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Editor and Output */}
      <div className="flex-1 flex">
        {/* Code Editor */}
        <div className="flex-1">
          <Editor
            height="100%"
            language={language}
            value={code}
            onChange={(value) => setCode(value || '')}
            onMount={handleEditorDidMount}
            theme={theme === 'dark' ? 'openreplica-dark' : 'openreplica-light'}
            options={{
              fontSize: preferences.fontSize,
              tabSize: preferences.tabSize,
              lineNumbers: preferences.showLineNumbers ? 'on' : 'off',
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              automaticLayout: true,
              wordWrap: 'on',
              renderWhitespace: 'selection',
              bracketPairColorization: { enabled: true },
              padding: { top: 16, bottom: 16 },
            }}
          />
        </div>

        {/* Output Panel */}
        {output && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: '40%', opacity: 1 }}
            className="border-l border-secondary-200 dark:border-secondary-700 bg-secondary-50 dark:bg-secondary-800"
          >
            <div className="p-4 border-b border-secondary-200 dark:border-secondary-700">
              <h3 className="text-sm font-medium text-secondary-900 dark:text-white">
                Output
              </h3>
            </div>
            <div className="p-4">
              <pre className="text-sm font-mono text-secondary-700 dark:text-secondary-300 whitespace-pre-wrap">
                {output}
              </pre>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  )
}
