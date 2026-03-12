<template>
  <!-- 患者列表页面 - 图5对应的界面 -->
  <div class="main-container">
    <!-- 左侧导航栏 -->
    <Sidebar :currentRoute="'patients_info'" @navigate="handleNavigate" @open-settings="handleOpenSettings" />

    <!-- 主内容区域 -->
    <div class="main-content">
      <!-- 顶部用户信息栏 -->
      <Header />

      <!-- 内容区域 -->
      <div class="content">
        <!-- 患者分类选择按钮 -->
        <!-- <div class="category-tabs">
          <el-button :type="activeCategory === 'all' ? 'primary' : 'default'" @click="setCategory('all')">
            所有患者
          </el-button>
          <el-button :type="activeCategory === 'real' ? 'primary' : 'default'" @click="setCategory('real')">
            真实患者
          </el-button>
          <el-button :type="activeCategory === 'virtual' ? 'primary' : 'default'" @click="setCategory('virtual')">
            虚拟患者
          </el-button>
        </div> -->

        <!-- 搜索和筛选栏 -->
        <div class="search-bar">
          <div class="search-section">
            <el-input v-model="searchQuery" placeholder="搜索患者姓名、ID等" clearable @input="handleSearch"
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

            <el-button :type="activeCategory === 'all' ? 'primary' : 'default'" @click="setCategory('all')">
              所有患者
            </el-button>
            <el-button :type="activeCategory === 'real' ? 'primary' : 'default'" @click="setCategory('real')">
              真实患者
            </el-button>
            <el-button :type="activeCategory === 'virtual' ? 'primary' : 'default'" @click="setCategory('virtual')">
              虚拟患者
            </el-button>
          </div>
        </div>

        <!-- 患者信息表格 -->
        <div class="patients-table">
          <el-table :data="filteredPatients" stripe style="width: 100%" max-height="calc(100vh - 300px)"
            v-loading="loading">
            <!-- 患者ID列 -->
            <el-table-column prop="id" label="患者ID" width="120" fixed="left" />

            <!-- 患者姓名列 -->
            <el-table-column prop="name" label="患者姓名" width="120" />

            <!-- 患者类型列 -->
            <el-table-column prop="type" label="类型" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.type === '真实患者' ? 'success' : 'info'" size="small">
                  {{ scope.row.type }}
                </el-tag>
              </template>
            </el-table-column>

            <!-- 年龄列 -->
            <el-table-column prop="age" label="年龄" width="80">
              <template #default="scope">
                {{ scope.row.age || '--' }}
              </template>
            </el-table-column>

            <!-- 性别列 -->
            <el-table-column prop="gender" label="性别" width="80">
              <template #default="scope">
                {{ scope.row.gender || '--' }}
              </template>
            </el-table-column>

            <!-- 血型列 -->
            <el-table-column prop="bloodType" label="血型" width="80">
              <template #default="scope">
                {{ scope.row.bloodType || '--' }}
              </template>
            </el-table-column>

            <!-- 最后更新时间列 -->
            <el-table-column prop="lastUpdate" label="最后更新" width="160">
              <template #default="scope">
                {{ formatDateTime(scope.row.lastUpdate) }}
              </template>
            </el-table-column>

            <!-- 状态列 -->
            <el-table-column prop="status" label="状态" width="100">
              <template #default="scope">
                <el-tag :type="getStatusTagType(scope.row.status)" size="small">
                  {{ scope.row.status }}
                </el-tag>
              </template>
            </el-table-column>

            <!-- 操作列 -->
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="scope">
                <el-button type="primary" size="small" @click="checkPatient(scope.row)">
                  查看
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 分页组件 -->
          <!-- :page-sizes="[10, 20, 50, 100]" -->
          <div class="pagination">
            <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :total="totalPatients"
              :page-sizes="[20]" layout="total, sizes, prev, pager, next, jumper" @size-change="handleSizeChange"
              @current-change="handleCurrentChange" />
          </div>
        </div>
      </div>
    </div>

    <!-- 患者详情弹窗 -->
    <el-dialog v-model="showPatientDetail" title="患者详细信息" width="500px">
      <div v-if="selectedPatient" class="patient-detail">
        <div class="detail-row">
          <span class="detail-label">患者ID:</span>
          <span class="detail-value">{{ selectedPatient.id }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">患者姓名:</span>
          <span class="detail-value">{{ selectedPatient.name }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">类型:</span>
          <span class="detail-value">
            <el-tag :type="selectedPatient.type === '真实患者' ? 'success' : 'info'">
              {{ selectedPatient.type }}
            </el-tag>
          </span>
        </div>
        <div class="detail-row">
          <span class="detail-label">年龄:</span>
          <span class="detail-value">{{ selectedPatient.age || '--' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">性别:</span>
          <span class="detail-value">{{ selectedPatient.gender || '--' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">血型:</span>
          <span class="detail-value">{{ selectedPatient.bloodType || '--' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">状态:</span>
          <span class="detail-value">
            <el-tag :type="getStatusTagType(selectedPatient.status)">
              {{ selectedPatient.status }}
            </el-tag>
          </span>
        </div>
        <div class="detail-row">
          <span class="detail-label">创建时间:</span>
          <span class="detail-value">{{ formatDateTime(selectedPatient.createTime) }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">最后更新:</span>
          <span class="detail-value">{{ formatDateTime(selectedPatient.lastUpdate) }}</span>
        </div>
      </div>

      <template #footer>
        <el-button @click="showPatientDetail = false">关闭</el-button>
        <el-button type="primary" @click="goToMonitor">
          进入监控页面
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { patientsAPI } from '@/api'
import Sidebar from '@/components/Sidebar.vue'
import Header from '@/components/Header.vue'
import { Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'TotalPatientsList',
  components: {
    Sidebar,
    Header,
    Search
  },
  setup() {
    const router = useRouter()

    // 响应式数据
    const loading = ref(false)
    const activeCategory = ref('all') // 当前选中的患者类别
    const searchQuery = ref('') // 搜索关键词
    const currentPage = ref(1) // 当前页码
    const pageSize = ref(20) // 每页显示数量
    const totalPatients = ref(0) // 总患者数
    const showPatientDetail = ref(false) // 是否显示患者详情弹窗
    const selectedPatient = ref(null) // 选中的患者

    // 患者列表数据
    const patientsList = ref([])

    // 处理导航
    const handleNavigate = (routeName) => {
      console.log('导航到:', routeName)
    }

    // 处理设置
    const handleOpenSettings = () => {
      console.log('打开设置')
    }

    // 设置患者类别
    const setCategory = (category) => {
      activeCategory.value = category
      currentPage.value = 1
      loadPatients()
    }

    // 处理搜索
    const handleSearch = () => {
      currentPage.value = 1
      loadPatients()
    }

    // 重置搜索
    const resetSearch = () => {
      searchQuery.value = ''
      currentPage.value = 1
      loadPatients()
    }

    // 处理页面大小改变
    const handleSizeChange = (newSize) => {
      pageSize.value = newSize
      currentPage.value = 1
      loadPatients()
    }

    // 处理当前页改变
    const handleCurrentChange = (newPage) => {
      currentPage.value = newPage
      loadPatients()
    }

    // 查看患者详情
    const checkPatient = (patient) => {
      selectedPatient.value = patient
      showPatientDetail.value = true
    }

    // 进入监控页面
    const goToMonitor = () => {
      if (!selectedPatient.value) return

      const patient = selectedPatient.value
      const routeName = patient.type === '真实患者'
        ? 'true-patients-monitor'
        : 'v-patients-monitor'

      showPatientDetail.value = false
      router.push(`/${routeName}/${patient.id}`)
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
          minute: '2-digit'
        })
      } catch (error) {
        return '--'
      }
    }

    // 获取状态标签类型
    const getStatusTagType = (status) => {
      switch (status) {
        case '在线':
          return 'success'
        case '离线':
          return 'info'
        case '仿真中':
          return 'warning'
        case '异常':
          return 'danger'
        default:
          return 'info'
      }
    }

    // 计算过滤后的患者列表
    const filteredPatients = computed(() => {
      let filtered = [...patientsList.value]

      // 按类别过滤
      if (activeCategory.value !== 'all') {
        const filterType = activeCategory.value === 'real' ? '真实患者' : '虚拟患者'
        filtered = filtered.filter(patient => patient.type === filterType)
      }

      // 按搜索关键词过滤
      if (searchQuery.value.trim()) {
        const query = searchQuery.value.toLowerCase().trim()
        filtered = filtered.filter(patient =>
          patient.name?.toLowerCase().includes(query) ||
          patient.id?.toLowerCase().includes(query) ||
          patient.type?.toLowerCase().includes(query)
        )
      }

      // 更新总数
      totalPatients.value = filtered.length

      // 分页
      const start = (currentPage.value - 1) * pageSize.value
      const end = start + pageSize.value
      return filtered.slice(start, end)
    })

    // 加载患者列表
    const loadPatients = async () => {
      loading.value = true
      try {
        let apiCall

        switch (activeCategory.value) {
          case 'real':
            apiCall = patientsAPI.getRealPatients()
            break
          case 'virtual':
            apiCall = patientsAPI.getVirtualPatients()
            break
          default:
            apiCall = patientsAPI.getAllPatients()
        }

        const response = await apiCall
        patientsList.value = response.data || response

      } catch (error) {
        console.error('加载患者列表失败:', error)
        ElMessage.error('加载患者列表失败')

        // 使用模拟数据
        loadMockPatients()
      } finally {
        loading.value = false
      }
    }

    // 加载模拟患者数据
    const loadMockPatients = () => {
      const mockPatients = []

      // 真实患者模拟数据
      for (let i = 1; i <= 15; i++) {
        mockPatients.push({
          id: `TP${String(i).padStart(3, '0')}`,
          name: `真实患者${i}`,
          type: '真实患者',
          age: Math.floor(Math.random() * 60) + 20,
          gender: Math.random() > 0.5 ? '男' : '女',
          bloodType: ['A', 'B', 'AB', 'O'][Math.floor(Math.random() * 4)],
          status: ['在线', '离线', '异常'][Math.floor(Math.random() * 3)],
          createTime: new Date(Date.now() - Math.random() * 365 * 24 * 60 * 60 * 1000).toISOString(),
          lastUpdate: new Date(Date.now() - Math.random() * 24 * 60 * 60 * 1000).toISOString()
        })
      }

      // 虚拟患者模拟数据
      for (let i = 1; i <= 10; i++) {
        mockPatients.push({
          id: `VP${String(i).padStart(3, '0')}`,
          name: `虚拟患者${i}`,
          type: '虚拟患者',
          age: Math.floor(Math.random() * 50) + 25,
          gender: Math.random() > 0.5 ? '男' : '女',
          bloodType: ['A', 'B', 'AB', 'O'][Math.floor(Math.random() * 4)],
          status: ['仿真中', '离线', '异常'][Math.floor(Math.random() * 3)],
          createTime: new Date(Date.now() - Math.random() * 365 * 24 * 60 * 60 * 1000).toISOString(),
          lastUpdate: new Date(Date.now() - Math.random() * 24 * 60 * 60 * 1000).toISOString()
        })
      }

      patientsList.value = mockPatients
    }

    // 组件挂载时加载数据
    onMounted(() => {
      loadPatients()
    })

    return {
      handleNavigate,
      handleOpenSettings,
      loading,
      activeCategory,
      searchQuery,
      currentPage,
      pageSize,
      totalPatients,
      showPatientDetail,
      selectedPatient,
      filteredPatients,
      setCategory,
      handleSearch,
      resetSearch,
      handleSizeChange,
      handleCurrentChange,
      checkPatient,
      goToMonitor,
      formatDateTime,
      getStatusTagType
    }
  }
}
</script>

<style scoped>
.category-tabs {
  margin-bottom: 20px;
  padding: 15px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  gap: 15px;
}

.search-bar {
  margin-bottom: 20px;
  padding: 15px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.search-section {
  display: flex;
  align-items: center;
  gap: 1%;
  flex-wrap: wrap;
}

.patients-table {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 2%;
  width: 100%;
  box-sizing: border-box;
}

.pagination {
  margin-top: 1%;
  display: flex;
  justify-content: flex-start;
  padding: 1% 1% 0.3%;
  max-width: none;
  width: auto;
  position: relative;
  z-index: 2000;
}

.patient-detail {
  padding: 1% 0;
}

.detail-row {
  display: flex;
  align-items: center;
  padding: 0.8% 0;
  border-bottom: 1px solid #f0f0f0;
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-label {
  width: 35%;
  max-width: 120px;
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

/* 响应式设计 */
@media (max-width: 1400px) {
  .search-section {
    gap: 0.8%;
  }

  .patients-table {
    padding: 1.8%;
  }
}

@media (max-width: 1200px) {
  .search-section {
    gap: 1.2%;
  }

  .patients-table {
    padding: 1.5%;
  }

  .detail-label,
  .detail-value {
    font-size: 0.9em;
  }
}

@media (max-width: 1024px) {
  .search-section {
    gap: 1.5%;
  }

  .patients-table {
    overflow-x: auto;
  }
}

@media (max-width: 768px) {
  .search-section {
    flex-direction: column;
    align-items: stretch;
    gap: 2%;
  }

  .patients-table {
    overflow-x: auto;
    padding: 3%;
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
  .patients-table {
    padding: 4%;
  }

  .detail-label,
  .detail-value {
    font-size: 0.8em;
  }
}
</style>