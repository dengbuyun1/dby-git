<template>
	<!-- 仿真记录列表页面 -->
	<div class="main-container">
		<!-- 左侧导航栏 -->
		<Sidebar :currentRoute="'simulations_list'" @navigate="handleNavigate" @open-settings="handleOpenSettings" />

		<!-- 主内容区域 -->
		<div class="main-content">
			<!-- 顶部用户信息栏 -->
			<Header />

			<!-- 内容区域 -->
			<div class="content">
				<!-- 搜索和筛选栏 -->
				<div class="search-bar">
					<div class="search-section">
						<el-input v-model="searchQuery" placeholder="搜索仿真ID、患者姓名等" clearable @input="handleSearch"
							style="width: 300px;">
							<template #prepend>
								<el-icon>
									<Search />
								</el-icon>
							</template>
						</el-input>

						<el-button type="primary" @click="handleSearch">
							搜索
						</el-button>

						<el-button @click="resetSearch">
							重置
						</el-button>

						<el-button type="success" @click="refreshList">
							刷新列表
						</el-button>

						<el-select v-model="filterType" placeholder="患者类型" style="width: 120px" clearable
							@change="handleSearch">
							<el-option label="全部类型" value="all" />
							<el-option label="真实患者" value="real" />
							<el-option label="虚拟患者" value="virtual" />
						</el-select>

						<el-select v-model="filterStatus" placeholder="状态" style="width: 120px" clearable
							@change="handleSearch">
							<el-option label="全部状态" value="all" />
							<el-option label="运行中" value="running" />
							<el-option label="已完成" value="completed" />
							<el-option label="异常" value="error" />
						</el-select>

						<el-button type="danger" :disabled="selectedRows.length === 0" @click="batchDelete">
							批量删除
						</el-button>
					</div>

					<!-- 统计信息 -->
					<div class="stats-section">
						<div class="stat-item">
							<span class="stat-label">总计:</span>
							<span class="stat-value">{{ total }}</span>
						</div>
						<el-divider direction="vertical" />
						<div class="stat-item">
							<span class="stat-label">真实患者:</span>
							<span class="stat-value">{{ realPatientCount }}</span>
						</div>
						<el-divider direction="vertical" />
						<div class="stat-item">
							<span class="stat-label">虚拟患者:</span>
							<span class="stat-value">{{ virtualPatientCount }}</span>
						</div>
					</div>
				</div>

				<!-- 仿真记录表格 -->
				<div class="simulations-table">
					<el-table :data="paginatedSimulations" stripe style="width: 100%" max-height="calc(100vh - 300px)"
						v-loading="loading" @selection-change="handleSelectionChange">
						<!-- 多选列 -->
						<el-table-column type="selection" width="55" />

						<!-- ID列 (直接显示patient_id) -->
						<el-table-column prop="patient_id" label="ID" width="100" fixed="left" sortable
							:sort-method="sortById">
						</el-table-column>

						<!-- 患者姓名列 -->
						<el-table-column prop="patient_name" label="患者姓名" min-width="120" />

						<!-- 患者类型列 -->
						<el-table-column prop="patient_type" label="类型" min-width="100" />

						<!-- 年龄列 -->
						<el-table-column label="年龄" width="80">
							<template #default="scope">
								{{ isVirtualPatient(scope.row) ? '-' : scope.row.patient_age }}
							</template>
						</el-table-column>

						<!-- 性别列 -->
						<el-table-column label="性别" width="80">
							<template #default="scope">
								{{ isVirtualPatient(scope.row) ? '-' : scope.row.patient_gender }}
							</template>
						</el-table-column>

						<!-- 血型列 -->
						<el-table-column label="血型" width="80">
							<template #default="scope">
								{{ isVirtualPatient(scope.row) ? '-' : scope.row.patient_blood_type }}
							</template>
						</el-table-column>

						<!-- 传感器列 -->
						<el-table-column prop="sensor" label="传感器" min-width="120" />

						<!-- 控制器列 -->
						<el-table-column prop="controller" label="控制器" min-width="120" />

						<!-- 运行时长列 -->
						<el-table-column label="运行时长(小时)" min-width="160">
							<template #default="scope">
								{{ formatRuntime(scope.row) }}
							</template>
						</el-table-column>

						<!-- 开始时间列 -->
						<el-table-column prop="start_time" label="开始时间" min-width="180">
							<template #default="scope">
								{{ formatDateTime(scope.row.start_time) }}
							</template>
						</el-table-column>

						<!-- 状态列 -->
						<el-table-column prop="status" label="状态" width="100">
							<template #default="scope">
								<el-tag :type="getStatusTagType(scope.row.status)">
									{{ scope.row.status === 'running' ? '运行中' : scope.row.status === 'completed' ? '已完成'
										: '异常' }}
								</el-tag>
							</template>
						</el-table-column>

						<!-- 操作列 -->
						<el-table-column label="操作" width="180" fixed="right">
							<template #default="scope">
								<el-button type="primary" size="small" @click="viewSimulation(scope.row)">
									查看
								</el-button>
								<el-button type="danger" size="small" @click="deleteSimulation(scope.row)">
									删除
								</el-button>
							</template>
						</el-table-column>
					</el-table>

					<!-- 分页控件 -->
					<div class="pagination-container">
						<el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize"
							:page-sizes="[13, 20, 50, 100]" :small="false" :disabled="loading" :background="true"
							layout="total, sizes, prev, pager, next, jumper" :total="total"
							@size-change="handleSizeChange" @current-change="handleCurrentChange" />
					</div>
				</div>
			</div>
		</div>

		<!-- 仿真详情弹窗 -->
		<el-dialog v-model="showSimulationDetail" title="仿真详细信息" width="80%" top="5vh">
			<div v-if="selectedSimulation" class="simulation-detail">
				<!-- 基本信息 -->
				<div class="detail-section">
					<h4>基本信息</h4>
					<div class="detail-row">
						<span class="detail-label">仿真ID:</span>
						<span class="detail-value">{{ selectedSimulation.id }}</span>
					</div>
					<div class="detail-row">
						<span class="detail-label">患者姓名:</span>
						<span class="detail-value">{{ selectedSimulation.person }}</span>
					</div>
					<div class="detail-row">
						<span class="detail-label">传感器:</span>
						<span class="detail-value">{{ selectedSimulation.sensor }}</span>
					</div>
					<div class="detail-row">
						<span class="detail-label">泵类型:</span>
						<span class="detail-value">{{ selectedSimulation.pump }}</span>
					</div>
					<div class="detail-row">
						<span class="detail-label">控制器:</span>
						<span class="detail-value">{{ selectedSimulation.controller }}</span>
					</div>
					<div class="detail-row">
						<span class="detail-label">仿真时长:</span>
						<span class="detail-value">{{ selectedSimulation.simulate_hours }} 小时</span>
					</div>
					<div class="detail-row">
						<span class="detail-label">数据点数:</span>
						<span class="detail-value">{{ selectedSimulation.data_count }}</span>
					</div>
					<div class="detail-row">
						<span class="detail-label">状态:</span>
						<span class="detail-value">
							<el-tag :type="getStatusTagType(selectedSimulation.status)">
								{{ selectedSimulation.status === 'running' ? '运行中' : selectedSimulation.status ===
									'completed' ?
									'已完成' : '异常' }}
							</el-tag>
						</span>
					</div>
				</div>

				<!-- 数据图表 -->
				<div class="charts-section" v-loading="loadingData">
					<h4>仿真数据图表</h4>
					<div class="charts-grid">
						<div class="chart-container">
							<h5>SIN 函数</h5>
							<div ref="sinChart" class="chart"></div>
						</div>
						<div class="chart-container">
							<h5>COS 函数</h5>
							<div ref="cosChart" class="chart"></div>
						</div>
						<div class="chart-container">
							<h5>TAN 函数</h5>
							<div ref="tanChart" class="chart"></div>
						</div>
					</div>
				</div>
			</div>

			<template #footer>
				<el-button @click="showSimulationDetail = false">关闭</el-button>
			</template>
		</el-dialog>
	</div>
