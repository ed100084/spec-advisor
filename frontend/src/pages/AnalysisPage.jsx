import { useState, useEffect } from 'react'
import { Search, Shield, CheckCircle, Loader2, BookOpen } from 'lucide-react'
import { getDocuments, analyzeBinding, analyzeReasonability, analyzeFull, getAnalysisHistory, getKnowledgeList } from '../api'
import MarkdownView from '../components/MarkdownView'

const analysisTypes = [
  { key: 'binding', label: '綁標檢測', icon: Shield, fn: analyzeBinding, color: 'red' },
  { key: 'reasonability', label: '合理性分析', icon: CheckCircle, fn: analyzeReasonability, color: 'yellow' },
  { key: 'full', label: '完整分析', icon: Search, fn: analyzeFull, color: 'blue' },
]

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

  useEffect(() => {
    getDocuments().then(({ data }) => setDocs(data))
    getKnowledgeList().then(({ data }) => {
      setKnowledgeItems(data.filter((k) => k.enabled))
      // Default: all enabled selected
      const sel = {}
      data.filter((k) => k.enabled).forEach((k) => { sel[k.id] = true })
      setSelectedKb(sel)
    })
  }, [])

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
    try {
      const kbIds = getSelectedKbIds()
      const { data } = await type.fn(selectedDoc, kbIds)
      setResult({ type: type.label, content: data.result })
    } catch (err) {
      alert(`分析失敗: ${err.response?.data?.detail || err.message}`)
    } finally {
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

      {/* Analysis Buttons */}
      <div className="flex gap-3 mb-6">
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
                'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Icon size={16} />}
              {type.label}
            </button>
          )
        })}
      </div>

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
                onClick={() => setResult({ type: h.type, content: h.result?.analysis || '' })}
              >
                <div className="flex justify-between text-sm">
                  <span className="font-medium">{h.type}</span>
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
