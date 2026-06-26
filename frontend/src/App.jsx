import { Routes, Route, NavLink } from 'react-router-dom'
import { FileText, Search, GitCompare, Users, BookTemplate, BookOpen, FileCheck, Database } from 'lucide-react'
import DocumentsPage from './pages/DocumentsPage'
import AnalysisPage from './pages/AnalysisPage'
import ComparePage from './pages/ComparePage'
import ReviewsPage from './pages/ReviewsPage'
import TemplatesPage from './pages/TemplatesPage'
import KnowledgePage from './pages/KnowledgePage'
import BidNoticePage from './pages/BidNoticePage'
import ControlsPage from './pages/ControlsPage'

const navItems = [
  { to: '/', icon: FileText, label: '文件管理' },
  { to: '/analysis', icon: Search, label: 'AI 分析' },
  { to: '/compare', icon: GitCompare, label: '版本差異比對' },
  { to: '/bid', icon: FileCheck, label: '投標須知' },
  { to: '/reviews', icon: Users, label: '協作審閱' },
  { to: '/templates', icon: BookTemplate, label: '範本產生' },
  { to: '/knowledge', icon: BookOpen, label: '知識庫' },
  { to: '/controls', icon: Database, label: '控制措施' },
]

export default function App() {
  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      {/* Sidebar */}
      <nav className="bg-slate-800 text-white flex flex-col md:w-56 md:min-h-screen">
        <div className="p-4 border-b border-slate-700">
          <h1 className="text-lg font-bold">📋 Spec Advisor</h1>
          <p className="text-xs text-slate-400 mt-1">規格書檢視與建議系統</p>
          <p className="text-xs text-slate-500 mt-0.5">v{__APP_VERSION__}</p>
        </div>
        <div className="flex gap-1 overflow-x-auto px-2 py-2 md:block md:flex-1 md:px-0">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors md:gap-3 md:rounded-none md:px-4 md:py-3 ${
                  isActive
                    ? 'bg-slate-700 text-white md:border-r-2 md:border-blue-400'
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
      <main className="min-w-0 flex-1 overflow-auto p-4 md:p-6">
        <Routes>
          <Route path="/" element={<DocumentsPage />} />
          <Route path="/analysis" element={<AnalysisPage />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/reviews" element={<ReviewsPage />} />
          <Route path="/templates" element={<TemplatesPage />} />
          <Route path="/bid" element={<BidNoticePage />} />
          <Route path="/knowledge" element={<KnowledgePage />} />
          <Route path="/controls" element={<ControlsPage />} />
        </Routes>
      </main>
    </div>
  )
}
