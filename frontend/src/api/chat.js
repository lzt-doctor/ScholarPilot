import request from './request'

export const sendQuestion = (data) => request.post('/chat', data)
export const getChatHistory = (params = {}) => request.get('/chat/history', { params })
export const getChatSessions = () => request.get('/chat/sessions')
export const deleteChatSession = (id) => request.delete(`/chat/sessions/${id}`)
