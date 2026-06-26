import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// Documents
export const uploadDocument = (file, department = '', project = '', securityMeta = {}) => {
  const form = new FormData()
  form.append('file', file)
  form.append('department', department)
  form.append('project', project)
  form.append('is_information_system', securityMeta.isInformationSystem || false)
  form.append('security_responsibility_level', securityMeta.securityResponsibilityLevel || 'A')
  form.append('confidentiality_level', securityMeta.confidentialityLevel || '普')
  form.append('integrity_level', securityMeta.integrityLevel || '普')
  form.append('availability_level', securityMeta.availabilityLevel || '普')
  form.append('legal_compliance_level', securityMeta.legalComplianceLevel || '普')
  form.append('system_importance', securityMeta.systemImportance || '')
  form.append('processes_personal_data', securityMeta.processesPersonalData || false)
  form.append('personal_data_description', securityMeta.personalDataDescription || '')
  return api.post('/documents', form)
}
export const getDocuments = (params) => api.get('/documents', { params })
export const getDocumentFilters = () => api.get('/documents/filters')
export const getDocument = (id) => api.get(`/documents/${id}`)
export const deleteDocument = (id) => api.delete(`/documents/${id}`)

// Analysis
export const analyzeBinding = (docId, knowledgeIds) =>
  api.post(`/analysis/${docId}/binding`, { knowledge_ids: knowledgeIds })
export const analyzeReasonability = (docId, knowledgeIds) =>
  api.post(`/analysis/${docId}/reasonability`, { knowledge_ids: knowledgeIds })
export const analyzeFull = (docId, knowledgeIds) =>
  api.post(`/analysis/${docId}/full`, { knowledge_ids: knowledgeIds })
export const analyzeCost = (docId, knowledgeIds) =>
  api.post(`/analysis/${docId}/cost`, { knowledge_ids: knowledgeIds })
export const analyzeSecurity = (docId, knowledgeIds) =>
  api.post(`/analysis/${docId}/security`, { knowledge_ids: knowledgeIds })
export const analyzeImprovement = (docId, knowledgeIds) =>
  api.post(`/analysis/${docId}/improvement`, { knowledge_ids: knowledgeIds })
export const getAnalysisJob = (jobId) => api.get(`/analysis/jobs/${jobId}`)
export const getActiveJobs = () => api.get('/analysis/jobs')
export const compareDocuments = (docIdA, docIdB) =>
  api.post('/analysis/compare', { doc_id_a: docIdA, doc_id_b: docIdB })
export const getAnalysisHistory = (docId) => api.get(`/analysis/${docId}/history`)

// Reviews
export const createReview = (data) => api.post('/reviews', data)
export const getReviews = (docId) => api.get(`/reviews/document/${docId}`)
export const updateReviewStatus = (reviewId, status) =>
  api.patch(`/reviews/${reviewId}`, { status })

// Bid Notice
export const uploadBidTemplate = (form) => api.post('/bid/templates', form)
export const getBidTemplates = () => api.get('/bid/templates')
export const deleteBidTemplate = (id) => api.delete(`/bid/templates/${id}`)
export const generateBidNotice = (documentId, templateId) =>
  api.post('/bid/generate', { document_id: documentId, template_id: templateId })
export const getBidHistory = (documentId) =>
  api.get('/bid/history', { params: documentId ? { document_id: documentId } : {} })

// Knowledge Base
export const getKnowledgeList = () => api.get('/knowledge')
export const getKnowledgeCategories = () => api.get('/knowledge/categories')
export const getKnowledge = (id) => api.get(`/knowledge/${id}`)
export const createKnowledge = (data) => api.post('/knowledge', data)
export const uploadKnowledge = (form) => api.post('/knowledge/upload', form)
export const updateKnowledge = (id, data) => api.patch(`/knowledge/${id}`, data)
export const deleteKnowledge = (id) => api.delete(`/knowledge/${id}`)

// Control Measures
export const importControlBaseline = (form) => api.post('/controls/import', form)
export const getControlVersions = () => api.get('/controls/versions')
export const getControlMeasures = (params) => api.get('/controls/measures', { params })
export const updateControlMeasure = (id, data) => api.patch(`/controls/measures/${id}`, data)
export const deleteControlVersion = (id) => api.delete(`/controls/versions/${id}`)

// Templates
export const generateTemplate = (category, description) =>
  api.post('/templates/generate', { category, description })
export const saveTemplate = (data) => api.post('/templates', data)
export const getTemplates = () => api.get('/templates')
export const getTemplate = (id) => api.get(`/templates/${id}`)
