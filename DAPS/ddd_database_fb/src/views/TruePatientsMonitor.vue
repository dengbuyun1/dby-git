<template>
  <div class="main-container">
    <Sidebar :currentRoute="'true_patients'" @navigate="handleNavigate" @open-settings="handleOpenSettings" />

    <div class="main-content">
      <Header />

      <div class="content">
        <div class="data-section">
          <div class="data-left">
            <div class="card patient-info-card">
              <h4>患者信息</h4>
              <div class="patient-info-content">
                <div class="patient-details">
                  <div class="detail-item">
                    <span class="detail-label">Name</span>
                    <span class="detail-value">{{ patientInfo.name || patientInfo.id || '未设置' }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Gender / Age</span>
                    <span class="detail-value">{{ patientInfo.gender || '--' }} / {{ patientInfo.age || '--' }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Blood Type</span>
                    <span class="detail-value">{{ patientInfo.bloodType || '--' }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Sensor</span>
                    <span class="detail-value">{{ paramSettings.sensor || '未设置' }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Controller</span>
                    <span class="detail-value">{{ paramSettings.controller || '未设置' }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Status</span>
                    <span class="detail-value" :class="{
                      'status-running': isSimulationRunning,
                      'status-completed': simulationStatusText === '已完成',
                      'status-idle': !isSimulationRunning && simulationStatusText !== '已完成'
                    }">{{ simulationStatusText }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">ID</span>
                    <span class="detail-value">{{ patientInfo.id || '未设置' }}</span>
                  </div>
                  <div class="detail-item" v-if="patientInfo.notes">
                    <span class="detail-label">Remarks</span>
                    <span class="detail-value" style="font-size: 14px; font-weight: normal;">{{ patientInfo.notes
                    }}</span>
                  </div>
                </div>
                <div class="patient-avatar">
                  <img src="/tp_define_photo.svg" alt="Patient Avatar" class="avatar-img" />
                </div>
              </div>

              <div class="action-buttons">
                <el-button type="primary" size="small" @click="openEditDialog">
                  编辑
                </el-button>
              </div>
            </div>

            <div class="card" style="margin-bottom: 15px;">
              <h4>生理指标</h4>
              <div class="vital-signs">
                <div class="vital-item">
                  <span class="vital-label">ECG/心电图:</span>
                  <span class="vital-value">{{ otherData.ecg || '--' }}</span>
                </div>
                <div class="vital-item">
                  <span class="vital-label">NIBP/血压:</span>
                  <span class="vital-value">{{ otherData.nibp || '--' }}</span>
                </div>
                <div class="vital-item">
                  <span class="vital-label">SPO2/血氧:</span>
                  <span class="vital-value">{{ otherData.spo2 || '--' }}%</span>
                </div>
                <div class="vital-item">
                  <span class="vital-label">PR/脉率:</span>
                  <span class="vital-value">{{ otherData.pr || '--' }}</span>
                </div>
                <div class="vital-item">
                  <span class="vital-label">PRSP/脉搏:</span>
                  <span class="vital-value">{{ otherData.prsp || '--' }}</span>
                </div>
                <div class="vital-item">
                  <span class="vital-label">TEMP/体温:</span>
                  <span class="vital-value">{{ otherData.temp || '--' }}°C</span>
                </div>
              </div>
            </div>
          </div>

          <div class="data-center">
            <div class="chart-container">
              <div class="chart-header">
                <h4>BG & CGM (血糖监测)</h4>
                <div class="custom-legend">
                  <div class="legend-item" @click="toggleSeries('bgCgm', 'BG')">
                    <span class="legend-marker" style="background-color: #3498db;"></span>
                    <span class="legend-text">BG</span>
                  </div>
                  <div class="legend-item" @click="toggleSeries('bgCgm', 'CGM')">
                    <span class="legend-marker" style="background-color: #f39c12;"></span>
                    <span class="legend-text">CGM</span>
                  </div>
                </div>
              </div>
              <div class="monitor-screen main-chart-screen">
                <div ref="bgCgmChart" class="chart"></div>
              </div>
            </div>

            <div class="chart-container combined-chart-container">
              <div class="chart-section top-section">
                <div class="chart-header compact-header">
                  <h4>CHO & COB (碳水化合物)</h4>
                  <div class="custom-legend">
                    <div class="legend-item" @click="toggleSeries('choCob', 'CHO')">
                      <span class="legend-marker" style="background-color: #3498db;"></span>
                      <span class="legend-text">CHO</span>
                    </div>
                    <div class="legend-item" @click="toggleSeries('choCob', 'COB')">
                      <span class="legend-marker" style="background-color: #9b59b6;"></span>
                      <span class="legend-text">COB</span>
                    </div>
                  </div>
                </div>
                <div class="monitor-screen compact-screen">
                  <div ref="choCobChart" class="chart"></div>
                </div>
              </div>

              <div class="chart-divider"></div>

              <div class="chart-section bottom-section">
                <div class="chart-header compact-header">
                  <h4>INSULIN & IOB (胰岛素)</h4>
                  <div class="custom-legend">
                    <div class="legend-item" @click="toggleSeries('insulinIob', 'INSULIN')">
                      <span class="legend-marker" style="background-color: #2ecc71;"></span>
                      <span class="legend-text">INSULIN</span>
                    </div>
                    <div class="legend-item" @click="toggleSeries('insulinIob', 'IOB')">
                      <span class="legend-marker" style="background-color: #e67e22;"></span>
                      <span class="legend-text">IOB</span>
                    </div>
                  </div>
                </div>
                <div class="monitor-screen compact-screen">
                  <div ref="insulinIobChart" class="chart"></div>
                </div>
              </div>
            </div>

            <Teleport to="body">
              <div v-if="historyMode" class="history-slider-section" :style="historyWindowStyle">
                <div class="history-header" @mousedown="startDragHistoryWindow"
                  style="cursor: grab; user-select: none; border-bottom: 1px solid rgba(255,255,255,0.2); padding-bottom: 10px; margin-bottom: 15px;">
                  <h4 style="margin:0;">📊 历史数据查看 <small
                      style="font-size: 12px; opacity: 0.8; font-weight: normal;">(按住拖动)</small></h4>
                  <div class="history-actions" @mousedown.stop>
                    <el-button type="danger" size="small" @click="handleDeleteSimulation">
                      删除记录
                    </el-button>
                    <el-button size="small" @click="exitHistoryMode">
                      {{ fromHistory ? '返回列表' : '退出查看' }}
                    </el-button>
                  </div>
                </div>

                <!-- 多天数据选择器 -->
                <div v-if="historyDays.length > 1" class="day-selector">
                  <span class="info-label">选择日期:</span>
                  <div class="day-buttons">
                    <el-button v-for="(day, index) in historyDays" :key="index" size="small"
                      :type="selectedDayIndex === index ? 'primary' : 'default'" @click="selectDay(index)">
                      {{ day }}
                    </el-button>
                  </div>
                </div>

                <div class="slider-info">
                  <span class="info-label">当前查看:</span>
                  <span class="info-value">{{ currentViewTimeLabel }}</span>
                  <span class="info-label" style="margin-left: 15px;">数据点:</span>
                  <span class="info-value">{{ currentViewIndex + 1 }} / {{ maxHistoryIndex + 1 }}</span>
                </div>

                <el-slider v-model="currentViewIndex" :min="dayStartIndex" :max="dayEndIndex" :show-tooltip="false"
                  @input="onHistorySliderChange" />
              </div>
            </Teleport>


          </div>

          <div class="data-right">
            <div class="card therapy-stats-card">
              <h4>治疗统计 (24h)</h4>
              <div class="stats-content">
                <div class="tir-chart-container">
                  <div class="tir-bar-wrapper">
                    <div class="tir-bar">
                      <div class="tir-segment high" :style="{ width: cgmStats.tar + '%' }"
                        :title="'High: ' + cgmStats.tar + '%'"></div>
                      <div class="tir-segment in-range" :style="{ width: cgmStats.tir + '%' }"
                        :title="'In Range: ' + cgmStats.tir + '%'"></div>
                      <div class="tir-segment low" :style="{ width: cgmStats.tbr + '%' }"
                        :title="'Low: ' + cgmStats.tbr + '%'"></div>
                    </div>
                  </div>
                  <div class="tir-legend">
                    <span class="legend-item"><span class="dot high"></span>High ({{ cgmStats.tar }}%)</span>
                    <span class="legend-item"><span class="dot in-range"></span>Range ({{ cgmStats.tir }}%)</span>
                    <span class="legend-item"><span class="dot low"></span>Low ({{ cgmStats.tbr }}%)</span>
                  </div>
                </div>
                <div class="stats-grid">
                  <div class="stat-item">
                    <span class="stat-label">Avg Glucose</span>
                    <span class="stat-value">{{ cgmStats.average }} <small>mg/dL</small></span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">GMI (A1c)</span>
                    <span class="stat-value">{{ cgmStats.gmi }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">CV (Var)</span>
                    <span class="stat-value">{{ cgmStats.cv }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 硬件监控卡片 (下位机) -->
            <div class="card hardware-monitor-card">
              <h4>硬件监控 (下位机)</h4>
              <div class="hardware-info">
                <div class="info-row">
                  <div class="info-item">
                    <span class="label">PWM占空比:</span>
                    <span class="value">{{ hardwareData.pwmDuty }}%</span>
                  </div>
                  <div class="info-item">
                    <span class="label">PWM频率:</span>
                    <span class="value">{{ hardwareData.pwmFreq }} Hz</span>
                  </div>
                </div>
                <div class="info-row">
                  <div class="info-item">
                    <span class="label">电机状态:</span>
                    <span class="value" :class="{ 'status-active': hardwareData.motorStatus === 'Running' }">
                      {{ hardwareData.motorStatus }}
                    </span>
                  </div>
                  <div class="info-item">
                    <span class="label">推注方向:</span>
                    <span class="value">{{ hardwareData.direction }}</span>
                  </div>
                </div>
                <div class="info-row">
                  <div class="info-item">
                    <span class="label">实时推注:</span>
                    <span class="value">{{ hardwareData.actualDelivery }} U</span>
                  </div>
                </div>
              </div>
              <div class="hardware-chart-container">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                  <h5 style="margin: 0;">PWM & 推注曲线</h5>
                  <el-button type="primary" link size="small" @click="showPwmChart = !showPwmChart">
                    {{ showPwmChart ? '隐藏' : '显示' }}
                  </el-button>
                </div>
                <el-collapse-transition>
                  <div v-show="showPwmChart" class="monitor-screen">
                    <div ref="motorChart" class="motor-chart"></div>
                  </div>
                </el-collapse-transition>
              </div>
            </div>

            <div class="card">
              <h4>其他信息</h4>
              <div class="other-info">
                <div class="status-indicators-row">
                  <div class="info-item compact">
                    <span class="info-label">WebSocket</span>
                    <span class="info-value">
                      <span class="status-dot" :class="connectionStatus"></span>
                      {{ connectionStatus === 'connected' ? '已连接' :
                        connectionStatus === 'connecting' ? '连接中' :
                          '未连接' }}
                    </span>
                  </div>

                  <div class="info-item compact">
                    <span class="info-label">数据库</span>
                    <span class="info-value">
                      <span class="status-dot" :class="dbConnectionStatus"></span>
                      {{ dbConnectionStatus === 'connected' ? '已连接' : '未连接' }}
                    </span>
                  </div>

                  <div class="info-item compact">
                    <span class="info-label">树莓派</span>
                    <span class="info-value">
                      <span class="status-dot" :class="tcpConnectionStatus"></span>
                      {{ tcpConnectionStatus === 'connected' ? '已连接' :
                        tcpConnectionStatus === 'connecting' ? '连接中' :
                          '未连接' }}
                    </span>
                  </div>
                </div>

                <div class="simulation-details-toggle">
                  <el-button type="text" @click="showSimulationDetails = !showSimulationDetails" size="small">
                    {{ showSimulationDetails ? '隐藏详情' : '显示详情' }}
                    <el-icon :class="{ 'rotate-icon': showSimulationDetails }">
                      <ArrowDown />
                    </el-icon>
                  </el-button>
                </div>

                <el-collapse-transition>
                  <div v-show="showSimulationDetails" class="simulation-details-content">
                    <div class="info-item">
                      <span class="info-label">模式:</span>
                      <span class="info-value">{{ historyMode ? '历史查看模式' : '实时监控' }}</span>
                    </div>

                    <div class="info-item">
                      <span class="info-label">数据保存:</span>
                      <span class="info-value">{{ dataSaveStatus }}</span>
                    </div>

                    <div v-if="currentSimulationId" class="info-item">
                      <span class="info-label">记录ID:</span>
                      <span class="info-value">{{ currentSimulationId }}</span>
                    </div>

                    <div class="info-item">
                      <span class="info-label">数据点数:</span>
                      <span class="info-value">{{ baseData.bg.length }} 个</span>
                    </div>
                  </div>
                </el-collapse-transition>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加/编辑真实患者对话框 -->
    <el-dialog v-model="dialogVisible" title="患者信息设置" width="500px" :close-on-click-modal="false" class="blur-dialog">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="姓名">
          <el-input v-model="editForm.name" placeholder="请输入患者姓名" />
        </el-form-item>
        <el-form-item label="ID">
          <el-input v-model="editForm.patient_id" placeholder="自动生成" disabled />
        </el-form-item>
        <el-form-item label="性别">
          <el-select v-model="editForm.gender" placeholder="请选择性别">
            <el-option label="男" value="男" />
            <el-option label="女" value="女" />
          </el-select>
        </el-form-item>
        <el-form-item label="年龄">
          <el-input-number v-model="editForm.age" :min="1" :max="120" />
        </el-form-item>
        <el-form-item label="血型">
          <el-select v-model="editForm.bloodType" placeholder="请选择血型">
            <el-option label="A" value="A" />
            <el-option label="B" value="B" />
            <el-option label="AB" value="AB" />
            <el-option label="O" value="O" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.notes" type="textarea" placeholder="请输入备注信息" />
        </el-form-item>
        <el-form-item label="控制器">
          <el-select v-model="editForm.controller" placeholder="请选择控制器">
            <el-option label="PID" value="PID" />
            <el-option label="Basal-Bolus" value="Basal-Bolus" />
            <el-option label="MPC" value="MPC" />
          </el-select>
        </el-form-item>
        <el-form-item label="传感器">
          <el-select v-model="editForm.sensor" placeholder="请选择传感器">
            <el-option label="Dexcom" value="Dexcom" />
            <el-option label="GuardianRT" value="GuardianRT" />
            <el-option label="Navigator" value="Navigator" />
          </el-select>
        </el-form-item>
        <el-form-item label="泵类型">
          <el-select v-model="editForm.pump" placeholder="请选择泵类型">
            <el-option label="Insulet" value="Insulet" />
            <el-option label="Cozmo" value="Cozmo" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="savePatientInfoDialog">保存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePatientsStore } from '@/store'
import { glucoseDataAPI, otherDataAPI, patientsAPI } from '@/api'
import { BaseDataWebSocket } from '@/api/websocket'
import Sidebar from '@/components/Sidebar.vue'
import Header from '@/components/Header.vue'
import * as echarts from 'echarts'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown } from '@element-plus/icons-vue'

export default {
  name: 'TruePatientsMonitor',
  components: {
    Sidebar,
    Header
  },
  setup() {
    const route = useRoute()
    const router = useRouter()
    const patientsStore = usePatientsStore()

    // Base数据WebSocket客户端
    const baseDataWS = new BaseDataWebSocket()

    // 响应式数据
    const isEditing = ref(false)
    const dialogVisible = ref(false)
    const timeRange = ref([0, 24])
    const showSimulationDetails = ref(false) // 控制详情的展开/折叠
    const showPwmChart = ref(true) // 控制PWM曲线的展开/折叠

    const editForm = reactive({
      name: '',
      age: 30,
      gender: '男',
      bloodType: 'A',
      notes: '',
      controller: 'PID',
      sensor: 'Dexcom',
      pump: 'Insulet',
      patient_id: ''
    })

    const openEditDialog = () => {
      // 初始化表单数据
      editForm.name = patientInfo.name || ''
      editForm.age = patientInfo.age || 30
      editForm.gender = patientInfo.gender || '男'
      editForm.bloodType = patientInfo.bloodType || 'A'
      editForm.notes = patientInfo.notes || ''
      editForm.controller = paramSettings.controller || 'PID'
      editForm.sensor = paramSettings.sensor || 'Dexcom'
      editForm.pump = paramSettings.pump || 'Insulet'
      editForm.patient_id = patientInfo.id

      dialogVisible.value = true
    }

    const savePatientInfoDialog = () => {
      if (!editForm.name) {
        ElMessage.warning('请输入患者姓名')
        return
      }

      // 更新本地显示
      patientInfo.name = editForm.name
      patientInfo.age = editForm.age
      patientInfo.gender = editForm.gender
      patientInfo.bloodType = editForm.bloodType
      patientInfo.notes = editForm.notes
      paramSettings.controller = editForm.controller
      paramSettings.sensor = editForm.sensor
      paramSettings.pump = editForm.pump

      // 发送创建/更新请求
      baseDataWS.send({
        command: 'create_real_patient',
        params: {
          patient_name: editForm.name,
          patient_id: editForm.patient_id,
          patient_gender: editForm.gender === '男' ? 'Male' : 'Female',
          patient_age: editForm.age,
          patient_blood_type: editForm.bloodType,
          notes: editForm.notes,
          controller: editForm.controller,
          sensor: editForm.sensor,
          pump: editForm.pump
        }
      })

      dialogVisible.value = false
      ElMessage.success('患者信息保存成功')
    }
    const patientInfo = reactive({
      id: route.query.mode === 'create' ? '' : (route.params.patientId || 'TP001'),
      name: '',
      age: null,
      gender: '',
      bloodType: '',
      notes: ''
    })

    // 根据患者信息生成机器人颜色
    const robotColor = computed(() => {
      const str = patientInfo.name || patientInfo.id || 'default'
      let hash = 0
      for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash)
      }
      // 生成柔和的HSL颜色
      const h = Math.abs(hash) % 360
      return `hsl(${h}, 70%, 75%)`
    })

    const otherData = reactive({
      ecg: null,
      nibp: null,
      spo2: null,
      pr: null,
      prsp: null,
      temp: null
    })

    // 硬件监控数据
    const hardwareData = reactive({
      pwmDuty: 0,
      pwmFreq: 1000,
      motorPos: 0,
      motorStatus: 'Stopped',
      direction: 'Forward',
      actualDelivery: 0
    })
    const motorChart = ref(null)
    let motorChartInstance = null
    const motorDataSeries = [] // Store [timestamp, value] for chart
    const pwmDataSeries = [] // Store [timestamp, value] for PWM chart
    const actualDeliverySeries = [] // Store [timestamp, value] for Actual Delivery chart

    const pad2 = (value) => String(value).padStart(2, '0')
    const formatLocalDateTime = (date) => {
      if (!(date instanceof Date) || Number.isNaN(date.getTime())) return ''
      const y = date.getFullYear()
      const m = pad2(date.getMonth() + 1)
      const d = pad2(date.getDate())
      const h = pad2(date.getHours())
      const minute = pad2(date.getMinutes())
      const s = pad2(date.getSeconds())
      return `${y}-${m}-${d} ${h}:${minute}:${s}`
    }
    const parseLocalDateTime = (value) => {
      if (!value) return null
      if (value instanceof Date) return value
      if (typeof value === 'number') return new Date(value)
      if (typeof value === 'string') {
        const trimmed = value.trim()
        if (/Z$|[+-]\d{2}:?\d{2}$/.test(trimmed)) {
          const zonedDate = new Date(trimmed)
          if (!Number.isNaN(zonedDate.getTime())) {
            return zonedDate
          }
        }

        const normalized = trimmed.replace('T', ' ')
        const [datePart, timePartWithFraction = ''] = normalized.split(' ')
        const [year, month, day] = (datePart || '').split('-').map(Number)
        if ([year, month, day].some((n) => Number.isNaN(n))) return null

        const [timePart, fractional = ''] = timePartWithFraction.split('.')
        const cleanTimePart = (timePart || '').replace(/([+-]\d{2}:?\d{2})$/, '')
        const [hour = 0, minute = 0, second = 0] = cleanTimePart.split(':').map((v) => Number(v ?? 0))
        const millisecond = fractional ? Number(fractional.padEnd(3, '0').slice(0, 3)) : 0

        const candidate = new Date(year, month - 1, day, hour, minute, second, millisecond)
        if (!Number.isNaN(candidate.getTime())) {
          return candidate
        }

        const fallback = new Date(value)
        return Number.isNaN(fallback.getTime()) ? null : fallback
      }
      return null
    }

    const parseTimestampToLocalMs = (value) => {
      const parsed = parseLocalDateTime(value)
      return parsed ? parsed.getTime() : null
    }

    const toNumberOrNull = (value, fallback = null) => {
      const num = Number(value)
      return Number.isFinite(num) ? num : fallback
    }

    const replaceReactiveArray = (target, values) => {
      target.splice(0, target.length, ...values)
    }

    // 参数设置 (仅用于显示)
    const paramSettings = reactive({
      sensor: 'Dexcom',
      pump: 'Insulet',
      controller: 'pid',
      simulateHours: 24
    })

    // 仿真状态 (保留变量以兼容模板)
    const simulating = ref(false)
    const isSimulationRunning = ref(false)

    // Base数据
    const baseData = reactive({
      bg: [],
      cgm: [],
      cho: [],
      cob: [],
      insulin: [],
      iob: []
    })

    // 历史数据存储
    const historyData = reactive({
      bg: [],
      cgm: [],
      cho: [],
      cob: [],
      insulin: [],
      iob: [],
      timestamp: []
    })
    const currentViewIndex = ref(0)
    const historyMode = ref(false)

    // 历史数据窗口拖拽逻辑
    const historyWindowX = ref(window.innerWidth / 2 - 350) // 初始居中 (假设宽度700)
    const historyWindowY = ref(window.innerHeight - 250) // 初始底部
    const isDraggingHistory = ref(false)
    const dragOffset = reactive({ x: 0, y: 0 })

    const historyWindowStyle = computed(() => ({
      position: 'fixed',
      left: `${historyWindowX.value}px`,
      top: `${historyWindowY.value}px`,
      zIndex: 2000,
      width: '700px',
      margin: 0,
      boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
      cursor: isDraggingHistory.value ? 'grabbing' : 'default'
    }))

    const startDragHistoryWindow = (e) => {
      isDraggingHistory.value = true
      dragOffset.x = e.clientX - historyWindowX.value
      dragOffset.y = e.clientY - historyWindowY.value
      document.addEventListener('mousemove', onDragHistoryWindow)
      document.addEventListener('mouseup', stopDragHistoryWindow)
    }

    const onDragHistoryWindow = (e) => {
      if (!isDraggingHistory.value) return
      // 限制在屏幕范围内
      const newX = e.clientX - dragOffset.x
      const newY = e.clientY - dragOffset.y

      // 简单的边界检查
      const maxX = window.innerWidth - 100
      const maxY = window.innerHeight - 50

      historyWindowX.value = Math.min(Math.max(newX, -300), maxX)
      historyWindowY.value = Math.min(Math.max(newY, 0), maxY)
    }

    const stopDragHistoryWindow = () => {
      isDraggingHistory.value = false
      document.removeEventListener('mousemove', onDragHistoryWindow)
      document.removeEventListener('mouseup', stopDragHistoryWindow)
    }

    const fromHistory = ref(false)
    const loadingHistory = ref(false)
    const currentSimulationId = ref(null)

    // 多天历史数据支持
    const historyDays = ref([])
    const selectedDayIndex = ref(0)
    const dayStartIndex = ref(0)
    const dayEndIndex = ref(0)
    const currentViewTimeLabel = computed(() => {
      if (historyData.timestamp && historyData.timestamp[currentViewIndex.value]) {
        return historyData.timestamp[currentViewIndex.value]
      }
      return '--'
    })

    const maxHistoryIndex = computed(() => Math.max(0, historyData.bg.length - 1))

    // 图表配置
    const simulationDurationHours = 24 // 持续时间24小时

    // 开始时间
    const simulationStartTime = ref(new Date())
    const simulationTimeOffsetMs = ref(null)
    const connectionStatus = ref('connecting') // 'connecting', 'connected', 'disconnected'
    const dbConnectionStatus = ref('disconnected') // 数据库连接状态（由后端返回）
    const tcpConnectionStatus = ref('disconnected') // 树莓派TCP连接状态：'connecting', 'connected', 'disconnected'
    const dataSaveStatus = ref('自动保存') // 数据保存状态

    // 图表引用
    const bgCgmChart = ref(null)
    const choCobChart = ref(null)
    const insulinIobChart = ref(null)

    // 图表实例
    let bgCgmChartInstance = null
    let choCobChartInstance = null
    let insulinIobChartInstance = null

    // 初始化24小时时间轴
    const initTimeAxis = () => {
      if (!simulationStartTime.value) return

      const startTime = simulationStartTime.value
      const endTime = new Date(startTime.getTime() + simulationDurationHours * 60 * 60 * 1000)

      // 更新所有图表的xAxis范围
      const timeAxisOption = {
        xAxis: {
          min: startTime.getTime(),
          max: endTime.getTime()
        }
      }

      if (bgCgmChartInstance) bgCgmChartInstance.setOption(timeAxisOption, { notMerge: false, lazyUpdate: true })
      if (choCobChartInstance) choCobChartInstance.setOption(timeAxisOption, { notMerge: false, lazyUpdate: true })
      if (insulinIobChartInstance) insulinIobChartInstance.setOption(timeAxisOption, { notMerge: false, lazyUpdate: true })
      if (motorChartInstance) motorChartInstance.setOption(timeAxisOption, { notMerge: false, lazyUpdate: true })
    }

    // 处理导航
    const handleNavigate = (routeName) => {
      console.log('导航到:', routeName)
    }

    // 处理设置
    const handleOpenSettings = () => {
      console.log('打开设置')
    }

    // 切换编辑模式
    const toggleEdit = () => {
      if (!isEditing.value) {
        // 进入编辑模式，复制当前数据到编辑表单
        Object.assign(editForm, patientInfo)
      }
      isEditing.value = !isEditing.value
    }

    // 保存患者信息
    const savePatientInfo = async () => {
      try {
        // 调用API保存患者信息
        await patientsAPI.updatePatient(patientInfo.id, editForm)

        // 更新本地数据
        Object.assign(patientInfo, editForm)

        // 退出编辑模式
        isEditing.value = false

        ElMessage.success('患者信息保存成功')
      } catch (error) {
        ElMessage.error('保存失败：' + (error.message || '未知错误'))
      }
    }

    // 监听PWM变化并更新图表
    const updateMotorChart = () => {
      const now = hardwareData.timestamp || new Date().getTime()
      const pwm = hardwareData.pwmDuty

      // 1. 更新 PWM 数据
      pwmDataSeries.push([now, pwm])

      // 2. 使用下位机返回的实际推注量
      const currentDelivery = hardwareData.actualDelivery || 0
      actualDeliverySeries.push([now, currentDelivery])

      if (motorChartInstance && showPwmChart.value) {
        motorChartInstance.setOption({
          series: [
            { data: pwmDataSeries },
            { data: actualDeliverySeries }
          ]
        })
      }
    }

    // 启动WebSocket连接
    const startBaseDataConnection = () => {
      // 定义状态回调
      const onStatus = (status) => {
        connectionStatus.value = status
      }

      // 连接并传入回调
      baseDataWS.connect(null, onStatus)

      // 缓冲队列
      const dataBuffer = []
      let updateTimer = null
      let shouldUpdateMotorChart = false

      // 批量更新图表函数
      const flushBufferToCharts = () => {
        // 优先更新电机图表
        if (shouldUpdateMotorChart) {
          updateMotorChart()
          shouldUpdateMotorChart = false
        }

        if (dataBuffer.length === 0) return

        // 1. 批量处理数据
        const batchSize = dataBuffer.length
        const lastData = dataBuffer[batchSize - 1] // 取最新一条用于状态判断

        // 临时数组用于批量push，减少响应式触发次数
        const newBg = [], newCgm = [], newCho = [], newCob = [], newInsulin = [], newIob = []

        let maxBgCgm = 0
        let maxCho = 0
        let maxCob = 0
        let maxInsulin = 0
        let maxIob = 0

        dataBuffer.forEach(item => {
          const { timestampMs, newData } = item
          newBg.push([timestampMs, newData.bg])
          newCgm.push([timestampMs, newData.cgm])
          newCho.push([timestampMs, newData.cho])
          newCob.push([timestampMs, newData.cob])
          newInsulin.push([timestampMs, newData.insulin])
          newIob.push([timestampMs, newData.iob])

          // 计算最大值用于Y轴调整
          maxBgCgm = Math.max(maxBgCgm, newData.bg || 0, newData.cgm || 0)
          maxCho = Math.max(maxCho, newData.cho || 0)
          maxCob = Math.max(maxCob, newData.cob || 0)
          maxInsulin = Math.max(maxInsulin, newData.insulin || 0)
          maxIob = Math.max(maxIob, newData.iob || 0)
        })

        // 2. 更新响应式数据 (Vue 3 Proxy 性能较好，但批量push仍优于逐个push)
        baseData.bg.push(...newBg)
        baseData.cgm.push(...newCgm)
        baseData.cho.push(...newCho)
        baseData.cob.push(...newCob)
        baseData.insulin.push(...newInsulin)
        baseData.iob.push(...newIob)

        // 清空缓冲
        dataBuffer.length = 0

        // 3. 滚动逻辑 (仅检查最新时间点)
        const lastTimestampMs = lastData.timestampMs
        if (simulationStartTime.value) {
          const startTime = simulationStartTime.value.getTime()
          const durationMs = simulationDurationHours * 60 * 60 * 1000
          const endTime = startTime + durationMs

          if (lastTimestampMs > endTime) {
            const newEnd = lastTimestampMs
            const newStart = newEnd - durationMs
            const axisOption = { xAxis: { min: newStart, max: newEnd } }

            // 统一更新X轴
            if (bgCgmChartInstance) bgCgmChartInstance.setOption(axisOption, { lazyUpdate: true })
            if (choCobChartInstance) choCobChartInstance.setOption(axisOption, { lazyUpdate: true })
            if (insulinIobChartInstance) insulinIobChartInstance.setOption(axisOption, { lazyUpdate: true })
            if (motorChartInstance) motorChartInstance.setOption(axisOption, { lazyUpdate: true })
          }
        }

        // 4. 更新图表 (使用 lazyUpdate: true 优化性能)
        if (bgCgmChartInstance) {
          const opt = bgCgmChartInstance.getOption()
          const yAxis = Array.isArray(opt.yAxis) ? opt.yAxis[0] : opt.yAxis
          let currentMax = yAxis.max || 200

          let newYAxisOption = null
          if (maxBgCgm > currentMax * 0.9) {
            let newMax = Math.ceil(maxBgCgm / 50) * 50
            newMax = Math.max(newMax, 200)
            if (newMax > currentMax) {
              newYAxisOption = [{ max: newMax }, { max: newMax }]
            }
          }

          const option = { series: [{ data: baseData.bg }, { data: baseData.cgm }] }
          if (newYAxisOption) option.yAxis = newYAxisOption
          bgCgmChartInstance.setOption(option, { lazyUpdate: true })
        }

        if (choCobChartInstance) {
          const opt = choCobChartInstance.getOption()
          const yAxisList = Array.isArray(opt.yAxis) ? opt.yAxis : [opt.yAxis]
          let currentChoMax = yAxisList[0].max || 20
          let currentCobMax = yAxisList[1] ? (yAxisList[1].max || 100) : 100
          let needUpdate = false

          let newChoMax = currentChoMax
          if (maxCho > currentChoMax * 0.9) {
            newChoMax = Math.ceil(maxCho / 10) * 10
            newChoMax = Math.max(newChoMax, 20)
            if (newChoMax > currentChoMax) needUpdate = true
          }

          let newCobMax = currentCobMax
          if (maxCob > currentCobMax * 0.9) {
            newCobMax = Math.ceil(maxCob / 10) * 10
            newCobMax = Math.max(newCobMax, 100)
            if (newCobMax > currentCobMax) needUpdate = true
          }

          const option = { series: [{ data: baseData.cho }, { data: baseData.cob }] }
          if (needUpdate) option.yAxis = [{ max: newChoMax }, { max: newCobMax }]
          choCobChartInstance.setOption(option, { lazyUpdate: true })
        }

        if (insulinIobChartInstance) {
          const opt = insulinIobChartInstance.getOption()
          const yAxisList = Array.isArray(opt.yAxis) ? opt.yAxis : [opt.yAxis]
          let currentInsulinMax = yAxisList[0].max || 2
          let currentIobMax = yAxisList[1] ? (yAxisList[1].max || 5) : 5
          let needUpdate = false

          let newInsulinMax = currentInsulinMax
          if (maxInsulin > currentInsulinMax * 0.9) {
            newInsulinMax = Math.ceil(maxInsulin * 2) / 2
            newInsulinMax = Math.max(newInsulinMax, 2)
            if (newInsulinMax > currentInsulinMax) needUpdate = true
          }

          let newIobMax = currentIobMax
          if (maxIob > currentIobMax * 0.9) {
            newIobMax = Math.ceil(maxIob)
            newIobMax = Math.max(newIobMax, 5)
            if (newIobMax > currentIobMax) needUpdate = true
          }

          const option = { series: [{ data: baseData.insulin }, { data: baseData.iob }] }
          if (needUpdate) option.yAxis = [{ max: newInsulinMax }, { max: newIobMax }]
          insulinIobChartInstance.setOption(option, { lazyUpdate: true })
        }
      }

      // 监听数据
      baseDataWS.onMessage((data) => {
        if (data.type === 'base_data') {
          // 处理实时数据
          const timestamp = parseLocalDateTime(data.timestamp) || new Date()
          const timestampMs = timestamp.getTime()

          const newData = {
            bg: toNumberOrNull(data.bg),
            cgm: toNumberOrNull(data.cgm),
            cho: toNumberOrNull(data.cho),
            cob: toNumberOrNull(data.cob),
            insulin: toNumberOrNull(data.insulin),
            iob: toNumberOrNull(data.iob)
          }

          // 将数据放入缓冲
          dataBuffer.push({ timestampMs, newData })

          // 如果没有定时器，启动一个
          if (!updateTimer) {
            updateTimer = requestAnimationFrame(() => {
              flushBufferToCharts()
              updateTimer = null
            })
          }

          // 更新连接状态
          if (data.db_status) dbConnectionStatus.value = data.db_status
          if (data.tcp_status) tcpConnectionStatus.value = data.tcp_status

        } else if (data.type === 'status_update') {
          // 更新状态信息
          dbConnectionStatus.value = data.db_status || 'disconnected'
          tcpConnectionStatus.value = data.tcp_status || 'disconnected'
          if (data.hardware_data) {
            Object.assign(hardwareData, data.hardware_data)
            hardwareData.timestamp = new Date().getTime() // 记录时间戳
            shouldUpdateMotorChart = true
            // 如果没有定时器，启动一个以确保图表更新
            if (!updateTimer) {
              updateTimer = requestAnimationFrame(() => {
                flushBufferToCharts()
                updateTimer = null
              })
            }
          }
        }
      })
    }

    // 保存历史数据
    const saveHistoryData = () => {
      historyData.bg = [...baseData.bg]
      historyData.cgm = [...baseData.cgm]
      historyData.cho = [...baseData.cho]
      historyData.cob = [...baseData.cob]
      historyData.insulin = [...baseData.insulin]
      historyData.iob = [...baseData.iob]
      historyData.timestamp = baseData.bg.map(([time]) => formatLocalDateTime(new Date(time)))
      historyMode.value = true
      console.log(`历史数据已保存，共 ${historyData.bg.length} 个数据点`)
    }

    // 滑块值改变
    const onHistorySliderChange = (value) => {
      if (!historyMode.value) return
      currentViewIndex.value = value
      updateChartsWithHistoryData(value)
    }

    // 选择日期
    const selectDay = (index) => {
      selectedDayIndex.value = index
      calculateDayRange(index)
      // 切换日期时，将视图定位到该日期的开始
      currentViewIndex.value = dayStartIndex.value
      updateChartsWithHistoryData(dayStartIndex.value)
    }

    // 计算选中日期的索引范围
    const calculateDayRange = (dayIndex) => {
      if (!historyData.bg.length) return

      const startTime = historyData.bg[0][0]
      const dayMs = 24 * 60 * 60 * 1000

      // 目标日期的开始和结束时间戳
      const targetStart = startTime + dayIndex * dayMs
      const targetEnd = targetStart + dayMs

      // 查找对应的索引范围
      let start = 0
      let end = historyData.bg.length - 1

      // 简单的线性查找，数据量大时可优化为二分查找
      for (let i = 0; i < historyData.bg.length; i++) {
        if (historyData.bg[i][0] >= targetStart) {
          start = i
          break
        }
      }

      for (let i = start; i < historyData.bg.length; i++) {
        if (historyData.bg[i][0] >= targetEnd) {
          end = i - 1
          break
        }
        end = i
      }

      dayStartIndex.value = start
      dayEndIndex.value = end
    }

    // 生成日期列表
    const generateHistoryDays = () => {
      if (!historyData.bg.length) {
        historyDays.value = []
        return
      }

      const startTime = new Date(historyData.bg[0][0])
      const endTime = new Date(historyData.bg[historyData.bg.length - 1][0])

      const days = []
      let current = new Date(startTime)
      current.setHours(0, 0, 0, 0)

      const endDay = new Date(endTime)
      endDay.setHours(0, 0, 0, 0)

      let dayCount = 1
      // 如果跨天了
      const timeDiff = endTime.getTime() - startTime.getTime()
      const dayDiff = Math.ceil(timeDiff / (24 * 60 * 60 * 1000))

      for (let i = 0; i < Math.max(dayDiff, 1); i++) {
        const d = new Date(startTime.getTime() + i * 24 * 60 * 60 * 1000)
        days.push(`第 ${i + 1} 天 (${d.getMonth() + 1}/${d.getDate()})`)
      }

      historyDays.value = days
      selectedDayIndex.value = 0
      calculateDayRange(0)
    }

    // 更新图表显示历史数据
    const DAY_WINDOW_MS = 24 * 60 * 60 * 1000 // 历史窗口固定为1天

    const updateChartsWithHistoryData = (index) => {
      const total = historyData.bg.length
      if (!total) return

      const clampedIndex = Math.min(Math.max(index, 0), total - 1)
      // currentViewIndex.value = clampedIndex // 移除这行，避免循环触发

      const selectedTime = historyData.bg[clampedIndex][0]

      // 窗口逻辑：显示选中点所在的24小时窗口，或者以选中点为中心的窗口
      // 这里修改为：显示当前选中日期（24小时）的数据
      // 如果使用了日期选择器，则窗口固定为该日期

      let windowStart, windowEnd

      if (historyDays.value.length > 0) {
        const startTime = historyData.bg[0][0]
        windowStart = startTime + selectedDayIndex.value * DAY_WINDOW_MS
        windowEnd = windowStart + DAY_WINDOW_MS
      } else {
        // 默认逻辑
        windowStart = selectedTime - DAY_WINDOW_MS / 2
        windowEnd = selectedTime + DAY_WINDOW_MS / 2
      }

      const filterByWindow = (series) => series.filter(([time]) => time >= windowStart && time <= windowEnd)

      const bgWindow = filterByWindow(historyData.bg)
      const cgmWindow = filterByWindow(historyData.cgm)
      const choWindow = filterByWindow(historyData.cho)
      const cobWindow = filterByWindow(historyData.cob)
      const insulinWindow = filterByWindow(historyData.insulin)
      const iobWindow = filterByWindow(historyData.iob)

      if (bgCgmChartInstance) {
        const maxValue = Math.max(...bgWindow.map(([, v]) => v ?? 0), ...cgmWindow.map(([, v]) => v ?? 0), 200)
        // 使用更大的基数进行向上取整，减少Y轴频繁变化
        const newMax = Math.max(Math.ceil(maxValue / 50) * 50, 500)
        bgCgmChartInstance.setOption({
          animation: false,  // 全局禁用动画
          xAxis: { min: windowStart, max: windowEnd },
          yAxis: {
            max: newMax,
            min: 0,
            animation: false  // 禁用Y轴动画，避免漂移效果
          },
          series: [
            { data: bgWindow, animation: false },
            { data: cgmWindow, animation: false }
          ]
        }, { notMerge: false, lazyUpdate: false })  // 改为 false，立即更新避免抖动
      }

      if (choCobChartInstance) {
        // CHO 和 COB 分别计算最大值，使用独立的Y轴范围
        const choMaxValue = Math.max(...choWindow.map(([, v]) => v ?? 0), 10)
        const choNewMax = Math.max(Math.ceil(choMaxValue / 10) * 10, 20)  // 最小20g
        const cobMaxValue = Math.max(...cobWindow.map(([, v]) => v ?? 0), 10)
        const cobNewMax = Math.max(Math.ceil(cobMaxValue / 10) * 10, 100)  // 最小100g
        choCobChartInstance.setOption({
          animation: false,  // 全局禁用动画
          xAxis: { min: windowStart, max: windowEnd },
          yAxis: [
            {
              max: choNewMax,
              min: 0,
              animation: false  // 禁用动画
            },
            {
              max: cobNewMax,
              min: 0,
              animation: false  // 禁用动画
            }
          ],
          series: [
            { data: choWindow, animation: false },
            { data: cobWindow, animation: false }
          ]
        }, { notMerge: false, lazyUpdate: false })  // 改为 false，立即更新避免抖动
      }

      if (insulinIobChartInstance) {
        // INSULIN 和 IOB 分别计算最大值，使用独立的Y轴范围
        const insulinMaxValue = Math.max(...insulinWindow.map(([, v]) => v ?? 0), 0)
        const iobMaxValue = Math.max(...iobWindow.map(([, v]) => v ?? 0), 0)

        // 获取当前图表配置的 max 值
        const currentOption = insulinIobChartInstance.getOption()
        const currentInsulinMax = currentOption.yAxis[0].max || 2
        const currentIobMax = currentOption.yAxis[1].max || 5

        // 分别计算新的 max 值：加 30% 缓冲区，向上取整
        // INSULIN: 最小 2U，适合小剂量显示
        // IOB: 最小 5U，适合累积量显示
        let insulinNewMax = currentInsulinMax
        let iobNewMax = currentIobMax

        // 只有当数据超过当前 max 的 80% 时才调整（避免频繁变化）
        if (insulinMaxValue > currentInsulinMax * 0.8) {
          // INSULIN 使用更精细的刻度（0.5为单位）
          insulinNewMax = Math.max(Math.ceil(insulinMaxValue * 1.3 * 2) / 2, 2)
        }
        if (iobMaxValue > currentIobMax * 0.8) {
          // IOB 使用整数刻度
          iobNewMax = Math.max(Math.ceil(iobMaxValue * 1.3), 5)
        }

        insulinIobChartInstance.setOption({
          animation: false,  // 全局禁用动画
          xAxis: { min: windowStart, max: windowEnd },
          yAxis: [
            {
              max: insulinNewMax,
              min: 0,
              splitNumber: 5,
              scale: false,  // 不自动缩放
              animation: false  // 禁用动画
            },
            {
              max: iobNewMax,
              min: 0,
              splitNumber: 5,
              scale: false,  // 不自动缩放
              animation: false  // 禁用动画
            }
          ],
          series: [
            { data: insulinWindow, animation: false },
            { data: iobWindow, animation: false }
          ]
        }, { notMerge: false, lazyUpdate: false })  // 改为 false，立即更新避免抖动
      }
    }

    // 退出历史模式
    const exitHistoryMode = () => {
      if (fromHistory.value) {
        router.push('/simulations-list')
      } else {
        historyMode.value = false
        currentViewIndex.value = 0
        // 清空图表数据
        baseData.bg = []
        baseData.cgm = []
        baseData.cho = []
        baseData.cob = []
        baseData.insulin = []
        baseData.iob = []
        if (bgCgmChartInstance) bgCgmChartInstance.setOption(getBgCgmChartOption())
        if (choCobChartInstance) choCobChartInstance.setOption(getChoCobChartOption())
        if (insulinIobChartInstance) insulinIobChartInstance.setOption(getInsulinIobChartOption())
        ElMessage.info('已退出历史查看模式')
      }
    }

    // 删除仿真
    const handleDeleteSimulation = () => {
      if (!currentSimulationId.value) return

      ElMessageBox.confirm(
        '确定要删除当前仿真记录吗？此操作不可恢复。',
        '警告',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning',
        }
      ).then(async () => {
        try {
          await baseDataWS.deleteSimulation(currentSimulationId.value)
          ElMessage.success('删除成功')
          router.push('/simulations-list')
        } catch (error) {
          ElMessage.error('删除失败: ' + error.message)
        }
      }).catch(() => { })
    }

    // 加载历史仿真数据
    const loadHistorySimulation = async (simulationId) => {
      loadingHistory.value = true
      fromHistory.value = true
      currentSimulationId.value = simulationId

      try {
        const result = await baseDataWS.getSimulationData(simulationId)

        // 加载元数据
        if (result.info) {
          // 填充患者信息
          if (result.info.patient_id) {
            patientInfo.id = result.info.patient_id
            patientInfo.name = result.info.patient_name || ''
            patientInfo.age = result.info.patient_type || ''
            patientInfo.gender = result.info.patient_gender || ''
            patientInfo.bloodType = result.info.patient_blood_type || ''
          }

          // 填充参数设置
          paramSettings.sensor = result.info.sensor || 'Dexcom'
          paramSettings.pump = result.info.pump || 'Insulet'
          paramSettings.controller = result.info.controller || 'pid'
          paramSettings.simulateHours = result.info.simulate_hours || 1

          if (result.info.start_time) {
            const startDate = parseLocalDateTime(result.info.start_time)
            if (startDate) {
              // paramSettings.startDateTime = formatLocalDateTime(startDate)
            }
          }
        }

        // 加载数据
        if (result.data && result.data.length > 0) {
          const parsedRows = result.data
            .map((row) => {
              const timestamp = parseLocalDateTime(row.time)
              if (!timestamp) {
                return null
              }

              const timestampMs = timestamp.getTime()
              return {
                timestampMs,
                timestampLabel: formatLocalDateTime(timestamp),
                bg: toNumberOrNull(row.bg),
                cgm: toNumberOrNull(row.cgm),
                cho: toNumberOrNull(row.cho, 0),
                cob: toNumberOrNull(row.cob, 0),
                insulin: toNumberOrNull(row.insulin, 0),
                iob: toNumberOrNull(row.iob, 0)
              }
            })
            .filter(Boolean)

          if (parsedRows.length === 0) {
            throw new Error('历史数据时间格式无效或为空')
          }

          const bgSeries = parsedRows.map((item) => [item.timestampMs, item.bg])
          const cgmSeries = parsedRows.map((item) => [item.timestampMs, item.cgm])
          const choSeries = parsedRows.map((item) => [item.timestampMs, item.cho])
          const cobSeries = parsedRows.map((item) => [item.timestampMs, item.cob])
          const insulinSeries = parsedRows.map((item) => [item.timestampMs, item.insulin])
          const iobSeries = parsedRows.map((item) => [item.timestampMs, item.iob])
          const timestampLabels = parsedRows.map((item) => item.timestampLabel)

          replaceReactiveArray(historyData.bg, bgSeries)
          replaceReactiveArray(historyData.cgm, cgmSeries)
          replaceReactiveArray(historyData.cho, choSeries)
          replaceReactiveArray(historyData.cob, cobSeries)
          replaceReactiveArray(historyData.insulin, insulinSeries)
          replaceReactiveArray(historyData.iob, iobSeries)
          replaceReactiveArray(historyData.timestamp, timestampLabels)

          replaceReactiveArray(baseData.bg, bgSeries)
          replaceReactiveArray(baseData.cgm, cgmSeries)
          replaceReactiveArray(baseData.cho, choSeries)
          replaceReactiveArray(baseData.cob, cobSeries)
          replaceReactiveArray(baseData.insulin, insulinSeries)
          replaceReactiveArray(baseData.iob, iobSeries)

          simulationStartTime.value = parseLocalDateTime(result.info?.start_time) || new Date(parsedRows[0].timestampMs)
          initTimeAxis()

          historyMode.value = true
          dataSaveStatus.value = '历史数据查看'
          const lastIndex = Math.max(parsedRows.length - 1, 0)

          // 生成日期列表
          generateHistoryDays()

          await nextTick()
          updateChartsWithHistoryData(lastIndex)
        } else {
          replaceReactiveArray(historyData.bg, [])
          replaceReactiveArray(historyData.cgm, [])
          replaceReactiveArray(historyData.cho, [])
          replaceReactiveArray(historyData.cob, [])
          replaceReactiveArray(historyData.insulin, [])
          replaceReactiveArray(historyData.iob, [])
          replaceReactiveArray(historyData.timestamp, [])
          replaceReactiveArray(baseData.bg, [])
          replaceReactiveArray(baseData.cgm, [])
          replaceReactiveArray(baseData.cho, [])
          replaceReactiveArray(baseData.cob, [])
          replaceReactiveArray(baseData.insulin, [])
          replaceReactiveArray(baseData.iob, [])
          currentViewIndex.value = 0
          historyMode.value = false
        }

        const pointCount = result.data ? result.data.length : 0
        ElMessage.success(`历史仿真数据加载成功（${pointCount} 个数据点）`)
      } catch (error) {
        ElMessage.error('加载历史数据失败: ' + error.message)
        console.error('加载历史仿真失败:', error)
      } finally {
        loadingHistory.value = false
      }
    }

    // 仿真状态文本
    const simulationStatusText = computed(() => {
      if (isSimulationRunning.value) return '监控中...'
      if (baseData.bg.length === 0) return '等待数据'
      return '已连接'
    })

    // 格式化时间滑块提示
    const formatTime = (val) => {
      const hours = Math.floor(val)
      const minutes = Math.round((val - hours) * 60)
      return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`
    }

    // 时间范围变化处理
    const onTimeRangeChange = (val) => {
      // 这里可以添加筛选逻辑，目前仅更新UI
      console.log('Time range changed:', val)
    }

    // 刷新数据
    const refreshData = () => {
      // 重新加载数据
      loadOtherData()
      // 如果有其他刷新逻辑可以在这里添加
    }

    // 切换图例显示
    const toggleSeries = (chartName, seriesName) => {
      let instance = null
      if (chartName === 'bgCgm') instance = bgCgmChartInstance
      else if (chartName === 'choCob') instance = choCobChartInstance
      else if (chartName === 'insulinIob') instance = insulinIobChartInstance

      if (instance) {
        instance.dispatchAction({
          type: 'legendToggleSelect',
          name: seriesName
        })
      }
    }

    // BG & CGM 图表配置
    const getBgCgmChartOption = () => ({
      animation: false,
      backgroundColor: 'transparent',
      title: { show: false },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        borderColor: '#ccc',
        textStyle: { color: '#333' },
        axisPointer: { type: 'cross', label: { backgroundColor: '#6a7985' } },
        formatter: function (params) {
          if (!params || params.length === 0 || !params[0].name) return '暂无数据'
          const timestamp = params[0].name
          let result = `<div style="font-weight:bold;margin-bottom:4px;color:#666">${timestamp}</div>`
          params.forEach(param => {
            const valueText = param.value !== null && param.value !== undefined ? param.value.toFixed(2) : 'N/A'
            const color = param.color
            result += `<span style="display:inline-block;margin-right:5px;border-radius:10px;width:9px;height:9px;background-color:${color}"></span>${param.seriesName}: <span style="color:#333;font-weight:bold">${valueText}</span> mg/dL<br/>`
          })
          return result
        }
      },
      legend: { show: false },
      grid: { left: '1%', right: '1%', bottom: '1%', top: 35, containLabel: true },
      xAxis: {
        type: 'time',
        boundaryGap: false,
        axisLabel: {
          show: true,
          color: '#666',
          hideOverlap: true,
          formatter: (value) => {
            const date = new Date(value)
            const hour = date.getHours()
            const minute = date.getMinutes()
            if (hour === 0 && minute === 0) return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
            return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
          }
        },
        axisTick: { alignWithLabel: true, lineStyle: { color: '#ccc' } },
        axisLine: { lineStyle: { color: '#ccc' } },
        splitLine: { show: true, lineStyle: { color: '#eee', type: 'dashed' } },
        min: simulationStartTime.value ? simulationStartTime.value.getTime() : undefined,
        max: simulationStartTime.value ? simulationStartTime.value.getTime() + simulationDurationHours * 60 * 60 * 1000 : undefined
      },
      yAxis: [
        {
          type: 'value',
          name: 'mg/dL',
          position: 'left',
          nameTextStyle: { color: '#666' },
          scale: false,
          min: 0,
          max: 200,
          minInterval: 20,
          splitNumber: 5,
          animation: false,
          axisLabel: { color: '#666' },
          axisLine: { show: true, lineStyle: { color: '#ccc' } },
          splitLine: { show: true, lineStyle: { color: '#eee', type: 'dashed' } }
        },
        {
          type: 'value',
          position: 'right',
          scale: false,
          min: 0,
          max: 200,
          axisLine: { show: true, lineStyle: { color: '#ccc' } },
          axisLabel: { show: false },
          axisTick: { show: false },
          splitLine: { show: false }
        }
      ],
      series: [
        {
          name: 'BG',
          type: 'line',
          data: [],
          color: '#3498db',
          smooth: true,
          showSymbol: false,
          animation: false,
          lineStyle: { width: 2 },
          markLine: {
            silent: true,
            symbol: 'none',
            lineStyle: { type: 'dashed', width: 1 },
            data: [
              ...(() => {
                const lines = []
                if (simulationStartTime.value) {
                  const startTime = new Date(simulationStartTime.value)
                  const endTime = new Date(startTime.getTime() + simulationDurationHours * 60 * 60 * 1000)
                  let currentDay = new Date(startTime)
                  currentDay.setHours(0, 0, 0, 0)
                  if (currentDay.getTime() < startTime.getTime()) currentDay.setDate(currentDay.getDate() + 1)
                  while (currentDay.getTime() <= endTime.getTime()) {
                    lines.push({
                      xAxis: currentDay.getTime(),
                      lineStyle: { color: '#909399', type: 'dashed', width: 1 },
                      label: { show: false }
                    })
                    currentDay.setDate(currentDay.getDate() + 1)
                  }
                }
                return lines
              })(),
              { yAxis: 180, lineStyle: { color: '#ff6b6b', opacity: 0.8 }, label: { show: false, position: 'end', formatter: '高 (180)', color: '#ff6b6b', fontSize: 10 } },
              { yAxis: 140, lineStyle: { color: '#51cf66', opacity: 0.8 }, label: { show: false, position: 'end', formatter: '目标 (140)', color: '#51cf66', fontSize: 10 } },
              { yAxis: 30, lineStyle: { color: '#ff6b6b', opacity: 0.8 }, label: { show: false, position: 'end', formatter: '低 (30)', color: '#ff6b6b', fontSize: 10 } }
            ]
          }
        },
        {
          name: 'CGM',
          type: 'line',
          data: [],
          color: '#f39c12',
          smooth: true,
          showSymbol: false,
          animation: false,
          lineStyle: { width: 2 }
        }
      ],
      markLine: {
        silent: true,
        symbol: 'none',
        lineStyle: { type: 'dashed', width: 1 },
        data: [
          ...(() => {
            const lines = []
            if (simulationStartTime.value) {
              const startTime = new Date(simulationStartTime.value)
              const endTime = new Date(startTime.getTime() + simulationDurationHours * 60 * 60 * 1000)
              let currentDay = new Date(startTime)
              currentDay.setHours(0, 0, 0, 0)
              if (currentDay.getTime() < startTime.getTime()) currentDay.setDate(currentDay.getDate() + 1)
              while (currentDay.getTime() <= endTime.getTime()) {
                lines.push({ xAxis: currentDay.getTime(), lineStyle: { color: '#ccc', type: 'dashed', width: 1 } })
                currentDay.setDate(currentDay.getDate() + 1)
              }
            }
            return lines
          })(),
          { yAxis: 180, lineStyle: { color: '#ff6b6b', opacity: 0.8 }, label: { show: true, position: 'end', formatter: '高 (180)', color: '#ff6b6b', fontSize: 10 } },
          { yAxis: 140, lineStyle: { color: '#51cf66', opacity: 0.8 }, label: { show: true, position: 'end', formatter: '目标 (140)', color: '#51cf66', fontSize: 10 } },
          { yAxis: 30, lineStyle: { color: '#ffd43b', opacity: 0.8 }, label: { show: true, position: 'end', formatter: '低 (30)', color: '#ffd43b', fontSize: 10 } }
        ]
      }
    })

    // CHO & COB 图表配置
    const getChoCobChartOption = () => ({
      animation: false,
      backgroundColor: 'transparent',
      title: { show: false },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        borderColor: '#ccc',
        textStyle: { color: '#333' },
        axisPointer: { type: 'cross', label: { backgroundColor: '#6a7985' }, snap: true, triggerTooltip: true },
        formatter: function (params) {
          if (!params || params.length === 0 || !params[0].name) return '暂无数据'
          const timestamp = params[0].name
          let result = `<div style="font-weight:bold;margin-bottom:4px;color:#666">${timestamp}</div>`
          params.forEach(param => {
            const valueText = param.value !== null && param.value !== undefined ? param.value.toFixed(2) : 'N/A'
            const color = param.color
            result += `<span style="display:inline-block;margin-right:5px;border-radius:10px;width:9px;height:9px;background-color:${color}"></span>${param.seriesName}: <span style="color:#333;font-weight:bold">${valueText}</span> g<br/>`
          })
          return result
        }
      },
      axisPointer: { link: [{ xAxisIndex: 'all' }], snap: true },
      legend: { show: false },
      grid: { left: '1.5%', right: '1%', bottom: "5%", top: 32, containLabel: true },
      xAxis: {
        type: 'time',
        boundaryGap: false,
        axisLabel: {
          show: false, // 恢复显示X轴标签
          color: '#666',
          formatter: (value) => {
            const date = new Date(value)
            const hour = date.getHours()
            const minute = date.getMinutes()
            if (hour === 0 && minute === 0) return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
            return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
          }
        },
        axisTick: { show: true, alignWithLabel: true, lineStyle: { color: '#ccc' } }, // 恢复刻度
        axisLine: { show: true, lineStyle: { color: '#ccc' } }, // 恢复轴线
        splitLine: { show: true, lineStyle: { color: '#eee', type: 'dashed' } },
        min: simulationStartTime.value ? simulationStartTime.value.getTime() : undefined,
        max: simulationStartTime.value ? simulationStartTime.value.getTime() + simulationDurationHours * 60 * 60 * 1000 : undefined
      },
      yAxis: [
        {
          type: 'value',
          name: 'CHO (g)',
          position: 'left',
          nameTextStyle: { color: '#666' },
          scale: false,
          min: 0,
          max: 20,
          minInterval: 5,
          splitNumber: 5,
          animation: false,
          axisLabel: { formatter: '{value} g', color: '#666' },
          axisLine: { show: true, lineStyle: { color: '#ccc' } },
          splitLine: { show: true, lineStyle: { color: '#eee', type: 'dashed' } }
        },
        {
          type: 'value',
          name: 'COB (g)',
          position: 'right',
          nameTextStyle: { color: '#666' },
          scale: false,
          min: 0,
          max: 100,
          minInterval: 5,
          splitNumber: 5,
          animation: false,
          axisLabel: { formatter: '{value} g', color: '#666' },
          axisLine: { show: true, lineStyle: { color: '#ccc' } },
          splitLine: { show: false }
        }
      ],
      series: [
        {
          name: 'CHO',
          type: 'line',
          data: [],
          color: '#3498db',
          smooth: true,
          showSymbol: false,
          animation: false,
          lineStyle: { width: 2 },
          yAxisIndex: 0,
          markLine: {
            silent: true,
            symbol: 'none',
            lineStyle: { type: 'dashed', width: 1 },
            data: (() => {
              const lines = []
              if (simulationStartTime.value) {
                const startTime = new Date(simulationStartTime.value)
                const endTime = new Date(startTime.getTime() + simulationDurationHours * 60 * 60 * 1000)
                let currentDay = new Date(startTime)
                currentDay.setHours(0, 0, 0, 0)
                if (currentDay.getTime() < startTime.getTime()) currentDay.setDate(currentDay.getDate() + 1)
                while (currentDay.getTime() <= endTime.getTime()) {
                  lines.push({
                    xAxis: currentDay.getTime(),
                    lineStyle: { color: '#909399', type: 'dashed', width: 1 },
                    label: { show: false }
                  })
                  currentDay.setDate(currentDay.getDate() + 1)
                }
              }
              return lines
            })()
          }
        },
        {
          name: 'COB',
          type: 'line',
          data: [],
          color: '#9b59b6',
          smooth: true,
          showSymbol: false,
          animation: false,
          lineStyle: { width: 2, type: 'dashed' },
          yAxisIndex: 1
        }
      ]
    })

    // INSULIN & IOB 图表配置
    const getInsulinIobChartOption = () => ({
      animation: false,
      backgroundColor: 'transparent',
      title: { show: false },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        borderColor: '#ccc',
        textStyle: { color: '#333' },
        axisPointer: { type: 'cross', label: { backgroundColor: '#6a7985' }, snap: true, triggerTooltip: true },
        formatter: function (params) {
          if (!params || params.length === 0 || !params[0].name) return '暂无数据'
          const timestamp = params[0].name
          let result = `<div style="font-weight:bold;margin-bottom:4px;color:#666">${timestamp}</div>`
          params.forEach(param => {
            const valueText = param.value !== null && param.value !== undefined ? param.value.toFixed(3) : 'N/A'
            const color = param.color
            result += `<span style="display:inline-block;margin-right:5px;border-radius:10px;width:9px;height:9px;background-color:${color}"></span>${param.seriesName}: <span style="color:#333;font-weight:bold">${valueText}</span> U<br/>`
          })
          return result
        }
      },
      axisPointer: { link: [{ xAxisIndex: 'all' }], snap: true },
      legend: { show: false },
      grid: { left: '1%', right: '3%', bottom: 0, top: 32, containLabel: true },
      xAxis: {
        type: 'time',
        boundaryGap: false,
        axisLabel: {
          color: '#666',
          formatter: (value) => {
            const date = new Date(value)
            const hour = date.getHours()
            const minute = date.getMinutes()
            if (hour === 0 && minute === 0) return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
            return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
          }
        },
        axisTick: { alignWithLabel: true, lineStyle: { color: '#ccc' } },
        axisLine: { lineStyle: { color: '#ccc' } },
        splitLine: { show: true, lineStyle: { color: '#eee', type: 'dashed' } },
        min: simulationStartTime.value ? simulationStartTime.value.getTime() : undefined,
        max: simulationStartTime.value ? simulationStartTime.value.getTime() + simulationDurationHours * 60 * 60 * 1000 : undefined
      },
      yAxis: [
        {
          type: 'value',
          name: 'INSULIN (U)',
          position: 'left',
          nameTextStyle: { color: '#666' },
          scale: false,
          min: 0,
          max: 2,
          minInterval: 0.1,
          splitNumber: 5,
          animation: false,
          axisLabel: { formatter: '{value} U', color: '#666' },
          axisLine: { show: true, lineStyle: { color: '#ccc' } },
          splitLine: { show: true, lineStyle: { color: '#eee', type: 'dashed' } }
        },
        {
          type: 'value',
          name: 'IOB (U)',
          position: 'right',
          nameTextStyle: { color: '#666' },
          scale: false,
          min: 0,
          max: 5,
          minInterval: 0.1,
          splitNumber: 5,
          animation: false,
          axisLabel: { formatter: '{value} U', color: '#666' },
          axisLine: { show: true, lineStyle: { color: '#ccc' } },
          splitLine: { show: false }
        }
      ],
      series: [
        {
          name: 'INSULIN',
          type: 'line',
          data: [],
          color: '#2ecc71',
          smooth: true,
          showSymbol: false,
          animation: false,
          connectNulls: true,
          lineStyle: { width: 2 },
          yAxisIndex: 0,
          markLine: {
            silent: true,
            symbol: 'none',
            lineStyle: { type: 'dashed', width: 1 },
            data: (() => {
              const lines = []
              if (simulationStartTime.value) {
                const startTime = new Date(simulationStartTime.value)
                const endTime = new Date(startTime.getTime() + simulationDurationHours * 60 * 60 * 1000)
                let currentDay = new Date(startTime)
                currentDay.setHours(0, 0, 0, 0)
                if (currentDay.getTime() < startTime.getTime()) currentDay.setDate(currentDay.getDate() + 1)
                while (currentDay.getTime() <= endTime.getTime()) {
                  lines.push({
                    xAxis: currentDay.getTime(),
                    lineStyle: { color: '#909399', type: 'dashed', width: 1 },
                    label: { show: false }
                  })
                  currentDay.setDate(currentDay.getDate() + 1)
                }
              }
              return lines
            })()
          }
        },
        {
          name: 'IOB',
          type: 'line',
          data: [],
          color: '#e67e22',
          smooth: true,
          showSymbol: false,
          animation: false,
          connectNulls: true,
          lineStyle: { width: 2, type: 'dashed' },
          yAxisIndex: 1
        }
      ],
      markLine: {
        silent: true,
        symbol: 'none',
        lineStyle: { type: 'dashed', width: 1 },
        data: [
          ...(() => {
            const lines = []
            if (simulationStartTime.value) {
              const startTime = new Date(simulationStartTime.value)
              const endTime = new Date(startTime.getTime() + simulationDurationHours * 60 * 60 * 1000)
              let currentDay = new Date(startTime)
              currentDay.setHours(0, 0, 0, 0)
              if (currentDay.getTime() < startTime.getTime()) currentDay.setDate(currentDay.getDate() + 1)
              while (currentDay.getTime() <= endTime.getTime()) {
                lines.push({
                  xAxis: currentDay.getTime(),
                  lineStyle: { color: '#909399', type: 'dashed', width: 1 },
                  label: { show: false }
                })
                currentDay.setDate(currentDay.getDate() + 1)
              }
            }
            return lines
          })()
        ]
      }
    })

    const getPwmChartOption = () => ({
      animation: false,
      backgroundColor: 'transparent',
      grid: { left: '2%', right: '4%', top: '15%', bottom: '2%', containLabel: true },
      legend: {
        show: false
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        borderColor: '#ccc',
        textStyle: { color: '#333' },
        formatter: function (params) {
          if (!params || params.length === 0) return ''
          const date = new Date(params[0].value[0])
          const timeStr = `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`
          let result = `<div style="font-weight:bold;margin-bottom:4px;color:#666">${timeStr}</div>`
          params.forEach(param => {
            const color = param.color
            const name = param.seriesName
            const value = param.value[1]
            const unit = name === 'PWM Duty' ? '%' : ' U'
            result += `<div style="display:flex;align-items:center;gap:5px;">
              <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color}"></span>
              <span style="font-size:12px">${name}: </span>
              <span style="font-weight:bold;margin-left:auto">${value}${unit}</span>
            </div>`
          })
          return result
        }
      },
      xAxis: {
        type: 'time',
        boundaryGap: false,
        axisLabel: {
          color: '#666',
          formatter: (value) => {
            const date = new Date(value)
            const hour = date.getHours()
            const minute = date.getMinutes()
            if (hour === 0 && minute === 0) return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
            return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
          }
        },
        axisTick: { alignWithLabel: true, lineStyle: { color: '#ccc' } },
        axisLine: { lineStyle: { color: '#ccc' } },
        splitLine: { show: true, lineStyle: { color: '#eee', type: 'dashed' } },
        min: simulationStartTime.value ? simulationStartTime.value.getTime() : undefined,
        max: simulationStartTime.value ? simulationStartTime.value.getTime() + simulationDurationHours * 60 * 60 * 1000 : undefined
      },
      yAxis: [
        {
          type: 'value',
          name: 'PWM (%)',
          min: 0,
          max: 100,
          nameTextStyle: { color: '#e6a23c', padding: [0, 0, 0, -10], fontSize: 10 },
          splitLine: { show: true, lineStyle: { type: 'dashed', color: '#eee' } },
          axisLabel: { fontSize: 10, color: '#e6a23c' }
        },
        {
          type: 'value',
          name: 'Delivery (U)',
          min: 0,
          max: 5, // 假设最大推注量，可动态调整
          nameTextStyle: { color: '#67c23a', padding: [0, 0, 0, 10], fontSize: 10 },
          splitLine: { show: false },
          axisLabel: { fontSize: 10, color: '#67c23a' }
        }
      ],
      series: [
        {
          name: 'PWM Duty',
          type: 'line',
          data: [],
          showSymbol: false,
          smooth: false,
          symbol: 'circle',
          symbolSize: 6,
          itemStyle: {
            color: '#e6a23c',
            borderWidth: 2,
            borderColor: '#fff'
          },
          lineStyle: { width: 2, color: '#e6a23c' },
          markLine: {
            silent: true,
            symbol: 'none',
            lineStyle: { type: 'dashed', width: 1 },
            data: [
              ...(() => {
                const lines = []
                if (simulationStartTime.value) {
                  const startTime = new Date(simulationStartTime.value)
                  const endTime = new Date(startTime.getTime() + simulationDurationHours * 60 * 60 * 1000)
                  let currentDay = new Date(startTime)
                  currentDay.setHours(0, 0, 0, 0)
                  if (currentDay.getTime() < startTime.getTime()) currentDay.setDate(currentDay.getDate() + 1)
                  while (currentDay.getTime() <= endTime.getTime()) {
                    lines.push({
                      xAxis: currentDay.getTime(),
                      lineStyle: { color: '#909399', type: 'dashed', width: 1 },
                      label: { show: false }
                    })
                    currentDay.setDate(currentDay.getDate() + 1)
                  }
                }
                return lines
              })()
            ]
          }
        },
        {
          name: 'Actual Delivery',
          type: 'line',
          yAxisIndex: 1,
          data: [],
          showSymbol: false,
          smooth: false,
          symbol: 'circle',
          symbolSize: 6,
          itemStyle: {
            color: '#67c23a',
            borderWidth: 2,
            borderColor: '#fff'
          },
          lineStyle: { width: 2, color: '#67c23a' }
        }
      ]
    })

    const loadOtherData = async () => {
      try {
        const res = await otherDataAPI.getOtherData(patientInfo.id)
        if (res.data) {
          Object.assign(otherData, res.data)
        }
      } catch (error) {
        console.error('Failed to load other data:', error)
      }
    }

    onMounted(async () => {
      // 初始化图表
      if (bgCgmChart.value) {
        bgCgmChartInstance = echarts.init(bgCgmChart.value)
        bgCgmChartInstance.setOption(getBgCgmChartOption())
      }
      if (choCobChart.value) {
        choCobChartInstance = echarts.init(choCobChart.value)
        choCobChartInstance.setOption(getChoCobChartOption())
      }
      if (insulinIobChart.value) {
        insulinIobChartInstance = echarts.init(insulinIobChart.value)
        insulinIobChartInstance.setOption(getInsulinIobChartOption())
      }
      if (motorChart.value) {
        motorChartInstance = echarts.init(motorChart.value)
        motorChartInstance.setOption(getPwmChartOption())
      }

      // 监听窗口大小变化
      window.addEventListener('resize', () => {
        bgCgmChartInstance?.resize()
        choCobChartInstance?.resize()
        insulinIobChartInstance?.resize()
        motorChartInstance?.resize()
      })

      // 加载初始数据
      const { simulation_id, mode } = route.query

      // 如果是创建模式，立即打开编辑对话框，无需等待数据加载
      if (mode === 'create') {
        openEditDialog()
      }

      startBaseDataConnection()
      await loadOtherData()

      if (simulation_id && mode === 'view') {
        await loadHistorySimulation(parseInt(simulation_id))
      }
    })

    watch(showPwmChart, (val) => {
      if (val) {
        nextTick(() => {
          motorChartInstance?.resize()
        })
      }
    })

    // 计算 CGM 统计数据
    const cgmStats = computed(() => {
      // 确定数据源：如果是历史模式，使用当前窗口的数据；如果是实时模式，使用 baseData
      let data = []
      if (historyMode.value) {
        // 历史模式下，使用当前选中的一天的窗口数据
        if (historyData.cgm && historyData.cgm.length > 0) {
          const DAY_WINDOW_MS = 24 * 60 * 60 * 1000
          let windowStart, windowEnd
          if (historyDays.value.length > 0) {
            const startTime = historyData.cgm[0][0]
            windowStart = startTime + selectedDayIndex.value * DAY_WINDOW_MS
            windowEnd = windowStart + DAY_WINDOW_MS
          } else {
            // 默认取全部
            windowStart = 0
            windowEnd = Date.now() * 2
          }
          data = historyData.cgm.filter(([t]) => t >= windowStart && t <= windowEnd).map(d => d[1])
        }
      } else {
        // 实时模式，使用所有累积的数据
        if (baseData.cgm && baseData.cgm.length > 0) {
          data = baseData.cgm.map(d => d[1])
        }
      }

      if (!data || data.length === 0) {
        return {
          average: '--',
          gmi: '--',
          cv: '--',
          tir: 0,
          tbr: 0,
          tar: 0,
          count: 0
        }
      }

      // 过滤掉无效值 (null/undefined)
      const validData = data.filter(v => v !== null && v !== undefined)
      const count = validData.length
      if (count === 0) return { average: '--', gmi: '--', cv: '--', tir: 0, tbr: 0, tar: 0, count: 0 }

      // 计算平均值
      const sum = validData.reduce((a, b) => a + b, 0)
      const avg = sum / count

      // 计算标准差
      const squareDiffs = validData.map(v => Math.pow(v - avg, 2))
      const avgSquareDiff = squareDiffs.reduce((a, b) => a + b, 0) / count
      const stdDev = Math.sqrt(avgSquareDiff)

      // 计算 CV (变异系数)
      const cv = (stdDev / avg) * 100

      // 计算 GMI (Glucose Management Indicator)
      // Formula: GMI(%) = 3.31 + 0.02392 * mean(mg/dL)
      const gmi = 3.31 + 0.02392 * avg

      // 计算 TIR (Time In Range)
      // Range: 70 - 180 mg/dL
      const lowCount = validData.filter(v => v < 70).length
      const highCount = validData.filter(v => v > 180).length
      const inRangeCount = count - lowCount - highCount

      return {
        average: avg.toFixed(0),
        gmi: gmi.toFixed(1) + '%',
        cv: cv.toFixed(1) + '%',
        tir: ((inRangeCount / count) * 100).toFixed(1),
        tbr: ((lowCount / count) * 100).toFixed(1),
        tar: ((highCount / count) * 100).toFixed(1),
        count
      }
    })

    return {
      cgmStats,
      patientInfo,
      robotColor,
      isEditing,
      dialogVisible,
      openEditDialog,
      savePatientInfoDialog,
      editForm,
      toggleEdit,
      savePatientInfo,
      paramSettings,
      simulating,
      isSimulationRunning,
      bgCgmChart,
      choCobChart,
      insulinIobChart,
      motorChart,
      toggleSeries,
      historyMode,
      fromHistory,
      exitHistoryMode,
      currentViewIndex,
      maxHistoryIndex,
      historyData,
      onHistorySliderChange,
      timeRange,
      formatTime,
      onTimeRangeChange,
      refreshData,
      otherData,
      connectionStatus,
      dbConnectionStatus,
      tcpConnectionStatus,
      dataSaveStatus,
      currentSimulationId,
      baseData,
      hardwareData,
      handleNavigate,
      handleOpenSettings,
      simulationStatusText,
      showSimulationDetails,
      showPwmChart,
      handleDeleteSimulation,
      selectDay,
      historyDays,
      selectedDayIndex,
      dayStartIndex,
      dayEndIndex,
      currentViewTimeLabel,
      // History Window Drag
      historyWindowStyle,
      startDragHistoryWindow
    }
  }
}
</script>

<style scoped>
.day-selector {
  margin-bottom: 15px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.day-buttons {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.patient-info-card {
  margin-bottom: 15px;
}

.patient-info-content {
  display: flex;
  justify-content: space-between;
  align-items: stretch;
}

.patient-avatar {
  width: 180px;
  height: 240px;
  margin-left: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f0f2f5;
  border-radius: 12px;
  padding: 0;
  border: 1px solid #dcdfe6;
  box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.05);
  overflow: hidden;
  position: relative;
}

/* 
  调整此处的 scale 值可以缩放图片大小 
  scale(1.0) = 原始大小
  scale(1.2) = 放大 20%
  translate(x, y) = 平移位置
*/
.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  transform: scale(1.3) translateY(10px);
  transition: transform 0.3s ease;
}

.patient-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 12px;
  padding: 5px 0;
}

.detail-item {
  display: flex;
  flex-direction: column;
  position: relative;
  padding-left: 10px;
}

.detail-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 5px;
  bottom: 5px;
  width: 3px;
  background-color: #e4e7ed;
  border-radius: 2px;
}

.detail-item:hover::before {
  background-color: #409eff;
}

.detail-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
}

.detail-value {
  font-size: 18px;
  font-weight: 700;
  color: #303133;
  line-height: 1.4;
}

.status-running {
  color: #67c23a;
}

.status-completed {
  color: #409eff;
}

.status-idle {
  color: #909399;
}

/* 编辑区按钮（左侧）保持原来横向 */
.action-buttons {
  margin-top: 15px;
  display: flex;
  gap: 10px;
}

.action-buttons .el-button {
  flex: 1;
}

/* 卡片通用样式（与 VPatientsMonitor 保持一致） */
.card {
  background: #fff;
  border: 1px solid #e0e6ed;
  /* 更柔和的边框 */
  border-radius: 6px;
  /* 稍微锐利一点的圆角，更符合医疗设备风格 */
  padding: 12px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
  /* 极简阴影 */
  width: 100%;
  box-sizing: border-box;
  position: relative;
}

/* 顶部强调条，增加专业感 */
.card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: #409eff;
  border-radius: 6px 6px 0 0;
  opacity: 0.8;
}

.card h4 {
  font-size: 1em;
  margin: 8px 0 12px 0;
  /* 调整间距 */
  color: #2c3e50;
  /* 深色标题 */
  font-weight: 600;
  display: flex;
  align-items: center;
}

/* 标题前的装饰块 */
.card h4::before {
  content: '';
  display: inline-block;
  width: 4px;
  height: 14px;
  background: #409eff;
  margin-right: 8px;
  border-radius: 2px;
}

.card h5 {
  font-size: 0.85em;
  margin: 8px 0 5px 0;
  color: #7f8c8d;
  /* 柔和的副标题颜色 */
  font-weight: 500;
  text-transform: uppercase;
  /* 大写增加技术感 */
  letter-spacing: 0.5px;
}

/* 响应式卡片标题 */
@media (max-width: 1200px) {
  .card {
    padding: 8px;
  }

  .card h4 {
    font-size: 0.95em;
    margin-bottom: 8px;
  }

  .card h5 {
    font-size: 0.85em;
  }
}

@media (max-width: 1024px) {
  .card {
    padding: 6px;
  }

  .card h4 {
    font-size: 0.9em;
    margin-bottom: 6px;
  }

  .card h5 {
    font-size: 0.8em;
  }
}

.chart-container {
  padding: 10px;
  background: #f7f9fc;
  /* 浅蓝灰色背景，营造医疗设备屏幕感 */
  border: 1px solid #cfd7e6;
  border-radius: 6px;
  flex-direction: column;
  height: 30%;
  min-height: 200px;
  width: 100%;
  box-sizing: border-box;
  position: relative;
  box-shadow: inset 2px 2px 5px rgba(0, 0, 0, 0.05), inset -2px -2px 5px rgba(255, 255, 255, 0.8);
  /* 内阴影效果 */
}

/* 移除之前的左侧强调条，因为现在整体已经是屏幕风格 */
.chart-container::after {
  display: none;
}

.chart-container h4 {
  margin: 0 0 8px 0;
  font-size: 0.95em;
  font-weight: 600;
  color: #2c3e50;
  letter-spacing: 0.5px;

  padding-left: 5px;
  /* 稍微缩进 */
}

.chart {
  width: 100%;
  height: 100%;
  /* 填满屏幕容器 */
  min-height: 200px;
}

/* 主图表屏幕样式 - 已移至底部统一管理 */


/* 调整图表容器高度以适应新布局 */
.chart-container {
  padding: 12px;
  /* 增加内边距 */
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  height: 32%;
  /* 稍微增加高度占比 */
  min-height: 240px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

/* 布局：左-中-右 三栏 - 使用固定宽度侧边栏 */
.data-section {
  display: grid;
  grid-template-columns: 380px 1fr 380px;
  gap: 20px;
  align-items: start;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

/* 响应式布局：大屏幕优化 */
@media (min-width: 1800px) {
  .data-section {
    grid-template-columns: 420px 1fr 420px;
    gap: 25px;
  }

  .chart {
    height: 320px;
  }
}

/* 响应式布局：中等屏幕 - 缩小侧边栏 */
@media (max-width: 1600px) {
  .data-section {
    grid-template-columns: 340px 1fr 340px;
    gap: 15px;
  }
}

/* 响应式布局：笔记本屏幕 - 进一步缩小 */
@media (max-width: 1400px) {
  .data-section {
    grid-template-columns: 300px 1fr 300px;
    gap: 12px;
  }

  .chart {
    height: 240px;
  }

  .patient-avatar {
    width: 140px;
    height: 180px;
  }
}

/* 响应式布局：小屏幕 - 变为两列布局 (左+中，右侧下沉) 或 单列 */
@media (max-width: 1200px) {
  .data-section {
    grid-template-columns: 300px 1fr;
    grid-template-rows: auto auto;
  }

  .data-right {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 15px;
  }

  .card {
    padding: 10px;
  }
}

/* 响应式布局：平板 - 单列布局 */
@media (max-width: 900px) {
  .data-section {
    display: flex;
    flex-direction: column;
    gap: 15px;
  }

  .data-right {
    display: flex;
    flex-direction: column;
  }

  .chart {
    height: 240px;
  }
}

.data-left,
.data-right {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  min-width: 0;
  /* 允许缩小 */
}

.data-center {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  min-width: 0;
  overflow: hidden;
  /* 防止图表撑开容器 */
}

/* 时间滑块样式一致化 */
.time-slider {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  background: #fff;
  border: 1px solid #eaeaea;
  border-radius: 6px;
  width: 100%;
  box-sizing: border-box;
}

.vital-signs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 20px;
  /* 列间距 */
}

.vital-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  /* 增加垂直间距 */
  border-bottom: 1px solid #ebeef5;
  font-size: 0.9em;
}

.vital-label {
  font-size: 0.9em;
  color: #909399;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}

.vital-value {
  font-size: 1.1em;
  /* 放大数值 */
  font-weight: 600;
  color: #2c3e50;
  white-space: nowrap;
  font-family: Consolas, Monaco, monospace;
  /* 使用等宽字体显示数值 */
}

/* 其他信息/系统状态样式 */
.other-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.status-indicators-row {
  display: flex;
  justify-content: space-between;
  gap: 4px;
  margin-bottom: 4px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  border-bottom: 1px solid #f0f0f0;
  font-size: 0.9em;
}

.info-item.compact {
  flex-direction: column;
  align-items: center;
  border-bottom: none;
  padding: 0;
  flex: 1;
  text-align: center;
}

.info-item.compact .info-label {
  font-size: 0.85em;
  margin-bottom: 4px;
  color: #888;
  max-width: 100%;
}

.info-item:last-child {
  border-bottom: none;
}

.info-item .info-label {
  color: #666;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 0 0 auto;
  max-width: 50%;
}

.info-item .info-value {
  color: #333;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  justify-content: flex-end;
}

/* 状态指示点样式 */
.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
  animation: pulse 2s infinite;
}

.status-dot.connected {
  background-color: #67c23a;
}

.status-dot.connecting {
  background-color: #e6a23c;
}

.status-dot.disconnected {
  background-color: #f56c6c;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(103, 194, 58, 0.7);
  }

  70% {
    box-shadow: 0 0 0 8px rgba(103, 194, 58, 0);
  }

  100% {
    box-shadow: 0 0 0 0 rgba(103, 194, 58, 0);
  }
}

/* 历史数据滑块样式 */
.history-slider-section {
  margin-top: 20px;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  color: white;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.history-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.history-actions {
  display: flex;
  gap: 10px;
}

.slider-info {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
  font-size: 14px;
}

.info-label {
  font-weight: 500;
  opacity: 0.9;
}

.info-value {
  font-weight: 700;
  background: rgba(255, 255, 255, 0.2);
  padding: 4px 12px;
  border-radius: 6px;
}

.rotate-icon {
  transform: rotate(180deg);
  transition: transform 0.3s ease;
}

/* 硬件监控卡片样式 */
.hardware-monitor-card {
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  padding: 10px;
  margin-top: 0px;
  flex: none;
  display: flex;
  flex-direction: column;
  height: fit-content;
  position: relative;
}

/* 移除之前的左边框样式，统一使用顶部条 */
.hardware-monitor-card h4 {
  margin: 5px 0 15px 0;
  color: #2c3e50;
  font-size: 15px;
  border-left: none;
  padding-left: 0;
  display: flex;
  align-items: center;
}

.hardware-monitor-card h4::before {
  content: '';
  display: inline-block;
  width: 4px;
  height: 14px;
  background: #409eff;
  margin-right: 8px;
  border-radius: 2px;
}

.hardware-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.info-item {
  flex: 1;
  background: #f0f2f5;
  /* 更深的背景色增加对比 */
  padding: 6px 10px;
  border-radius: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid #e4e7ed;
  /* 增加微弱边框 */
}

.info-item .label {
  color: #606266;
  font-size: 11px;
  font-weight: 500;
}

.info-item .value {
  color: #303133;
  font-weight: 700;
  font-size: 13px;
  font-family: Consolas, Monaco, monospace;
}

.status-active {
  color: #67c23a !important;
}

.hardware-chart-container {
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
}

.hardware-chart-container h5 {
  margin: 0 0 8px 0;
  font-size: 12px;
  color: #909399;
  text-align: center;
  font-weight: normal;
  letter-spacing: 1px;
}

.motor-chart {
  flex: 1;
  width: 100%;
  min-height: 160px;
}

/* 监视器屏幕样式 - 优化立体感 */
.monitor-screen {
  background-color: #f5f7fa;
  /* 浅色背景，高对比度 */
  border: 2px solid #dcdfe6;
  border-radius: 4px;
  box-shadow: inset 0 0 8px rgba(0, 0, 0, 0.05);
  /* 柔和的内阴影 */
  padding: 5px;
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

/* 屏幕反光效果 - 减弱 */
.monitor-screen::after {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: linear-gradient(to bottom right,
      rgba(255, 255, 255, 0.4) 0%,
      rgba(255, 255, 255, 0) 40%,
      rgba(255, 255, 255, 0) 100%);
  pointer-events: none;
  opacity: 0.3;
}

.monitor-screen::before {
  display: none;
}

/* 主图表屏幕样式 */
.main-chart-screen {
  background-color: #f5f7fa;
  padding: 0;
  border: 2px solid #dcdfe6;
  box-shadow: inset 0 0 8px rgba(0, 0, 0, 0.05);
}

/* 图表头部样式 */
.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.chart-header h4 {
  margin: 0;
}

/* 自定义图例样式 */
.custom-legend {
  display: flex;
  gap: 15px;
  margin-right: 5px;
}

.legend-item {
  display: flex;
  align-items: center;
  cursor: pointer;
  font-size: 12px;
  color: #606266;
  user-select: none;
  transition: opacity 0.2s;
}

.legend-item:hover {
  opacity: 0.8;
}

.legend-marker {
  width: 25px;
  height: 14px;
  border-radius: 3px;
  margin-right: 6px;
  display: inline-block;
}

/* 弹窗背景模糊效果 */
:deep(.el-overlay) {
  backdrop-filter: blur(5px);
  background-color: rgba(0, 0, 0, 0.3);
}

/* 治疗统计卡片样式 */
.therapy-stats-card {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  padding: 15px;
  display: flex;
  flex-direction: column;
}

.therapy-stats-card h4 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #303133;
  border-left: 4px solid #409eff;
  padding-left: 10px;
}

.stats-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.tir-chart-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tir-bar-wrapper {
  height: 20px;
  background-color: #f0f2f5;
  border-radius: 10px;
  overflow: hidden;
  width: 100%;
}

.tir-bar {
  display: flex;
  height: 100%;
  width: 100%;
}

.tir-segment {
  height: 100%;
  transition: width 0.5s ease;
}

.tir-segment.high {
  background-color: #f39c12;
  /* Yellow/Orange */
}

.tir-segment.in-range {
  background-color: #2ecc71;
  /* Green */
}

.tir-segment.low {
  background-color: #e74c3c;
  /* Red */
}

.tir-legend {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #606266;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.dot.high {
  background-color: #f39c12;
}

.dot.in-range {
  background-color: #2ecc71;
}

.dot.low {
  background-color: #e74c3c;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  background-color: #f9fafc;
  padding: 10px;
  border-radius: 6px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-label {
  font-size: 12px;
  color: #909399;
}

.stat-value {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

.stat-value small {
  font-size: 12px;
  font-weight: normal;
  color: #909399;
}

/* 合并后的图表容器样式 */
.combined-chart-container {
  height: 38% !important;
  /* 增加高度 */
  min-height: 360px !important;
  display: flex;
  flex-direction: column;
  padding: 8px 12px !important;
  gap: 4px;
}

.chart-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  /* 允许flex子项收缩 */
  overflow: hidden;
}

.compact-header {
  margin-bottom: 2px !important;
  min-height: 22px;
  flex-shrink: 0;
  /* 防止标题被压缩 */
}

.compact-header h4 {
  font-size: 0.85em !important;
  margin: 0 !important;
}

.compact-screen {
  flex: 1;
  min-height: 0 !important;
  /* 关键：允许高度收缩 */
  border-width: 1px !important;
  /* 减细边框 */
  padding: 2px !important;
  display: flex;
  flex-direction: column;
}

.compact-screen .chart {
  flex: 1;
  width: 100%;
  height: 100% !important;
  min-height: 120px !important;
  /* 确保有最小高度 */
}

.chart-divider {
  height: 1px;
  background-color: #ebeef5;
  margin: 4px 0;
  width: 100%;
}
</style>