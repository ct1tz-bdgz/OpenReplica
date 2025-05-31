import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FolderIcon,
  FolderOpenIcon,
  DocumentIcon,
  PlusIcon,
  TrashIcon,
  EllipsisHorizontalIcon,
} from '@heroicons/react/24/outline'
import { useQuery } from '@tanstack/react-query'
import { runtimeAPI } from '@/lib/api'

interface FileExplorerProps {
  sessionId?: string
}

interface FileNode {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileNode[]
  isExpanded?: boolean
}

export default function FileExplorer({ sessionId }: FileExplorerProps) {
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['/']))

  const { data: filesData, isLoading } = useQuery({
    queryKey: ['files', sessionId],
    queryFn: () => sessionId ? runtimeAPI.listFiles(sessionId) : Promise.resolve({ data: [] }),
    enabled: !!sessionId,
    refetchInterval: 5000, // Refresh every 5 seconds
  })

  const buildFileTree = (files: string[]): FileNode[] => {
    const tree: FileNode[] = []
    const pathMap = new Map<string, FileNode>()

    // Add root directory
    const root: FileNode = {
      name: 'workspace',
      path: '/',
      type: 'directory',
      children: [],
      isExpanded: true,
    }
    tree.push(root)
    pathMap.set('/', root)

    files.forEach((filePath) => {
      const parts = filePath.split('/').filter(Boolean)
      let currentPath = ''

      parts.forEach((part, index) => {
        const parentPath = currentPath || '/'
        currentPath = currentPath ? `${currentPath}/${part}` : part
        const isFile = index === parts.length - 1

        if (!pathMap.has(currentPath)) {
          const node: FileNode = {
            name: part,
            path: currentPath,
            type: isFile ? 'file' : 'directory',
            children: isFile ? undefined : [],
            isExpanded: false,
          }

          pathMap.set(currentPath, node)

          const parent = pathMap.get(parentPath)
          if (parent && parent.children) {
            parent.children.push(node)
          }
        }
      })
    })

    return tree
  }

  const toggleFolder = (path: string) => {
    const newExpanded = new Set(expandedFolders)
    if (newExpanded.has(path)) {
      newExpanded.delete(path)
    } else {
      newExpanded.add(path)
    }
    setExpandedFolders(newExpanded)
  }

  const renderFileNode = (node: FileNode, depth = 0) => {
    const isExpanded = expandedFolders.has(node.path)
    const isSelected = selectedFile === node.path

    return (
      <div key={node.path}>
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          className={`file-tree-item ${node.type} ${isSelected ? 'active' : ''}`}
          style={{ paddingLeft: `${depth * 12 + 8}px` }}
          onClick={() => {
            if (node.type === 'directory') {
              toggleFolder(node.path)
            } else {
              setSelectedFile(node.path)
            }
          }}
        >
          {node.type === 'directory' ? (
            isExpanded ? (
              <FolderOpenIcon className="w-4 h-4 text-primary-500" />
            ) : (
              <FolderIcon className="w-4 h-4 text-secondary-400" />
            )
          ) : (
            <DocumentIcon className="w-4 h-4 text-secondary-400" />
          )}
          
          <span className="flex-1 truncate">{node.name}</span>
          
          {node.type === 'file' && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                // Handle file actions
              }}
              className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-secondary-100 dark:hover:bg-secondary-600"
            >
              <EllipsisHorizontalIcon className="w-3 h-3" />
            </button>
          )}
        </motion.div>

        <AnimatePresence>
          {node.type === 'directory' && isExpanded && node.children && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              {node.children.map((child) => renderFileNode(child, depth + 1))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    )
  }

  const fileTree = filesData ? buildFileTree(filesData.data) : []

  return (
    <div className="h-full flex flex-col bg-white dark:bg-secondary-800">
      {/* Header */}
      <div className="p-4 border-b border-secondary-200 dark:border-secondary-700">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-secondary-900 dark:text-white">
            Explorer
          </h3>
          <div className="flex space-x-1">
            <button
              className="p-1 rounded hover:bg-secondary-100 dark:hover:bg-secondary-700"
              title="New file"
            >
              <PlusIcon className="w-4 h-4" />
            </button>
            <button
              className="p-1 rounded hover:bg-secondary-100 dark:hover:bg-secondary-700"
              title="Delete"
            >
              <TrashIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* File Tree */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="p-4 space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="animate-pulse flex items-center space-x-2">
                <div className="w-4 h-4 bg-secondary-200 dark:bg-secondary-600 rounded" />
                <div className="h-4 bg-secondary-200 dark:bg-secondary-600 rounded flex-1" />
              </div>
            ))}
          </div>
        ) : fileTree.length > 0 ? (
          <div className="py-2">
            {fileTree.map((node) => renderFileNode(node))}
          </div>
        ) : (
          <div className="p-4 text-center text-secondary-500">
            <FolderIcon className="w-8 h-8 mx-auto mb-2 text-secondary-300" />
            <p className="text-sm">No files yet</p>
            <p className="text-xs mt-1">Create or upload files to get started</p>
          </div>
        )}
      </div>
    </div>
  )
}
