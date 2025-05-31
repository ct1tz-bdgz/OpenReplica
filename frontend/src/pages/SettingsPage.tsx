import { motion } from 'framer-motion'
import { useState } from 'react'
import {
  CpuChipIcon,
  PaintBrushIcon,
  CodeBracketIcon,
  KeyIcon,
  BellIcon,
} from '@heroicons/react/24/outline'
import { useAppStore } from '@/store/appStore'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import toast from 'react-hot-toast'

export default function SettingsPage() {
  const { theme, toggleTheme, preferences, updatePreferences } = useAppStore()
  const [activeTab, setActiveTab] = useState('ai')

  const handleSavePreferences = () => {
    toast.success('Settings saved successfully!')
  }

  const settingsSections = [
    {
      id: 'ai',
      name: 'AI Configuration',
      icon: CpuChipIcon,
      description: 'Configure your AI models and providers',
    },
    {
      id: 'appearance',
      name: 'Appearance',
      icon: PaintBrushIcon,
      description: 'Customize the look and feel',
    },
    {
      id: 'editor',
      name: 'Code Editor',
      icon: CodeBracketIcon,
      description: 'Editor preferences and shortcuts',
    },
    {
      id: 'api',
      name: 'API Keys',
      icon: KeyIcon,
      description: 'Manage your API keys',
    },
    {
      id: 'notifications',
      name: 'Notifications',
      icon: BellIcon,
      description: 'Notification preferences',
    },
  ]

  return (
    <div className="max-w-6xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-bold text-secondary-900 dark:text-white mb-2">
          Settings
        </h1>
        <p className="text-secondary-600 dark:text-secondary-300">
          Customize your OpenReplica experience
        </p>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Settings Navigation */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="lg:col-span-1"
        >
          <div className="card p-4">
            <nav className="space-y-2">
              {settingsSections.map((section) => (
                <button
                  key={section.id}
                  onClick={() => setActiveTab(section.id)}
                  className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-left transition-colors ${
                    activeTab === section.id
                      ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                      : 'hover:bg-secondary-50 dark:hover:bg-secondary-700'
                  }`}
                >
                  <section.icon className="w-5 h-5" />
                  <div>
                    <p className="font-medium text-sm">{section.name}</p>
                    <p className="text-xs text-secondary-500">{section.description}</p>
                  </div>
                </button>
              ))}
            </nav>
          </div>
        </motion.div>

        {/* Settings Content */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="lg:col-span-3"
        >
          <div className="card">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              {/* AI Configuration */}
              <TabsContent value="ai" className="space-y-6">
                <div>
                  <h2 className="text-xl font-semibold mb-4">AI Configuration</h2>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Default LLM Provider
                      </label>
                      <select
                        value={preferences.defaultLLMProvider}
                        onChange={(e) => updatePreferences({ defaultLLMProvider: e.target.value })}
                        className="input"
                      >
                        <option value="openai">OpenAI</option>
                        <option value="anthropic">Anthropic</option>
                        <option value="litellm">LiteLLM</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Default Model
                      </label>
                      <select
                        value={preferences.defaultLLMModel}
                        onChange={(e) => updatePreferences({ defaultLLMModel: e.target.value })}
                        className="input"
                      >
                        <option value="gpt-4">GPT-4</option>
                        <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                        <option value="claude-3-sonnet-20240229">Claude 3 Sonnet</option>
                        <option value="claude-3-haiku-20240307">Claude 3 Haiku</option>
                      </select>
                    </div>
                  </div>
                </div>
              </TabsContent>

              {/* Appearance */}
              <TabsContent value="appearance" className="space-y-6">
                <div>
                  <h2 className="text-xl font-semibold mb-4">Appearance</h2>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Theme
                      </label>
                      <div className="flex space-x-3">
                        <button
                          onClick={() => theme === 'dark' && toggleTheme()}
                          className={`px-4 py-2 rounded-lg border transition-colors ${
                            theme === 'light'
                              ? 'border-primary-500 bg-primary-50 text-primary-700'
                              : 'border-secondary-300 hover:bg-secondary-50'
                          }`}
                        >
                          Light
                        </button>
                        <button
                          onClick={() => theme === 'light' && toggleTheme()}
                          className={`px-4 py-2 rounded-lg border transition-colors ${
                            theme === 'dark'
                              ? 'border-primary-500 bg-primary-50 text-primary-700'
                              : 'border-secondary-300 hover:bg-secondary-50'
                          }`}
                        >
                          Dark
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </TabsContent>

              {/* Code Editor */}
              <TabsContent value="editor" className="space-y-6">
                <div>
                  <h2 className="text-xl font-semibold mb-4">Code Editor</h2>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          checked={preferences.showLineNumbers}
                          onChange={(e) => updatePreferences({ showLineNumbers: e.target.checked })}
                          className="rounded"
                        />
                        <span className="text-sm">Show line numbers</span>
                      </label>
                    </div>

                    <div>
                      <label className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          checked={preferences.autoSave}
                          onChange={(e) => updatePreferences({ autoSave: e.target.checked })}
                          className="rounded"
                        />
                        <span className="text-sm">Auto-save files</span>
                      </label>
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Font Size
                      </label>
                      <input
                        type="range"
                        min="10"
                        max="24"
                        value={preferences.fontSize}
                        onChange={(e) => updatePreferences({ fontSize: parseInt(e.target.value) })}
                        className="w-full"
                      />
                      <span className="text-sm text-secondary-500">{preferences.fontSize}px</span>
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Tab Size
                      </label>
                      <select
                        value={preferences.tabSize}
                        onChange={(e) => updatePreferences({ tabSize: parseInt(e.target.value) })}
                        className="input w-24"
                      >
                        <option value={2}>2</option>
                        <option value={4}>4</option>
                        <option value={8}>8</option>
                      </select>
                    </div>
                  </div>
                </div>
              </TabsContent>

              {/* API Keys */}
              <TabsContent value="api" className="space-y-6">
                <div>
                  <h2 className="text-xl font-semibold mb-4">API Keys</h2>
                  <p className="text-sm text-secondary-600 mb-4">
                    Configure your API keys for different LLM providers. Keys are stored securely.
                  </p>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-2">
                        OpenAI API Key
                      </label>
                      <input
                        type="password"
                        placeholder="sk-..."
                        className="input"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Anthropic API Key
                      </label>
                      <input
                        type="password"
                        placeholder="sk-ant-..."
                        className="input"
                      />
                    </div>
                  </div>
                </div>
              </TabsContent>

              {/* Notifications */}
              <TabsContent value="notifications" className="space-y-6">
                <div>
                  <h2 className="text-xl font-semibold mb-4">Notifications</h2>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="flex items-center space-x-2">
                        <input type="checkbox" defaultChecked className="rounded" />
                        <span className="text-sm">Code execution completion</span>
                      </label>
                    </div>

                    <div>
                      <label className="flex items-center space-x-2">
                        <input type="checkbox" defaultChecked className="rounded" />
                        <span className="text-sm">Agent responses</span>
                      </label>
                    </div>

                    <div>
                      <label className="flex items-center space-x-2">
                        <input type="checkbox" className="rounded" />
                        <span className="text-sm">File changes</span>
                      </label>
                    </div>
                  </div>
                </div>
              </TabsContent>
            </Tabs>

            {/* Save Button */}
            <div className="flex justify-end pt-6 border-t border-secondary-200 dark:border-secondary-700 mt-8">
              <button
                onClick={handleSavePreferences}
                className="btn-primary"
              >
                Save Changes
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
