import { lazy, Suspense, useEffect, useState } from 'react'
import { Routes, Route, NavLink } from 'react-router-dom'
import {
  FileText, Search, GitCompare, Users, BookTemplate, BookOpen,
  FileCheck, Database, Menu, X, Loader2,
} from 'lucide-react'

const DocumentsPage = lazy(() => import('./pages/DocumentsPage'))
const AnalysisPage = lazy(() => import('./pages/AnalysisPage'))
const ComparePage = lazy(() => import('./pages/ComparePage'))
const ReviewsPage = lazy(() => import('./pages/ReviewsPage'))
const TemplatesPage = lazy(() => import('./pages/TemplatesPage'))
const KnowledgePage = lazy(() => import('./pages/KnowledgePage'))
const BidNoticePage = lazy(() => import('./pages/BidNoticePage'))
const ControlsPage = lazy(() => import('./pages/ControlsPage'))

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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  useEffect(() => {
    if (!mobileMenuOpen) return undefined

    const previousOverflow = document.body.style.overflow
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') setMobileMenuOpen(false)
    }
    document.body.style.overflow = 'hidden'
    document.addEventListener('keydown', closeOnEscape)

    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [mobileMenuOpen])

  return (
    <div className="min-h-screen md:flex">
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-slate-700 bg-slate-800 px-4 text-white md:hidden">
        <div className="min-w-0">
          <h1 className="truncate text-base font-bold">📋 Spec Advisor</h1>
          <p className="text-[11px] text-slate-400">規格書檢視與建議系統</p>
        </div>
        <button
          type="button"
          onClick={() => setMobileMenuOpen(true)}
          className="tap-target inline-flex items-center justify-center rounded-lg text-slate-100 hover:bg-slate-700"
          aria-label="開啟主選單"
          aria-expanded={mobileMenuOpen}
          aria-controls="mobile-navigation"
        >
          <Menu size={22} />
        </button>
      </header>

      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-slate-950/55"
            onClick={() => setMobileMenuOpen(false)}
            aria-label="關閉主選單"
          />
          <nav
            id="mobile-navigation"
            className="absolute inset-y-0 right-0 flex w-[min(82vw,20rem)] flex-col bg-slate-800 text-white shadow-2xl"
            aria-label="手機版主選單"
          >
            <div className="flex items-center justify-between border-b border-slate-700 p-4">
              <div>
                <h2 className="font-bold">功能選單</h2>
                <p className="text-xs text-slate-400">v{__APP_VERSION__}</p>
              </div>
              <button
                type="button"
                onClick={() => setMobileMenuOpen(false)}
                className="tap-target inline-flex items-center justify-center rounded-lg hover:bg-slate-700"
                aria-label="關閉主選單"
              >
                <X size={22} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto py-2">
              {navItems.map(({ to, icon: Icon, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  onClick={() => setMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    `flex min-h-12 items-center gap-3 border-r-2 px-5 py-3 text-sm transition-colors ${
                      isActive
                        ? 'border-blue-400 bg-slate-700 text-white'
                        : 'border-transparent text-slate-300 hover:bg-slate-700/50'
                    }`
                  }
                >
                  <Icon size={19} />
                  {label}
                </NavLink>
              ))}
            </div>
          </nav>
        </div>
      )}

      {/* Desktop sidebar */}
      <nav className="hidden bg-slate-800 text-white md:sticky md:top-0 md:flex md:h-screen md:w-56 md:shrink-0 md:flex-col">
        <div className="p-4 border-b border-slate-700">
          <h1 className="text-lg font-bold">📋 Spec Advisor</h1>
          <p className="text-xs text-slate-400 mt-1">規格書檢視與建議系統</p>
          <p className="text-xs text-slate-500 mt-0.5">v{__APP_VERSION__}</p>
        </div>
        <div className="flex-1 overflow-y-auto py-2">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 border-r-2 px-4 py-3 text-sm transition-colors ${
                  isActive
                    ? 'border-blue-400 bg-slate-700 text-white'
                    : 'border-transparent text-slate-300 hover:bg-slate-700/50'
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
      <main className="min-w-0 flex-1 overflow-x-hidden p-4 pb-8 md:p-6">
        <Suspense
          fallback={(
            <div className="flex min-h-48 items-center justify-center gap-2 text-sm text-gray-500">
              <Loader2 className="animate-spin" size={18} />
              載入功能中…
            </div>
          )}
        >
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
        </Suspense>
      </main>
    </div>
  )
}
