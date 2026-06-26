import { useState, useEffect } from 'react'
import { MessageSquare, Check, X } from 'lucide-react'
import { getDocuments, getReviews, createReview, updateReviewStatus } from '../api'

const statusColors = {
  pending: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
}
const statusLabels = { pending: '待審', approved: '通過', rejected: '退回' }

export default function ReviewsPage() {
  const [docs, setDocs] = useState([])
  const [selectedDoc, setSelectedDoc] = useState('')
  const [reviews, setReviews] = useState([])
  const [name, setName] = useState('')
  const [comment, setComment] = useState('')

  useEffect(() => {
    getDocuments().then(({ data }) => setDocs(data))
  }, [])

  useEffect(() => {
    if (selectedDoc) loadReviews()
  }, [selectedDoc])

  const loadReviews = async () => {
    const { data } = await getReviews(selectedDoc)
    setReviews(data)
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
          {docs.map((d) => <option key={d.id} value={d.id}>{d.filename}</option>)}
        </select>
      </div>

      {selectedDoc && (
        <>
          {/* Add Review */}
          <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm p-6 mb-6">
            <h3 className="font-semibold mb-4">新增審閱意見</h3>
            <div className="grid grid-cols-4 gap-4">
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="審閱者姓名"
                className="border rounded-lg px-3 py-2"
              />
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="審閱意見..."
                className="col-span-2 border rounded-lg px-3 py-2 resize-none"
                rows={2}
              />
              <button type="submit" className="bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                <MessageSquare size={16} className="inline mr-1" /> 送出
              </button>
            </div>
          </form>

          {/* Review List */}
          <div className="space-y-3">
            {reviews.map((r) => (
              <div key={r.id} className="bg-white rounded-xl shadow-sm p-4 flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium">{r.reviewer_name}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${statusColors[r.status]}`}>
                      {statusLabels[r.status]}
                    </span>
                    <span className="text-xs text-gray-400">{new Date(r.created_at).toLocaleString('zh-TW')}</span>
                  </div>
                  <p className="text-gray-600 text-sm">{r.comment}</p>
                </div>
                {r.status === 'pending' && (
                  <div className="flex gap-2 ml-4">
                    <button onClick={() => handleStatus(r.id, 'approved')} className="text-green-600 hover:bg-green-50 p-1 rounded">
                      <Check size={18} />
                    </button>
                    <button onClick={() => handleStatus(r.id, 'rejected')} className="text-red-600 hover:bg-red-50 p-1 rounded">
                      <X size={18} />
                    </button>
                  </div>
                )}
              </div>
            ))}
            {reviews.length === 0 && <p className="text-gray-400 text-center py-6">尚無審閱意見</p>}
          </div>
        </>
      )}
    </div>
  )
}
