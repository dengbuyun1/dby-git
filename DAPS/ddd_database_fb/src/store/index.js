import { defineStore } from 'pinia'

// 用户状态管理
export const useUserStore = defineStore('user', {
	state: () => ({
		userInfo: {
			id: null,
			username: '',
			email: '',
			role: ''
		},
		isLoggedIn: false
	}),

	actions: {
		// 登录
		login(userData) {
			this.userInfo = userData
			this.isLoggedIn = true
			localStorage.setItem('userToken', userData.token)
			localStorage.setItem('userInfo', JSON.stringify(userData))
		},

		// 登出
		logout() {
			this.userInfo = {
				id: null,
				username: '',
				email: '',
				role: ''
			}
			this.isLoggedIn = false
			localStorage.removeItem('userToken')
			localStorage.removeItem('userInfo')
		},

		// 从本地存储恢复用户信息
		restoreUserInfo() {
			const token = localStorage.getItem('userToken')
			const userInfo = localStorage.getItem('userInfo')

			if (token && userInfo) {
				this.userInfo = JSON.parse(userInfo)
				this.isLoggedIn = true
			}
		}
	}
})

// 患者数据状态管理
export const usePatientsStore = defineStore('patients', {
	state: () => ({
		currentPatient: null,
		patientsList: [],
		realTimeData: {
			bg: [],
			cgm: [],
			cho: [],
			cob: [],
			insulin: [],
			iob: [],
			timestamp: []
		},
		otherData: {
			ecg: null,
			nibp: null,
			spo2: null,
			pr: null,
			prsp: null,
			temp: null
		},
		simulationParams: {
			sensor: 'Dexcom',
			patientId: 'adult001',
			meals: [
				{ id: 1, startTime: '2025/09/15 00:00', carbs: 30 },
				// { id: 2, startTime: '2025/09/15 00:00', carbs: 30 }
			],
			generalSettings: {
				startTime: '2025/09/15 00:00',
				duration: 24,
				stepSize: 1,
				saveInterval: 5
			}
		}
	}),

	actions: {
		// 设置当前患者
		setCurrentPatient(patient) {
			this.currentPatient = patient
		},

		// 更新实时数据
		updateRealTimeData(data) {
			this.realTimeData = { ...this.realTimeData, ...data }
		},

		// 更新其他数据
		updateOtherData(data) {
			this.otherData = { ...this.otherData, ...data }
		},

		// 更新仿真参数
		updateSimulationParams(params) {
			this.simulationParams = { ...this.simulationParams, ...params }
		},

		// 获取患者列表
		setPatientsList(list) {
			this.patientsList = list
		}
	}
})