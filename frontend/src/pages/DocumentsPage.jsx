import { useState, useEffect, useCallback } from 'react'
import { Upload, Trash2, FileText, FileSpreadsheet, File, Filter } from 'lucide-react'
import { uploadDocument, getDocuments, deleteDocument, getDocumentFilters } from '../api'

const fileIcons = {
  pdf: FileText,
  docx: FileText,
  xlsx: FileSpreadsheet,
  xls: FileSpreadsheet,
}

const securityResponsibilityLevels = ['A', 'B', 'C', 'D', 'E']
const protectionLevels = ['普', '中', '高']
const protectionRank = { 普: 0, 中: 1, 高: 2 }

function deriveProtectionLevel(confidentiality, integrity, availability, legalCompliance) {
  return [confidentiality, integrity, availability, legalCompliance]
    .reduce((highest, current) => protectionRank[current] > protectionRank[highest] ? current : highest, '普')
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
  const [filters, setFilters] = useState({ departments: [], projects: [] })
  const [filterDept, setFilterDept] = useState('')
  const [filterProj, setFilterProj] = useState('')
  const [uploadDept, setUploadDept] = useState('')
  const [uploadProj, setUploadProj] = useState('')
  const [isInformationSystem, setIsInformationSystem] = useState(false)
  const [securityResponsibilityLevel, setSecurityResponsibilityLevel] = useState('A')
  const [confidentialityLevel, setConfidentialityLevel] = useState('普')
  const [integrityLevel, setIntegrityLevel] = useState('普')
  const [availabilityLevel, setAvailabilityLevel] = useState('普')
  const [legalComplianceLevel, setLegalComplianceLevel] = useState('普')
  const [systemImportance, setSystemImportance] = useState('')
  const [showUploadForm, setShowUploadForm] = useState(false)
  const [pendingFiles, setPendingFiles] = useState([])

  const loadDocs = useCallback(async () => {
    const params = {}
    if (filterDept) params.department = filterDept
    if (filterProj) params.project = filterProj
    const { data } = await getDocuments(params)
    setDocs(data)
  }, [filterDept, filterProj])

  const loadFilters = async () => {
    const { data } = await getDocumentFilters()
    setFilters(data)
  }

  useEffect(() => { loadDocs(); loadFilters() }, [loadDocs])

  const handleFilesSelected = (files) => {
    setPendingFiles(Array.from(files))
    setShowUploadForm(true)
  }

  const handleUploadConfirm = async () => {
    setUploading(true)
    try {
      for (const file of pendingFiles) {
        await uploadDocument(file, uploadDept, uploadProj, {
          isInformationSystem,
          securityResponsibilityLevel,
          confidentialityLevel,
          integrityLevel,
          availabilityLevel,
          legalComplianceLevel,
          systemImportance,
        })
      }
      setPendingFiles([])
      setShowUploadForm(false)
      await loadDocs()
      await loadFilters()
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
    await loadFilters()
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    handleFilesSelected(e.dataTransfer.files)
  }

  const derivedProtectionLevel = deriveProtectionLevel(
    confidentialityLevel,
    integrityLevel,
    availabilityLevel,
    legalComplianceLevel,
  )

  // Group docs by department > project
  const grouped = {}
  docs.forEach((doc) => {
    const dept = doc.department || '未分類'
    const proj = doc.project || '未指定專案'
    if (!grouped[dept]) grouped[dept] = {}
    if (!grouped[dept][proj]) grouped[dept][proj] = []
    grouped[dept][proj].push(doc)
  })

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">文件管理</h2>

      {/* Upload Area */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors mb-6 ${
          dragOver ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
        }`}
      >
        <Upload className="mx-auto mb-3 text-gray-400" size={36} />
        <p className="text-gray-600 mb-1">拖放檔案到此處，或點擊選擇檔案</p>
        <p className="text-xs text-gray-400 mb-3">支援 PDF、Word (.docx)、Excel (.xlsx/.xls)</p>
        <label className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg cursor-pointer hover:bg-blue-700">
          選擇檔案
          <input
            type="file"
            className="hidden"
            accept=".pdf,.docx,.xlsx,.xls"
            multiple
            onChange={(e) => handleFilesSelected(e.target.files)}
          />
        </label>
      </div>

      {/* Upload Form (department/project) */}
      {showUploadForm && (
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <h3 className="font-semibold mb-3">上傳 {pendingFiles.length} 個檔案</h3>
          <div className="text-sm text-gray-500 mb-4">
            {pendingFiles.map((f) => f.name).join('、')}
          </div>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">部門</label>
              <input
                list="dept-list"
                value={uploadDept}
                onChange={(e) => setUploadDept(e.target.value)}
                placeholder="輸入或選擇部門（如：資訊室）"
                className="w-full border rounded-lg px-3 py-2"
              />
              <datalist id="dept-list">
                {filters.departments.map((d) => <option key={d} value={d} />)}
              </datalist>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">專案</label>
              <input
                list="proj-list"
                value={uploadProj}
                onChange={(e) => setUploadProj(e.target.value)}
                placeholder="輸入或選擇專案（如：113年度HIS系統更新）"
                className="w-full border rounded-lg px-3 py-2"
              />
              <datalist id="proj-list">
                {filters.projects.map((p) => <option key={p} value={p} />)}
              </datalist>
            </div>
          </div>

          <div className="border rounded-xl p-4 mb-4 bg-slate-50">
            <h4 className="font-semibold text-sm mb-2">資通訊系統導入分級</h4>
            <label className="flex items-center gap-2 text-sm mb-3">
              <input
                type="checkbox"
                checked={isInformationSystem}
                onChange={(e) => setIsInformationSystem(e.target.checked)}
                className="rounded"
              />
              這份規格書是資通訊系統導入案，需要依資通系統防護需求分級與防護基準檢視
            </label>
            {!isInformationSystem ? (
              <p className="text-xs text-gray-500">
                若不是資通訊系統，可略過資安責任等級與防護需求分級；後續 AI 分析也不會套用資通系統防護基準。
              </p>
            ) : (
              <>
                <p className="text-xs text-gray-500 mb-4">
                  先確認組織資安責任等級，再依機密性、完整性、可用性、法律遵循性四構面取最高者，推導資通系統防護需求等級。
                </p>
                <div className="grid grid-cols-5 gap-3 mb-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">資安責任等級</label>
                <select
                  value={securityResponsibilityLevel}
                  onChange={(e) => setSecurityResponsibilityLevel(e.target.value)}
                  className="w-full border rounded-lg px-2 py-2 text-sm"
                >
                  {securityResponsibilityLevels.map((level) => <option key={level} value={level}>{level}</option>)}
                </select>
              </div>
              {[
                ['機密性', confidentialityLevel, setConfidentialityLevel],
                ['完整性', integrityLevel, setIntegrityLevel],
                ['可用性', availabilityLevel, setAvailabilityLevel],
                ['法律遵循性', legalComplianceLevel, setLegalComplianceLevel],
              ].map(([label, value, setter]) => (
                <div key={label}>
                  <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
                  <select
                    value={value}
                    onChange={(e) => setter(e.target.value)}
                    className="w-full border rounded-lg px-2 py-2 text-sm"
                  >
                    {protectionLevels.map((level) => <option key={level} value={level}>{level}</option>)}
                  </select>
                </div>
              ))}
              </div>
              <div className="grid grid-cols-3 gap-3 items-end">
              <div className="bg-white border rounded-lg px-3 py-2">
                <p className="text-xs text-gray-500">推導防護需求等級</p>
                <p className={`text-lg font-bold ${derivedProtectionLevel === '高' ? 'text-red-600' : derivedProtectionLevel === '中' ? 'text-amber-600' : 'text-green-600'}`}>
                  {derivedProtectionLevel}
                </p>
              </div>
              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-600 mb-1">系統重要性 / 判斷原因</label>
                <input
                  value={systemImportance}
                  onChange={(e) => setSystemImportance(e.target.value)}
                  placeholder="例如：此系統為核心醫療作業系統，可用性需達高等級"
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
                </div>
              </>
            )}
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleUploadConfirm}
              disabled={uploading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {uploading ? '上傳中...' : '確認上傳'}
            </button>
            <button
              onClick={() => { setShowUploadForm(false); setPendingFiles([]) }}
              className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300"
            >
              取消
            </button>
          </div>
        </div>
      )}

      {/* Filters */}
      {(filters.departments.length > 0 || filters.projects.length > 0) && (
        <div className="flex items-center gap-3 mb-4">
          <Filter size={16} className="text-gray-400" />
          <select
            value={filterDept}
            onChange={(e) => setFilterDept(e.target.value)}
            className="border rounded-lg px-3 py-1.5 text-sm"
          >
            <option value="">全部部門</option>
            {filters.departments.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
          <select
            value={filterProj}
            onChange={(e) => setFilterProj(e.target.value)}
            className="border rounded-lg px-3 py-1.5 text-sm"
          >
            <option value="">全部專案</option>
            {filters.projects.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          {(filterDept || filterProj) && (
            <button
              onClick={() => { setFilterDept(''); setFilterProj('') }}
              className="text-xs text-blue-600 hover:underline"
            >
              清除篩選
            </button>
          )}
        </div>
      )}

      {/* Document List grouped */}
      {docs.length === 0 ? (
        <p className="text-gray-400 text-center py-10">尚無上傳的文件</p>
      ) : (
        Object.entries(grouped).map(([dept, projects]) => (
          <div key={dept} className="mb-6">
            <h3 className="text-sm font-semibold text-gray-500 uppercase mb-2 flex items-center gap-2">
              🏢 {dept}
            </h3>
            {Object.entries(projects).map(([proj, projDocs]) => (
              <div key={proj} className="ml-4 mb-4">
                <h4 className="text-xs font-medium text-gray-400 mb-2">📁 {proj}</h4>
                <div className="bg-white rounded-xl shadow-sm overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-gray-50 text-left text-xs text-gray-500">
                      <tr>
                        <th className="px-4 py-2">檔案名稱</th>
                        <th className="px-4 py-2">格式</th>
                        <th className="px-4 py-2">資安分級</th>
                        <th className="px-4 py-2">大小</th>
                        <th className="px-4 py-2">上傳時間</th>
                        <th className="px-4 py-2 w-12"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y text-sm">
                      {projDocs.map((doc) => {
                        const Icon = fileIcons[doc.file_type] || File
                        return (
                          <tr key={doc.id} className="hover:bg-gray-50">
                            <td className="px-4 py-2 flex items-center gap-2">
                              <Icon size={16} className="text-gray-400" />
                              {doc.filename}
                            </td>
                            <td className="px-4 py-2 uppercase text-gray-500">{doc.file_type}</td>
                            <td className="px-4 py-2 text-gray-500">
                              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
                                {doc.is_information_system ? `責任${doc.security_responsibility_level || 'A'} / 防護${doc.protection_level || '普'}` : '非資通系統'}
                              </span>
                            </td>
                            <td className="px-4 py-2 text-gray-500">{formatSize(doc.file_size)}</td>
                            <td className="px-4 py-2 text-gray-500">
                              {new Date(doc.uploaded_at).toLocaleString('zh-TW')}
                            </td>
                            <td className="px-4 py-2">
                              <button
                                onClick={() => handleDelete(doc.id, doc.filename)}
                                className="text-red-400 hover:text-red-600"
                              >
                                <Trash2 size={14} />
                              </button>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        ))
      )}
    </div>
  )
}
