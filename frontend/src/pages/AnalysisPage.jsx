import { useState, useEffect } from 'react'
import { Search, Shield, CheckCircle, Loader2, BookOpen, DollarSign, ShieldCheck, FileEdit, KeyRound } from 'lucide-react'
import {
  getDocuments, analyzeBinding, analyzeReasonability, analyzeFull,
  analyzeCost, analyzeSecurity, analyzeIntellectualProperty, analyzeImprovement,
  getAnalysisHistory, getKnowledgeList, getAnalysisJob, getActiveJobs,
} from '../api'
import MarkdownView from '../components/MarkdownView'

const analysisTypes = [
  { key: 'binding', label: '綁標檢測', icon: Shield, fn: analyzeBinding, color: 'red' },
  { key: 'reasonability', label: '合理性分析', icon: CheckCircle, fn: analyzeReasonability, color: 'yellow' },
  { key: 'cost', label: '成本合理性', icon: DollarSign, fn: analyzeCost, color: 'green' },
  { key: 'security', label: '資安合規', icon: ShieldCheck, fn: analyzeSecurity, color: 'purple' },
  { key: 'intellectual_property', label: '智財授權檢視', icon: KeyRound, fn: analyzeIntellectualProperty, color: 'indigo' },
  { key: 'improvement', label: '改善建議', icon: FileEdit, fn: analyzeImprovement, color: 'teal' },
  { key: 'full', label: '完整分析', icon: Search, fn: analyzeFull, color: 'blue' },
]

const typeLabels = {
  binding_check: '綁標檢測',
  reasonability: '合理性分析',
  cost: '成本合理性',
  security: '資安合規',
  intellectual_property: '智財授權檢視',
  improvement: '改善建議',
  full: '完整分析',
}

const categoryLabels = {
  law: '政府法規',
  internal_rule: '院內規章',
  standard: '產業標準',
  custom: '自訂規則',
}