</template>

<script>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { BaseDataWebSocket } from '@/api/websocket'
import Sidebar from '@/components/Sidebar.vue'
import Header from '@/components/Header.vue'
import { Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'

export default {
	name: 'SimulationsList',
	components: {
		Sidebar,
		Header,
		Search
	},
	setup() {
		const router = useRouter()

		// Base数据WebSocket客户端
		const baseDataWS = new BaseDataWebSocket()

		// 响应式数据
		const loading = ref(false)
		const loadingData = ref(false)
		const searchQuery = ref('')
		const filterType = ref('all')
		const filterStatus = ref('all')
		const selectedRows = ref([])
		const showSimulationDetail = ref(false)
		const selectedSimulation = ref(null)

		// 分页数据
		const currentPage = ref(1)
		const pageSize = ref(13)

		// 仿真列表数据
		const simulationsList = ref([])

		// 图表引用
		const sinChart = ref(null)
		const cosChart = ref(null)
		const tanChart = ref(null)

		// 图表实例
		let sinChartInstance = null
		let cosChartInstance = null
		let tanChartInstance = null

		// 处理导航
		const handleNavigate = (routeName) => {
			console.log('导航到:', routeName)
		}

		// 处理设置
		const handleOpenSettings = () => {
			console.log('打开设置')
		}

		// 处理搜索
		const handleSearch = () => {
			// 搜索功能由计算属性自动处理
			currentPage.value = 1 // 重置到第一页
		}

		// 重置搜索
		const resetSearch = () => {
			searchQuery.value = ''
			filterType.value = 'all'
			filterStatus.value = 'all'
			currentPage.value = 1
		}

		// 处理多选变化
		const handleSelectionChange = (val) => {
			selectedRows.value = val
		}

		// 批量删除
		const batchDelete = () => {
			if (selectedRows.value.length === 0) return

			ElMessageBox.confirm(
				`确定要删除选中的 ${selectedRows.value.length} 条仿真记录吗？此操作不可恢复。`,
				'批量删除警告',
				{
					confirmButtonText: '确定',
					cancelButtonText: '取消',
					type: 'warning',
				}
			).then(async () => {
				try {
					loading.value = true
					// 并行执行删除操作
					const deletePromises = selectedRows.value.map(row => baseDataWS.deleteSimulation(row.id))
					await Promise.all(deletePromises)

					ElMessage.success(`成功删除 ${selectedRows.value.length} 条记录`)
					selectedRows.value = [] // 清空选择
					loadSimulations() // 重新加载列表
				} catch (error) {
					console.error('批量删除失败:', error)
					ElMessage.error('批量删除部分或全部失败: ' + error.message)
					loadSimulations() // 即使失败也刷新列表
				} finally {
					loading.value = false
				}
			}).catch(() => {
				// 用户取消
			})
		}

		// 刷新列表
		const refreshList = () => {
			loadSimulations()
		}

		// 查看仿真详情 - 跳转到VPatientsMonitor页面
		const viewSimulation = (simulation) => {
			// 跳转到虚拟患者监控页面，传递仿真ID和查看模式
			router.push({
				path: '/v-patients-monitor',
				query: {
					simulation_id: simulation.id,
					mode: 'view'
				}
			})
		}

		// 删除仿真
		const deleteSimulation = (simulation) => {
			const isReal = !isVirtualPatient(simulation)
			const typeText = isReal ? '真实患者' : '仿真'

			ElMessageBox.confirm(
				`确定要删除${typeText}ID ${simulation.id} 吗？此操作将删除所有相关数据且不可恢复。`,
				'警告',
				{
					confirmButtonText: '确定',
					cancelButtonText: '取消',
					type: 'warning',
				}
			).then(async () => {
				try {
					if (isReal) {
						await baseDataWS.deleteRealPatient(simulation.id)
					} else {
						await baseDataWS.deleteSimulation(simulation.id)
					}
					ElMessage.success('删除成功')
					// 重新加载列表
					loadSimulations()
				} catch (error) {
					console.error('删除失败:', error)
					ElMessage.error('删除失败: ' + error.message)
				}
			}).catch(() => {
				// 用户取消删除
			})
		}

		// 格式化日期时间
		const formatDateTime = (dateString) => {
			if (!dateString) return '--'

			try {
				const date = new Date(dateString)
				return date.toLocaleString('zh-CN', {
					year: 'numeric',
					month: '2-digit',
					day: '2-digit',
					hour: '2-digit',
					minute: '2-digit',
					second: '2-digit'
				})
			} catch (error) {
				return '--'
			}
		}

		// 排序函数 (按patient_id中的数字部分排序)
		const sortById = (a, b) => {
			// 提取patient_id中的数字部分 (VP003 -> 3, TP010 -> 10)
			const getNumber = (row) => {
				if (!row.patient_id) return 0
				const match = row.patient_id.match(/\d+/)
				return match ? parseInt(match[0]) : 0
			}
			return getNumber(a) - getNumber(b)
		}

		// 获取状态标签类型
		const getStatusTagType = (status) => {
			switch (status) {
				case 'running':
					return 'warning'
				case 'completed':
					return 'success'
				case 'error':
					return 'danger'
				default:
					return 'info'
			}
		}

		// 判断是否为虚拟患者
		const isVirtualPatient = (row) => {
			return row.patient_type === '虚拟患者' || (row.patient_id && row.patient_id.startsWith('VP'))
		}

		// 计算过滤后的仿真列表 (所有符合搜索条件的数据)
		const allFilteredSimulations = computed(() => {
			let filtered = [...simulationsList.value]

			// 按搜索关键词过滤
			if (searchQuery.value.trim()) {
				const query = searchQuery.value.toLowerCase().trim()
				filtered = filtered.filter(sim =>
					String(sim.id).includes(query) ||
					String(sim.patient_id).toLowerCase().includes(query) ||
					sim.patient_type?.toLowerCase().includes(query) ||
					sim.patient_name?.toLowerCase().includes(query) ||
					sim.person?.toLowerCase().includes(query) ||
					sim.sensor?.toLowerCase().includes(query) ||
					sim.pump?.toLowerCase().includes(query) ||
					sim.controller?.toLowerCase().includes(query)
				)
			}

			// 按患者类型过滤
			if (filterType.value && filterType.value !== 'all') {
				if (filterType.value === 'real') {
					filtered = filtered.filter(sim => !isVirtualPatient(sim))
				} else if (filterType.value === 'virtual') {
					filtered = filtered.filter(sim => isVirtualPatient(sim))
				}
			}

			// 按状态过滤
			if (filterStatus.value && filterStatus.value !== 'all') {
				filtered = filtered.filter(sim => sim.status === filterStatus.value)
			}

			return filtered
		})

		// 统计数据
		const realPatientCount = computed(() => {
			return allFilteredSimulations.value.filter(sim => !isVirtualPatient(sim)).length
		})

		const virtualPatientCount = computed(() => {
			return allFilteredSimulations.value.filter(sim => isVirtualPatient(sim)).length
		})

		// 分页后的仿真列表 (当前页显示的数据)
		const paginatedSimulations = computed(() => {
			const start = (currentPage.value - 1) * pageSize.value
			const end = start + pageSize.value
			return allFilteredSimulations.value.slice(start, end)
		})

		// 总条数
		const total = computed(() => allFilteredSimulations.value.length)

		// 处理每页条数变化
		const handleSizeChange = (val) => {
			pageSize.value = val
			currentPage.value = 1
		}

		// 处理页码变化
		const handleCurrentChange = (val) => {
			currentPage.value = val
		}

		// 加载仿真列表
		const loadSimulations = async () => {
			loading.value = true
			try {
				// 并行获取仿真列表和真实患者列表
				const [simulations, realPatients] = await Promise.all([
					baseDataWS.getSimulationsList().catch(e => {
						console.error('获取仿真列表失败', e)
						return []
					}),
					baseDataWS.getRealPatientsList().catch(e => {
						console.error('获取真实患者列表失败', e)
						return []
					})
				])

				// 合并列表
				// 真实患者数据结构可能需要适配
				const formattedRealPatients = (realPatients || []).map(p => ({
					id: p.id,
					patient_id: p.patient_id,
					patient_name: p.patient_name,
					patient_type: '真实患者', // 强制标记
					patient_age: p.patient_age,
					patient_gender: p.patient_gender,
					patient_blood_type: p.patient_blood_type,
					start_time: p.start_time,
					status: p.status || 'active',
					data_count: p.data_count || 0,
					sensor: p.sensor,
					pump: p.pump,
					controller: p.controller
				}))

				simulationsList.value = [...formattedRealPatients, ...(simulations || [])]

				// 重置到第一页
				currentPage.value = 1
				ElMessage.success(`加载成功，共 ${simulationsList.value.length} 条记录`)
			} catch (error) {
				console.error('加载列表失败:', error)
				ElMessage.error('加载列表失败: ' + error.message)
				simulationsList.value = []
			} finally {
				loading.value = false
			}
		}

		// 初始化图表
		const initCharts = (data) => {
			// 销毁旧图表
			if (sinChartInstance) sinChartInstance.dispose()
			if (cosChartInstance) cosChartInstance.dispose()
			if (tanChartInstance) tanChartInstance.dispose()

			if (!data || data.length === 0) {
				ElMessage.warning('该仿真暂无数据')
				return
			}

			// 提取数据
			const iValues = data.map(d => d.i)
			const sinValues = data.map(d => d.sin)
			const cosValues = data.map(d => d.cos)
			const tanValues = data.map(d => d.tan)

			// SIN图表
			sinChartInstance = echarts.init(sinChart.value)
			sinChartInstance.setOption({
				title: { text: 'SIN 函数', left: 'center' },
				tooltip: { trigger: 'axis' },
				xAxis: { type: 'category', data: iValues, name: 'i' },
				yAxis: { type: 'value', name: '值' },
				series: [{
					name: 'SIN',
					type: 'line',
					data: sinValues,
					color: '#e74c3c',
					smooth: true
				}],
				grid: { left: '10%', right: '10%', bottom: '15%', top: '15%' }
			})

			// COS图表
			cosChartInstance = echarts.init(cosChart.value)
			cosChartInstance.setOption({
				title: { text: 'COS 函数', left: 'center' },
				tooltip: { trigger: 'axis' },
				xAxis: { type: 'category', data: iValues, name: 'i' },
				yAxis: { type: 'value', name: '值' },
				series: [{
					name: 'COS',
					type: 'line',
					data: cosValues,
					color: '#3498db',
					smooth: true
				}],
				grid: { left: '10%', right: '10%', bottom: '15%', top: '15%' }
			})

			// TAN图表
			tanChartInstance = echarts.init(tanChart.value)
			tanChartInstance.setOption({
				title: { text: 'TAN 函数', left: 'center' },
				tooltip: { trigger: 'axis' },
				xAxis: { type: 'category', data: iValues, name: 'i' },
				yAxis: { type: 'value', name: '值' },
				series: [{
					name: 'TAN',
					type: 'line',
					data: tanValues,
					color: '#f39c12',
					smooth: true
				}],
				grid: { left: '10%', right: '10%', bottom: '15%', top: '15%' }
			})
		}

		// 启动Base数据连接
		const startBaseDataConnection = () => {
			baseDataWS.connect(
				null, // 不需要实时数据回调
				(status) => {
					console.log('WebSocket状态:', status)
					if (status === 'connected') {
						// 连接成功后加载仿真列表
						loadSimulations()
					}
				}
			)
		}

		// 停止Base数据连接
		const stopBaseDataConnection = () => {
			baseDataWS.disconnect()
		}

		// 计算实际运行时长
		const calculateDuration = (row) => {
			if (!row.data_count) return '0.00'

			let sampleTime = 3 // Dexcom 默认为 3分钟
			if (row.sensor && row.sensor.includes('Guardian')) sampleTime = 5
			if (row.sensor && row.sensor.includes('Navigator')) sampleTime = 1

			const hours = (row.data_count * sampleTime) / 60
			return hours.toFixed(2)
		}

		// 格式化运行时长显示 (设定时长 / 实际时长)
		const formatRuntime = (row) => {
			const configured = row.simulate_hours ? Number(row.simulate_hours).toFixed(2) : '0.00'
			const actual = calculateDuration(row)
			return `${configured} / ${actual}`
		}

		// 组件挂载
		onMounted(() => {
			startBaseDataConnection()
		})

		// 组件卸载
		onBeforeUnmount(() => {
			stopBaseDataConnection()
			if (sinChartInstance) sinChartInstance.dispose()
			if (cosChartInstance) cosChartInstance.dispose()
			if (tanChartInstance) tanChartInstance.dispose()
		})

		return {
			handleNavigate,
			handleOpenSettings,
			loading,
			loadingData,
			searchQuery,
			filterType,
			filterStatus,
			selectedRows,
			showSimulationDetail,
			selectedSimulation,
			paginatedSimulations,
			currentPage,
			pageSize,
			total,
			realPatientCount,
			virtualPatientCount,
			handleSizeChange,
			handleCurrentChange,
			handleSearch,
			resetSearch,
			handleSelectionChange,
			batchDelete,
			refreshList,
			viewSimulation,
			deleteSimulation,
			formatDateTime,
			sortById,
			getStatusTagType,
			sinChart,
			cosChart,
			tanChart,
			isVirtualPatient,
			calculateDuration,
			formatRuntime
		}
	}
}
</script>

<style scoped>
.search-bar {
	margin-bottom: 20px;
	padding: 15px;
	background: white;
	border-radius: 8px;
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	display: flex;
	justify-content: space-between;
	align-items: center;
	flex-wrap: wrap;
	gap: 15px;
}

.search-section {
	display: flex;
	align-items: center;
	gap: 10px;
	flex-wrap: wrap;
}

.stats-section {
	display: flex;
	align-items: center;
	gap: 10px;
	background-color: #f5f7fa;
	padding: 8px 15px;
	border-radius: 4px;
	border: 1px solid #e4e7ed;
}

.stat-item {
	display: flex;
	align-items: center;
	gap: 5px;
	font-size: 14px;
}

.stat-label {
	color: #606266;
}

.stat-value {
	font-weight: bold;
	color: #409eff;
	font-size: 16px;
}

.simulations-table {
	background: white;
	border-radius: 8px;
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	padding: 1%;
	width: 100%;
	box-sizing: border-box;
}

.simulation-detail {
	padding: 2%;
}

.detail-section {
	margin-bottom: 3%;
}

.detail-section h4 {
	margin-bottom: 1.5%;
	font-size: 1.1em;
	font-weight: 600;
	color: #333;
	border-bottom: 2px solid #409eff;
	padding-bottom: 0.8%;
}

.detail-row {
	display: flex;
	align-items: center;
	padding: 1% 0;
	border-bottom: 1px solid #f0f0f0;
}

.detail-row:last-child {
	border-bottom: none;
}

.detail-label {
	width: 35%;
	max-width: 150px;
	font-weight: bold;
	color: #666;
	flex-shrink: 0;
	font-size: 0.95em;
}

.detail-value {
	flex: 1;
	color: #333;
	font-size: 0.95em;
}

.charts-section h4 {
	margin-bottom: 2%;
	font-size: 1.1em;
	font-weight: 600;
	color: #333;
	border-bottom: 2px solid #67c23a;
	padding-bottom: 0.8%;
}

.charts-grid {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(45%, 1fr));
	gap: 2%;
}

