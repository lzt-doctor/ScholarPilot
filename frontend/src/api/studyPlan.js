import request from './request'

export const generateStudyPlan = (data) => request.post('/study-plan/generate', data)
export const listStudyPlans = () => request.get('/study-plan')

