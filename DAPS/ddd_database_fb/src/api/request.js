import axios from 'axios'

// 创建axios实例
const api = axios.create({
	// 默认指向 5000 端口的主后端（glucose_api_server）
	baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api',
	timeout: 10000
})

// 请求拦截器
api.interceptors.request.use(
	config => {
		const token = localStorage.getItem('userToken')
		if (token) {
			config.headers.Authorization = `Bearer ${token}`
		}
		return config
	},
	error => {
		return Promise.reject(error)
	}
)

// 响应拦截器
api.interceptors.response.use(
	response => {
		return response.data
	},
	error => {
		if (error.response?.status === 401) {
			localStorage.removeItem('userToken')
			window.location.href = '/login'
		}
		return Promise.reject(error)
	}
)

export default api