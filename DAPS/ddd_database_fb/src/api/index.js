import api from './request'

// 本地 mock 用户存储 key
const MOCK_USERS_KEY = 'mockUsers'

function getMockUsers() {
	try {
		const raw = localStorage.getItem(MOCK_USERS_KEY)
		if (!raw) return []
		return JSON.parse(raw)
	} catch (e) {
		return []
	}
}

function saveMockUsers(users) {
	try {
		localStorage.setItem(MOCK_USERS_KEY, JSON.stringify(users))
	} catch (e) {
		// ignore
	}
}

// 确保有一个默认账户，便于调试
function ensureDefaultUser() {
	const users = getMockUsers()
	if (!users.find(u => u.username === 'admin')) {
		users.push({
			id: 'local-admin',
			username: 'admin',
			email: 'admin@example.com',
			password: 'admin123',
			token: 'mock-token-admin'
		})
		saveMockUsers(users)
	}
}

ensureDefaultUser()

// 用户相关API
export const authAPI = {
	// 用户登录
	login: async (credentials) => {
		// 尝试调用后端 API，失败则使用本地模拟用户回退
		try {
			const res = await api.post('/auth/login', credentials)
			// request.js 的响应拦截器返回的是 response.data，
			// 为兼容现有代码（Login.vue 期待 response.data），返回 { data: res }
			return { data: res }
		} catch (err) {
			const users = getMockUsers()
			const found = users.find(u => u.username === credentials.username && u.password === credentials.password)
			if (found) {
				return { data: found }
			} else {
				return Promise.reject({ response: { data: { message: '用户名或密码不正确（本地模拟）' } } })
			}
		}
	},

	// 用户注册
	register: async (userData) => {
		try {
			const res = await api.post('/auth/register', userData)
			return { data: res }
		} catch (err) {
			const users = getMockUsers()
			if (users.find(u => u.username === userData.username)) {
				return Promise.reject({ response: { data: { message: '用户名已存在（本地模拟）' } } })
			}
			const newUser = {
				id: `local-${Date.now()}`,
				username: userData.username,
				email: userData.email || '',
				password: userData.password,
				token: `mock-token-${Date.now()}`
			}
			users.push(newUser)
			saveMockUsers(users)
			return { data: newUser }
		}
	}
}
// 患者相关API
export const patientsAPI = {
	// 获取所有患者列表
	getAllPatients: () => {
		return api.get('/patients')
	},

	// 获取真实患者列表
	getRealPatients: () => {
		return api.get('/patients/real')
	},

	// 获取虚拟患者列表
	getVirtualPatients: () => {
		return api.get('/patients/virtual')
	},

	// 根据ID获取患者信息
	getPatientById: (id) => {
		return api.get(`/patients/${id}`)
	},

	// 创建新患者（真实患者）
	createRealPatient: (patientData) => {
		return api.post('/patients/real', patientData)
	},

	// 创建新患者（虚拟患者）
	createVirtualPatient: (patientData) => {
		return api.post('/patients/virtual', patientData)
	},

	// 更新患者信息
	updatePatient: (id, patientData) => {
		return api.put(`/patients/${id}`, patientData)
	},

	// 删除患者
	deletePatient: (id) => {
		return api.delete(`/patients/${id}`)
	}
}

// 血糖数据相关API（实时数据接口）
export const glucoseDataAPI = {
	// 获取实时血糖数据 (BG, CGM, CHO, COB, INSULIN, IOB)
	getRealTimeData: (patientId) => {
		const pid = encodeURIComponent(patientId)
		return api.get(`/glucose-data/${pid}/realtime`)
	},

	// 获取历史血糖数据
	getHistoricalData: (patientId, startTime, endTime) => {
		const pid = encodeURIComponent(patientId)
		return api.get(`/glucose-data/${pid}/history`, {
			params: { startTime, endTime }
		})
	},

	// 提交血糖数据
	submitGlucoseData: (patientId, data) => {
		const pid = encodeURIComponent(patientId)
		return api.post(`/glucose-data/${pid}`, data)
	}
}

// 其他生理数据API（外接接口 - ECG/NIBP/SPO2/PR/PRSP/TEMP）
export const otherDataAPI = {
	// 获取其他生理数据
	getOtherData: (patientId) => {
		const pid = encodeURIComponent(patientId)
		return api.get(`/other-data/${pid}`)
	},

	// 更新其他生理数据
	updateOtherData: (patientId, data) => {
		const pid = encodeURIComponent(patientId)
		return api.post(`/other-data/${pid}`, data)
	}
}

// 仿真相关API
export const simulationAPI = {
	// 启动仿真
	startSimulation: (patientId, params) => {
		const pid = encodeURIComponent(patientId)
		return api.post(`/simulation/${pid}/start`, params)
	},

	// 停止仿真
	stopSimulation: (patientId) => {
		const pid = encodeURIComponent(patientId)
		return api.post(`/simulation/${pid}/stop`)
	},

	// 获取仿真状态
	getSimulationStatus: (patientId) => {
		const pid = encodeURIComponent(patientId)
		return api.get(`/simulation/${pid}/status`)
	},

	// 保存仿真参数
	saveSimulationParams: (patientId, params) => {
		const pid = encodeURIComponent(patientId)
		return api.post(`/simulation/${pid}/params`, params)
	},

	// 获取仿真参数
	getSimulationParams: (patientId) => {
		const pid = encodeURIComponent(patientId)
		return api.get(`/simulation/${pid}/params`)
	}
}

// 系统健康检查/连通性
export const systemAPI = {
	health: () => api.get('/health')
}