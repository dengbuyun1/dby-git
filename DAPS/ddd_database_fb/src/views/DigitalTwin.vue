<template>
	<div class="main-container">
		<Sidebar :currentRoute="'digital_twin'" @navigate="handleNavigate" />

		<div class="main-content">
			<Header />

			<div class="content">
				<!-- 统计卡片 -->
				<div class="stats-section">
					<div class="card stat-card">
						<div class="stat-icon adult-icon">
							<el-icon>
								<User />
							</el-icon>
						</div>
						<div class="stat-info">
							<span class="stat-label">Adults</span>
							<span class="stat-value">{{ stats.adult || 0 }}</span>
						</div>
					</div>
					<div class="card stat-card">
						<div class="stat-icon adolescent-icon">
							<el-icon>
								<UserFilled />
							</el-icon>
						</div>
						<div class="stat-info">
							<span class="stat-label">Adolescents</span>
							<span class="stat-value">{{ stats.adolescent || 0 }}</span>
						</div>
					</div>
					<div class="card stat-card">
						<div class="stat-icon child-icon">
							<el-icon>
								<Avatar />
							</el-icon>
						</div>
						<div class="stat-info">
							<span class="stat-label">Children</span>
							<span class="stat-value">{{ stats.child || 0 }}</span>
						</div>
					</div>
				</div>

				<div class="matching-container">
					<!-- 左侧：输入表单 (Adaptive Width) -->
					<div class="card input-card">
						<h3>真实患者画像 (Real Patient Profile)</h3>
						<el-form :model="form" label-position="top" class="match-form">
							<el-form-item label="Patient ID">
								<el-input v-model="form.patient_id" placeholder="e.g. P001" />
							</el-form-item>

							<el-row :gutter="20">
								<el-col :span="12">
									<el-form-item label="Age Group">
										<el-select v-model="form.age_group" placeholder="Select group">
											<el-option label="Adult (≥18)" value="adult" />
											<el-option label="Adolescent (13-17)" value="adolescent" />
											<el-option label="Child (<13)" value="child" />
										</el-select>
									</el-form-item>
								</el-col>
								<el-col :span="12">
									<el-form-item label="Weight (kg)">
										<el-input-number v-model="form.weight_kg" :min="1" :max="200"
											style="width: 100%" />
									</el-form-item>
								</el-col>
							</el-row>

							<el-form-item label="Basal Insulin (U/day)">
								<el-input-number v-model="form.basal_u_day" :min="0" :step="0.1" style="width: 100%" />
								<div class="form-tip">基础胰岛素总量 (可选)</div>
							</el-form-item>

							<el-form-item label="Total Daily Dose (U/day)">
								<el-input-number v-model="form.tdd_u_day" :min="0" :step="1" style="width: 100%" />
								<div class="form-tip">每日胰岛素总量 (可选，若无基础率则必填)</div>
							</el-form-item>

							<el-row :gutter="20">
								<el-col :span="12">
									<el-form-item label="Carb Ratio (g/U)">
										<el-input-number v-model="form.cr_g_u" :min="1" :step="1" style="width: 100%" />
										<div class="form-tip">碳水系数 (CR)</div>
									</el-form-item>
								</el-col>
								<el-col :span="12">
									<el-form-item label="Correction Factor (mg/dL/U)">
										<el-input-number v-model="form.cf_mg_dl_u" :min="1" :step="1"
											style="width: 100%" />
										<div class="form-tip">矫正系数 (CF)</div>
									</el-form-item>
								</el-col>
							</el-row>

							<el-button type="primary" class="match-btn" @click="startMatching" :loading="loading">
								开始匹配 (Start Matching)
							</el-button>
						</el-form>
					</div>

					<!-- 右侧列 -->
					<div class="right-column">
						<!-- 散点图卡片 -->
						<div class="card chart-card">
							<div class="card-header"
								style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
								<h3 style="margin: 0;">虚拟患者分布 (Virtual Patient Library)</h3>
								<div style="display: flex; gap: 10px;">
									<el-select v-model="currentView" placeholder="Select View" size="small"
										style="width: 180px" @change="updateChart">
										<el-option label="Weight vs Basal" value="weight_basal" />
										<el-option label="Weight vs TDI/kg" value="weight_tdi" />
										<el-option label="TDI/kg vs CR" value="tdi_cr" />
										<el-option label="TDI/kg vs CF" value="tdi_cf" />
										<el-option label="CR vs CF" value="cr_cf" />
									</el-select>
									<el-button size="small" @click="refreshData">刷新数据</el-button>
								</div>
							</div>
							<div ref="chartRef" class="chart-container"></div>

							<!-- Progress Bar -->
							<div v-if="isCreating" style="padding: 10px 20px;">
								<div style="margin-bottom: 5px; font-size: 12px; color: #666;">正在创建专属虚拟患者...</div>
								<el-progress :percentage="creatingProgress"
									:status="creatingProgress === 100 ? 'success' : ''" :stroke-width="15" striped
									striped-flow></el-progress>
							</div>
						</div>

						<!-- 匹配结果列表 -->
						<div class="results-area">
							<div v-if="!results && selectedPatients.length === 0" class="empty-state">
								<el-empty description="请输入参数并点击匹配，或点击图上点查看详情" />
							</div>

							<div v-else class="results-list">
								<!-- Selected Patients Section -->
								<div v-if="selectedPatients.length > 0" style="margin-bottom: 20px;">
									<h3 style="color: #E6A23C;">Selected Comparison ({{ selectedPatients.length }}/3)
									</h3>
									<div v-for="pid in selectedPatients" :key="pid" class="card candidate-card"
										style="border-left-color: #E6A23C; background-color: #fdf6ec;">
										<div class="candidate-header">
											<div class="candidate-id">{{ pid }}</div>
											<el-button type="text" icon="el-icon-close"
												@click="toggleSelection(pid)">Remove</el-button>
										</div>
										<!-- Simple details for selected -->
										<div class="candidate-details" v-if="libraryData.find(p => p.id === pid)">
											<div class="detail-row">
												<span class="label">Weight</span>
												<span class="value">{{libraryData.find(p => p.id === pid).weight}}
													kg</span>
											</div>
											<div class="detail-row">
												<span class="label">Basal</span>
												<span class="value">{{(libraryData.find(p => p.id === pid).basal_per_kg
													*
													libraryData.find(p => p.id === pid).weight).toFixed(1)}} U</span>
											</div>
											<div class="detail-row">
												<span class="label">TDI</span>
												<span class="value">{{libraryData.find(p => p.id === pid).tdi ?
													libraryData.find(p => p.id === pid).tdi.toFixed(1) : '-'}} U</span>
											</div>
										</div>
									</div>
								</div>

								<h3 v-if="results">Top-3 匹配候选 (Candidates)</h3>

								<div v-if="results" v-for="(candidate, index) in results.candidates" :key="index"
									class="card candidate-card" :class="{ 'best-match': index === 0 }">
									<div class="candidate-header">
										<div class="rank-badge">#{{ index + 1 }}</div>
										<div class="candidate-id">{{ candidate.base_vp_id }}</div>
										<div class="match-score">
											Score: <span class="score-val">{{ (candidate.score * 100).toFixed(1)
											}}%</span>
										</div>
									</div>

									<div class="candidate-details">
										<div class="detail-row">
											<span class="label">Distance:</span>
											<span class="value">{{ candidate.distance.toFixed(4) }}</span>
										</div>
										<div class="detail-row">
											<span class="label">Weight Diff:</span>
											<span class="value"
												:class="getDiffClass(candidate.details.real_weight, candidate.details.vp_weight)">
												{{ candidate.details.real_weight }} vs {{
													candidate.details.vp_weight.toFixed(1) }} kg
											</span>
										</div>
										<div class="detail-row">
											<span class="label">Basal Diff:</span>
											<span class="value"
												:class="getDiffClass(candidate.details.real_basal, candidate.details.vp_basal)">
												{{ (candidate.details.real_basal * 1).toFixed(3) }} vs {{
													candidate.details.vp_basal.toFixed(3) }}
											</span>
										</div>
									</div>

									<div class="candidate-actions">
										<el-button type="primary" size="small" @click="applyModel(candidate)">
											应用此模型 (Apply)
										</el-button>
										<el-button size="small" type="success" @click="calibrateModel(candidate)">
											AI 精准校准 (100%)
										</el-button>
										<el-button size="small" @click="toggleSelection(candidate.base_vp_id)">
											{{ selectedPatients.includes(candidate.base_vp_id) ? '取消对比' : '加入对比' }}
										</el-button>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Calibration Dialog -->
				<el-dialog v-model="showCalibration" title="AI High-Fidelity Calibration" width="30%" :close-on-click-modal="false">
					<div style="text-align: center; padding: 20px;">
						<div v-if="calibStatus === 'running'">
							<p>正在进行差分进化参数辨识...</p>
							<p style="font-size: 12px; color: #888;">优化物理参数: Vmx, kabs, EGPb</p>
							<el-icon class="is-loading" size="40" color="#409EFF"><Loading /></el-icon>
						</div>
						<div v-if="calibStatus === 'success'" style="color: #67C23A;">
							<el-icon size="40"><CircleCheckFilled /></el-icon>
							<h3>校准成功! (Calibration Success)</h3>
							<p>New Patient ID: <b>{{ calibResult.new_id }}</b></p>
							
							<!-- Metrics Section -->
							<div v-if="calibResult.metrics" style="display: flex; gap: 10px; justify-content: center; margin: 10px 0;">
								<el-tag type="success">RMSE: {{ calibResult.metrics.rmse.toFixed(2) }}</el-tag>
								<el-tag type="warning">MARD: {{ calibResult.metrics.mard.toFixed(2) }}%</el-tag>
								<el-tag>R²: {{ calibResult.metrics.correlation.toFixed(3) }}</el-tag>
							</div>

							<div style="text-align: left; background: #f0f9eb; padding: 10px; border-radius: 4px; font-size: 12px;">
								<div v-for="(val, key) in calibResult.params" :key="key">
									{{ key }}: {{ val.toFixed(4) }}
								</div>
							</div>
						</div>
						<div v-if="calibStatus === 'error'" style="color: #F56C6C;">
							<el-icon size="40"><CircleCloseFilled /></el-icon>
							<h3>失败 (Failed)</h3>
							<p>{{ calibError }}</p>
						</div>
					</div>
					<template #footer>
						<span class="dialog-footer">
							<el-button @click="showCalibration = false" :disabled="calibStatus === 'running'">Close</el-button>
							<el-button type="primary" @click="applyCalibrated" v-if="calibStatus === 'success'">
								Use This Model
							</el-button>
						</span>
					</template>
				</el-dialog>
			</div>
		</div>
	</div>
