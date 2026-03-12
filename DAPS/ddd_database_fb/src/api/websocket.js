// src/api/websocket.js
class WebSocketClient {
	constructor() {
		this.ws = null
		this.reconnectTimer = null
		this.messageHandlers = new Map()
		this.openHandlers = new Map()
		this.errorHandlers = new Map()
	}

	connect(url, patientId) {
		if (this.ws) {
			this.ws.close()
		}

		// 注意: patientId 含有 # 需要编码，否则浏览器会把 # 视为锚点截断
		const encodedId = encodeURIComponent(patientId)
		let finalUrl = url
		try {
			const u = new URL(url)
			// 对接 lll/pc_fb/2_PC/sin.py 的服务器（默认 4502）不需要拼接 patientId 路径
			// sin.py 可能运行在 4502 或 8765，这两种都不追加 patientId
			if (u.port !== '4502' && u.port !== '8765') {
				finalUrl = `${url}/${encodedId}`
			}
		} catch (e) {
			// 解析失败则保持兼容行为：拼接 patientId
			finalUrl = `${url}/${encodedId}`
		}
		this.ws = new WebSocket(finalUrl)

		this.ws.onopen = () => {
			console.log(`WebSocket 连接成功: ${patientId}`)
			this.clearReconnectTimer()
			// 触发所有注册的 onOpen 处理器
			this.openHandlers.forEach(handler => {
				try {
					handler({ url, patientId })
				} catch (e) {
					console.error('onOpen 处理器执行失败', e)
				}
			})
		}

		this.ws.onmessage = (event) => {
			try {
				// debug: log raw incoming text for first few messages
				try {
					if (!this._msgCount) this._msgCount = 0
					this._msgCount++
					if (this._msgCount <= 10) console.debug('[ws-client] raw:', event.data)
				} catch (e) { /* ignore */ }
				const data = JSON.parse(event.data)
				// 触发所有注册的处理器
				this.messageHandlers.forEach(handler => handler(data))
			} catch (error) {
				console.error('解析 WebSocket 数据失败:', error)
			}
		}

		this.ws.onerror = (error) => {
			console.error('WebSocket 错误:', error)
			this.errorHandlers.forEach(handler => {
				try { handler(error) } catch (e) { /* ignore */ }
			})
		}

		this.ws.onclose = () => {
			console.log('WebSocket 连接关闭，尝试重连...')
			this.reconnect(url, patientId)
		}
	}

	// 注册连接打开处理器
	onOpen(handlerId, callback) {
		this.openHandlers.set(handlerId, callback)
	}

	// 注销连接打开处理器
	offOpen(handlerId) {
		this.openHandlers.delete(handlerId)
	}

	// 注册错误处理器
	onError(handlerId, callback) {
		this.errorHandlers.set(handlerId, callback)
	}

	// 注销错误处理器
	offError(handlerId) {
		this.errorHandlers.delete(handlerId)
	}

	// 注册数据处理器
	onMessage(handlerId, callback) {
		this.messageHandlers.set(handlerId, callback)
	}

	// 移除数据处理器
	offMessage(handlerId) {
		this.messageHandlers.delete(handlerId)
	}

	// 发送消息
	send(data) {
		if (this.ws && this.ws.readyState === WebSocket.OPEN) {
			this.ws.send(JSON.stringify(data))
		}
	}

	// 自动重连
	reconnect(url, patientId) {
		this.clearReconnectTimer()
		this.reconnectTimer = setTimeout(() => {
			console.log('尝试重新连接 WebSocket...')
			this.connect(url, patientId)
		}, 3000)
	}

	clearReconnectTimer() {
		if (this.reconnectTimer) {
			clearTimeout(this.reconnectTimer)
			this.reconnectTimer = null
		}
	}

	disconnect() {
		this.clearReconnectTimer()
		if (this.ws) {
			this.ws.close()
			this.ws = null
		}
		this.messageHandlers.clear()
		this.openHandlers.clear()
		this.errorHandlers.clear()
	}
}

export default new WebSocketClient()

// Base数据专用WebSocket客户端
export class BaseDataWebSocket {
	constructor() {
		this.ws = null
		this.reconnectTimer = null
		this.isConnected = false
		this.messageCallback = null
		this.maxDataPoints = 100 // 最多保留100个数据点
		this.dataHistory = []
		this.statusCallback = null // 连接状态回调
		this.listeners = new Set() // 用于处理一次性请求的监听器
	}

	// 注册消息回调
	onMessage(callback) {
		this.messageCallback = callback
	}

	connect(onMessage, onStatus) {
		if (this.ws) {
			this.ws.close()
		}

		if (onMessage) this.messageCallback = onMessage
		if (onStatus) this.statusCallback = onStatus
		this.ws = new WebSocket('ws://localhost:8766')

		this.ws.onopen = () => {
			console.log('Base数据WebSocket连接成功')
			this.isConnected = true
			this.clearReconnectTimer()
			if (this.statusCallback) this.statusCallback('connected')
		}

		this.ws.onmessage = (event) => {
			try {
				const data = JSON.parse(event.data)

				// 添加到历史数据
				this.dataHistory.push(data)
				if (this.dataHistory.length > this.maxDataPoints) {
					this.dataHistory.shift() // 移除最旧的数据
				}

				// 调用主要回调函数
				if (this.messageCallback) {
					this.messageCallback(data, this.dataHistory)
				}

				// 调用所有注册的监听器
				this.listeners.forEach(listener => {
					try {
						listener(data)
					} catch (err) {
						console.error('监听器执行错误', err)
					}
				})

			} catch (e) {
				console.error('解析Base数据失败:', e)
			}
		}

		this.ws.onclose = () => {
			console.log('Base数据WebSocket连接关闭')
			this.isConnected = false
			if (this.statusCallback) this.statusCallback('disconnected')
			this.scheduleReconnect()
		}

		this.ws.onerror = (error) => {
			console.error('Base数据WebSocket错误:', error)
			this.isConnected = false
			if (this.statusCallback) this.statusCallback('connecting')
		}
	}