export default function AnalysisPage() {
  const [docs, setDocs] = useState([])
  const [selectedDoc, setSelectedDoc] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState([])
  const [knowledgeItems, setKnowledgeItems] = useState([])
  const [selectedKb, setSelectedKb] = useState({}) // { id: true/false }
  const [showKbPanel, setShowKbPanel] = useState(false)
  const [jobStatus, setJobStatus] = useState(null)
  const [activeJobs, setActiveJobs] = useState([])

  useEffect(() => {
    getDocuments().then(({ data }) => setDocs(data))
    getKnowledgeList().then(({ data }) => {
      setKnowledgeItems(data.filter((k) => k.enabled))
      // Default: all enabled selected
      const sel = {}
      data.filter((k) => k.enabled).forEach((k) => { sel[k.id] = true })
      setSelectedKb(sel)
    })
    // Load active jobs on page entry
    loadActiveJobs()
  }, [])

  const loadActiveJobs = async () => {
    try {
      const { data } = await getActiveJobs()
      setActiveJobs(data)
      // Resume polling for each active job
      data.forEach((job) => pollJob(job.job_id))
    } catch (e) { /* ignore */ }
  }

  const pollJob = (jobId) => {
    const poll = async () => {
      try {
        const { data: status } = await getAnalysisJob(jobId)
        setJobStatus(status)
        // Update activeJobs list
        setActiveJobs((prev) => {
          if (status.status === 'completed' || status.status === 'failed') {
            return prev.filter((j) => j.job_id !== jobId)
          }
          return prev.map((j) => j.job_id === jobId ? status : j)
        })
        if (status.status === 'completed') {
          setResult({
            type: status.type_label,
            content: status.result?.result || '',
          })
          setLoading(false)
          if (selectedDoc) {
            getAnalysisHistory(selectedDoc).then(({ data }) => setHistory(data))
          }
        } else if (status.status === 'failed') {
          alert(`分析失敗: ${status.error || '未知錯誤'}`)
          setLoading(false)
        } else {
          setTimeout(poll, 3000)
        }
      } catch (e) {
        setTimeout(poll, 5000)
      }
    }
    setTimeout(poll, 2000)
  }

  useEffect(() => {
    if (selectedDoc) {
      getAnalysisHistory(selectedDoc).then(({ data }) => setHistory(data))
    }
  }, [selectedDoc, result])

  const getSelectedKbIds = () => {
    const ids = Object.entries(selectedKb).filter(([, v]) => v).map(([k]) => k)
    return ids.length === 0 ? [] : ids
  }

  const runAnalysis = async (type) => {
    if (!selectedDoc) return alert('請先選擇文件')
    setLoading(true)
    setResult(null)
    setJobStatus(null)
    try {
      const kbIds = getSelectedKbIds()
      const { data: job } = await type.fn(selectedDoc, kbIds)
      setActiveJobs((prev) => [...prev, job])
      pollJob(job.job_id)
    } catch (err) {
      alert(`分析啟動失敗: ${err.response?.data?.detail || err.message}`)
      setLoading(false)
    }
  }

  const toggleKb = (id) => setSelectedKb((prev) => ({ ...prev, [id]: !prev[id] }))
  const selectAllKb = () => {
    const sel = {}
    knowledgeItems.forEach((k) => { sel[k.id] = true })
    setSelectedKb(sel)
  }
  const selectNoneKb = () => setSelectedKb({})

  // Group knowledge by category
  const kbGrouped = {}
  knowledgeItems.forEach((k) => {
    if (!kbGrouped[k.category]) kbGrouped[k.category] = []
    kbGrouped[k.category].push(k)
  })

  const selectedCount = Object.values(selectedKb).filter(Boolean).length

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">AI 分析</h2>

      {/* Document Selector */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">選擇文件</label>
        <select
          value={selectedDoc}
          onChange={(e) => setSelectedDoc(e.target.value)}
          className="w-full max-w-md border rounded-lg px-3 py-2"
        >
          <option value="">-- 請選擇 --</option>
          {docs.map((d) => (
            <option key={d.id} value={d.id}>
              {d.department ? `[${d.department}] ` : ''}{d.filename}
            </option>
          ))}
        </select>
      </div>

      {/* Knowledge Base Selector */}
      <div className="mb-6">
        <button
          onClick={() => setShowKbPanel(!showKbPanel)}
          className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-800"
        >
          <BookOpen size={16} />
          審查依據：已選 {selectedCount}/{knowledgeItems.length} 項知識庫
          <span className="text-xs text-gray-400">（點擊展開）</span>
        </button>

        {showKbPanel && (
          <div className="mt-2 bg-white rounded-xl shadow-sm p-4 border">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-gray-700">選擇分析時要引用的知識庫</span>
              <div className="flex gap-2 text-xs">
                <button onClick={selectAllKb} className="text-blue-600 hover:underline">全選</button>
                <button onClick={selectNoneKb} className="text-blue-600 hover:underline">全不選</button>
              </div>
            </div>
            {knowledgeItems.length === 0 ? (
              <p className="text-sm text-gray-400">尚無知識庫項目，請先到「知識庫」頁面新增</p>
            ) : (
              Object.entries(kbGrouped).map(([cat, items]) => (
                <div key={cat} className="mb-3">
                  <p className="text-xs font-semibold text-gray-500 mb-1">{categoryLabels[cat] || cat}</p>
                  <div className="flex flex-wrap gap-2">
                    {items.map((k) => (
                      <label
                        key={k.id}
                        className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border cursor-pointer transition-colors ${
                          selectedKb[k.id]
                            ? 'bg-blue-50 border-blue-300 text-blue-800'
                            : 'bg-gray-50 border-gray-200 text-gray-500'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={!!selectedKb[k.id]}
                          onChange={() => toggleKb(k.id)}
                          className="rounded"
                        />
                        {k.name}
                      </label>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Active Jobs */}
      {activeJobs.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6">
          <h3 className="text-sm font-semibold text-blue-800 mb-3 flex items-center gap-2">
            <Loader2 size={14} className="animate-spin" />
            進行中的分析任務（{activeJobs.length}）
          </h3>
          <div className="space-y-2">
            {activeJobs.map((job) => (
              <div key={job.job_id} className="flex items-center gap-3">
                <span className="text-sm font-medium text-gray-700 min-w-[100px]">
                  {job.type_label}
                </span>
                <div className="flex-1 bg-gray-200 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${job.progress}%` }}
                  />
                </div>
                <span className="text-xs text-gray-500 min-w-[80px]">
                  {job.status === 'pending' ? '排隊中' : job.message || '執行中'} {job.progress}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Analysis Buttons */}
      <div className="flex flex-wrap gap-3 mb-6">
        {analysisTypes.map((type) => {
          const Icon = type.icon
          return (
            <button
              key={type.key}
              onClick={() => runAnalysis(type)}
              disabled={loading || !selectedDoc}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-white transition-colors disabled:opacity-50 ${
                type.color === 'red' ? 'bg-red-600 hover:bg-red-700' :
                type.color === 'yellow' ? 'bg-amber-600 hover:bg-amber-700' :
                type.color === 'green' ? 'bg-emerald-600 hover:bg-emerald-700' :
                type.color === 'purple' ? 'bg-purple-600 hover:bg-purple-700' :
                type.color === 'indigo' ? 'bg-indigo-600 hover:bg-indigo-700' :
                type.color === 'teal' ? 'bg-teal-600 hover:bg-teal-700' :
                'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Icon size={16} />}
              {type.label}
            </button>
          )
        })}
      </div>

      {/* Progress */}
      {loading && jobStatus && (
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <div className="flex items-center gap-3 mb-3">
            <Loader2 size={18} className="animate-spin text-blue-600" />
            <span className="text-sm font-medium">{jobStatus.message || '分析中...'}</span>
            <span className="text-xs text-gray-400">{jobStatus.progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-500"
              style={{ width: `${jobStatus.progress}%` }}
            />
          </div>
          <p className="text-xs text-gray-400 mt-2">
            分析類型：{jobStatus.type_label} · 狀態：{jobStatus.status === 'running' ? '執行中' : jobStatus.status === 'pending' ? '排隊中' : jobStatus.status}
          </p>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <h3 className="text-lg font-semibold mb-4">{result.type} 結果</h3>
          <MarkdownView>{result.content}</MarkdownView>
        </div>
      )}

      {/* History */}
      {history.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-4">分析歷史</h3>
          <div className="space-y-3">
            {history.map((h) => (
              <div
                key={h.id}
                className="border rounded-lg p-3 cursor-pointer hover:bg-gray-50"
                onClick={() => setResult({ type: typeLabels[h.type] || h.type, content: h.result?.analysis || '' })}
              >
                <div className="flex justify-between text-sm">
                  <span className="font-medium">{typeLabels[h.type] || h.type}</span>
                  <span className="text-gray-400">{new Date(h.created_at).toLocaleString('zh-TW')}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
