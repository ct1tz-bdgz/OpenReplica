import { Outlet } from 'react-router-dom'
import { motion } from 'framer-motion'
import Sidebar from './Sidebar'
import Header from './Header'
import { useAppStore } from '@/store/appStore'

export default function Layout() {
  const { sidebarOpen } = useAppStore()

  return (
    <div className="min-h-screen bg-secondary-50 dark:bg-secondary-900">
      <Header />
      
      <div className="flex">
        <Sidebar />
        
        <motion.main
          layout
          className={`flex-1 transition-all duration-300 ${
            sidebarOpen ? 'ml-64' : 'ml-16'
          }`}
        >
          <div className="p-6">
            <Outlet />
          </div>
        </motion.main>
      </div>
    </div>
  )
}
