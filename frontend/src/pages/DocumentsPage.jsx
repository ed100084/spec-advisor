import { useState, useEffect, useCallback } from 'react'
import { Upload, Trash2, FileText, FileSpreadsheet, File } from 'lucide-react'
import { uploadDocument, getDocuments, deleteDocument } from '../api'

const fileIcons = {
  pdf: FileText,
  docx: FileText,
  xlsx: FileSpreadsheet,
  xls: FileSpreadsheet,
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function DocumentsPage() {
  const [docs, setDocs] = useState([])
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)

  const loadDocs = useCallback(async () => {
    const { data } = await getDocuments()
    setDocs(data)
  }, [])

  useEffect(() => { loadDocs() }, [loadDocs])

  const handleUpload = async (files) => {
    setUploading(true)
    try {
      for (const file of files) {
        await uploadDocument(file)
      }
      await loadDocs()
    } catch (err) {
      alert(`上傳失敗: ${err.response?.data?.detail || err.message}`)
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (id, filename) => {
    if (!confirm(`確定要刪除「${filename}」？`)) return
    await deleteDocument(id)
    await loadDocs()
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    handleUpload(Array.from(e.dataTransfer.files))
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">文件管理</h2>

      {/* Upload Area */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-10 text-center transition-colors mb-6 ${
          dragOver ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
        }`}
      >
        <Upload className="mx-auto mb-3 text-gray-400" size={40} />
        <p className="text-gray-600 mb-2">
          {uploading ? '上傳中...' : '拖放檔案到此處，或點擊選擇檔案'}
        </p>
        <p className="text-xs text-gray-400 mb-4">支援 PDF、Word (.docx)、Excel (.xlsx/.xls)</p>
        <label className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg cursor-pointer hover:bg-blue-700 transition-colors">
          選擇檔案
          <input
            type="file"
            className="hidden"
            accept=".pdf,.docx,.xlsx,.xls"
            multiple
            onChange={(e) => handleUpload(Array.from(e.target.files))}
            disabled={uploading}
          />
        </label>
      </div>

      {/* Document List */}
      {docs.length === 0 ? (
        <p className="text-gray-400 text-center py-10">尚無上傳的文件</p>
      ) : (
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 text-left text-sm text-gray-500">
              <tr>
                <th className="px-4 py-3">檔案名稱</th>
                <th className="px-4 py-3">格式</th>
                <th className="px-4 py-3">大小</th>
                <th className="px-4 py-3">上傳時間</th>
                <th className="px-4 py-3 w-16"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {docs.map((doc) => {
                const Icon = fileIcons[doc.file_type] || File
                return (
                  <tr key={doc.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 flex items-center gap-2">
                      <Icon size={18} className="text-gray-400" />
                      {doc.filename}
                    </td>
                    <td className="px-4 py-3 text-sm uppercase text-gray-500">{doc.file_type}</td>
                    <td className="px-4 py-3 text-sm text-gray-500">{formatSize(doc.file_size)}</td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {new Date(doc.uploaded_at).toLocaleString('zh-TW')}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleDelete(doc.id, doc.filename)}
                        className="text-red-400 hover:text-red-600 transition-colors"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
