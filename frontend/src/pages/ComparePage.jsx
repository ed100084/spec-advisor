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
      <h2 className="mb-4 text-xl font-bold md:mb-6 md:text-2xl">版本差異比對</h2>

      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2">
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
        disabled={loading || !docA || !docB || docA === docB}
        className="mb-6 flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-white hover:bg-purple-700 disabled:opacity-50 sm:w-auto"
      >
        {loading ? <Loader2 size={16} className="animate-spin" /> : <GitCompare size={16} />}
        開始比對
      </button>

      {result && (
        <div className="rounded-xl bg-white p-4 shadow-sm md:p-6">
          <div className="mb-4 flex flex-col gap-1 break-words text-sm text-gray-500 sm:flex-row sm:gap-4">
            <span>A：{result.doc_a.filename}</span>
            <span className="hidden sm:inline">vs</span>
            <span>B：{result.doc_b.filename}</span>
          </div>
          <MarkdownView>{result.result}</MarkdownView>
        </div>
      )}
    </div>
  )
}