</template>

<script>
import Sidebar from '@/components/Sidebar.vue'
import Header from '@/components/Header.vue'
import { User, UserFilled, Avatar, Loading, CircleCheckFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'

export default {
	name: 'DigitalTwin',
	components: {
		Sidebar,
		Header,
		User,
		UserFilled,
		Avatar,
		Loading,
		CircleCheckFilled,
		CircleCloseFilled
	},
	data() {
		return {
			ws: null,
			stats: {},
			isCreating: false,
			creatingProgress: 0,
			form: {
				patient_id: '',
				age_group: 'adult',
				weight_kg: 70,
				basal_u_day: null,
				tdd_u_day: null,
				cr_g_u: null,
				cf_mg_dl_u: null
			},
			loading: false,
			results: null,
			chartInstance: null,
			libraryData: [],
			currentView: 'weight_basal',
			selectedPatients: [],
			
			// Calibration
			showCalibration: false,
			calibStatus: 'idle', // idle, running, success, error
			calibResult: null,
			calibError: ''
		}
	},
	mounted() {
		this.connectWebSocket()
		this.initChart()

		// Use ResizeObserver for robust chart resizing
		this.resizeObserver = new ResizeObserver(() => {
			if (this.chartInstance) {
				this.chartInstance.resize()
			}
		})
		if (this.$refs.chartRef) {
			this.resizeObserver.observe(this.$refs.chartRef)
		}
	},
	beforeUnmount() {
		if (this.ws) {
			this.ws.close()
		}
		if (this.chartInstance) {
			this.chartInstance.dispose()
		}
		if (this.resizeObserver) {
			this.resizeObserver.disconnect()
		}
	},
	methods: {
		handleNavigate(route) {
			// Sidebar handles navigation
		},
		refreshData() {
			if (this.ws && this.ws.readyState === WebSocket.OPEN) {
				this.ws.send(JSON.stringify({ command: 'get_vpatients_stats' }))
				this.ws.send(JSON.stringify({ command: 'get_vpatients_data' }))
				ElMessage.success('已发送刷新请求')
			} else {
				ElMessage.warning('WebSocket 未连接，正在重连...')
				this.connectWebSocket()
			}
		},
		connectWebSocket() {
			this.ws = new WebSocket('ws://localhost:8766')

			this.ws.onopen = () => {
				console.log('WS Connected')
				this.ws.send(JSON.stringify({ command: 'get_vpatients_stats' }))
				this.ws.send(JSON.stringify({ command: 'get_vpatients_data' }))
			}

			this.ws.onmessage = (event) => {
				const msg = JSON.parse(event.data)
				if (msg.type === 'vpatients_stats') {
					this.stats = msg.data
				} else if (msg.type === 'vpatients_data') {
					this.libraryData = msg.data
					this.updateChart()
				} else if (msg.type === 'match_result') {
					this.results = msg.data
					this.loading = false
					this.updateChart() // Update chart to show real patient
					ElMessage.success('匹配完成')
				} else if (msg.type === 'create_vpatient_result') {
					this.creatingProgress = 100
					setTimeout(() => {
						this.isCreating = false
					}, 1000)

					if (msg.data.error) {
						ElMessage.error('创建失败: ' + msg.data.error)
					} else {
						ElMessage.success('新虚拟患者已创建: ' + msg.data.new_id)
					}
				} else if (msg.type === 'calibration_result') {
					if (msg.data.status === 'success') {
						this.calibStatus = 'success'
						this.calibResult = msg.data
					} else {
						this.calibStatus = 'error'
						this.calibError = msg.data.message
					}
				}
			}

			this.ws.onerror = (err) => {
				console.error('WS Error', err)
				ElMessage.error('WebSocket 连接失败')
			}
		},
		calibrateModel(candidate) {
			if (!this.form.patient_id) {
				ElMessage.warning('请先输入 Real Patient ID (对应CSV文件名)')
				return
			}
			
			this.showCalibration = true
			this.calibStatus = 'running'
			this.calibResult = null
			
			this.ws.send(JSON.stringify({
				command: 'start_calibration',
				real_patient_id: this.form.patient_id,
				base_vp_id: candidate.base_vp_id
			}))
		},
		applyCalibrated() {
			this.showCalibration = false
			// Optionally refresh or select the new patient
			this.refreshData()
		},
		initChart() {

			const chartDom = this.$refs.chartRef
			if (chartDom) {
				this.chartInstance = echarts.init(chartDom)
				this.chartInstance.on('click', (params) => {
					if (params.componentType === 'series' && (params.seriesName === 'Virtual Patients' || params.seriesName === 'Candidates' || params.seriesName === 'Selected')) {
						// Use data[2] which is the ID in our data structure
						const id = params.data[2]
						if (id) this.toggleSelection(id)
					}
				})
				this.updateChart()
			}
		},
		toggleSelection(id) {
			const idx = this.selectedPatients.indexOf(id)
			if (idx > -1) {
				this.selectedPatients.splice(idx, 1)
			} else {
				if (this.selectedPatients.length >= 3) this.selectedPatients.shift()
				this.selectedPatients.push(id)
			}
			this.updateChart()
		},
		updateChart() {
			if (!this.chartInstance) return

			// Helper to get X, Y values based on currentView
			const getViewConfig = () => {
				switch (this.currentView) {
					case 'weight_basal':
						return {
							xName: 'Weight (kg)', yName: 'Basal Intensity (U/kg/day)',
							getX: d => d.weight, getY: d => d.basal_per_kg,
							getRealX: f => f.weight_kg,
							getRealY: f => f.basal_u_day ? f.basal_u_day / f.weight_kg : (f.tdd_u_day ? (f.tdd_u_day * 0.5) / f.weight_kg : null)
						}
					case 'weight_tdi':
						return {
							xName: 'Weight (kg)', yName: 'TDI (U/kg/day)',
							getX: d => d.weight, getY: d => d.tdi ? d.tdi / d.weight : 0,
							getRealX: f => f.weight_kg,
							getRealY: f => f.tdd_u_day ? f.tdd_u_day / f.weight_kg : null
						}
					case 'tdi_cr':
						return {
							xName: 'TDI (U/kg/day)', yName: 'CR (g/U)',
							getX: d => d.tdi ? d.tdi / d.weight : 0, getY: d => d.cr,
							getRealX: f => f.tdd_u_day ? f.tdd_u_day / f.weight_kg : null,
							getRealY: f => f.cr_g_u
						}
					case 'tdi_cf':
						return {
							xName: 'TDI (U/kg/day)', yName: 'CF (mg/dL/U)',
							getX: d => d.tdi ? d.tdi / d.weight : 0, getY: d => d.cf,
							getRealX: f => f.tdd_u_day ? f.tdd_u_day / f.weight_kg : null,
							getRealY: f => f.cf_mg_dl_u
						}
					case 'cr_cf':
						return {
							xName: 'CR (g/U)', yName: 'CF (mg/dL/U)',
							getX: d => d.cr, getY: d => d.cf,
							getRealX: f => f.cr_g_u,
							getRealY: f => f.cf_mg_dl_u
						}
					default:
						return {
							xName: 'Weight (kg)', yName: 'Basal Intensity (U/kg/day)',
							getX: d => d.weight, getY: d => d.basal_per_kg,
							getRealX: f => f.weight_kg,
							getRealY: f => f.basal_u_day ? f.basal_u_day / f.weight_kg : (f.tdd_u_day ? (f.tdd_u_day * 0.5) / f.weight_kg : null)
						}
				}
			}

			const config = getViewConfig()

			// Common Tooltip Formatter
			const tooltipFormatter = (params) => {
				const d = params.data
				// [x, y, id, age_group, weight, basal_per_kg, tdi, cr, cf, age]
				const id = d[2]
				const group = d[3]
				const weight = d[4]
				const basal_kg = d[5]
				const basal_total = weight * basal_kg
				const tdi_total = d[6]
				const tdi_kg = (tdi_total && weight) ? tdi_total / weight : 0
				const cr = d[7]
				const cf = d[8]
				const age = d[9]

				let scoreHtml = ''
				if (params.seriesName === 'Candidates' && this.results && this.results.candidates) {
					const cand = this.results.candidates.find(c => c.base_vp_id === id)
					if (cand) {
						scoreHtml = `<div style="color: #67C23A; font-weight: bold; margin-bottom: 4px;">Match Score: ${(cand.score * 100).toFixed(1)}%</div>`
					}
				}

				return `
					<div style="font-family: sans-serif; text-align: left; min-width: 200px;">
						<div style="border-bottom: 1px solid #eee; padding-bottom: 4px; margin-bottom: 4px; font-weight: bold; display: flex; justify-content: space-between;">
							<span>${id} <span style="font-weight: normal; color: #888; font-size: 12px;">(${group})</span></span>
						</div>
						${scoreHtml}
						<div style="display: grid; grid-template-columns: auto auto; gap: 4px 16px; font-size: 12px;">
							<span style="color: #666;">Age:</span> <span>${age || '-'}</span>
							<span style="color: #666;">Weight:</span> <span>${weight} kg</span>
							
							<span style="color: #666;">Basal:</span> 
							<span>${basal_total.toFixed(1)} U <span style="color:#888">(${basal_kg.toFixed(3)} U/kg/d)</span></span>
							
							<span style="color: #666;">TDI:</span> 
							<span>${tdi_total ? tdi_total.toFixed(1) : '-'} U <span style="color:#888">(${tdi_kg ? tdi_kg.toFixed(2) : '-'} U/kg/d)</span></span>
							
							<span style="color: #666;">CR:</span> <span>${cr ? cr.toFixed(1) : '-'}</span>
							<span style="color: #666;">CF:</span> <span>${cf ? cf.toFixed(1) : '-'}</span>
						</div>
						<div style="margin-top: 6px; font-size: 11px; color: #999; font-style: italic;">
							${this.selectedPatients.includes(id) ? 'Click to deselect' : 'Click to select/compare'}
						</div>
					</div>
				`
			}

			// 1. Library Series
			const librarySeries = {
				name: 'Virtual Patients',
				type: 'scatter',
				data: this.libraryData.filter(p => !this.selectedPatients.includes(p.id)).map(p => {
					const x = config.getX(p)
					const y = config.getY(p)
					// [x, y, id, age_group, weight, basal_per_kg, tdi, cr, cf, age]
					return [x, y, p.id, p.age_group, p.weight, p.basal_per_kg, p.tdi, p.cr, p.cf, p.age]
				}),
				symbolSize: (params) => {
					if (this.currentView === 'cr_cf') {
						return Math.max(5, params.data[4] / 5)
					}
					return 8
				},
				itemStyle: {
					color: (params) => {
						const group = params.data[3]
						if (group === 'adult') return '#409EFF'
						if (group === 'adolescent') return '#E6A23C'
						return '#67C23A'
					},
					opacity: 0.5
				},
				tooltip: {
					formatter: tooltipFormatter
				}
			}

			// 2. Real Patient Series
			const realX = config.getRealX(this.form)
			const realY = config.getRealY(this.form)
			let realData = []

			if (realX != null && realY != null && !isNaN(realX) && !isNaN(realY)) {
				realData = [[realX, realY]]
			}

			const realSeries = {
				name: 'Real Patient',
				type: 'scatter',
				data: realData,
				symbol: 'star',
				symbolSize: 24,
				itemStyle: {
					color: '#F56C6C',
					borderColor: '#fff',
					borderWidth: 2,
					shadowBlur: 10,
					shadowColor: 'rgba(245, 108, 108, 0.5)'
				},
				label: {
					show: true,
					formatter: 'Target',
					position: 'top',
					fontWeight: 'bold'
				},
				z: 10,
				tooltip: {
					formatter: () => {
						return `
								<div style="font-family: sans-serif; text-align: left;">
									<div style="border-bottom: 1px solid #eee; padding-bottom: 4px; margin-bottom: 4px; font-weight: bold; color: #F56C6C;">
										Real Patient Target
									</div>
									<div style="font-size: 12px;">
										<div>${config.xName}: ${realX ? realX.toFixed(2) : '-'}</div>
										<div>${config.yName}: ${realY ? realY.toFixed(3) : '-'}</div>
									</div>
								</div>
							`
					}
				}
			}

			// 3. Candidates Series (Highlight)
			let candData = []
			if (this.results && this.results.candidates) {
				candData = this.results.candidates.map(c => {
					const original = this.libraryData.find(p => p.id === c.base_vp_id)
					if (original) {
						const x = config.getX(original)
						const y = config.getY(original)
						return [x, y, c.base_vp_id, original.age_group, original.weight, original.basal_per_kg, original.tdi, original.cr, original.cf, original.age]
					}
					return null
				}).filter(Boolean)
			}

			const candidateSeries = {
				name: 'Candidates',
				type: 'effectScatter',
				data: candData,
				symbolSize: 16,
				itemStyle: {
					color: '#67C23A',
					shadowBlur: 10,
					shadowColor: 'rgba(103, 194, 58, 0.5)'
				},
				rippleEffect: {
					brushType: 'stroke',
					scale: 3
				},
				z: 5,
				tooltip: {
					formatter: tooltipFormatter
				}
			}

			// 4. Selected Series
			let selData = []
			if (this.selectedPatients.length > 0) {
				selData = this.libraryData.filter(p => this.selectedPatients.includes(p.id)).map(p => {
					const x = config.getX(p)
					const y = config.getY(p)
					return [x, y, p.id, p.age_group, p.weight, p.basal_per_kg, p.tdi, p.cr, p.cf, p.age]
				})
			}

			const selectedSeries = {
				name: 'Selected',
				type: 'scatter',
				data: selData,
				symbolSize: 18,
				itemStyle: {
					color: '#E6A23C',
					borderColor: '#fff',
					borderWidth: 3,
					shadowBlur: 10,
					shadowColor: 'rgba(230, 162, 60, 0.5)'
				},
				z: 20,
				tooltip: {
					formatter: tooltipFormatter
				}
			}

			const option = {
				title: {
					text: `${config.xName} vs ${config.yName}`,
					left: 'center',
					textStyle: { fontSize: 14, color: '#666' }
				},
				tooltip: {
					trigger: 'item',
					backgroundColor: 'rgba(255, 255, 255, 0.95)',
					borderColor: '#eee',
					borderWidth: 1,
					textStyle: {
						color: '#333'
					},
					extraCssText: 'box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);'
				},
				legend: {
					bottom: 10,
					data: ['Virtual Patients', 'Real Patient', 'Candidates', 'Selected']
				},
				grid: {
					left: '3%',
					right: '4%',
					bottom: '15%',
					containLabel: true
				},
				xAxis: {
					type: 'value',
					name: config.xName,
					nameLocation: 'middle',
					nameGap: 25,
					scale: true
				},
				yAxis: {
					type: 'value',
					name: config.yName,
					scale: true
				},
				series: [
					librarySeries,
					realSeries,
					candidateSeries,
					selectedSeries
				]
			}

			this.chartInstance.setOption(option)
		},
		startMatching() {
			if (!this.form.weight_kg) {
				ElMessage.warning('请输入体重')
				return
			}
			this.loading = true
			this.results = null

			this.ws.send(JSON.stringify({
				command: 'match_vpatient',
				params: this.form
			}))
		},
		getDiffClass(val1, val2) {
			const diff = Math.abs(val1 - val2) / val1
			if (diff < 0.1) return 'text-success'
			if (diff < 0.3) return 'text-warning'
			return 'text-danger'
		},
		applyModel(candidate) {
			this.creatingProgress = 0
			this.isCreating = true

			// 模拟进度条动画
			const timer = setInterval(() => {
				if (this.creatingProgress < 90) {
					this.creatingProgress += 10
				} else {
					clearInterval(timer)
				}
			}, 200)

			this.ws.send(JSON.stringify({
				command: 'create_vpatient',
				real_profile: this.form,
				base_vp_id: candidate.base_vp_id
			}))
		}
	}
}
</script>

<style scoped>
.main-container {
	display: flex;
	height: 100vh;
	background-color: #f5f7fa;
}

.main-content {
	flex: 1;
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.content {
	flex: 1;
	padding: 10px;
	overflow-y: auto;
}

.page-header {
	margin-bottom: 10px;
}

.page-header h2 {
	margin: 0;
	color: #2c3e50;
}

.subtitle {
	color: #7f8c8d;
	margin-top: 5px;
}

.stats-section {
	display: flex;
	gap: 10px;
	margin-bottom: 10px;
}

.stat-card {
	flex: 1;
	display: flex;
	align-items: center;
	padding: 15px;
	background: white;
	border-radius: 8px;
	box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.stat-icon {
	width: 48px;
	height: 48px;
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	margin-right: 15px;
	font-size: 24px;
	color: white;
}

.adult-icon {
	background-color: #409EFF;
}

.adolescent-icon {
	background-color: #E6A23C;
}

.child-icon {
	background-color: #67C23A;
}

.stat-info {
	display: flex;
	flex-direction: column;
}

.stat-label {
	font-size: 14px;
	color: #909399;
}

.stat-value {
	font-size: 24px;
	font-weight: bold;
	color: #303133;
}

.matching-container {
	display: flex;
	gap: 10px;
	height: calc(100% - 120px);
}

.input-card {
	/* Adaptive width: min 300px, preferred 30% */
	flex: 0 0 30%;
	min-width: 320px;
	background: white;
	padding: 15px;
	border-radius: 8px;
	box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
	display: flex;
	flex-direction: column;
	overflow-y: auto;
}

.right-column {
	flex: 1;
	display: flex;
	flex-direction: column;
	gap: 10px;
	min-width: 0;
	/* Prevent flex overflow */
}

.chart-card {
	flex: 1;
	min-height: 400px;
	background: white;
	padding: 10px;
	border-radius: 8px;
	box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
	display: flex;
	flex-direction: column;
}

.chart-container {
	flex: 1;
	width: 100%;
	height: 100%;
	min-height: 0;
}

.results-area {
	flex: 0 0 250px;
	overflow-y: auto;
	min-height: 0;
}

.match-form {
	margin-top: 20px;
}

.form-tip {
	font-size: 12px;
	color: #909399;
	margin-top: 4px;
}

.match-btn {
	width: 100%;
	margin-top: 20px;
}

.candidate-card {
	background: white;
	padding: 10px;
	border-radius: 8px;
	margin-bottom: 10px;
	box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
	border-left: 4px solid transparent;
	transition: transform 0.2s;
}

.candidate-card:hover {
	transform: translateY(-2px);
	box-shadow: 0 4px 16px 0 rgba(0, 0, 0, 0.1);
}

.best-match {
	border-left-color: #67C23A;
	background-color: #f0f9eb;
}

.candidate-header {
	display: flex;
	align-items: center;
	margin-bottom: 5px;
}

.rank-badge {
	background: #909399;
	color: white;
	padding: 2px 8px;
	border-radius: 4px;
	font-weight: bold;
	margin-right: 10px;
}

.best-match .rank-badge {
	background: #67C23A;
}

.candidate-id {
	font-size: 18px;
	font-weight: bold;
	flex: 1;
}

.score-val {
	font-size: 20px;
	font-weight: bold;
	color: #409EFF;
}

.candidate-details {
	display: grid;
	grid-template-columns: repeat(3, 1fr);
	gap: 10px;
	margin-bottom: 10px;
	padding: 10px;
	background: rgba(0, 0, 0, 0.02);
	border-radius: 4px;
}

.detail-row {
	display: flex;
	flex-direction: column;
}

.label {
	font-size: 12px;
	color: #909399;
	margin-bottom: 4px;
}

.value {
	font-weight: 500;
}

.text-success {
	color: #67C23A;
}

.text-warning {
	color: #E6A23C;
}

.text-danger {
	color: #F56C6C;
}

.candidate-actions {
	display: flex;
	justify-content: flex-end;
}
</style>