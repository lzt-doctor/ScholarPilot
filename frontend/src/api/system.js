import request from './request'

export const getRuntimeStatus = () => request.get('/health/details')
