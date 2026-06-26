import { useState, useEffect } from 'react'
import { MessageSquare, Check, X, ChevronDown } from 'lucide-react'
import { getDocuments, getReviews, createReview, updateReviewStatus, getAnalysisHistory } from '../api'
import MarkdownView from '../components/MarkdownView'

const statusColors = {
  pending: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
}
const statusLabels = { pending: '待審', approved: '通過', rejected: '退回' }
const typeLabels = {
  binding_check: '綁標檢測',
  reasonability: '合理性分析',
  cost: '成本合理性',
  security: '資安合規',
  improvement: '改善建議',
  full: '完整分析',
}

export default function ReviewsPage() {
  const [docs, setDocs] = useState([])
  const [selectedDoc, setSelectedDoc] = useState('')
  const [reviews, setReviews] = useState([])
  const [analyses, setAnalyses] = useState([])
  const [selectedAnalysis, setSelectedAnalysis] = useState(null)
  const [name, setName] = useState('')
  const [comment, setComment] = useState('')

  useEffect(() => {
    getDocuments().then(({ data }) => setDocs(data))
  }, [])

  useEffect(() => {
    if (selectedDoc) {
      loadReviews()
      loadAnalyses()
    } else {
      setReviews([])
      setAnalyses([])
      setSelectedAnalysis(null)
    }
  }, [selectedDoc])

  const loadReviews = async () => {
    const { data } = await getReviews(selectedDoc)
    setReviews(data)
  }

  const loadAnalyses = async () => {
    const { data } = await getAnalysisHistory(selectedDoc)
    setAnalyses(data)
    if (data.length > 0) setSelectedAnalysis(data[0])
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!selectedDoc || !name || !comment) return
    await createReview({ document_id: selectedDoc, reviewer_name: name, comment })
    setComment('')
    await loadReviews()
  }

  const handleStatus = async (reviewId, status) => {
    await updateReviewStatus(reviewId, status)
    await loadReviews()
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">協作審閱</h2>

      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">選擇文件</label>
        <select value={selectedDoc} onChange={(e) => setSelectedDoc(e.target.value)} className="w-full max-w-md border rounded-lg px-3 py-2">
          <option value="">-- 請選擇 --</option>
          {docs.map((d) => (
            <option key={d.id} value={d.id}>
              {d.department ? `[${d.department}] ` : ''}{d.filename}
            </option>
          ))}
        </select>
      </div>

      {selectedDoc && (
        <div className="grid grid-cols-2 gap-6" style={{ minHeight: '70vh' }}>
          {/* Left: AI Analysis Results */}
          <div className="flex flex-col">
            <div className="bg-white rounded-xl shadow-sm flex flex-col flex-1 overflow-hidden">
              <div className="px-4 py-3 border-b bg-gray-50 flex items-center justify-between">
                <h3 className="font-semibold text-sm">AI 分析結果</h3>
                {analyses.length > 0 && (
                  <div className="relative">
                    <select
                      value={selectedAnalysis?.id || ''}
                      onChange={(e) => {
                        const a = analyses.find((x) => x.id === e.target.value)
                        setSelectedAnalysis(a)
                      }}
                      className="text-sm border rounded-lg px-2 py-1 pr-7 appearance-none bg-white"
                    >
                      {analyses.map((a) => (
                        <option key={a.id} value={a.id}>
                          {typeLabels[a.type] || a.type} — {new Date(a.created_at).toLocaleString('zh-TW')}
                        </option>
                      ))}
                    </select>
                    <ChevronDown size={14} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                  </div>
                )}
              </div>
              <div className="flex-1 overflow-auto p-4">
                {selectedAnalysis ? (
                  <MarkdownView>{selectedAnalysis.result?.analysis || ''}</MarkdownView>
                ) : (
                  <p className="text-gray-400 text-center py-10">
                    尚無分析結果，請先到「AI 分析」頁面進行分析
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Right: Reviews */}
          <div className="flex flex-col">
            {/* Add Review */}
            <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm p-4 mb-4">
              <h3 className="font-semibold text-sm mb-3">新增審閱意見</h3>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="審閱者姓名"
                className="w-full border rounded-lg px-3 py-2 mb-2 text-sm"
              />
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="參考左側分析結果，寫下您的審閱意見..."
                className="w-full border rounded-lg px-3 py-2 resize-none text-sm mb-2"
                rows={4}
              />
              <button type="submit" className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white rounded-lg py-2 hover:bg-blue-700 text-sm">
                <MessageSquare size={14} /> 送出意見
              </button>
            </form>

            {/* Review List */}
            <div className="flex-1 overflow-auto space-y-2">
              {reviews.map((r) => (
                <div key={r.id} className="bg-white rounded-xl shadow-sm p-3 flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm">{r.reviewer_name}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${statusColors[r.status]}`}>
                        {statusLabels[r.status]}
                      </span>
                      <span className="text-xs text-gray-400">{new Date(r.created_at).toLocaleString('zh-TW')}</span>
                    </div>
                    <p className="text-gray-600 text-sm whitespace-pre-wrap">{r.comment}</p>
                  </div>
                  {r.status === 'pending' && (
                    <div className="flex gap-1 ml-3 shrink-0">
                      <button onClick={() => handleStatus(r.id, 'approved')} className="text-green-600 hover:bg-green-50 p-1 rounded" title="通過">
                        <Check size={16} />
                      </button>
                      <button onClick={() => handleStatus(r.id, 'rejected')} className="text-red-600 hover:bg-red-50 p-1 rounded" title="退回">
                        <X size={16} />
                      </button>
                    </div>
                  )}
                </div>
              ))}
              {reviews.length === 0 && <p className="text-gray-400 text-center py-6 text-sm">尚無審閱意見</p>}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
