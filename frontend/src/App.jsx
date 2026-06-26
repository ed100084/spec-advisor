import { Routes, Route, NavLink } from 'react-router-dom'
import { FileText, Search, GitCompare, Users, BookTemplate } from 'lucide-react'
import DocumentsPage from './pages/DocumentsPage'
import AnalysisPage from './pages/AnalysisPage'
import ComparePage from './pages/ComparePage'
import ReviewsPage from './pages/ReviewsPage'
import TemplatesPage from './pages/TemplatesPage'

const navItems = [
  { to: '/', icon: FileText, label: '文件管理' },
  { to: '/analysis', icon: Search, label: 'AI 分析' },
  { to: '/compare', icon: GitCompare, label: '規格比對' },
  { to: '/reviews', icon: Users, label: '協作審閱' },
  { to: '/templates', icon: BookTemplate, label: '範本產生' },
]

export default function App() {
  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <nav className="w-56 bg-slate-800 text-white flex flex-col">
        <div className="p-4 border-b border-slate-700">
          <h1 className="text-lg font-bold">📋 Spec Advisor</h1>
          <p className="text-xs text-slate-400 mt-1">規格書檢視與建議系統</p>
          <p className="text-xs text-slate-500 mt-0.5">v{__APP_VERSION__}</p>
        </div>
        <div className="flex-1 py-2">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 text-sm transition-colors ${
                  isActive
                    ? 'bg-slate-700 text-white border-r-2 border-blue-400'
                    : 'text-slate-300 hover:bg-slate-700/50'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </div>
      </nav>

      {/* Main */}
      <main className="flex-1 p-6 overflow-auto">
        <Routes>
          <Route path="/" element={<DocumentsPage />} />
          <Route path="/analysis" element={<AnalysisPage />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/reviews" element={<ReviewsPage />} />
          <Route path="/templates" element={<TemplatesPage />} />
        </Routes>
      </main>
    </div>
  )
}
