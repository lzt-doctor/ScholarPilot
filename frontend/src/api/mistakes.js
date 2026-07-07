import request from './request'

export const createMistake = (data) => request.post('/mistakes', data)
export const listMistakes = () => request.get('/mistakes')
export const getMistakeStatistics = () => request.get('/mistakes/statistics')

