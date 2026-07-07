import request from './request'

export const listDocuments = () => request.get('/documents')
export const getDocument = (id) => request.get(`/documents/${id}`)
export const deleteDocument = (id) => request.delete(`/documents/${id}`)

export const uploadDocument = (file, category = '未分类', onProgress) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('category', category)
  return request.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress,
  })
}

