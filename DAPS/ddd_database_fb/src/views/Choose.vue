<template>
  <!-- 选择页面 - 图1对应的界面 -->
  <div class="main-container">
    <!-- 左侧导航栏 -->
    <Sidebar :currentRoute="'choose'" @navigate="handleNavigate" @open-settings="handleOpenSettings" />

    <!-- 主内容区域 -->
    <div class="main-content">
      <!-- 顶部用户信息栏 -->
      <Header />

      <!-- 内容区域 -->
      <div class="content">
        <div class="page-header">
          <h2>请选择添加患者类型</h2>
          <p>Select Patient Type to Continue</p>
        </div>

        <!-- 选择卡片容器 -->
        <div class="choose-container">
          <!-- 添加真实患者卡片 -->
          <div class="choice-card real-patient" @click="openRealPatientDialog">
            <div class="card-content">
              <div class="card-icon">
                <el-icon size="80">
                  <User />
                </el-icon>
              </div>
              <h3 class="card-title">添加真实患者</h3>
              <p class="card-description">Add Real Patient</p>
              <div class="patient-count-badge">
                当前数量: {{ realPatientCount }}
              </div>
              <div class="card-action">
                <span>点击进入</span>
                <el-icon>
                  <ArrowRight />
                </el-icon>
              </div>
            </div>
          </div>

          <!-- 添加虚拟患者卡片 -->
          <div class="choice-card virtual-patient" @click="navigateToVPatients">
            <div class="card-content">
              <div class="card-icon">
                <el-icon size="80">
                  <Avatar />
                </el-icon>
              </div>
              <h3 class="card-title">添加虚拟患者</h3>
              <p class="card-description">Add Virtual Patient</p>
              <div class="patient-count-badge">
                当前数量: {{ virtualPatientCount }}
              </div>
              <div class="card-action">
                <span>点击进入</span>
                <el-icon>
                  <ArrowRight />
                </el-icon>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加真实患者对话框已移除，改为跳转到监控页面后显示 -->
  </div>
</template>

<script>
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store'
import { ref, onMounted } from 'vue'
import { BaseDataWebSocket } from '@/api/websocket'
import Sidebar from '@/components/Sidebar.vue'
import Header from '@/components/Header.vue'
import { User, Avatar, ArrowRight } from '@element-plus/icons-vue'

export default {
  name: 'Choose',
  components: {
    Sidebar,
    Header,
    User,
    Avatar,
    ArrowRight
  },
  setup() {
    const router = useRouter()
    const userStore = useUserStore()
    const baseDataWS = new BaseDataWebSocket()

    const realPatientCount = ref(0)
    const virtualPatientCount = ref(0)

    // 恢复用户信息
    userStore.restoreUserInfo()

    const openRealPatientDialog = () => {
      // 跳转到监控页面，带上 create=true 参数，不传递 ID 以便后端自动生成
      router.push({
        name: 'TruePatientsMonitor',
        query: { mode: 'create' }
      })
    }

    // 判断是否为虚拟患者 (与SimulationsList.vue保持一致)
    const isVirtualPatient = (row) => {
      return row.patient_type === '虚拟患者' || (row.patient_id && row.patient_id.startsWith('VP'))
    }

    // 获取患者数量 (从仿真列表统计)
    const fetchPatientCounts = async () => {
      try {
        // 连接WebSocket并获取数据
        await new Promise((resolve) => {
          baseDataWS.connect(null, (status) => {
            if (status === 'connected') resolve()
          })
          // 设置超时，如果WebSocket连接太慢，尝试直接获取
          setTimeout(resolve, 1000)
        })

        // 并行获取仿真列表和真实患者列表
        const [simulations, realPatients] = await Promise.all([
          baseDataWS.getSimulationsList().catch(() => []),
          baseDataWS.getRealPatientsList().catch(() => [])
        ])

        // 更新数量
        if (simulations && Array.isArray(simulations)) {
          virtualPatientCount.value = simulations.length
        }
        
        if (realPatients && Array.isArray(realPatients)) {
          realPatientCount.value = realPatients.length
        }

      } catch (error) {
        console.error('Failed to fetch patient counts:', error)
      } finally {
        // 获取完数据后断开连接，避免占用资源
        baseDataWS.disconnect()
      }
    }

    onMounted(() => {
      fetchPatientCounts()
    })

    // 处理导航
    const handleNavigate = (routeName) => {
      console.log('导航到:', routeName)
    }

    // 处理设置
    const handleOpenSettings = () => {
      console.log('打开设置')
    }

    // 导航到真实患者监控页面
    const navigateToTruePatients = () => {
      router.push('/true-patients-monitor')
    }

    // 导航到虚拟患者监控页面
    const navigateToVPatients = () => {
      router.push('/v-patients-monitor')
    }

    return {
      handleNavigate,
      handleOpenSettings,
      navigateToTruePatients,
      navigateToVPatients,
      realPatientCount,
      virtualPatientCount,
      openRealPatientDialog
    }
  }
}
</script>