.chart-container {
	background: #f9f9f9;
	border: 1px solid #eaeaea;
	border-radius: 6px;
	padding: 2%;
	width: 100%;
	box-sizing: border-box;
}

.chart-container h5 {
	margin: 0 0 1% 0;
	font-size: 1em;
	font-weight: 600;
	color: #333;
	text-align: center;
}

.chart {
	width: 100%;
	height: 300px;
}

.pagination-container {
	margin-top: 20px;
	display: flex;
	justify-content: flex-end;
	padding: 23px 0;
}

/* 响应式断点 */
@media (max-width: 1400px) {
	.search-section {
		gap: 0.8%;
	}

	.simulations-table {
		padding: 1.8%;
	}

	.chart {
		height: 280px;
	}
}

@media (max-width: 1200px) {
	.search-section {
		gap: 1.2%;
	}

	.simulations-table {
		padding: 1.5%;
	}

	.charts-grid {
		grid-template-columns: 1fr;
		gap: 2.5%;
	}

	.chart {
		height: 260px;
	}

	.detail-label,
	.detail-value {
		font-size: 0.9em;
	}
}

@media (max-width: 1024px) {
	.simulations-table {
		overflow-x: auto;
	}

	.chart {
		height: 240px;
	}
}

@media (max-width: 768px) {
	.search-section {
		flex-direction: column;
		align-items: stretch;
		gap: 2%;
	}

	.simulations-table {
		overflow-x: auto;
		padding: 3%;
	}

	.simulation-detail {
		padding: 3%;
	}

	.charts-grid {
		grid-template-columns: 1fr;
		gap: 3%;
	}

	.chart {
		height: 220px;
	}

	.detail-label {
		width: 40%;
		font-size: 0.85em;
	}

	.detail-value {
		font-size: 0.85em;
	}
}

@media (max-width: 480px) {
	.simulations-table {
		padding: 4%;
	}

	.simulation-detail {
		padding: 4%;
	}

	.chart {
		height: 200px;
	}

	.detail-section h4,
	.charts-section h4 {
		font-size: 1em;
	}

	.chart-container h5 {
		font-size: 0.9em;
	}

	.detail-label,
	.detail-value {
		font-size: 0.8em;
	}
}
</style>
