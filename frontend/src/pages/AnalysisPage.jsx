import { useState, useEffect } from 'react'
import { Search, Shield, CheckCircle, Loader2 } from 'lucide-react'
import MarkdownView from '../components/MarkdownView'
import { getDocuments, analyzeBinding, analyzeReasonability, analyzeFull, getAnalysisHistory } from '../api'

const analysisTypes = [
  { key: 'binding', label: '綁標檢測', icon: Shield, fn: analyzeBinding, color: 'red' },
  { key: 'reasonability', label: '合理性分析', icon: CheckCircle, fn: analyzeReasonability, color: 'yellow' },
  { key: 'full', label: '完整分析', icon: Search, fn: analyzeFull, color: 'blue' },
]

export default function AnalysisPage() {
  const [docs, setDocs] = useState([])
  const [selectedDoc, setSelectedDoc] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState([])

  useEffect(() => {
    getDocuments().then(({ data }) => setDocs(data))
  }, [])

  useEffect(() => {
    if (selectedDoc) {
      getAnalysisHistory(selectedDoc).then(({ data }) => setHistory(data))
    }
  }, [selectedDoc, result])

  const runAnalysis = async (type) => {
    if (!selectedDoc) return alert('請先選擇文件')
    setLoading(true)
    setResult(null)
    try {
      const { data } = await type.fn(selectedDoc)
      setResult({ type: type.label, content: data.result })
    } catch (err) {
      alert(`分析失敗: ${err.response?.data?.detail || err.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">AI 分析</h2>

      {/* Document Selector */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">選擇文件</label>
        <select
          value={selectedDoc}
          onChange={(e) => setSelectedDoc(e.target.value)}
          className="w-full max-w-md border rounded-lg px-3 py-2"
        >
          <option value="">-- 請選擇 --</option>
          {docs.map((d) => (
            <option key={d.id} value={d.id}>{d.filename}</option>
          ))}
        </select>
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