	disconnect() {
		if (this.ws) {
			this.ws.close()
			this.ws = null
		}
		this.isConnected = false
		this.clearReconnectTimer()
		this.dataHistory = []
	}

	// 安排重连
	scheduleReconnect() {
		if (!this.reconnectTimer) {
			this.reconnectTimer = setTimeout(() => {
				console.log('尝试重新连接Base数据WebSocket...')
				this.connect(this.messageCallback, this.statusCallback)
			}, 3000) // 3秒后重连，避免过于频繁
		}
	}

	clearReconnectTimer() {
		if (this.reconnectTimer) {
			clearTimeout(this.reconnectTimer)
			this.reconnectTimer = null
		}
	}

	getDataHistory() {
		return this.dataHistory
	}

	isWebSocketConnected() {
		return this.isConnected
	}

	// 发送消息到服务端
	send(data) {
		if (this.ws && this.ws.readyState === WebSocket.OPEN) {
			this.ws.send(JSON.stringify(data))
			console.log('发送消息到Base数据服务端', data)
		} else {
			console.error('WebSocket未连接，无法发送消息')
		}
	}

	// 获取所有仿真记录列表
	getSimulationsList() {
		return new Promise((resolve, reject) => {
			if (!this.isWebSocketConnected()) {
				reject(new Error('WebSocket未连接'))
				return
			}

			const listener = (data) => {
				if (data.status === 'simulations_list') {
					this.listeners.delete(listener)
					resolve(data.data)
				}
			}

			this.listeners.add(listener)
			this.send({ command: 'get_simulations_list' })

			setTimeout(() => {
				if (this.listeners.has(listener)) {
					this.listeners.delete(listener)
					reject(new Error('请求超时'))
				}
			}, 10000)
		})
	}

	// 获取指定仿真的数据
	getSimulationData(simulationId) {
		return new Promise((resolve, reject) => {
			if (!this.isWebSocketConnected()) {
				reject(new Error('WebSocket未连接'))
				return
			}

			const listener = (data) => {
				if (data.status === 'simulation_data' && data.simulation_id === simulationId) {
					this.listeners.delete(listener)
					resolve({ info: data.info, data: data.data })
				}
			}

			this.listeners.add(listener)
			this.send({ command: 'get_simulation_data', simulation_id: simulationId })

			setTimeout(() => {
				if (this.listeners.has(listener)) {
					this.listeners.delete(listener)
					reject(new Error('请求超时'))
				}
			}, 10000)
		})
	}

	// 删除指定仿真
	deleteSimulation(simulationId) {
		return new Promise((resolve, reject) => {
			if (!this.isWebSocketConnected()) {
				reject(new Error('WebSocket未连接'))
				return
			}

			const listener = (data) => {
				if (data.status === 'simulation_deleted' && data.simulation_id === simulationId) {
					this.listeners.delete(listener)
					resolve(data.simulation_id)
				}
			}

			this.listeners.add(listener)
			this.send({ command: 'delete_simulation', simulation_id: simulationId })

			setTimeout(() => {
				if (this.listeners.has(listener)) {
					this.listeners.delete(listener)
					reject(new Error('请求超时'))
				}
			}, 10000)
		})
	}

	// 删除真实患者
	deleteRealPatient(patientRecordId) {
		return new Promise((resolve, reject) => {
			if (!this.isWebSocketConnected()) {
				reject(new Error('WebSocket未连接'))
				return
			}

			const listener = (data) => {
				if (data.status === 'real_patient_deleted' && data.patient_record_id === patientRecordId) {
					this.listeners.delete(listener)
					resolve(data.patient_record_id)
				}
			}

			this.listeners.add(listener)
			this.send({ command: 'delete_real_patient', patient_record_id: patientRecordId })

			setTimeout(() => {
				if (this.listeners.has(listener)) {
					this.listeners.delete(listener)
					reject(new Error('请求超时'))
				}
			}, 10000)
		})
	}

	// 获取真实患者列表
	getRealPatientsList() {
		return new Promise((resolve, reject) => {
			if (!this.isWebSocketConnected()) {
				reject(new Error('WebSocket未连接'))
				return
			}

			const listener = (data) => {
				if (data.type === 'real_patients_list') {
					this.listeners.delete(listener)
					resolve(data.data)
				}
			}

			this.listeners.add(listener)
			this.send({ command: 'get_real_patients_list' })

			setTimeout(() => {
				if (this.listeners.has(listener)) {
					this.listeners.delete(listener)
					reject(new Error('请求超时'))
				}
			}, 10000)
		})
	}
}
