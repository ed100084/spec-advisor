import { useState, useEffect } from 'react'
import { GitCompare, Loader2 } from 'lucide-react'
import MarkdownView from '../components/MarkdownView'
import { getDocuments, compareDocuments } from '../api'

export default function ComparePage() {
  const [docs, setDocs] = useState([])
  const [docA, setDocA] = useState('')
  const [docB, setDocB] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getDocuments().then(({ data }) => setDocs(data))
  }, [])

  const handleCompare = async () => {
    if (!docA || !docB) return alert('請選擇兩份文件')
    if (docA === docB) return alert('請選擇不同的文件')
    setLoading(true)
    setResult(null)
    try {
      const { data } = await compareDocuments(docA, docB)
      setResult(data)
    } catch (err) {
      alert(`比對失敗: ${err.response?.data?.detail || err.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">版本差異比對</h2>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">規格書 A</label>
          <select value={docA} onChange={(e) => setDocA(e.target.value)} className="w-full border rounded-lg px-3 py-2">
            <option value="">-- 請選擇 --</option>
            {docs.map((d) => <option key={d.id} value={d.id}>{d.filename}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">規格書 B</label>
          <select value={docB} onChange={(e) => setDocB(e.target.value)} className="w-full border rounded-lg px-3 py-2">
            <option value="">-- 請選擇 --</option>
            {docs.map((d) => <option key={d.id} value={d.id}>{d.filename}</option>)}
          </select>
        </div>
      </div>

      <button
        onClick={handleCompare}
        disabled={loading || !docA || !docB}
        className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 mb-6"
      >
        {loading ? <Loader2 size={16} className="animate-spin" /> : <GitCompare size={16} />}
        開始比對
      </button>

      {result && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex gap-4 mb-4 text-sm text-gray-500">
            <span>A: {result.doc_a.filename}</span>
            <span>vs</span>
            <span>B: {result.doc_b.filename}</span>
          </div>
          <MarkdownView>{result.result}</MarkdownView>
        </div>
      )}
    </div>
  )
}
