import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// Documents
export const uploadDocument = (file) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/documents', form)
}
export const getDocuments = () => api.get('/documents')
export const getDocument = (id) => api.get(`/documents/${id}`)
export const deleteDocument = (id) => api.delete(`/documents/${id}`)

// Analysis
export const analyzeBinding = (docId) => api.post(`/analysis/${docId}/binding`)
export const analyzeReasonability = (docId) => api.post(`/analysis/${docId}/reasonability`)
export const analyzeFull = (docId) => api.post(`/analysis/${docId}/full`)
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

// Templates
export const generateTemplate = (category, description) =>
  api.post('/templates/generate', { category, description })
export const saveTemplate = (data) => api.post('/templates', data)
export const getTemplates = () => api.get('/templates')
export const getTemplate = (id) => api.get(`/templates/${id}`)