<style scoped>
.content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  height: 100%;
}

.page-header {
  text-align: center;
  margin-bottom: 50px;
  animation: fadeInDown 0.8s ease;
}

.page-header h2 {
  font-size: 32px;
  color: #2c3e50;
  margin-bottom: 12px;
  font-weight: 600;
  letter-spacing: 1px;
}

.page-header p {
  font-size: 16px;
  color: #909399;
  margin: 0;
  font-weight: 300;
}

.choose-container {
  display: flex;
  gap: 60px;
  justify-content: center;
  align-items: center;
  width: 100%;
  padding: 0 20px;
  box-sizing: border-box;
}

.choice-card {
  width: 380px;
  height: 480px;
  background: white;
  border-radius: 24px;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.04);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  border: 1px solid #fff;
}

.choice-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 6px;
  background: #e4e7ed;
  transition: all 0.3s;
}

.choice-card:hover {
  transform: translateY(-15px);
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.08);
}

.real-patient:hover::before {
  background: #409eff;
}

.virtual-patient:hover::before {
  background: #67c23a;
}

.card-content {
  text-align: center;
  padding: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  z-index: 1;
  width: 100%;
}

.card-icon {
  color: #909399;
  background: #f5f7fa;
  width: 140px;
  height: 140px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  transition: all 0.4s ease;
}

.choice-card:hover .card-icon {
  color: white;
  transform: scale(1.1);
}

.real-patient:hover .card-icon {
  background: linear-gradient(135deg, #409eff, #79bbff);
  box-shadow: 0 10px 25px rgba(64, 158, 255, 0.4);
}

.virtual-patient:hover .card-icon {
  background: linear-gradient(135deg, #67c23a, #95d475);
  box-shadow: 0 10px 25px rgba(103, 194, 58, 0.4);
}

.card-title {
  font-size: 26px;
  font-weight: 700;
  color: #2c3e50;
  margin: 0;
  transition: color 0.3s;
}

.real-patient:hover .card-title {
  color: #409eff;
}

.virtual-patient:hover .card-title {
  color: #67c23a;
}

.card-description {
  font-size: 16px;
  color: #909399;
  margin: 0;
  font-family: 'Segoe UI', sans-serif;
}

.patient-count-badge {
  margin-top: 15px;
  background-color: #f0f9eb;
  color: #67c23a;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  border: 1px solid #e1f3d8;
}

.real-patient .patient-count-badge {
  background-color: #ecf5ff;
  color: #409eff;
  border-color: #d9ecff;
}

.card-action {
  margin-top: 20px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #409eff;
  font-weight: 600;
  font-size: 16px;
  opacity: 0;
  transform: translateY(20px);
  transition: all 0.4s ease;
}

.virtual-patient .card-action {
  color: #67c23a;
}

.choice-card:hover .card-action {
  opacity: 1;
  transform: translateY(0);
}

@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 响应式设计 */
@media (max-width: 1400px) {
  .choose-container {
    gap: 40px;
  }

  .choice-card {
    width: 320px;
    height: 420px;
  }

  .card-icon {
    width: 120px;
    height: 120px;
  }
}

@media (max-width: 1024px) {
  .choose-container {
    flex-direction: column;
    gap: 30px;
    height: auto;
    padding: 40px 20px;
  }

  .choice-card {
    width: 100%;
    max-width: 400px;
    height: 300px;
    flex-direction: row;
    padding: 0 30px;
  }

  .card-content {
    flex-direction: row;
    text-align: left;
    padding: 20px;
    justify-content: space-between;
  }

  .card-icon {
    width: 80px;
    height: 80px;
    margin-bottom: 0;
    margin-right: 20px;
  }

  .card-info {
    flex: 1;
  }

  .card-action {
    display: none;
  }
}
</style>